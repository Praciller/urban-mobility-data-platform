from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import app
from urban_mobility.download import trip_data_path, zone_lookup_path
from urban_mobility.load_duckdb import load_validated_to_duckdb
from urban_mobility.validate import validate_trip_data


def test_dbt_run_and_test_on_generated_fixture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    source = trip_data_path(data_dir, 2026, 1, "yellow", sample=True, sample_rows=1000)
    source.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "VendorID": 1,
                    "tpep_pickup_datetime": datetime(2026, 1, 1, 8, 0),
                    "tpep_dropoff_datetime": datetime(2026, 1, 1, 8, 30),
                    "passenger_count": 1,
                    "trip_distance": 3.0,
                    "RatecodeID": 1,
                    "store_and_fwd_flag": "N",
                    "PULocationID": 1,
                    "DOLocationID": 132,
                    "payment_type": 1,
                    "fare_amount": 18.0,
                    "extra": 1.0,
                    "mta_tax": 0.5,
                    "tip_amount": 3.0,
                    "tolls_amount": 0.0,
                    "improvement_surcharge": 1.0,
                    "total_amount": 23.5,
                    "congestion_surcharge": 0.0,
                    "Airport_fee": 0.0,
                }
            ]
        ),
        source,
    )
    zones = zone_lookup_path(data_dir)
    zones.parent.mkdir(parents=True, exist_ok=True)
    zones.write_text(
        "LocationID,Borough,Zone,service_zone\n"
        "1,Manhattan,Alpha,Yellow Zone\n"
        "132,Queens,JFK Airport,Airports\n",
        encoding="utf-8",
    )

    validation = validate_trip_data(
        year=2026,
        month=1,
        service="yellow",
        data_dir=data_dir,
        input_path=source,
    )
    database = data_dir / "processed" / "dbt-test.duckdb"
    load_validated_to_duckdb(
        year=2026,
        month=1,
        service="yellow",
        data_dir=data_dir,
        duckdb_path=database,
        validated_path=validation.validated_path,
    )

    executable = shutil.which("dbt")
    assert executable is not None, "dbt executable is unavailable"
    project_root = Path(__file__).resolve().parents[2]
    dbt_dir = project_root / "dbt"
    environment = os.environ.copy()
    environment["DUCKDB_PATH"] = str(database)

    for command in (("run",), ("test",), ("docs", "generate")):
        completed = subprocess.run(
            [
                executable,
                *command,
                "--project-dir",
                str(dbt_dir),
                "--profiles-dir",
                str(dbt_dir),
            ],
            cwd=project_root,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr

    with duckdb.connect(str(database), read_only=True) as connection:
        fact = connection.execute(
            "select trip_id, is_airport_trip, quality_status from fct_trips"
        ).fetchone()
        daily_count = connection.execute("select count(*) from mart_daily_trip_metrics").fetchone()

    assert fact is not None
    assert fact[1:] == (True, "valid")
    assert daily_count == (1,)

    monkeypatch.setenv("DUCKDB_PATH", str(database))
    with TestClient(app) as client:
        health = client.get("/health")
        overview = client.get("/metrics/overview")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert overview.status_code == 200
    assert overview.json()["total_trips"] == 1
