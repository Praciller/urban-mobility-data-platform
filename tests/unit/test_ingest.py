import json
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from urban_mobility.download import trip_data_path
from urban_mobility.ingest import ProfileError, main, profile_parquet, profile_path


def write_profile_fixture(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table(
        {
            "tpep_pickup_datetime": pa.array(
                [datetime(2026, 1, 1), datetime(2026, 1, 1, 1), None],
                type=pa.timestamp("s"),
            ),
            "tpep_dropoff_datetime": pa.array(
                [datetime(2026, 1, 1, 0, 10), datetime(2026, 1, 1, 1, 30), None],
                type=pa.timestamp("s"),
            ),
            "trip_distance": [1.0, 3.0, None],
            "fare_amount": [10.0, 20.0, None],
            "total_amount": [12.5, 25.0, None],
            "passenger_count": [1, 2, None],
            "PULocationID": [100, 101, 102],
            "DOLocationID": [200, 201, 202],
        }
    )
    pq.write_table(table, path)


def test_profiles_parquet_metadata_and_key_statistics(tmp_path: Path) -> None:
    parquet_path = tmp_path / "fixture.parquet"
    write_profile_fixture(parquet_path)

    profile = profile_parquet(parquet_path)

    assert profile["row_count"] == 3
    assert profile["column_names"] == [
        "tpep_pickup_datetime",
        "tpep_dropoff_datetime",
        "trip_distance",
        "fare_amount",
        "total_amount",
        "passenger_count",
        "PULocationID",
        "DOLocationID",
    ]
    assert profile["null_counts"]["tpep_pickup_datetime"] == 1
    assert profile["datetime_ranges"]["pickup"]["min"] == "2026-01-01T00:00:00"
    assert profile["datetime_ranges"]["dropoff"]["max"] == "2026-01-01T01:30:00"
    assert profile["numeric_stats"]["trip_distance"] == {
        "min": 1.0,
        "max": 3.0,
        "avg": 2.0,
    }
    assert profile["numeric_stats"]["total_amount"]["avg"] == 18.75


def test_profile_rejects_unreadable_parquet(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.parquet"
    invalid.write_text("not parquet", encoding="utf-8")

    with pytest.raises(ProfileError, match="Unable to read Parquet"):
        profile_parquet(invalid)


def test_inspect_cli_uses_sample_and_writes_profile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sample = trip_data_path(tmp_path, 2026, 1, "yellow", sample=True, sample_rows=1000)
    write_profile_fixture(sample)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    result = main(["inspect", "--year", "2026", "--month", "1", "--service", "yellow"])

    assert result == 0
    report_path = profile_path(tmp_path, 2026, 1)
    assert report_path.is_file()
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved["source_path"] == str(sample)
    assert '"row_count": 3' in capsys.readouterr().out
