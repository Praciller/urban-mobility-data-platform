from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    repository_root = Path(__file__).resolve().parents[1]
    data_directory = (
        Path(
            os.environ.get(
                "URBAN_MOBILITY_E2E_DATA_DIR",
                Path(tempfile.gettempdir()) / "urban-mobility-web-e2e",
            )
        )
        .expanduser()
        .resolve()
    )
    duckdb_path = data_directory / "processed" / "urban_mobility.duckdb"
    environment = os.environ.copy()
    environment.update(
        {
            "DATA_DIR": str(data_directory),
            "DUCKDB_PATH": str(duckdb_path),
            "URBAN_MOBILITY_E2E_DATA_DIR": str(data_directory),
        }
    )

    uv = shutil.which("uv") or "uv"
    subprocess.run(
        [
            uv,
            "run",
            "python",
            str(repository_root / "scripts" / "run_demo.py"),
            "--data-dir",
            str(data_directory),
            "--duckdb-path",
            str(duckdb_path),
            "--year",
            "2026",
            "--month",
            "1",
            "--service",
            "yellow",
            "--sample-rows",
            "1000",
        ],
        cwd=repository_root,
        env=environment,
        check=True,
    )

    npx = shutil.which("npx.cmd" if sys.platform == "win32" else "npx") or "npx"
    result = subprocess.run(
        [npx, "playwright", "test", *sys.argv[1:]],
        cwd=repository_root / "apps" / "web",
        env=environment,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
