from __future__ import annotations

from dagster import DefaultScheduleStatus, ScheduleDefinition

from dagster_project.jobs import monthly_tlc_ingestion_job

local_monthly_tlc_schedule = ScheduleDefinition(
    name="local_monthly_tlc_schedule",
    cron_schedule="0 7 3 * *",
    job=monthly_tlc_ingestion_job,
    default_status=DefaultScheduleStatus.STOPPED,
    description="Local demo schedule only; stopped by default and not used for cloud automation.",
)

DAGSTER_SCHEDULES = [local_monthly_tlc_schedule]
