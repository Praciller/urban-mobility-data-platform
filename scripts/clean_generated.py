from __future__ import annotations

import shutil
from pathlib import Path

from urban_mobility.config import get_data_dir


def clear_directory(directory: Path) -> int:
    if not directory.exists():
        return 0

    removed = 0
    for child in directory.iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
        removed += 1
    return removed


def main() -> int:
    data_dir = get_data_dir()
    project_root = Path(__file__).resolve().parents[1]
    targets = [
        data_dir / "processed",
        project_root / "reports" / "data_quality",
    ]
    removed = sum(clear_directory(target) for target in targets)
    print(f"Removed {removed} generated item(s). Raw data was preserved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
