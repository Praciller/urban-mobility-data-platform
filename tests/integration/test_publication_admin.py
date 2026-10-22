from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.create_demo_fixture import create_demo_fixture
from scripts.manage_publications import inspect_versions, restore_revision
from urban_mobility.validate import validate_trip_data, validated_trip_path
from urban_mobility.validation_store import PublicationError, current_version


def test_inspect_and_restore_requires_matching_current_revision(tmp_path: Path) -> None:
    fixture = create_demo_fixture(
        data_dir=tmp_path, year=2026, month=1, service="yellow", sample_rows=1000
    )
    source = Path(str(fixture["trip_path"]))
    old = validate_trip_data(
        year=2026, month=1, service="yellow", data_dir=tmp_path, input_path=source
    )
    new = validate_trip_data(
        year=2026, month=1, service="yellow", data_dir=tmp_path, input_path=source
    )
    evidence = inspect_versions(tmp_path, year=2026, month=1, service="yellow")
    assert evidence["active_revision"] == new.validated_path.parent.name
    assert len(evidence["versions"]) == 2
    assert all(item["complete"] for item in evidence["versions"])

    with pytest.raises(PublicationError, match="stale restore"):
        restore_revision(
            tmp_path,
            year=2026,
            month=1,
            service="yellow",
            revision=old.validated_path.parent.name,
            expected_current=old.validated_path.parent.name,
        )
    assert current_version(tmp_path, 2026, 1, "yellow") == new.validated_path.parent

    restored = restore_revision(
        tmp_path,
        year=2026,
        month=1,
        service="yellow",
        revision=old.validated_path.parent.name,
        expected_current=new.validated_path.parent.name,
    )
    assert restored["active_revision"] == old.validated_path.parent.name
    assert validated_trip_path(tmp_path, 2026, 1, "yellow") == old.validated_path
    assert new.validated_path.is_file()
    assert len(restored["versions"]) == 2


def test_restore_refuses_missing_invalid_and_active_targets(tmp_path: Path) -> None:
    fixture = create_demo_fixture(
        data_dir=tmp_path, year=2026, month=1, service="yellow", sample_rows=1000
    )
    current = validate_trip_data(
        year=2026,
        month=1,
        service="yellow",
        data_dir=tmp_path,
        input_path=Path(str(fixture["trip_path"])),
    )
    active = current.validated_path.parent.name
    with pytest.raises(PublicationError, match="already active"):
        restore_revision(
            tmp_path,
            year=2026,
            month=1,
            service="yellow",
            revision=active,
            expected_current=active,
        )
    with pytest.raises(PublicationError, match="full 32-character"):
        restore_revision(
            tmp_path,
            year=2026,
            month=1,
            service="yellow",
            revision="../../escape",
            expected_current=active,
        )
    with pytest.raises(PublicationError, match="incomplete"):
        restore_revision(
            tmp_path,
            year=2026,
            month=1,
            service="yellow",
            revision="0" * 32,
            expected_current=active,
        )
    assert current_version(tmp_path, 2026, 1, "yellow") == current.validated_path.parent


def test_inspection_cli_is_read_only(tmp_path: Path) -> None:
    output = subprocess.run(
        [
            sys.executable,
            "scripts/manage_publications.py",
            "--data-dir",
            str(tmp_path),
            "--year",
            "2026",
            "--month",
            "1",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    report = json.loads(output.stdout)
    assert report["active_revision"] is None
    assert report["versions"] == []
    assert not (tmp_path / "processed").exists()


def test_active_snapshot_supersedes_future_dated_legacy_report(tmp_path: Path) -> None:
    from apps.api.app.repositories.quality import QualityReportRepository

    fixture = create_demo_fixture(
        data_dir=tmp_path, year=2026, month=1, service="yellow", sample_rows=1000
    )
    current = validate_trip_data(
        year=2026,
        month=1,
        service="yellow",
        data_dir=tmp_path,
        input_path=Path(str(fixture["trip_path"])),
    )
    legacy = tmp_path / "reports" / "data_quality" / "validation_2026_01.json"
    legacy.parent.mkdir(parents=True)
    corrupted_stale = dict(current.summary)
    corrupted_stale["validated_at"] = "2099-01-01T00:00:00Z"
    corrupted_stale["total_rows"] = 100
    corrupted_stale["status_counts"] = {"valid": 100, "warning": 0, "rejected": 0}
    legacy.write_text(json.dumps(corrupted_stale), encoding="utf-8")
    selected = QualityReportRepository(tmp_path).latest_summary()
    assert selected["total_rows"] == 3
    assert selected["validated_at"] == current.summary["validated_at"]


def test_inventory_reports_actual_revision_storage_without_deleting(tmp_path: Path) -> None:
    fixture = create_demo_fixture(
        data_dir=tmp_path, year=2026, month=1, service="yellow", sample_rows=1000
    )
    source = Path(str(fixture["trip_path"]))
    old = validate_trip_data(
        year=2026, month=1, service="yellow", data_dir=tmp_path, input_path=source
    )
    new = validate_trip_data(
        year=2026, month=1, service="yellow", data_dir=tmp_path, input_path=source
    )
    report = inspect_versions(tmp_path, year=2026, month=1, service="yellow")
    expected_old_size = sum(
        (old.validated_path.parent / name).stat().st_size
        for name in ("validated.parquet", "rejected.parquet", "summary.json")
    )
    expected_new_size = sum(
        (new.validated_path.parent / name).stat().st_size
        for name in ("validated.parquet", "rejected.parquet", "summary.json")
    )
    assert report["total_bytes"] == expected_old_size + expected_new_size
    assert report["inactive_bytes"] == expected_old_size
    assert report["active_revision"] == new.validated_path.parent.name
    assert old.validated_path.is_file()


def test_restore_refuses_corrupted_parquet_and_inconsistent_summary(tmp_path: Path) -> None:
    fixture = create_demo_fixture(
        data_dir=tmp_path, year=2026, month=1, service="yellow", sample_rows=1000
    )
    source = Path(str(fixture["trip_path"]))
    old = validate_trip_data(
        year=2026, month=1, service="yellow", data_dir=tmp_path, input_path=source
    )
    new = validate_trip_data(
        year=2026, month=1, service="yellow", data_dir=tmp_path, input_path=source
    )
    old_revision = old.validated_path.parent.name
    new_revision = new.validated_path.parent.name
    original = old.validated_path.read_bytes()
    old.validated_path.write_bytes(b"not parquet")
    try:
        with pytest.raises(PublicationError, match="corrupted"):
            restore_revision(
                tmp_path,
                year=2026,
                month=1,
                service="yellow",
                revision=old_revision,
                expected_current=new_revision,
            )
    finally:
        old.validated_path.write_bytes(original)
    summary = json.loads(old.summary_path.read_text(encoding="utf-8"))
    summary["status_counts"]["valid"] = 999
    old.summary_path.write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(PublicationError, match="row counts"):
        restore_revision(
            tmp_path,
            year=2026,
            month=1,
            service="yellow",
            revision=old_revision,
            expected_current=new_revision,
        )
    assert current_version(tmp_path, 2026, 1, "yellow") == new.validated_path.parent


def test_restore_cli_declares_unreconciled_warehouse(tmp_path: Path) -> None:
    fixture = create_demo_fixture(
        data_dir=tmp_path, year=2026, month=1, service="yellow", sample_rows=1000
    )
    source = Path(str(fixture["trip_path"]))
    previous = validate_trip_data(
        year=2026, month=1, service="yellow", data_dir=tmp_path, input_path=source
    )
    active = validate_trip_data(
        year=2026, month=1, service="yellow", data_dir=tmp_path, input_path=source
    )
    command = [
        sys.executable,
        "scripts/manage_publications.py",
        "--data-dir",
        str(tmp_path),
        "--year",
        "2026",
        "--month",
        "1",
        "--restore",
        previous.validated_path.parent.name,
        "--expect-current",
        active.validated_path.parent.name,
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=20)
    report = json.loads(result.stdout)
    assert report["warehouse_sync_required"] is True
    assert report["active_revision"] == previous.validated_path.parent.name
    assert "DuckDB staging and dbt marts" in result.stderr
    assert "NOT been restored" in result.stderr
