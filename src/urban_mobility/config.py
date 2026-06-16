import os
from pathlib import Path


def get_data_dir() -> Path:
    """Return the configured data directory as an absolute path."""
    configured = os.getenv("DATA_DIR", "./data").strip()
    if not configured:
        configured = "./data"
    return Path(configured).expanduser().resolve()


def get_duckdb_path() -> Path:
    """Return the configured DuckDB path, defaulting under DATA_DIR."""
    configured = os.getenv("DUCKDB_PATH", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return get_data_dir() / "processed" / "urban_mobility.duckdb"
