import os
from pathlib import Path


def get_data_dir() -> Path:
    """Return the configured data directory as an absolute path."""
    configured = os.getenv("DATA_DIR", "./data").strip()
    if not configured:
        configured = "./data"
    return Path(configured).expanduser().resolve()
