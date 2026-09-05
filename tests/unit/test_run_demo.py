from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from scripts import run_demo as demo_module
from scripts.run_demo import run_demo


def test_run_demo_uses_offline_fixture_and_external_paths(tmp_path: Path) -> None:
    commands: list[tuple[list[str], dict[str, str]]] = []

    def record_command(
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        check: bool,
        **_: object,
    ) -> CompletedProcess[str]:
        assert cwd.is_dir()
        assert check is True
        commands.append((command, env))
        return CompletedProcess(command, 0)

    data_dir = tmp_path / "demo-data"
    result = run_demo(
        data_dir=data_dir,
        year=2026,
        month=1,
        service="yellow",
        sample_rows=1000,
        command_runner=record_command,
    )

    assert result["data_dir"] == str(data_dir.resolve())
    expected_database = (data_dir / "processed" / "urban_mobility.duckdb").resolve()
    assert result["duckdb_path"] == str(expected_database)
    assert result["steps"] == [
        "fixture",
        "profile",
        "validate",
        "load_duckdb",
        "dbt_parse",
        "dbt_run",
        "dbt_test",
    ]
    assert "scripts/create_demo_fixture.py" in " ".join(commands[0][0]).replace("\\", "/")
    assert all("urban_mobility.download" not in " ".join(command) for command, _ in commands)
    assert all(environment["DATA_DIR"] == str(data_dir.resolve()) for _, environment in commands)
    assert all(environment["DUCKDB_PATH"] == str(expected_database) for _, environment in commands)
    assert all(environment.keys() >= os.environ.keys() for _, environment in commands)


def test_cli_data_dir_keeps_default_database_beneath_it(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def capture_demo(**arguments: object) -> dict[str, object]:
        captured.update(arguments)
        return {"status": "ok"}

    monkeypatch.delenv("DUCKDB_PATH", raising=False)
    monkeypatch.setattr(demo_module, "run_demo", capture_demo)

    assert demo_module.main(["--data-dir", str(tmp_path)]) == 0
    assert captured["data_dir"] == tmp_path
    assert captured["duckdb_path"] is None


def test_run_demo_correlates_all_stages_and_children(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    commands: list[tuple[list[str], dict[str, str]]] = []

    def record_command(
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        check: bool,
        **_: object,
    ) -> CompletedProcess[str]:
        commands.append((command, env.copy()))
        return CompletedProcess(command, 0)

    run_id = "run-observability-001"
    result = run_demo(
        data_dir=tmp_path / "data",
        year=2026,
        month=1,
        service="yellow",
        sample_rows=1000,
        run_id=run_id,
        command_runner=record_command,
    )

    captured = capsys.readouterr()
    events = [json.loads(line) for line in captured.err.splitlines() if line]
    assert result["run_id"] == run_id
    assert len(commands) == 7
    assert all(environment["URBAN_MOBILITY_RUN_ID"] == run_id for _, environment in commands)
    assert events[0]["event"] == "pipeline.run.started"
    assert events[-1]["event"] == "pipeline.run.completed"
    started_stages = [
        event["stage"]
        for event in events
        if "stage" in event and event["event"] == "pipeline.stage.started"
    ]
    assert started_stages == [
        "fixture",
        "profile",
        "validate",
        "load_duckdb",
        "dbt_parse",
        "dbt_run",
        "dbt_test",
    ]
    assert {event["run_id"] for event in events} == {run_id}
    assert str(tmp_path) not in captured.err


def test_run_demo_emits_failed_events_and_preserves_stage_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls = 0

    def fail_on_validate(
        command: list[str],
        *,
        cwd: Path,
        env: dict[str, str],
        check: bool,
        **_: object,
    ) -> CompletedProcess[str]:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise subprocess.CalledProcessError(2, command)
        return CompletedProcess(command, 0)

    with pytest.raises(subprocess.CalledProcessError):
        run_demo(
            data_dir=tmp_path / "data",
            year=2026,
            month=1,
            service="yellow",
            sample_rows=1000,
            run_id="run-failure-001",
            command_runner=fail_on_validate,
        )

    captured = capsys.readouterr()
    events = [json.loads(line) for line in captured.err.splitlines() if line]
    assert events[-2]["event"] == "pipeline.stage.failed"
    assert events[-2]["stage"] == "validate"
    assert events[-2]["error_type"] == "CalledProcessError"
    assert events[-1]["event"] == "pipeline.run.failed"
    assert events[-1]["run_id"] == "run-failure-001"
    assert events[-1]["error_type"] == "CalledProcessError"
    assert str(tmp_path) not in "\n".join(json.dumps(event) for event in events)
