"""Inspect immutable validation revisions; restore one only with an explicit guard.

Read-only by default. Never deletes versions, legacy data or lock files.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from urban_mobility.validation_store import (
    PublicationError,
    activate_version,
    current_version,
    partition_root,
    partition_write_lock,
)

_REVISION = re.compile(r"^[0-9a-f]{32}$")
_FILES = ("validated.parquet", "rejected.parquet", "summary.json")


def inspect_versions(data_dir: Path, *, year: int, month: int, service: str) -> dict[str, object]:
    root = partition_root(data_dir, year, month, service)
    active = current_version(data_dir, year, month, service)
    versions = sorted((root / "versions").glob("*")) if (root / "versions").is_dir() else []
    return {
        "service": service,
        "year": year,
        "month": month,
        "active_revision": active.name if active else None,
        "versions": [
            {
                "revision": path.name,
                "complete": all((path / name).is_file() for name in _FILES),
                "active": path == active,
            }
            for path in versions
            if path.is_dir() and _REVISION.fullmatch(path.name)
        ],
    }


def restore_revision(
    data_dir: Path,
    *,
    year: int,
    month: int,
    service: str,
    revision: str,
    expected_current: str,
) -> dict[str, object]:
    """Compare-and-swap rollback under the same per-partition publisher lock."""
    if _REVISION.fullmatch(revision) is None or _REVISION.fullmatch(expected_current) is None:
        raise PublicationError("Use full 32-character lowercase revision IDs")
    with partition_write_lock(data_dir, year, month, service):
        active = current_version(data_dir, year, month, service)
        if active is None or active.name != expected_current:
            raise PublicationError("Active revision changed; refusing stale restore request")
        target = partition_root(data_dir, year, month, service) / "versions" / revision
        if target == active:
            raise PublicationError("Requested revision is already active")
        activate_version(data_dir, year, month, service, target)
        return inspect_versions(data_dir, year=year, month=month, service=service)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--service", choices=("yellow",), default="yellow")
    parser.add_argument("--restore", help="Full 32-character revision ID to activate")
    parser.add_argument(
        "--expect-current", help="Guard: full revision ID that must still be active"
    )
    args = parser.parse_args(argv)
    if bool(args.restore) != bool(args.expect_current):
        parser.error("--restore and --expect-current must be supplied together")
    try:
        if args.restore:
            result = restore_revision(
                args.data_dir,
                year=args.year,
                month=args.month,
                service=args.service,
                revision=args.restore,
                expected_current=args.expect_current,
            )
        else:
            result = inspect_versions(
                args.data_dir, year=args.year, month=args.month, service=args.service
            )
    except PublicationError as error:
        parser.exit(1, f"error: {error}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
