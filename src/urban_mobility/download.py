from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import duckdb
import httpx
import pyarrow as pa
import pyarrow.parquet as pq

from urban_mobility.config import get_data_dir
from urban_mobility.manifest import ManifestError, append_manifest_entry

TLC_TRIP_BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
TAXI_ZONE_LOOKUP_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
SUPPORTED_SERVICES = frozenset({"yellow"})
MIN_DATASET_YEAR = 2009
MAX_DATASET_YEAR = 2100
DEFAULT_SAMPLE_ROWS = 1000
MAX_DOWNLOAD_ATTEMPTS = 3
RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


class DownloadError(RuntimeError):
    """Raised when a source file cannot be safely materialized."""


@dataclass(frozen=True)
class DownloadRequest:
    year: int
    month: int
    service: str = "yellow"
    sample_rows: int | None = None
    force: bool = False

    def __post_init__(self) -> None:
        validate_trip_request(self.year, self.month, self.service)
        if self.sample_rows is not None and self.sample_rows <= 0:
            raise ValueError("sample_rows must be greater than zero")


@dataclass(frozen=True)
class DownloadResult:
    source_url: str
    local_path: str
    service: str
    year: int | None
    month: int | None
    file_size: int
    status: Literal["downloaded", "reused"]
    created_at: str
    sha256: str
    sample_row_count: int | None = None


def validate_trip_request(year: int, month: int, service: str) -> None:
    if not MIN_DATASET_YEAR <= year <= MAX_DATASET_YEAR:
        raise ValueError(f"year must be between {MIN_DATASET_YEAR} and {MAX_DATASET_YEAR}")
    if not 1 <= month <= 12:
        raise ValueError("month must be between 1 and 12")
    if service not in SUPPORTED_SERVICES:
        allowed = ", ".join(sorted(SUPPORTED_SERVICES))
        raise ValueError(f"service must be one of: {allowed}")


def build_trip_url(year: int, month: int, service: str = "yellow") -> str:
    validate_trip_request(year, month, service)
    return f"{TLC_TRIP_BASE_URL}/{service}_tripdata_{year:04d}-{month:02d}.parquet"


def build_zone_lookup_url() -> str:
    return TAXI_ZONE_LOOKUP_URL


def trip_data_path(
    data_dir: Path,
    year: int,
    month: int,
    service: str = "yellow",
    *,
    sample: bool,
    sample_rows: int = DEFAULT_SAMPLE_ROWS,
) -> Path:
    validate_trip_request(year, month, service)
    if sample_rows <= 0:
        raise ValueError("sample_rows must be greater than zero")

    root = "sample" if sample else "raw"
    stem = f"{service}_tripdata_{year:04d}-{month:02d}"
    filename = f"{stem}_sample_{sample_rows}.parquet" if sample else f"{stem}.parquet"
    return (
        data_dir
        / root
        / "tlc"
        / f"service={service}"
        / f"year={year:04d}"
        / f"month={month:02d}"
        / filename
    )


def zone_lookup_path(data_dir: Path) -> Path:
    return data_dir / "raw" / "tlc" / "taxi_zone_lookup.csv"


def manifest_path(data_dir: Path) -> Path:
    return data_dir / "processed" / "download_manifest.json"


def materialize_sample(
    source: str | Path,
    destination: Path,
    sample_rows: int,
) -> Path:
    """Create a bounded Parquet sample without persisting a DuckDB database."""
    if sample_rows <= 0:
        raise ValueError("sample_rows must be greater than zero")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f"{destination.suffix}.part")
    temporary.unlink(missing_ok=True)

    connection = duckdb.connect()
    try:
        source_text = str(source)
        if source_text.startswith(("http://", "https://")):
            connection.install_extension("httpfs")
            connection.load_extension("httpfs")

        table = connection.execute(
            "SELECT * FROM read_parquet(?) LIMIT ?",
            [source_text, sample_rows],
        ).to_arrow_table()
        pq.write_table(table, temporary)
        validate_parquet(temporary)
        temporary.replace(destination)
    except (DownloadError, duckdb.Error, OSError, pa.ArrowException) as exc:
        temporary.unlink(missing_ok=True)
        raise DownloadError(
            f"Unable to create {sample_rows}-row sample from {source_text}"
        ) from exc
    finally:
        connection.close()

    return destination


def download_trip_data(
    request: DownloadRequest,
    *,
    data_dir: Path | None = None,
) -> DownloadResult:
    resolved_data_dir = (data_dir or get_data_dir()).resolve()
    source_url = build_trip_url(request.year, request.month, request.service)
    sample = request.sample_rows is not None
    sample_rows = request.sample_rows or DEFAULT_SAMPLE_ROWS
    destination = trip_data_path(
        resolved_data_dir,
        request.year,
        request.month,
        request.service,
        sample=sample,
        sample_rows=sample_rows,
    )

    if destination.exists() and not request.force:
        validate_parquet(destination)
        status: Literal["downloaded", "reused"] = "reused"
    else:
        if sample:
            materialize_sample(source_url, destination, sample_rows)
        else:
            _stream_download(source_url, destination, validator=validate_parquet)
        status = "downloaded"

    actual_sample_rows = pq.read_metadata(destination).num_rows if sample else None
    result = _build_result(
        source_url=source_url,
        destination=destination,
        service=request.service,
        year=request.year,
        month=request.month,
        status=status,
        sample_row_count=actual_sample_rows,
    )
    append_manifest_entry(manifest_path(resolved_data_dir), asdict(result))
    return result


def download_zone_lookup(
    *,
    data_dir: Path | None = None,
    force: bool = False,
) -> DownloadResult:
    resolved_data_dir = (data_dir or get_data_dir()).resolve()
    destination = zone_lookup_path(resolved_data_dir)

    if _is_nonempty_file(destination) and not force:
        status: Literal["downloaded", "reused"] = "reused"
    else:
        _stream_download(build_zone_lookup_url(), destination)
        status = "downloaded"

    result = _build_result(
        source_url=build_zone_lookup_url(),
        destination=destination,
        service="taxi_zone_lookup",
        year=None,
        month=None,
        status=status,
        sample_row_count=None,
    )
    append_manifest_entry(manifest_path(resolved_data_dir), asdict(result))
    return result


def validate_parquet(path: Path) -> None:
    try:
        with path.open("rb") as source:
            metadata = pq.read_metadata(source)
    except (OSError, ValueError, pa.ArrowException) as exc:
        raise DownloadError(f"Downloaded file is not readable Parquet: {path}") from exc
    if metadata.num_columns == 0:
        raise DownloadError(f"Parquet file has no columns: {path}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stream_download(
    source_url: str,
    destination: Path,
    *,
    validator: Callable[[Path], None] | None = None,
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(f"{destination.suffix}.part")
    temporary.unlink(missing_ok=True)

    timeout = httpx.Timeout(60.0, connect=15.0)
    transport = httpx.HTTPTransport(retries=2)
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            transport=transport,
        ) as client:
            for attempt in range(1, MAX_DOWNLOAD_ATTEMPTS + 1):
                with client.stream("GET", source_url) as response:
                    if response.status_code == httpx.codes.NOT_FOUND:
                        raise DownloadError(f"Remote file not found: {source_url}")
                    if (
                        response.status_code in RETRYABLE_STATUS_CODES
                        and attempt < MAX_DOWNLOAD_ATTEMPTS
                    ):
                        continue
                    response.raise_for_status()
                    with temporary.open("wb") as output:
                        for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                            output.write(chunk)
                break
        if temporary.stat().st_size == 0:
            raise DownloadError(f"Downloaded file is empty: {source_url}")
        if validator is not None:
            validator(temporary)
        temporary.replace(destination)
    except DownloadError:
        temporary.unlink(missing_ok=True)
        raise
    except (httpx.HTTPError, OSError) as exc:
        temporary.unlink(missing_ok=True)
        raise DownloadError(f"Unable to download {source_url}: {exc}") from exc

    return destination


def _is_nonempty_file(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def _build_result(
    *,
    source_url: str,
    destination: Path,
    service: str,
    year: int | None,
    month: int | None,
    status: Literal["downloaded", "reused"],
    sample_row_count: int | None,
) -> DownloadResult:
    return DownloadResult(
        source_url=source_url,
        local_path=str(destination),
        service=service,
        year=year,
        month=month,
        file_size=destination.stat().st_size,
        status=status,
        created_at=datetime.now(UTC).isoformat(),
        sha256=sha256_file(destination),
        sample_row_count=sample_row_count,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download official NYC TLC data")
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--month", required=True, type=int)
    parser.add_argument("--service", default="yellow")
    parser.add_argument("--sample-rows", type=int)
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        trip = download_trip_data(
            DownloadRequest(
                year=args.year,
                month=args.month,
                service=args.service,
                sample_rows=args.sample_rows,
                force=args.force,
            )
        )
        zones = download_zone_lookup(force=args.force)
    except (DownloadError, ManifestError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"trip": asdict(trip), "zone_lookup": asdict(zones)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
