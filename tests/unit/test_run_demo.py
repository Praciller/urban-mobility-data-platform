from __future__ import annotations

import os
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
