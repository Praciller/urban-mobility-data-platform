from pathlib import Path

from urban_mobility.__main__ import main
from urban_mobility.config import get_data_dir


def test_data_dir_defaults_to_project_data(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATA_DIR", raising=False)

    assert get_data_dir() == tmp_path / "data"


def test_data_dir_supports_external_location(monkeypatch, tmp_path: Path) -> None:
    external_data = tmp_path / "external-data"
    monkeypatch.setenv("DATA_DIR", str(external_data))

    assert get_data_dir() == external_data


def test_bootstrap_entrypoint_reports_configuration(capsys) -> None:
    assert main() == 0

    output = capsys.readouterr().out
    assert "Phase 1 bootstrap" in output
    assert "DATA_DIR=" in output
