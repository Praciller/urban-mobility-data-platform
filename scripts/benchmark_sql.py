"""Reproducible SQL profiling of five critical DuckDB/dbt analytics queries.

No latency budgets in CI: timings depend on CPU, cache, disk and scheduling.
The same immutable synthetic input and DuckDB version should be used for comparisons.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from benchmark_pipeline import MAX_ROWS, _write_synthetic_inputs

from urban_mobility.load_duckdb import load_validated_to_duckdb
from urban_mobility.validate import validate_trip_data

QUERIES = {
    "filtered_overview": """
        select count(*) as trip_count, sum(total_amount) as revenue
        from fct_trips
        where pickup_date between date '2026-01-01' and date '2026-01-31'
    """,
    "daily_mart_page": """
        select pickup_date, trip_count, total_revenue
        from mart_daily_trip_metrics
        where pickup_date between date '2026-01-01' and date '2026-01-31'
        order by pickup_date limit 100
    """,
    "hourly_mart_page": """
        select pickup_date, pickup_hour, trip_count, total_revenue
        from mart_hourly_demand
        where pickup_date between date '2026-01-01' and date '2026-01-31'
        order by pickup_date, pickup_hour limit 100
    """,
    "route_zone_joins": """
        select r.pickup_zone_id, pickup.zone_name, dropoff.zone_name,
               r.trip_count, r.total_revenue
        from mart_route_metrics as r
        join dim_zone as pickup on pickup.zone_id = r.pickup_zone_id
        join dim_zone as dropoff on dropoff.zone_id = r.dropoff_zone_id
        order by r.trip_count desc, r.pickup_zone_id, r.dropoff_zone_id
        limit 100
    """,
    "anomaly_page": """
        select trip_id, pickup_datetime, quality_reasons
        from mart_anomalous_trips
        where pickup_date between date '2026-01-01' and date '2026-01-31'
        order by pickup_datetime desc limit 100
    """,
}


def profile_queries(connection: duckdb.DuckDBPyConnection, repetitions: int) -> dict:
    if not 1 <= repetitions <= 10:
        raise ValueError("repetitions must be between 1 and 10")
    results = {}
    for name, statement in QUERIES.items():
        plan = connection.execute("explain " + statement).fetchone()[1]
        analyzed = connection.execute("explain analyze " + statement).fetchone()[1]
        durations = []
        for _ in range(repetitions):
            start = time.perf_counter()
            connection.execute(statement).fetchall()
            durations.append((time.perf_counter() - start) * 1000)
        results[name] = {
            "sql": " ".join(statement.split()),
            "plan": plan,
            "analyzed_plan": analyzed,
            "plan_sha256": hashlib.sha256(plan.encode("utf-8")).hexdigest(),
            "median_ms": round(statistics.median(durations), 3),
            "samples_ms": [round(value, 3) for value in durations],
        }
    return results


def benchmark_sql(rows: int = 3000, repetitions: int = 3) -> dict:
    if not 1 <= rows <= MAX_ROWS:
        raise ValueError(f"rows must be between 1 and {MAX_ROWS}")
    if not 1 <= repetitions <= 10:
        raise ValueError("repetitions must be between 1 and 10")
    project = Path(__file__).resolve().parents[1]
    executable = shutil.which("dbt")
    if executable is None:
        raise RuntimeError("dbt executable is required")
    with tempfile.TemporaryDirectory(prefix="umdp-sql-profile-") as workspace:
        scratch = Path(workspace)
        database = scratch / "processed" / "profile.duckdb"
        source = _write_synthetic_inputs(scratch, rows)
        # Exercise the anomaly mart while preserving the number of curated trips.
        original = pq.read_table(source)
        pq.write_table(pa.concat_tables([original, original.slice(0, 1)]), source)
        validation = validate_trip_data(
            year=2026, month=1, service="yellow", data_dir=scratch, input_path=source
        )
        loaded = load_validated_to_duckdb(
            year=2026,
            month=1,
            service="yellow",
            data_dir=scratch,
            duckdb_path=database,
            validated_path=validation.validated_path,
        )
        if (
            loaded.loaded_rows != rows + 1
            or validation.summary["status_counts"]["warning"] != 1
            or validation.summary["status_counts"]["rejected"] != 0
        ):
            raise AssertionError("Unexpected synthetic staging counts")

        environment = os.environ.copy()
        environment["DUCKDB_PATH"] = str(database)
        environment["DBT_TARGET_PATH"] = str(scratch / "dbt-target")
        environment["DBT_LOG_PATH"] = str(scratch / "dbt-logs")
        for operation in ("run", "test"):
            completed = subprocess.run(
                [
                    executable,
                    operation,
                    "--project-dir",
                    str(project / "dbt"),
                    "--profiles-dir",
                    str(project / "dbt"),
                ],
                cwd=project,
                env=environment,
                text=True,
                capture_output=True,
                timeout=180,
                check=False,
            )
            if completed.returncode:
                raise RuntimeError(
                    f"dbt {operation} failed: " + (completed.stdout + completed.stderr)[-2500:]
                )
        with duckdb.connect(str(database), read_only=True) as connection:
            fact_rows = connection.execute("select count(*) from fct_trips").fetchone()[0]
            if fact_rows != rows:
                raise AssertionError(f"Expected {rows} curated trips; got {fact_rows}")
            anomaly_rows = connection.execute(
                "select count(*) from mart_anomalous_trips"
            ).fetchone()[0]
            if anomaly_rows < 1:
                raise AssertionError("Synthetic duplicate did not reach anomaly mart")
            results = profile_queries(connection, repetitions)
        # All measurements and plans were recorded before TemporaryDirectory cleanup.
        return {
            "dataset": "deterministic_2026_01_synthetic",
            "rows": rows,
            "staging_rows": loaded.loaded_rows,
            "facts_rows": fact_rows,
            "repetitions": repetitions,
            "duckdb_version": duckdb.__version__,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "queries": results,
            "caveat": "Local microbenchmark; not a performance SLA or regression threshold",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=3000)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Omit full plans from printed JSON; report still includes plan hashes",
    )
    arguments = parser.parse_args()
    report = benchmark_sql(rows=arguments.rows, repetitions=arguments.repetitions)
    if arguments.summary_only:
        for query in report["queries"].values():
            query.pop("plan")
            query.pop("analyzed_plan")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
