from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from urban_mobility.config import get_data_dir, get_duckdb_path
from urban_mobility.download import DEFAULT_SAMPLE_ROWS, validate_trip_request
from urban_mobility.observability import (
    RUN_ID_ENV,
    emit_event,
    generate_correlation_id,
    is_valid_correlation_id,
)

CommandRunner = Callable[..., subprocess.CompletedProcess[Any]]


def run_demo(
    *,
    data_dir: Path,
    year: int,
    month: int,
    service: str,
    sample_rows: int,
    duckdb_path: Path | None = None,
    run_id: str | None = None,
    command_runner: CommandRunner = subprocess.run,
) -> dict[str, object]:
    """Run the bounded offline pipeline and leave dbt marts ready for the API."""
    if run_id is not None and not is_valid_correlation_id(run_id):
        raise ValueError("run_id must be 1-128 ASCII characters from A-Z, a-z, 0-9, . _ : -")
    resolved_run_id = run_id or generate_correlation_id()
    emit_event(
        level="INFO",
        component="demo_pipeline",
        event="pipeline.run.started",
        run_id=resolved_run_id,
        service=service,
        year=year,
        month=month,
        sample_mode=True,
        sample_rows=sample_rows,
    )
    try:
        validate_trip_request(year, month, service)
        if sample_rows <= 0:
            raise ValueError("sample_rows must be greater than zero")

        repository_root = Path(__file__).resolve().parents[1]
        resolved_data_dir = data_dir.expanduser().resolve()
        resolved_duckdb_path = (
            duckdb_path.expanduser().resolve()
            if duckdb_path is not None
            else resolved_data_dir / "processed" / "urban_mobility.duckdb"
        )
        dbt_executable = shutil.which("dbt")
        if dbt_executable is None:
            raise RuntimeError("dbt is unavailable; run 'uv sync --locked --all-groups' first")

        shared_args = [
            "--year",
            str(year),
            "--month",
            str(month),
            "--service",
            service,
        ]
        steps = [
            (
                "fixture",
                [
                    sys.executable,
                    str(repository_root / "scripts" / "create_demo_fixture.py"),
                    *shared_args,
                    "--sample-rows",
                    str(sample_rows),
                ],
            ),
            (
                "profile",
                [
                    sys.executable,
                    "-m",
                    "urban_mobility.ingest",
                    "inspect",
                    *shared_args,
                    "--mode",
                    "sample",
                    "--sample-rows",
                    str(sample_rows),
                ],
            ),
            ("validate", [sys.executable, "-m", "urban_mobility.validate", *shared_args]),
            ("load_duckdb", [sys.executable, "-m", "urban_mobility.load_duckdb", *shared_args]),
            ("dbt_parse", _dbt_command(dbt_executable, repository_root, "parse")),
            ("dbt_run", _dbt_command(dbt_executable, repository_root, "run")),
            ("dbt_test", _dbt_command(dbt_executable, repository_root, "test")),
        ]
        environment = os.environ.copy()
        environment.update(
            {
                "DATA_DIR": str(resolved_data_dir),
                "DUCKDB_PATH": str(resolved_duckdb_path),
                RUN_ID_ENV: resolved_run_id,
            }
        )

        completed_steps: list[str] = []
        for name, command in steps:
            emit_event(
                level="INFO",
                component="demo_pipeline",
                event="pipeline.stage.started",
                run_id=resolved_run_id,
                stage=name,
            )
            started_at = time.perf_counter()
            try:
                command_runner(
                    command,
                    cwd=repository_root,
                    env=environment,
                    check=True,
                    stdout=sys.stderr,
                    stderr=sys.stderr,
                )
            except Exception as error:
                emit_event(
                    level="ERROR",
                    component="demo_pipeline",
                    event="pipeline.stage.failed",
                    run_id=resolved_run_id,
                    stage=name,
                    duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
                    error_type=type(error).__name__,
                )
                raise
            emit_event(
                level="INFO",
                component="demo_pipeline",
                event="pipeline.stage.completed",
                run_id=resolved_run_id,
                stage=name,
                duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
            )
            completed_steps.append(name)

        emit_event(
            level="INFO",
            component="demo_pipeline",
            event="pipeline.run.completed",
            run_id=resolved_run_id,
            service=service,
            year=year,
            month=month,
            sample_mode=True,
            sample_rows=sample_rows,
        )
        return {
            "data_dir": str(resolved_data_dir),
            "duckdb_path": str(resolved_duckdb_path),
            "year": year,
            "month": month,
            "service": service,
            "sample_rows": sample_rows,
            "steps": completed_steps,
            "run_id": resolved_run_id,
        }
    except Exception as error:
        emit_event(
            level="ERROR",
            component="demo_pipeline",
            event="pipeline.run.failed",
            run_id=resolved_run_id,
            error_type=type(error).__name__,
        )
        raise


def _dbt_command(dbt_executable: str, repository_root: Path, operation: str) -> list[str]:
    dbt_directory = repository_root / "dbt"
    return [
        dbt_executable,
        operation,
        "--project-dir",
        str(dbt_directory),
        "--profiles-dir",
        str(dbt_directory),
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the bounded offline mobility demo from fixture through dbt tests."
    )
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--duckdb-path", type=Path)
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--month", type=int, default=1)
    parser.add_argument("--service", choices=("yellow",), default="yellow")
    parser.add_argument("--sample-rows", type=int, default=DEFAULT_SAMPLE_ROWS)
    parser.add_argument("--run-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    duckdb_path = arguments.duckdb_path
    if duckdb_path is None and os.getenv("DUCKDB_PATH", "").strip():
        duckdb_path = get_duckdb_path()
    result = run_demo(
        data_dir=arguments.data_dir or get_data_dir(),
        duckdb_path=duckdb_path,
        year=arguments.year,
        month=arguments.month,
        service=arguments.service,
        sample_rows=arguments.sample_rows,
        run_id=arguments.run_id,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
