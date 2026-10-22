from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.api.app.repositories.quality import QualityReportRepository
from scripts.create_demo_fixture import create_demo_fixture
from urban_mobility import validate as validator
from urban_mobility.download import trip_data_path
from urban_mobility.ingest import resolve_trip_path
from urban_mobility.validation_store import (
    PublicationError,
    activate_version,
    allocate_version,
    current_version,
    partition_root,
)


def test_auto_mode_prefers_full_raw_data_over_existing_sample(tmp_path: Path) -> None:
    raw = trip_data_path(tmp_path, 2026, 1, "yellow", sample=False)
    sample = trip_data_path(tmp_path, 2026, 1, "yellow", sample=True)
    for path in (raw, sample):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"test-only")

    assert resolve_trip_path(tmp_path, 2026, 1, "yellow", mode="auto") == raw
    assert resolve_trip_path(tmp_path, 2026, 1, "yellow", mode="sample") == sample
    assert resolve_trip_path(tmp_path, 2026, 1, "yellow", mode="raw") == raw


def test_validation_preserves_last_successful_run_on_classification_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = create_demo_fixture(
        data_dir=tmp_path, year=2026, month=1, service="yellow", sample_rows=1000
    )
    path = Path(str(fixture["trip_path"]))
    result = validator.validate_trip_data(
        year=2026, month=1, service="yellow", data_dir=tmp_path, input_path=path
    )
    existing = {
        name: target.read_bytes()
        for name, target in (
            ("validated", result.validated_path),
            ("rejected", result.rejected_path),
            ("summary", result.summary_path),
        )
    }
    original_copy = validator._copy_classification
    calls = 0

    def fail_second_copy(*args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated Parquet write failure")
        original_copy(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(validator, "_copy_classification", fail_second_copy)
    with pytest.raises(RuntimeError, match="simulated Parquet"):
        validator.validate_trip_data(
            year=2026, month=1, service="yellow", data_dir=tmp_path, input_path=path
        )

    assert result.validated_path.read_bytes() == existing["validated"]
    assert result.rejected_path.read_bytes() == existing["rejected"]
    assert result.summary_path.read_bytes() == existing["summary"]
    assert validator.validated_trip_path(tmp_path, 2026, 1, "yellow") == result.validated_path
    assert len(list((result.validated_path.parent.parent).iterdir())) == 1


def test_activation_is_one_atomic_pointer_update(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def prepared_version(label: bytes) -> Path:
        version = allocate_version(tmp_path, 2026, 1, "yellow")
        for name in ("validated.parquet", "rejected.parquet", "summary.json"):
            (version / name).write_bytes(label)
        return version

    old = prepared_version(b"old")
    activate_version(tmp_path, 2026, 1, "yellow", old)
    assert current_version(tmp_path, 2026, 1, "yellow") == old

    new = prepared_version(b"new")
    original_replace = Path.replace

    def abort_pointer(self: Path, target: Path) -> Path:
        if target.name == "current.json":
            raise OSError("simulated interruption before commit")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", abort_pointer)
    with pytest.raises(OSError, match="simulated interruption"):
        activate_version(tmp_path, 2026, 1, "yellow", new)
    assert current_version(tmp_path, 2026, 1, "yellow") == old
    assert (old / "validated.parquet").read_bytes() == b"old"
    assert (new / "validated.parquet").read_bytes() == b"new"

    monkeypatch.setattr(Path, "replace", original_replace)
    activate_version(tmp_path, 2026, 1, "yellow", new)
    assert current_version(tmp_path, 2026, 1, "yellow") == new
    assert (old / "summary.json").read_bytes() == b"old"


def test_unreferenced_and_invalid_pointers_fail_safely(tmp_path: Path) -> None:
    orphan = allocate_version(tmp_path, 2026, 1, "yellow")
    (orphan / "validated.parquet").write_bytes(b"not published")
    assert current_version(tmp_path, 2026, 1, "yellow") is None

    pointer = partition_root(tmp_path, 2026, 1, "yellow") / "current.json"
    pointer.write_text('{"schema_version":1,"revision":"../../escape"}')
    with pytest.raises(PublicationError, match="Invalid active publication"):
        current_version(tmp_path, 2026, 1, "yellow")


def test_latest_quality_report_uses_run_timestamp_not_source_month(tmp_path: Path) -> None:
    directory = tmp_path / "reports" / "data_quality"
    directory.mkdir(parents=True)
    for name, month, validated_at in (
        ("validation_2026_02.json", 2, "2026-03-01T12:00:00Z"),
        ("validation_2026_01.json", 1, "2026-03-05T12:00:00Z"),
    ):
        (directory / name).write_text(
            json.dumps(
                {
                    "service": "yellow",
                    "year": 2026,
                    "month": month,
                    "validated_at": validated_at,
                    "total_rows": 2,
                    "status_counts": {"valid": 1, "warning": 1, "rejected": 0},
                    "rule_counts": {"duplicate_record": 1},
                }
            ),
            encoding="utf-8",
        )
    summary = QualityReportRepository(tmp_path).latest_summary()
    assert summary["month"] == 1
    assert summary["artifact_name"] == "validation_2026_01.json"


def test_immutable_publication_is_readable_via_resolvers_and_quality_api(tmp_path: Path) -> None:
    fixture = create_demo_fixture(
        data_dir=tmp_path, year=2026, month=1, service="yellow", sample_rows=1000
    )
    source = Path(str(fixture["trip_path"]))
    first = validator.validate_trip_data(
        year=2026, month=1, service="yellow", data_dir=tmp_path, input_path=source
    )
    second = validator.validate_trip_data(
        year=2026, month=1, service="yellow", data_dir=tmp_path, input_path=source
    )
    assert first.validated_path != second.validated_path
    assert first.validated_path.is_file() and second.validated_path.is_file()
    assert validator.validated_trip_path(tmp_path, 2026, 1, "yellow") == second.validated_path
    assert validator.rejected_trip_path(tmp_path, 2026, 1, "yellow") == second.rejected_path
    assert validator.validation_summary_path(tmp_path, 2026, 1) == second.summary_path
    summary = QualityReportRepository(tmp_path).latest_summary()
    assert summary["total_rows"] == 3
    assert summary["month"] == 1
    assert summary["artifact_name"] == "validation_2026_01.json"


def test_incomplete_active_snapshot_does_not_fall_back_to_legacy(tmp_path: Path) -> None:
    legacy = validator.validation_summary_path(tmp_path, 2026, 1)
    legacy.parent.mkdir(parents=True)
    legacy.write_text("{}", encoding="utf-8")
    version = allocate_version(tmp_path, 2026, 1, "yellow")
    for name in ("validated.parquet", "rejected.parquet", "summary.json"):
        (version / name).write_bytes(b"x")
    activate_version(tmp_path, 2026, 1, "yellow", version)
    (version / "summary.json").unlink()
    with pytest.raises(PublicationError):
        validator.validation_summary_path(tmp_path, 2026, 1)
