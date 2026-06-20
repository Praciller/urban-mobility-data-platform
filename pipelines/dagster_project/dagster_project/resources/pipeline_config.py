from __future__ import annotations

import os
from pathlib import Path

from dagster import ConfigurableResource

from urban_mobility.config import get_data_dir
from urban_mobility.download import DEFAULT_SAMPLE_ROWS, validate_trip_request


class PipelineConfigResource(ConfigurableResource):
    """Runtime configuration shared by local Dagster assets."""

    service: str = "yellow"
    year: int = 2026
    month: int = 1
    sample_mode: bool = True
    sample_rows: int = DEFAULT_SAMPLE_ROWS
    data_dir: str = ""
    duckdb_path: str = ""
    allow_remote_download: bool = False
    run_dbt_tests: bool = True

    def resolved_data_dir(self) -> Path:
        configured = self.data_dir.strip() or os.getenv("DATA_DIR", "").strip()
        if configured:
            return Path(configured).expanduser().resolve()
        return get_data_dir()

    def resolved_duckdb_path(self) -> Path:
        configured = self.duckdb_path.strip() or os.getenv("DUCKDB_PATH", "").strip()
        if configured:
            return Path(configured).expanduser().resolve()
        return self.resolved_data_dir() / "processed" / "urban_mobility.duckdb"

    def validate(self) -> None:
        validate_trip_request(self.year, self.month, self.service)
        if self.sample_rows <= 0:
            raise ValueError("sample_rows must be greater than zero")
