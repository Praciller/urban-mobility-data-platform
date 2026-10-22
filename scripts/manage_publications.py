"""Inspect immutable validation revisions; restore one only with an explicit guard.

Read-only by default. Never deletes versions, legacy data or lock files.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

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
    details = []
    for path in versions:
        if path.is_symlink() or not path.is_dir() or _REVISION.fullmatch(path.name) is None:
            continue
        paths = [path / name for name in _FILES]
        complete = all(item.is_file() and not item.is_symlink() for item in paths)
        size_bytes = sum(
            item.stat().st_size for item in paths if item.is_file() and not item.is_symlink()
        )
        details.append(
            {
                "revision": path.name,
                "complete": complete,
                "active": path == active,
                "size_bytes": size_bytes,
            }
        )
    return {
        "service": service,
        "year": year,
        "month": month,
        "active_revision": active.name if active else None,
        "total_bytes": sum(item["size_bytes"] for item in details),
        "inactive_bytes": sum(item["size_bytes"] for item in details if not item["active"]),
        "versions": details,
    }


def verify_revision_for_restore(version: Path, *, year: int, month: int, service: str) -> None:
    """Check Parquet footers and quality counts before activating a previous run."""
    try:
        if version.is_symlink() or not version.is_dir():
            raise ValueError("Revision directory is missing or symlinked")
        for name in _FILES:
            artifact = version / name
            if not artifact.is_file() or artifact.is_symlink():
                raise ValueError(f"Missing or unsafe artifact: {name}")
        accepted = pq.read_metadata(version / "validated.parquet").num_rows
        rejected = pq.read_metadata(version / "rejected.parquet").num_rows
        with (version / "summary.json").open(encoding="utf-8") as stream:
            summary = json.load(stream)
        if not isinstance(summary, dict):
            raise ValueError("Summary is not a JSON object")
        if (summary.get("year"), summary.get("month"), summary.get("service")) != (
            year,
            month,
            service,
        ):
            raise ValueError("Summary partition does not match")
        counts = summary.get("status_counts")
        if not isinstance(counts, dict) or any(
            type(counts.get(key)) is not int or counts[key] < 0
            for key in ("valid", "warning", "rejected")
        ):
            raise ValueError("Summary has invalid quality counts")
        if accepted != counts["valid"] + counts["warning"] or rejected != counts["rejected"]:
            raise ValueError("Parquet row counts do not match the summary")
        if summary.get("total_rows") != accepted + rejected:
            raise ValueError("Summary total does not match source classification")
        outputs = summary.get("outputs")
        if (
            not isinstance(outputs, dict)
            or outputs.get("validated") != str(version / "validated.parquet")
            or outputs.get("rejected") != str(version / "rejected.parquet")
        ):
            raise ValueError("Summary output paths do not refer to this revision")
    except (OSError, ValueError, TypeError, KeyError, pa.ArrowException) as error:
        raise PublicationError(
            f"Unsafe, corrupted or incomplete revision; restore refused: {error}"
        ) from error


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
        verify_revision_for_restore(target, year=year, month=month, service=service)
        activate_version(data_dir, year, month, service, target)
        report = inspect_versions(data_dir, year=year, month=month, service=service)
        # This operation changes publication files only. A previously loaded
        # DuckDB staging partition and dbt marts are NOT implicitly reverted.
        report["warehouse_sync_required"] = True
        return report


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
    if args.restore:
        print(
            "WARNING: Publication pointer restored only. DuckDB staging and dbt marts "
            "have NOT been restored; reload this partition and rerun dbt before "
            "using dashboard metrics.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
