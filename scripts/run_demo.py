from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from urban_mobility.config import get_data_dir, get_duckdb_path
from urban_mobility.download import DEFAULT_SAMPLE_ROWS, validate_trip_request

CommandRunner = Callable[..., subprocess.CompletedProcess[Any]]


def run_demo(
    *,
    data_dir: Path,
    year: int,
    month: int,
    service: str,
    sample_rows: int,
    duckdb_path: Path | None = None,
    command_runner: CommandRunner = subprocess.run,
) -> dict[str, object]:
    """Run the bounded offline pipeline and leave dbt marts ready for the API."""
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
        }
    )

    completed_steps: list[str] = []
    for name, command in steps:
        print(f"[demo] {name}", flush=True)
        command_runner(
            command,
            cwd=repository_root,
            env=environment,
            check=True,
        )
        completed_steps.append(name)

    return {
        "data_dir": str(resolved_data_dir),
        "duckdb_path": str(resolved_duckdb_path),
        "year": year,
        "month": month,
        "service": service,
        "sample_rows": sample_rows,
        "steps": completed_steps,
    }


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
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
