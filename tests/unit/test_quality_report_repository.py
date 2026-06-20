from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.api.app.core.errors import DataUnavailableError, ResourceNotFoundError
from apps.api.app.repositories.quality import QualityReportRepository


def test_latest_summary_returns_newest_sanitized_artifact(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "data_quality"
    reports.mkdir(parents=True)
    for name, month in (("validation_2026_01.json", 1), ("validation_2026_02.json", 2)):
        (reports / name).write_text(
            json.dumps(
                {
                    "service": "yellow",
                    "year": 2026,
                    "month": month,
                    "validated_at": f"2026-{month:02d}-03T10:00:00Z",
                    "total_rows": 3,
                    "status_counts": {"valid": 1, "warning": 1, "rejected": 1},
                    "rule_counts": {"negative_fare_amount": 1},
                    "source_path": "C:/private/raw-file.parquet",
                }
            ),
            encoding="utf-8",
        )

    summary = QualityReportRepository(tmp_path).latest_summary()

    assert summary["month"] == 2
    assert summary["artifact_name"] == "validation_2026_02.json"
    assert "source_path" not in summary


def test_latest_summary_rejects_missing_or_invalid_reports(tmp_path: Path) -> None:
    repository = QualityReportRepository(tmp_path)
    with pytest.raises(ResourceNotFoundError):
        repository.latest_summary()

    reports = tmp_path / "reports" / "data_quality"
    reports.mkdir(parents=True)
    (reports / "validation_2026_01.json").write_text("{}", encoding="utf-8")

    with pytest.raises(DataUnavailableError):
        repository.latest_summary()

    (reports / "validation_2026_01.json").write_text(
        json.dumps(
            {
                "service": "yellow",
                "year": 2026,
                "month": 1,
                "validated_at": "2026-01-03T10:00:00Z",
                "total_rows": 2,
                "status_counts": {"valid": 1, "warning": 0, "rejected": 0},
                "rule_counts": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(DataUnavailableError, match="inconsistent row counts"):
        repository.latest_summary()
