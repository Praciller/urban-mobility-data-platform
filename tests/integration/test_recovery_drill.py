"""Deterministic offline restore → DuckDB → dbt → API recovery drill."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import app
from scripts.create_demo_fixture import create_demo_fixture
from scripts.manage_publications import restore_revision
from urban_mobility.load_duckdb import load_validated_to_duckdb
from urban_mobility.validate import validate_trip_data
from urban_mobility.validation_store import current_version


def _rebuild_marts(database: Path, scratch: Path) -> None:
    dbt = shutil.which("dbt")
    assert dbt is not None, "dbt executable is required for the recovery drill"
    project = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    environment["DUCKDB_PATH"] = str(database)
    environment["DBT_TARGET_PATH"] = str(scratch / "dbt-target")
    environment["DBT_LOG_PATH"] = str(scratch / "dbt-logs")
    for operation in ("run", "test"):
        finished = subprocess.run(
            [
                dbt,
                operation,
                "--project-dir",
                str(project / "dbt"),
                "--profiles-dir",
                str(project / "dbt"),
            ],
            cwd=project,
            env=environment,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        assert finished.returncode == 0, finished.stdout + finished.stderr


def _warehouse_state(database: Path) -> tuple[int, int, float, int]:
    with duckdb.connect(str(database), read_only=True) as connection:
        return (
            connection.execute("select count(*) from staging.yellow_trips").fetchone()[0],
            connection.execute("select count(*) from fct_trips").fetchone()[0],
            connection.execute(
                "select coalesce(sum(total_revenue), 0) from mart_daily_trip_metrics"
            ).fetchone()[0],
            connection.execute(
                "select count(*) from mart_anomalous_trips "
                "where quality_reasons = 'duplicate_record'"
            ).fetchone()[0],
        )


def test_recovery_drill_restores_all_reader_views(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Restore only moves the pointer: a separate pinned reload and dbt run is required."""
    data_dir = tmp_path / "isolated-data"
    database = data_dir / "processed" / "warehouse.duckdb"
    fixture = create_demo_fixture(
        data_dir=data_dir, year=2026, month=1, service="yellow", sample_rows=1000
    )
    source = Path(str(fixture["trip_path"]))
    original_rows = pq.read_table(source).to_pylist()

    def publish_and_rebuild():
        result = validate_trip_data(
            year=2026, month=1, service="yellow", data_dir=data_dir, input_path=source
        )
        loaded = load_validated_to_duckdb(
            year=2026,
            month=1,
            service="yellow",
            data_dir=data_dir,
            duckdb_path=database,
            validated_path=result.validated_path,
        )
        _rebuild_marts(database, tmp_path)
        return result, loaded

    original, loaded = publish_and_rebuild()
    original_revision = original.validated_path.parent.name
    baseline = _warehouse_state(database)
    assert original.summary["status_counts"] == {"valid": 1, "warning": 1, "rejected": 1}
    assert loaded.loaded_rows == 2
    assert baseline == (2, 1, 23.5, 1)

    changed = dict(original_rows[0])
    changed.update(
        tpep_pickup_datetime=original_rows[0]["tpep_pickup_datetime"].replace(day=3),
        tpep_dropoff_datetime=original_rows[0]["tpep_dropoff_datetime"].replace(day=3),
        total_amount=36.0,
    )
    pq.write_table(pa.Table.from_pylist([*original_rows, changed]), source)
    bad, bad_loaded = publish_and_rebuild()
    assert bad_loaded.loaded_rows == 3
    assert _warehouse_state(database) == (3, 2, 59.5, 1)
    assert bad.validated_path.parent.name != original_revision

    outcome = restore_revision(
        data_dir,
        year=2026,
        month=1,
        service="yellow",
        revision=original_revision,
        expected_current=bad.validated_path.parent.name,
    )
    assert outcome["warehouse_sync_required"] is True
    assert current_version(data_dir, 2026, 1, "yellow") == original.validated_path.parent
    assert bad.validated_path.is_file(), "inactive revisions remain available to readers"

    # The unsafe intermediate state is an expected demonstration, not a passing recovery.
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("DUCKDB_PATH", str(database))
    with TestClient(app) as client:
        quality_before = client.get("/quality/summary")
        overview_before = client.get("/metrics/overview")
    assert quality_before.status_code == overview_before.status_code == 200
    assert quality_before.json()["total_rows"] == 3
    assert overview_before.json()["total_trips"] == 2  # old pointer, newer marts

    repaired = load_validated_to_duckdb(
        year=2026,
        month=1,
        service="yellow",
        data_dir=data_dir,
        duckdb_path=database,
        validated_path=original.validated_path,
    )
    _rebuild_marts(database, tmp_path)
    assert repaired.loaded_rows == 2
    assert _warehouse_state(database) == baseline

    with TestClient(app) as client:
        quality = client.get("/quality/summary")
        overview = client.get("/metrics/overview")
        daily = client.get("/metrics/daily")
        anomalies = client.get("/anomalies")
        metadata = client.get("/metadata")
    assert all(item.status_code == 200 for item in (quality, overview, daily, anomalies, metadata))
    assert quality.json()["status_counts"] == original.summary["status_counts"]
    assert quality.json()["total_rows"] == 3
    assert overview.json()["total_trips"] == 1
    assert overview.json()["total_revenue"] == pytest.approx(23.5)
    assert daily.json()["total"] == 1
    assert daily.json()["items"][0]["trip_count"] == overview.json()["total_trips"]
    assert daily.json()["items"][0]["total_revenue"] == pytest.approx(
        overview.json()["total_revenue"]
    )
    assert anomalies.json()["total"] == 1
    assert metadata.json()["row_counts"]["fct_trips"] == overview.json()["total_trips"]
    assert sum(quality.json()["status_counts"].values()) == quality.json()["total_rows"]
