import json
from datetime import datetime
from pathlib import Path

import httpx
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from urban_mobility.download import (
    DownloadError,
    DownloadRequest,
    _stream_download,
    build_trip_url,
    build_zone_lookup_url,
    download_trip_data,
    download_zone_lookup,
    manifest_path,
    materialize_sample,
    trip_data_path,
    validate_parquet,
    zone_lookup_path,
)


def write_tiny_parquet(path: Path, rows: int = 3) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table(
        {
            "tpep_pickup_datetime": pa.array(
                [datetime(2026, 1, 1, 0, index) for index in range(rows)],
                type=pa.timestamp("s"),
            ),
            "trip_distance": [float(index + 1) for index in range(rows)],
        }
    )
    pq.write_table(table, path)


def test_builds_official_tlc_urls() -> None:
    assert (
        build_trip_url(2026, 1, "yellow") == "https://d37ci6vzurychx.cloudfront.net/trip-data/"
        "yellow_tripdata_2026-01.parquet"
    )
    assert (
        build_zone_lookup_url() == "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
    )


@pytest.mark.parametrize(
    ("year", "month", "service", "message"),
    [
        (2008, 1, "yellow", "year"),
        (2026, 0, "yellow", "month"),
        (2026, 13, "yellow", "month"),
        (2026, 1, "green", "service"),
    ],
)
def test_rejects_invalid_trip_request(
    year: int,
    month: int,
    service: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        build_trip_url(year, month, service)


def test_builds_partitioned_raw_sample_and_metadata_paths(tmp_path: Path) -> None:
    raw = trip_data_path(tmp_path, 2026, 1, "yellow", sample=False)
    sample = trip_data_path(tmp_path, 2026, 1, "yellow", sample=True)

    assert raw == (
        tmp_path
        / "raw"
        / "tlc"
        / "service=yellow"
        / "year=2026"
        / "month=01"
        / "yellow_tripdata_2026-01.parquet"
    )
    assert sample.parts[-5:] == (
        "tlc",
        "service=yellow",
        "year=2026",
        "month=01",
        "yellow_tripdata_2026-01_sample_1000.parquet",
    )
    assert zone_lookup_path(tmp_path) == tmp_path / "raw" / "tlc" / "taxi_zone_lookup.csv"
    assert manifest_path(tmp_path) == tmp_path / "processed" / "download_manifest.json"


@pytest.mark.filterwarnings("error::DeprecationWarning")
def test_materialize_sample_limits_rows_without_deprecation_warning(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.parquet"
    destination = tmp_path / "sample.parquet"
    write_tiny_parquet(source, rows=3)

    result = materialize_sample(source, destination, sample_rows=2)

    assert result == destination
    assert pq.ParquetFile(destination).metadata.num_rows == 2


def test_stream_download_reports_missing_remote_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    install_mock_http_client(monkeypatch, status_code=404, content=b"missing")

    with pytest.raises(DownloadError, match="Remote file not found"):
        _stream_download("https://example.test/missing.parquet", tmp_path / "missing.parquet")


def test_stream_download_retries_transient_http_status(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    attempts = install_sequence_http_client(
        monkeypatch,
        responses=[(503, b"temporary"), (200, b"downloaded")],
    )
    destination = tmp_path / "download.bin"

    _stream_download("https://example.test/download.bin", destination)

    assert attempts == [503, 200]
    assert destination.read_bytes() == b"downloaded"


def test_stream_download_validates_before_replacing_existing_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    destination = tmp_path / "existing.parquet"
    write_tiny_parquet(destination)
    original = destination.read_bytes()
    install_mock_http_client(monkeypatch, status_code=200, content=b"not parquet")

    with pytest.raises(DownloadError, match="not readable Parquet"):
        _stream_download(
            "https://example.test/invalid.parquet",
            destination,
            validator=validate_parquet,
        )

    assert destination.read_bytes() == original


def test_zone_lookup_replaces_empty_cached_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    destination = zone_lookup_path(tmp_path)
    destination.parent.mkdir(parents=True)
    destination.touch()

    def fake_download(source_url: str, path: Path, **_: object) -> Path:
        assert source_url == build_zone_lookup_url()
        path.write_text("LocationID,Borough,Zone,service_zone\n", encoding="utf-8")
        return path

    monkeypatch.setattr("urban_mobility.download._stream_download", fake_download)

    result = download_zone_lookup(data_dir=tmp_path)

    assert result.status == "downloaded"
    assert result.file_size > 0


def test_downloader_reuses_existing_sample_and_records_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls = 0

    def fake_materialize(source: str, destination: Path, sample_rows: int) -> Path:
        nonlocal calls
        calls += 1
        assert source.endswith("yellow_tripdata_2026-01.parquet")
        assert sample_rows == 2
        write_tiny_parquet(destination, rows=2)
        return destination

    monkeypatch.setattr("urban_mobility.download.materialize_sample", fake_materialize)
    request = DownloadRequest(year=2026, month=1, service="yellow", sample_rows=2)

    downloaded = download_trip_data(request, data_dir=tmp_path)
    reused = download_trip_data(request, data_dir=tmp_path)

    assert downloaded.status == "downloaded"
    assert reused.status == "reused"
    assert calls == 1

    manifest = json.loads(manifest_path(tmp_path).read_text(encoding="utf-8"))
    assert [entry["status"] for entry in manifest["downloads"]] == ["downloaded", "reused"]
    assert manifest["downloads"][0]["sample_row_count"] == 2
    assert manifest["downloads"][0]["sha256"]


def install_mock_http_client(
    monkeypatch: pytest.MonkeyPatch,
    *,
    status_code: int,
    content: bytes,
) -> None:
    original_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, request=request, content=content)

    def client_factory(**kwargs: object) -> httpx.Client:
        kwargs.pop("transport", None)
        return original_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr("urban_mobility.download.httpx.Client", client_factory)


def install_sequence_http_client(
    monkeypatch: pytest.MonkeyPatch,
    *,
    responses: list[tuple[int, bytes]],
) -> list[int]:
    original_client = httpx.Client
    attempts: list[int] = []
    response_iterator = iter(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        status_code, content = next(response_iterator)
        attempts.append(status_code)
        return httpx.Response(status_code, request=request, content=content)

    def client_factory(**kwargs: object) -> httpx.Client:
        kwargs.pop("transport", None)
        return original_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr("urban_mobility.download.httpx.Client", client_factory)
    return attempts
