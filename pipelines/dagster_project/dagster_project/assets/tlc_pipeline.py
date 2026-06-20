import csv
import json
import os
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

import duckdb
import pyarrow.parquet as pq
from dagster import AssetExecutionContext, MetadataValue, asset

from dagster_project.resources.pipeline_config import PipelineConfigResource
from urban_mobility.download import (
    DownloadRequest,
    download_trip_data,
    download_zone_lookup,
    trip_data_path,
    validate_parquet,
    zone_lookup_path,
)
from urban_mobility.ingest import inspect_trip, profile_path
from urban_mobility.load_duckdb import load_validated_to_duckdb
from urban_mobility.validate import validate_trip_data, validation_summary_path

REQUIRED_ASSET_NAMES = (
    "taxi_zone_lookup",
    "raw_yellow_trip_file",
    "raw_trip_profile",
    "validated_trip_data",
    "duckdb_staging",
    "dbt_models",
    "data_quality_report",
    "analytics_ready",
)

MART_RELATIONS = (
    "fct_trips",
    "dim_zone",
    "mart_daily_trip_metrics",
    "mart_hourly_demand",
    "mart_route_metrics",
    "mart_revenue_metrics",
    "mart_anomalous_trips",
)


@asset(group_name="local_tlc_pipeline")
def taxi_zone_lookup(
    context: AssetExecutionContext,
    pipeline_config: PipelineConfigResource,
) -> dict[str, Any]:
    pipeline_config.validate()
    data_dir = pipeline_config.resolved_data_dir()
    path = zone_lookup_path(data_dir)

    if path.is_file():
        status = "reused"
    elif pipeline_config.allow_remote_download:
        result = download_zone_lookup(data_dir=data_dir)
        status = result.status
        path = Path(result.local_path)
    else:
        raise FileNotFoundError(
            f"Remote download is disabled; expected local taxi zone lookup at {path}"
        )

    output = {
        "service": "taxi_zone_lookup",
        "path": str(path),
        "status": status,
        "row_count": _count_csv_rows(path),
    }
    _add_metadata(context, output)
    return output


@asset(group_name="local_tlc_pipeline")
def raw_yellow_trip_file(
    context: AssetExecutionContext,
    pipeline_config: PipelineConfigResource,
) -> dict[str, Any]:
    pipeline_config.validate()
    data_dir = pipeline_config.resolved_data_dir()
    path = trip_data_path(
        data_dir,
        pipeline_config.year,
        pipeline_config.month,
        pipeline_config.service,
        sample=pipeline_config.sample_mode,
        sample_rows=pipeline_config.sample_rows,
    )

    if path.is_file():
        validate_parquet(path)
        metadata = pq.read_metadata(path)
        output = {
            "service": pipeline_config.service,
            "year": pipeline_config.year,
            "month": pipeline_config.month,
            "path": str(path),
            "status": "reused",
            "sample_mode": pipeline_config.sample_mode,
            "sample_rows": pipeline_config.sample_rows if pipeline_config.sample_mode else None,
            "row_count": metadata.num_rows,
            "file_size": path.stat().st_size,
        }
    elif pipeline_config.allow_remote_download:
        result = download_trip_data(
            DownloadRequest(
                year=pipeline_config.year,
                month=pipeline_config.month,
                service=pipeline_config.service,
                sample_rows=(pipeline_config.sample_rows if pipeline_config.sample_mode else None),
            ),
            data_dir=data_dir,
        )
        output = asdict(result)
        output["path"] = output.pop("local_path")
        output["sample_mode"] = pipeline_config.sample_mode
        output["row_count"] = output.get("sample_row_count")
    else:
        raise FileNotFoundError(f"Remote download is disabled; expected local trip file at {path}")

    _add_metadata(context, output)
    return output


@asset(group_name="local_tlc_pipeline")
def raw_trip_profile(
    context: AssetExecutionContext,
    pipeline_config: PipelineConfigResource,
    raw_yellow_trip_file: dict[str, Any],
) -> dict[str, Any]:
    pipeline_config.validate()
    data_dir = pipeline_config.resolved_data_dir()
    profile = inspect_trip(
        data_dir=data_dir,
        year=pipeline_config.year,
        month=pipeline_config.month,
        service=pipeline_config.service,
        mode="sample" if pipeline_config.sample_mode else "auto",
        sample_rows=pipeline_config.sample_rows if pipeline_config.sample_mode else None,
    )
    output = {
        "service": pipeline_config.service,
        "year": pipeline_config.year,
        "month": pipeline_config.month,
        "source_path": raw_yellow_trip_file["path"],
        "profile_path": str(profile_path(data_dir, pipeline_config.year, pipeline_config.month)),
        "row_count": profile["row_count"],
        "column_count": len(profile["column_names"]),
        "file_size": profile["file_size"],
    }
    _add_metadata(context, output)
    return output


@asset(group_name="local_tlc_pipeline")
def validated_trip_data(
    context: AssetExecutionContext,
    pipeline_config: PipelineConfigResource,
    taxi_zone_lookup: dict[str, Any],
    raw_yellow_trip_file: dict[str, Any],
) -> dict[str, Any]:
    pipeline_config.validate()
    result = validate_trip_data(
        year=pipeline_config.year,
        month=pipeline_config.month,
        service=pipeline_config.service,
        data_dir=pipeline_config.resolved_data_dir(),
        input_path=Path(raw_yellow_trip_file["path"]),
    )
    status_counts = result.summary["status_counts"]
    output = {
        "service": pipeline_config.service,
        "year": pipeline_config.year,
        "month": pipeline_config.month,
        "zone_lookup_path": taxi_zone_lookup["path"],
        "validated_path": str(result.validated_path),
        "rejected_path": str(result.rejected_path),
        "summary_path": str(result.summary_path),
        "total_rows": result.summary["total_rows"],
        "valid_count": status_counts["valid"],
        "warning_count": status_counts["warning"],
        "rejected_count": status_counts["rejected"],
        "rule_counts": result.summary["rule_counts"],
    }
    _add_metadata(context, output)
    return output


@asset(group_name="local_tlc_pipeline")
def duckdb_staging(
    context: AssetExecutionContext,
    pipeline_config: PipelineConfigResource,
    validated_trip_data: dict[str, Any],
) -> dict[str, Any]:
    pipeline_config.validate()
    result = load_validated_to_duckdb(
        year=pipeline_config.year,
        month=pipeline_config.month,
        service=pipeline_config.service,
        data_dir=pipeline_config.resolved_data_dir(),
        duckdb_path=pipeline_config.resolved_duckdb_path(),
        validated_path=Path(validated_trip_data["validated_path"]),
    )
    output = {
        "service": pipeline_config.service,
        "year": pipeline_config.year,
        "month": pipeline_config.month,
        "duckdb_path": str(result.duckdb_path),
        "loaded_rows": result.loaded_rows,
        "zone_rows": result.zone_rows,
    }
    _add_metadata(context, output)
    return output


@asset(group_name="local_tlc_pipeline")
def dbt_models(
    context: AssetExecutionContext,
    pipeline_config: PipelineConfigResource,
    duckdb_staging: dict[str, Any],
) -> dict[str, Any]:
    pipeline_config.validate()
    root = _project_root()
    dbt_dir = root / "dbt"
    commands = [("run",)]
    if pipeline_config.run_dbt_tests:
        commands.append(("test",))

    statuses = []
    for command in commands:
        completed = _run_dbt_command(
            command=command,
            root=root,
            dbt_dir=dbt_dir,
            duckdb_path=Path(duckdb_staging["duckdb_path"]),
        )
        statuses.append({"command": " ".join(command), "returncode": completed.returncode})

    output = {
        "service": pipeline_config.service,
        "year": pipeline_config.year,
        "month": pipeline_config.month,
        "duckdb_path": duckdb_staging["duckdb_path"],
        "dbt_project_dir": str(dbt_dir),
        "dbt_status": "ok",
        "commands": statuses,
    }
    _add_metadata(context, output)
    return output


@asset(group_name="local_tlc_pipeline")
def data_quality_report(
    context: AssetExecutionContext,
    pipeline_config: PipelineConfigResource,
    raw_trip_profile: dict[str, Any],
    validated_trip_data: dict[str, Any],
    dbt_models: dict[str, Any],
) -> dict[str, Any]:
    data_dir = pipeline_config.resolved_data_dir()
    summary_path = validation_summary_path(data_dir, pipeline_config.year, pipeline_config.month)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    status_counts = summary["status_counts"]
    output = {
        "service": pipeline_config.service,
        "year": pipeline_config.year,
        "month": pipeline_config.month,
        "profile_path": raw_trip_profile["profile_path"],
        "summary_path": validated_trip_data["summary_path"],
        "dbt_status": dbt_models["dbt_status"],
        "total_rows": summary["total_rows"],
        "valid_count": status_counts["valid"],
        "warning_count": status_counts["warning"],
        "rejected_count": status_counts["rejected"],
        "report_paths": {
            "raw_profile": raw_trip_profile["profile_path"],
            "validation_summary": validated_trip_data["summary_path"],
        },
    }
    _add_metadata(context, output)
    return output


@asset(group_name="local_tlc_pipeline")
def analytics_ready(
    context: AssetExecutionContext,
    pipeline_config: PipelineConfigResource,
    dbt_models: dict[str, Any],
    data_quality_report: dict[str, Any],
) -> dict[str, Any]:
    database = pipeline_config.resolved_duckdb_path()
    row_counts = _relation_row_counts(database, MART_RELATIONS)
    output = {
        "service": pipeline_config.service,
        "year": pipeline_config.year,
        "month": pipeline_config.month,
        "duckdb_path": str(database),
        "dbt_status": dbt_models["dbt_status"],
        "quality_summary_path": data_quality_report["summary_path"],
        "row_counts": row_counts,
        "analytics_ready": _analytics_is_ready(row_counts),
    }
    _add_metadata(context, output)
    return output


def _run_dbt_command(
    *,
    command: tuple[str, ...],
    root: Path,
    dbt_dir: Path,
    duckdb_path: Path,
) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("dbt")
    if executable is None:
        raise RuntimeError("dbt executable is unavailable. Run `uv sync --all-groups`.")

    environment = os.environ.copy()
    environment["DUCKDB_PATH"] = str(duckdb_path)
    completed = subprocess.run(
        [
            executable,
            *command,
            "--project-dir",
            str(dbt_dir),
            "--profiles-dir",
            str(dbt_dir),
        ],
        cwd=root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stdout + "\n" + completed.stderr)[-4000:]
        raise RuntimeError(f"dbt {' '.join(command)} failed with {completed.returncode}\n{detail}")
    return completed


def _relation_row_counts(database: Path, relations: tuple[str, ...]) -> dict[str, int]:
    with duckdb.connect(str(database), read_only=True) as connection:
        return {
            relation: int(connection.execute(f"select count(*) from {relation}").fetchone()[0])
            for relation in relations
        }


def _analytics_is_ready(row_counts: dict[str, int]) -> bool:
    required_relations = set(MART_RELATIONS)
    return required_relations.issubset(row_counts) and all(
        row_counts[relation] > 0 for relation in ("fct_trips", "dim_zone")
    )


def _count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def _project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / "dbt").is_dir():
            return parent
    raise RuntimeError("Unable to locate project root")


def _add_metadata(context: AssetExecutionContext, metadata: dict[str, Any]) -> None:
    context.add_output_metadata({key: _metadata_value(value) for key, value in metadata.items()})


def _metadata_value(value: Any) -> object:
    if isinstance(value, Path):
        return MetadataValue.path(str(value))
    if isinstance(value, dict | list):
        return MetadataValue.json(value)
    if isinstance(value, bool | int | float | str) or value is None:
        return value
    return str(value)
