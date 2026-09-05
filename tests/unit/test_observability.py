from __future__ import annotations

import json
from pathlib import Path

from urban_mobility.observability import (
    SCHEMA_VERSION,
    build_event,
    generate_correlation_id,
    is_valid_correlation_id,
    redact_path,
    resolve_correlation_id,
    utc_timestamp,
)


def test_build_event_serializes_the_bounded_contract() -> None:
    event = build_event(
        level="INFO",
        component="api",
        event="api.request.completed",
        request_id="request-001",
        method="GET",
        path="/health?token=secret",
        status_code=200,
        relative_path=r"C:\Users\private\data\quality.json",
        unsupported={"Authorization": "Bearer secret"},
    )

    assert event["schema_version"] == SCHEMA_VERSION
    assert event["level"] == "INFO"
    assert event["component"] == "api"
    assert event["event"] == "api.request.completed"
    assert event["request_id"] == "request-001"
    assert event["path"] == "/health"
    assert event["relative_path"] == "quality.json"
    assert "unsupported" not in event
    assert "Authorization" not in json.dumps(event)
    assert utc_timestamp().endswith("Z")


def test_build_event_is_one_newline_safe_json_object() -> None:
    event = build_event(
        level="INFO",
        component="demo_pipeline",
        event="pipeline.stage.completed",
        run_id="run-001",
        stage="validate\nredacted",
    )

    encoded = json.dumps(event, separators=(",", ":"))

    assert "\n" not in encoded
    assert json.loads(encoded)["stage"] == "validate\nredacted"


def test_redact_path_keeps_only_safe_relative_or_basename_values(tmp_path: Path) -> None:
    data_dir = tmp_path / "external-data"
    inside = data_dir / "processed" / "quality.json"

    assert redact_path(inside, data_dir=data_dir) == "processed/quality.json"
    assert (
        redact_path(
            r"C:\Users\private\external-data\processed\quality.json",
            data_dir=Path(r"C:\Users\private\external-data"),
        )
        == "processed/quality.json"
    )
    assert redact_path("/home/private/quality.json") == "quality.json"


def test_correlation_ids_are_bounded_and_replace_invalid_values() -> None:
    assert is_valid_correlation_id("observability-smoke-001")
    assert not is_valid_correlation_id("contains whitespace")
    assert not is_valid_correlation_id("contains/slash")
    assert not is_valid_correlation_id("x" * 129)

    assert resolve_correlation_id("observability-smoke-001") == "observability-smoke-001"
    generated = resolve_correlation_id("contains whitespace")
    assert is_valid_correlation_id(generated)
    assert generated != "contains whitespace"
    assert is_valid_correlation_id(generate_correlation_id())
