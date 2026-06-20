from __future__ import annotations

from dagster import AssetSelection, define_asset_job

from dagster_project.assets import REQUIRED_ASSET_NAMES


def _pipeline_config(
    *,
    sample_mode: bool,
    allow_remote_download: bool,
) -> dict:
    return {
        "resources": {
            "pipeline_config": {
                "config": {
                    "service": "yellow",
                    "year": 2026,
                    "month": 1,
                    "sample_mode": sample_mode,
                    "sample_rows": 1000,
                    "allow_remote_download": allow_remote_download,
                }
            }
        }
    }


sample_ingestion_job = define_asset_job(
    name="sample_ingestion_job",
    selection=AssetSelection.assets(*REQUIRED_ASSET_NAMES),
    config=_pipeline_config(sample_mode=True, allow_remote_download=False),
    description="Materialize the local sample pipeline without remote downloads by default.",
)

monthly_tlc_ingestion_job = define_asset_job(
    name="monthly_tlc_ingestion_job",
    selection=AssetSelection.assets(*REQUIRED_ASSET_NAMES),
    config=_pipeline_config(sample_mode=False, allow_remote_download=False),
    description=(
        "Materialize a monthly local TLC pipeline; enable remote download explicitly if needed."
    ),
)

analytics_refresh_job = define_asset_job(
    name="analytics_refresh_job",
    selection=AssetSelection.assets(*REQUIRED_ASSET_NAMES),
    config=_pipeline_config(sample_mode=True, allow_remote_download=False),
    description=(
        "Refresh validation, DuckDB staging, dbt marts, and analytics readiness from local files."
    ),
)

DAGSTER_JOBS = [
    sample_ingestion_job,
    monthly_tlc_ingestion_job,
    analytics_refresh_job,
]
