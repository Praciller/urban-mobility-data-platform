from __future__ import annotations

import json
import logging
import math
import ntpath
import posixpath
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA_VERSION = 1
REQUEST_ID_HEADER = "X-Request-ID"
RUN_ID_ENV = "URBAN_MOBILITY_RUN_ID"
_CORRELATION_ID_PATTERN = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z", re.ASCII)
_MAX_STRING_LENGTH = 256
_SAFE_FIELDS = frozenset(
    {
        "method",
        "path",
        "status_code",
        "duration_ms",
        "stage",
        "service",
        "year",
        "month",
        "sample_mode",
        "sample_rows",
        "row_count",
        "error_type",
        "artifact",
        "relative_path",
    }
)
_LOGGER = logging.getLogger("urban_mobility.application")


class _JsonLineHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            sys.stderr.write(record.getMessage().rstrip("\r\n") + "\n")
        except Exception:
            self.handleError(record)


if not _LOGGER.handlers:
    _LOGGER.addHandler(_JsonLineHandler())
_LOGGER.setLevel(logging.INFO)
_LOGGER.propagate = False


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def is_valid_correlation_id(value: object) -> bool:
    return isinstance(value, str) and _CORRELATION_ID_PATTERN.fullmatch(value) is not None


def generate_correlation_id() -> str:
    from uuid import uuid4

    return uuid4().hex


def resolve_correlation_id(value: object) -> str:
    return value if is_valid_correlation_id(value) else generate_correlation_id()


def redact_path(
    value: str | Path,
    *,
    data_dir: Path | None = None,
    repository_root: Path | None = None,
) -> str:
    """Return a relative path under a known root, or only a basename."""
    raw = str(value)
    if not raw or len(raw) > 1024 or "\x00" in raw:
        return "<redacted>"

    normalized = posixpath.normpath(raw.replace("\\", "/"))
    roots = [root for root in (data_dir, repository_root) if root is not None]
    for root in roots:
        root_normalized = posixpath.normpath(str(root).replace("\\", "/"))
        comparison_value = normalized.casefold()
        comparison_root = root_normalized.casefold()
        if comparison_value == comparison_root:
            return "."
        prefix = comparison_root.rstrip("/") + "/"
        if comparison_value.startswith(prefix):
            relative = normalized[len(root_normalized.rstrip("/")) + 1 :]
            return relative.replace("\\", "/")

    if not posixpath.isabs(normalized) and not ntpath.isabs(raw):
        if normalized == ".." or normalized.startswith("../"):
            return posixpath.basename(normalized)
        return normalized
    return ntpath.basename(raw) or posixpath.basename(normalized) or "<redacted>"


def build_event(
    *,
    level: str,
    component: str,
    event: str,
    request_id: object | None = None,
    run_id: object | None = None,
    **fields: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": utc_timestamp(),
        "level": _bounded_string(level.upper()),
        "component": _bounded_string(component),
        "event": _bounded_string(event),
    }
    if request_id is not None:
        payload["request_id"] = resolve_correlation_id(request_id)
    if run_id is not None:
        payload["run_id"] = resolve_correlation_id(run_id)

    for key, value in fields.items():
        if key in _SAFE_FIELDS:
            safe_value = _safe_field(key, value)
            if safe_value is not None:
                payload[key] = safe_value
    return payload


def emit_event(
    *,
    level: str,
    component: str,
    event: str,
    request_id: object | None = None,
    run_id: object | None = None,
    **fields: object,
) -> dict[str, object]:
    payload = build_event(
        level=level,
        component=component,
        event=event,
        request_id=request_id,
        run_id=run_id,
        **fields,
    )
    log_level = getattr(logging, level.upper(), logging.INFO)
    _LOGGER.log(log_level, json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
    return payload


def _safe_field(key: str, value: object) -> object | None:
    if key == "path":
        return _safe_request_path(value)
    if key in {"artifact", "relative_path"}:
        return redact_path(value) if isinstance(value, (str, Path)) else None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, str):
        return _bounded_string(value)
    return None


def _safe_request_path(value: object) -> str | None:
    if not isinstance(value, str) or len(value) > _MAX_STRING_LENGTH:
        return None
    parsed = urlsplit(value)
    path = parsed.path
    if not path.startswith("/") or ntpath.splitdrive(path)[0]:
        return None
    return path


def _bounded_string(value: str) -> str:
    return value[:_MAX_STRING_LENGTH]
