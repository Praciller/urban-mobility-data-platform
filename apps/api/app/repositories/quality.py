from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apps.api.app.core.errors import DataUnavailableError, ResourceNotFoundError

MAX_VALIDATION_SUMMARY_BYTES = 1_000_000
STATUS_NAMES = ("valid", "warning", "rejected")


class QualityReportRepository:
    def __init__(self, data_dir: Path) -> None:
        self.reports_dir = data_dir.expanduser().resolve() / "reports" / "data_quality"

    def latest_summary(self) -> dict[str, Any]:
        candidates = sorted(
            self.reports_dir.glob("validation_[0-9][0-9][0-9][0-9]_[0-9][0-9].json")
        )
        if not candidates:
            raise ResourceNotFoundError("No validation summary is available")

        path = candidates[-1]
        try:
            if path.stat().st_size > MAX_VALIDATION_SUMMARY_BYTES:
                raise DataUnavailableError("The latest validation summary exceeds the size limit")
            payload = json.loads(path.read_text(encoding="utf-8"))
        except DataUnavailableError:
            raise
        except (OSError, json.JSONDecodeError) as error:
            raise DataUnavailableError("The latest validation summary is unreadable") from error

        return _normalize_summary(payload, path.name)


def _normalize_summary(payload: object, artifact_name: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise DataUnavailableError("The latest validation summary has an invalid structure")

    status_counts = payload.get("status_counts")
    rule_counts = payload.get("rule_counts")
    if not isinstance(status_counts, dict) or not isinstance(rule_counts, dict):
        raise DataUnavailableError("The latest validation summary is missing quality counts")

    normalized_statuses = {
        name: _non_negative_int(status_counts.get(name), f"status_counts.{name}")
        for name in STATUS_NAMES
    }
    total_rows = _non_negative_int(payload.get("total_rows"), "total_rows")
    if sum(normalized_statuses.values()) != total_rows:
        raise DataUnavailableError("The latest validation summary has inconsistent row counts")
    normalized_rules = {
        str(name): _non_negative_int(count, f"rule_counts.{name}")
        for name, count in rule_counts.items()
        if str(name).strip()
    }

    return {
        "service": _required_string(payload.get("service"), "service"),
        "year": _non_negative_int(payload.get("year"), "year"),
        "month": _month(payload.get("month")),
        "validated_at": _required_string(payload.get("validated_at"), "validated_at"),
        "total_rows": total_rows,
        "status_counts": normalized_statuses,
        "rule_counts": dict(sorted(normalized_rules.items())),
        "artifact_name": artifact_name,
    }


def _required_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DataUnavailableError(f"The latest validation summary has an invalid {field}")
    return value


def _non_negative_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DataUnavailableError(f"The latest validation summary has an invalid {field}")
    return value


def _month(value: object) -> int:
    month = _non_negative_int(value, "month")
    if not 1 <= month <= 12:
        raise DataUnavailableError("The latest validation summary has an invalid month")
    return month
