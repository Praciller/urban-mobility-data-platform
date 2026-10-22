from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.api.app.repositories.quality import QualityReportRepository
from scripts.create_demo_fixture import create_demo_fixture
from urban_mobility import validate as validator
from urban_mobility.download import trip_data_path
from urban_mobility.ingest import resolve_trip_path


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
    assert not list((tmp_path / "processed").glob(".validation-*"))


def test_publish_artifacts_rolls_back_after_partial_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    staging = tmp_path / "staging"
    staging.mkdir()
    published = tmp_path / "published"
    published.mkdir()
    valid = published / "part-valid.parquet"
    rejected = published / "part-rejected.parquet"
    valid.write_bytes(b"old valid")
    rejected.write_bytes(b"old rejected")
    new_valid = staging / "validated.parquet"
    new_rejected = staging / "rejected.parquet"
    new_valid.write_bytes(b"new valid")
    new_rejected.write_bytes(b"new rejected")
    original_replace = Path.replace

    def fail_rejected(self: Path, target: Path) -> Path:
        if self.name == "rejected.parquet":
            raise OSError("simulated publish failure")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_rejected)
    with pytest.raises(OSError, match="simulated publish"):
        validator._publish_artifacts(staging, ((new_valid, valid), (new_rejected, rejected)))
    assert valid.read_bytes() == b"old valid"
    assert rejected.read_bytes() == b"old rejected"


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
