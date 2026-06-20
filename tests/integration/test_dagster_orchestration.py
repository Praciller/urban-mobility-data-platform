from __future__ import annotations

from datetime import datetime
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from dagster import Definitions, materialize_to_memory
from dagster_project.assets.tlc_pipeline import _analytics_is_ready
from dagster_project.definitions import DAGSTER_ASSETS, defs
from dagster_project.resources.pipeline_config import PipelineConfigResource

from urban_mobility.download import trip_data_path, zone_lookup_path

REQUIRED_ASSETS = {
    "taxi_zone_lookup",
    "raw_yellow_trip_file",
    "raw_trip_profile",
    "validated_trip_data",
    "duckdb_staging",
    "dbt_models",
    "data_quality_report",
    "analytics_ready",
}
REQUIRED_JOBS = {
    "sample_ingestion_job",
    "monthly_tlc_ingestion_job",
    "analytics_refresh_job",
}


def test_analytics_readiness_allows_an_empty_anomaly_mart() -> None:
    row_counts = {
        "fct_trips": 3,
        "dim_zone": 265,
        "mart_daily_trip_metrics": 2,
        "mart_hourly_demand": 3,
        "mart_route_metrics": 3,
        "mart_revenue_metrics": 2,
        "mart_anomalous_trips": 0,
    }

    assert _analytics_is_ready(row_counts) is True
    assert _analytics_is_ready({**row_counts, "fct_trips": 0}) is False


def test_dagster_definitions_load_and_expose_required_assets_jobs() -> None:
    Definitions.validate_loadable(defs)

    asset_names = {asset.key.to_user_string() for asset in defs.assets or []}
    job_names = {job.name for job in defs.jobs or []}
    schedule_names = {schedule.name for schedule in defs.schedules or []}

    assert asset_names >= REQUIRED_ASSETS
    assert job_names >= REQUIRED_JOBS
    assert "local_monthly_tlc_schedule" in schedule_names


def test_sample_assets_materialize_against_local_fixture(tmp_path: Path) -> None:
    data_dir = tmp_path / "external-data"
    duckdb_path = data_dir / "processed" / "dagster-test.duckdb"
    _write_local_fixture(data_dir)

    result = materialize_to_memory(
        DAGSTER_ASSETS,
        resources={
            "pipeline_config": PipelineConfigResource(
                data_dir=str(data_dir),
                duckdb_path=str(duckdb_path),
                service="yellow",
                year=2026,
                month=1,
                sample_mode=True,
                sample_rows=1000,
                allow_remote_download=False,
            )
        },
    )

    assert result.success
    with duckdb.connect(str(duckdb_path), read_only=True) as connection:
        trip_count = connection.execute("select count(*) from fct_trips").fetchone()
        daily_count = connection.execute("select count(*) from mart_daily_trip_metrics").fetchone()

    assert trip_count == (1,)
    assert daily_count == (1,)


def test_sample_assets_refuse_remote_download_by_default(tmp_path: Path) -> None:
    result = materialize_to_memory(
        [DAGSTER_ASSETS[1]],
        resources={
            "pipeline_config": PipelineConfigResource(
                data_dir=str(tmp_path / "missing-data"),
                service="yellow",
                year=2026,
                month=1,
                sample_mode=True,
                sample_rows=1000,
                allow_remote_download=False,
            )
        },
        raise_on_error=False,
    )

    assert not result.success
    failures = [event for event in result.all_events if event.is_step_failure]
    assert failures
    assert "Remote download is disabled" in str(failures[0].event_specific_data.error)


def _write_local_fixture(data_dir: Path) -> None:
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
