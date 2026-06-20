from dagster import Definitions

from dagster_project.assets import (
    analytics_ready,
    data_quality_report,
    dbt_models,
    duckdb_staging,
    raw_trip_profile,
    raw_yellow_trip_file,
    taxi_zone_lookup,
    validated_trip_data,
)
from dagster_project.jobs import DAGSTER_JOBS
from dagster_project.resources import PipelineConfigResource
from dagster_project.schedules import DAGSTER_SCHEDULES

DAGSTER_ASSETS = [
    taxi_zone_lookup,
    raw_yellow_trip_file,
    raw_trip_profile,
    validated_trip_data,
    duckdb_staging,
    dbt_models,
    data_quality_report,
    analytics_ready,
]

defs = Definitions(
    assets=DAGSTER_ASSETS,
    jobs=DAGSTER_JOBS,
    schedules=DAGSTER_SCHEDULES,
    resources={"pipeline_config": PipelineConfigResource()},
)
