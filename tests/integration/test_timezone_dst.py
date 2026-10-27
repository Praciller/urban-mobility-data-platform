"""Explicit regressions for NYC TLC wall-clock timestamps and DST limitations.

TLC source timestamps are timezone-naive local times. The pipeline intentionally
does not infer UTC instants, fold values, or nonexistent-time corrections.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from scripts.create_demo_fixture import create_demo_fixture
from urban_mobility.load_duckdb import load_validated_to_duckdb
from urban_mobility.validate import validate_trip_data


@pytest.mark.parametrize(
    ("pickup", "dropoff", "status", "duration", "reason"),
    [
        (datetime(2026, 3, 8, 1, 55), datetime(2026, 3, 8, 3, 5), "valid", 70.0, None),
        (
            datetime(2026, 3, 8, 2, 20),
            datetime(2026, 3, 8, 3, 0),
            "valid",
            40.0,
            None,
        ),  # nonexistent NYC wall time is not detectable
        (
            datetime(2026, 11, 1, 1, 15),
            datetime(2026, 11, 1, 1, 45),
            "valid",
            30.0,
            None,
        ),  # ambiguous repeated hour lacks fold
        (
            datetime(2026, 11, 1, 1, 50),
            datetime(2026, 11, 1, 1, 10),
            "rejected",
            -40.0,
            "pickup_after_dropoff",
        ),
        (datetime(2026, 1, 31, 23, 45), datetime(2026, 2, 1, 0, 15), "valid", 30.0, None),
        (datetime(2026, 1, 1, 23, 50), datetime(2026, 1, 2, 0, 10), "valid", 20.0, None),
        (None, datetime(2026, 1, 1, 8, 30), "rejected", None, "missing_pickup_datetime"),
        (datetime(2026, 1, 1, 8), None, "rejected", None, "missing_dropoff_datetime"),
        (
            "invalid-timestamp",
            datetime(2026, 1, 1, 8, 30),
            "rejected",
            None,
            "missing_pickup_datetime",
        ),
    ],
)
def test_tlc_wall_clock_edge_cases_are_stable_through_load(
    tmp_path: Path,
    pickup: datetime | str | None,
    dropoff: datetime | None,
    status: str,
    duration: float | None,
    reason: str | None,
) -> None:
    month = pickup.month if isinstance(pickup, datetime) else 1
    fixture = create_demo_fixture(
        data_dir=tmp_path, year=2026, month=month, service="yellow", sample_rows=1000
    )
    source = Path(str(fixture["trip_path"]))
    row = pq.read_table(source).to_pylist()[0]
    row.update(tpep_pickup_datetime=pickup, tpep_dropoff_datetime=dropoff)
    pq.write_table(pa.Table.from_pylist([row]), source)

    result = validate_trip_data(
        year=2026, month=month, service="yellow", data_dir=tmp_path, input_path=source
    )
    assert result.summary["status_counts"][status] == 1
    selected = result.validated_path if status != "rejected" else result.rejected_path
    parsed = pq.read_table(selected).to_pylist()[0]
    assert parsed["pickup_datetime"] == (pickup if isinstance(pickup, datetime) else None)
    assert parsed["dropoff_datetime"] == dropoff
    if duration is not None:
        assert parsed["duration_minutes"] == pytest.approx(duration)
    if reason:
        assert reason in parsed["quality_reasons"]

    warehouse = tmp_path / "warehouse.duckdb"
    loaded = load_validated_to_duckdb(
        year=2026,
        month=month,
        service="yellow",
        data_dir=tmp_path,
        duckdb_path=warehouse,
        validated_path=result.validated_path,
    )
    assert loaded.loaded_rows == (0 if status == "rejected" else 1)
    with duckdb.connect(str(warehouse), read_only=True) as db:
        rows = db.execute(
            "select pickup_datetime, dropoff_datetime, duration_minutes, "
            "source_year, source_month from staging.yellow_trips"
        ).fetchall()
    if status != "rejected":
        assert rows == [(pickup, dropoff, pytest.approx(duration), 2026, month)]
    else:
        assert rows == []


def test_event_time_is_not_ingestion_time_and_dst_instant_is_unknowable(
    tmp_path: Path,
) -> None:
    fixture = create_demo_fixture(
        data_dir=tmp_path, year=2026, month=11, service="yellow", sample_rows=1000
    )
    source = Path(str(fixture["trip_path"]))
    row = pq.read_table(source).to_pylist()[0]
    event = datetime(2026, 11, 1, 1, 30)
    row.update(
        tpep_pickup_datetime=event,
        tpep_dropoff_datetime=datetime(2026, 11, 1, 2, 0),
    )
    pq.write_table(pa.Table.from_pylist([row]), source)
    before = datetime.now(UTC)
    result = validate_trip_data(
        year=2026, month=11, service="yellow", data_dir=tmp_path, input_path=source
    )
    after = datetime.now(UTC)
    parsed = pq.read_table(result.validated_path).to_pylist()[0]
    assert parsed["pickup_datetime"] == event
    assert parsed["ingested_at"] != event
    assert before.replace(tzinfo=None, microsecond=0) <= parsed["ingested_at"]
    assert parsed["ingested_at"] <= after.replace(tzinfo=None, microsecond=0)

    ny = ZoneInfo("America/New_York")
    first = event.replace(tzinfo=ny, fold=0).astimezone(UTC)
    second = event.replace(tzinfo=ny, fold=1).astimezone(UTC)
    assert (second - first).total_seconds() == 3600
    # No timezone/fold in the TLC field: the ETL must not silently choose either instant.


def test_wall_clock_grouping_reaches_dbt_and_api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pickup date/hour is preserved in marts and HTTP, including month rollover."""
    import os
    import shutil
    import subprocess

    from fastapi.testclient import TestClient

    from apps.api.app.main import app

    fixture = create_demo_fixture(
        data_dir=tmp_path, year=2026, month=3, service="yellow", sample_rows=1000
    )
    source = Path(str(fixture["trip_path"]))
    prototype = pq.read_table(source).to_pylist()[0]
    first = {
        **prototype,
        "tpep_pickup_datetime": datetime(2026, 3, 8, 1, 55),
        "tpep_dropoff_datetime": datetime(2026, 3, 8, 3, 5),
    }
    second = {
        **prototype,
        "tpep_pickup_datetime": datetime(2026, 3, 31, 23, 50),
        "tpep_dropoff_datetime": datetime(2026, 4, 1, 0, 10),
    }
    pq.write_table(pa.Table.from_pylist([first, second]), source)
    publication = validate_trip_data(
        year=2026, month=3, service="yellow", data_dir=tmp_path, input_path=source
    )
    assert publication.summary["status_counts"]["valid"] == 2
    database = tmp_path / "warehouse.duckdb"
    load_validated_to_duckdb(
        year=2026,
        month=3,
        service="yellow",
        data_dir=tmp_path,
        duckdb_path=database,
        validated_path=publication.validated_path,
    )
    executable = shutil.which("dbt")
    assert executable is not None
    root = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    environment["DUCKDB_PATH"] = str(database)
    environment["DBT_TARGET_PATH"] = str(tmp_path / "dbt-target")
    environment["DBT_LOG_PATH"] = str(tmp_path / "dbt-logs")
    for operation in ("run", "test"):
        completed = subprocess.run(
            [
                executable,
                operation,
                "--project-dir",
                str(root / "dbt"),
                "--profiles-dir",
                str(root / "dbt"),
            ],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
    with duckdb.connect(str(database), read_only=True) as connection:
        grouped = connection.execute(
            "select pickup_date, pickup_hour, duration_minutes from fct_trips order by pickup_date"
        ).fetchall()
    assert grouped == [
        (datetime(2026, 3, 8).date(), 1, 70.0),
        (datetime(2026, 3, 31).date(), 23, 20.0),
    ]
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DUCKDB_PATH", str(database))
    with TestClient(app) as client:
        daily = client.get("/metrics/daily")
        hourly = client.get("/metrics/hourly-demand")
        overview = client.get("/metrics/overview")
    assert daily.status_code == hourly.status_code == overview.status_code == 200
    assert daily.json()["total"] == hourly.json()["total"] == 2
    assert overview.json()["total_trips"] == 2
    assert [(item["pickup_date"], item["pickup_hour"]) for item in hourly.json()["items"]] == [
        ("2026-03-08", 1),
        ("2026-03-31", 23),
    ]
