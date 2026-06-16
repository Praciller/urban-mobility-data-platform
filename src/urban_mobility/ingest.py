from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from urban_mobility.config import get_data_dir
from urban_mobility.download import (
    DEFAULT_SAMPLE_ROWS,
    DownloadError,
    trip_data_path,
    validate_trip_request,
)

KEY_FIELDS = (
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "trip_distance",
    "fare_amount",
    "total_amount",
    "passenger_count",
    "PULocationID",
    "DOLocationID",
)
DATETIME_FIELDS = {
    "pickup": "tpep_pickup_datetime",
    "dropoff": "tpep_dropoff_datetime",
}
NUMERIC_FIELDS = ("trip_distance", "fare_amount", "total_amount")


class ProfileError(RuntimeError):
    """Raised when raw Parquet data cannot be inspected."""


def profile_path(data_dir: Path, year: int, month: int) -> Path:
    return data_dir / "reports" / "data_quality" / f"raw_profile_{year:04d}_{month:02d}.json"


def profile_parquet(path: Path) -> dict[str, Any]:
    resolved_path = path.resolve()
    try:
        with resolved_path.open("rb") as source:
            parquet_file = pq.ParquetFile(source)
            metadata = parquet_file.metadata
            schema = parquet_file.schema_arrow
    except (OSError, ValueError, pa.ArrowException) as exc:
        raise ProfileError(f"Unable to read Parquet file: {path}") from exc

    columns = schema.names
    profile: dict[str, Any] = {
        "source_path": str(resolved_path),
        "created_at": datetime.now(UTC).isoformat(),
        "file_size": resolved_path.stat().st_size,
        "row_count": metadata.num_rows,
        "row_groups": metadata.num_row_groups,
        "column_names": columns,
        "schema": {field.name: str(field.type) for field in schema},
        "null_counts": {},
        "datetime_ranges": {},
        "numeric_stats": {},
    }

    expressions: list[tuple[tuple[str, ...], str]] = []
    for field in KEY_FIELDS:
        if field in columns:
            identifier = _quote_identifier(field)
            expressions.append((("null_counts", field), f"count(*) - count({identifier})"))

    for label, field in DATETIME_FIELDS.items():
        if field in columns:
            identifier = _quote_identifier(field)
            expressions.extend(
                [
                    (("datetime_ranges", label, "min"), f"min({identifier})"),
                    (("datetime_ranges", label, "max"), f"max({identifier})"),
                ]
            )

    for field in NUMERIC_FIELDS:
        if field in columns:
            identifier = _quote_identifier(field)
            expressions.extend(
                [
                    (("numeric_stats", field, "min"), f"min({identifier})"),
                    (("numeric_stats", field, "max"), f"max({identifier})"),
                    (("numeric_stats", field, "avg"), f"avg({identifier})"),
                ]
            )

    if not expressions:
        return profile

    sql = "SELECT " + ", ".join(expression for _, expression in expressions)
    sql += " FROM read_parquet(?)"
    connection = duckdb.connect()
    try:
        values = connection.execute(sql, [str(resolved_path)]).fetchone()
    except duckdb.Error as exc:
        raise ProfileError(f"Unable to calculate Parquet profile: {path}") from exc
    finally:
        connection.close()

    if values is None:
        return profile

    for (keys, _), value in zip(expressions, values, strict=True):
        _set_nested(profile, keys, _json_value(value))
    return profile


def write_profile(path: Path, profile: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    try:
        temporary.write_text(
            json.dumps(profile, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise ProfileError(f"Unable to write profile: {path}") from exc
    return path


def resolve_trip_path(
    data_dir: Path,
    year: int,
    month: int,
    service: str,
    *,
    mode: str = "auto",
    sample_rows: int | None = None,
) -> Path:
    validate_trip_request(year, month, service)
    if mode not in {"auto", "raw", "sample"}:
        raise ValueError("mode must be one of: auto, raw, sample")

    raw = trip_data_path(
        data_dir,
        year,
        month,
        service,
        sample=False,
    )
    sample_directory = trip_data_path(
        data_dir,
        year,
        month,
        service,
        sample=True,
        sample_rows=sample_rows or DEFAULT_SAMPLE_ROWS,
    ).parent

    candidates: list[Path] = []
    if sample_rows is not None:
        candidates.append(
            trip_data_path(
                data_dir,
                year,
                month,
                service,
                sample=True,
                sample_rows=sample_rows,
            )
        )
    elif sample_directory.exists():
        candidates.extend(sorted(sample_directory.glob(f"{service}_tripdata_*_sample_*.parquet")))

    if mode in {"auto", "sample"}:
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        if mode == "sample":
            raise ProfileError(f"No sample Parquet found for {service} {year:04d}-{month:02d}")

    if mode in {"auto", "raw"} and raw.is_file():
        return raw

    raise ProfileError(f"No Parquet found for {service} {year:04d}-{month:02d} under {data_dir}")


def inspect_trip(
    *,
    data_dir: Path,
    year: int,
    month: int,
    service: str,
    mode: str = "auto",
    sample_rows: int | None = None,
) -> dict[str, Any]:
    source = resolve_trip_path(
        data_dir,
        year,
        month,
        service,
        mode=mode,
        sample_rows=sample_rows,
    )
    profile = profile_parquet(source)
    write_profile(profile_path(data_dir, year, month), profile)
    return profile


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _set_nested(
    target: dict[str, Any],
    keys: tuple[str, ...],
    value: Any,
) -> None:
    current = target
    for key in keys[:-1]:
        current = current.setdefault(key, {})
    current[keys[-1]] = value


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect local NYC TLC Parquet data")
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect", help="Write a raw profile report")
    inspect_parser.add_argument("--year", required=True, type=int)
    inspect_parser.add_argument("--month", required=True, type=int)
    inspect_parser.add_argument("--service", default="yellow")
    inspect_parser.add_argument("--mode", choices=("auto", "raw", "sample"), default="auto")
    inspect_parser.add_argument("--sample-rows", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        profile = inspect_trip(
            data_dir=get_data_dir(),
            year=args.year,
            month=args.month,
            service=args.service,
            mode=args.mode,
            sample_rows=args.sample_rows,
        )
    except (DownloadError, ProfileError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(profile, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
