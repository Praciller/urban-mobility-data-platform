"""Bounded, reproducible synthetic throughput probe (not a production SLA)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from urban_mobility.download import zone_lookup_path
from urban_mobility.load_duckdb import load_validated_to_duckdb
from urban_mobility.validate import validate_trip_data

MAX_ROWS = 50_000


def _write_synthetic_inputs(data_dir: Path, rows: int) -> Path:
    """Create distinct, valid January taxi trips in bounded Arrow batches."""
    source = data_dir / "raw" / "benchmark_yellow_2026-01.parquet"
    source.parent.mkdir(parents=True, exist_ok=True)
    writer: pq.ParquetWriter | None = None
    try:
        for begin in range(0, rows, 4096):
            batch = []
            for i in range(begin, min(begin + 4096, rows)):
                pickup = datetime(2026, 1, 1) + timedelta(seconds=i * 50)
                batch.append(
                    {
                        "VendorID": 1,
                        "tpep_pickup_datetime": pickup,
                        "tpep_dropoff_datetime": pickup + timedelta(minutes=30),
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
                )
            table = pa.Table.from_pylist(batch)
            if writer is None:
                writer = pq.ParquetWriter(source, table.schema)
            writer.write_table(table)
    finally:
        if writer is not None:
            writer.close()

    zones = zone_lookup_path(data_dir)
    zones.parent.mkdir(parents=True, exist_ok=True)
    zones.write_text(
        "LocationID,Borough,Zone,service_zone\n"
        "1,Manhattan,Alpha,Yellow Zone\n"
        "132,Queens,JFK Airport,Airports\n",
        encoding="utf-8",
    )
    return source


def benchmark(rows: int, *, include_dbt: bool = True) -> dict[str, object]:
    if not 1 <= rows <= MAX_ROWS:
        raise ValueError(f"--rows must be between 1 and {MAX_ROWS:,}")
    phases: dict[str, float] = {}
    with tempfile.TemporaryDirectory(prefix="urban-mobility-benchmark-") as scratch:
        data_dir = Path(scratch)
        database = data_dir / "processed" / "benchmark.duckdb"
        start = time.perf_counter()
        source = _write_synthetic_inputs(data_dir, rows)
        phases["input_seconds"] = round(time.perf_counter() - start, 3)

        start = time.perf_counter()
        validation = validate_trip_data(
            year=2026, month=1, service="yellow", data_dir=data_dir, input_path=source
        )
        phases["validate_seconds"] = round(time.perf_counter() - start, 3)

        start = time.perf_counter()
        loaded = load_validated_to_duckdb(
            year=2026,
            month=1,
            service="yellow",
            data_dir=data_dir,
            duckdb_path=database,
        )
        phases["load_seconds"] = round(time.perf_counter() - start, 3)
        if loaded.loaded_rows != rows or validation.summary["status_counts"]["rejected"] != 0:
            raise AssertionError("Benchmark data was unexpectedly lost or rejected")

        if include_dbt:
            executable = shutil.which("dbt")
            if executable is None:
                raise RuntimeError("dbt executable is required for --dbt")
            project_root = Path(__file__).resolve().parents[1]
            env = os.environ.copy()
            env["DUCKDB_PATH"] = str(database)
            for operation in ("run", "test"):
                start = time.perf_counter()
                completed = subprocess.run(
                    [
                        executable,
                        operation,
                        "--project-dir",
                        str(project_root / "dbt"),
                        "--profiles-dir",
                        str(project_root / "dbt"),
                    ],
                    cwd=project_root,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=180,
                    check=False,
                )
                if completed.returncode:
                    raise RuntimeError(
                        f"dbt {operation} failed: " + (completed.stdout + completed.stderr)[-2000:]
                    )
                phases[f"dbt_{operation}_seconds"] = round(time.perf_counter() - start, 3)
            with duckdb.connect(str(database), read_only=True) as connection:
                fact_rows = int(connection.execute("select count(*) from fct_trips").fetchone()[0])
                if fact_rows != rows:
                    raise AssertionError(f"Expected {rows} curated trips; got {fact_rows}")

        return {
            "benchmark": "synthetic_local_batch",
            "rows": rows,
            "loaded_rows": loaded.loaded_rows,
            "valid_rows": validation.summary["status_counts"]["valid"],
            "warning_rows": validation.summary["status_counts"]["warning"],
            "dbt_included": include_dbt,
            "phases_seconds": phases,
            "total_seconds": round(sum(phases.values()), 3),
            "notes": "Sequential synthetic records; not full NYC TLC or representative throughput",
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--skip-dbt", action="store_true")
    args = parser.parse_args(argv)
    result = benchmark(args.rows, include_dbt=not args.skip_dbt)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
