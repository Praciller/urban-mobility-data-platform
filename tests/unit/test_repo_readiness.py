from pathlib import Path

from scripts.check_repo_readiness import (
    check_forbidden_platform_refs,
    forbidden_tracked_reason,
)


def test_forbidden_tracked_reason_flags_generated_artifacts() -> None:
    assert forbidden_tracked_reason(Path(".env")) == ".env must remain local-only"
    assert forbidden_tracked_reason(Path("data/raw/example.parquet")) is not None
    assert forbidden_tracked_reason(Path("data/processed/warehouse.duckdb")) is not None
    assert forbidden_tracked_reason(Path("apps/web/dist/index.html")) is not None
    assert forbidden_tracked_reason(Path("recovered.bundle")) is not None


def test_forbidden_tracked_reason_allows_placeholders() -> None:
    assert forbidden_tracked_reason(Path("data/raw/.gitkeep")) is None
    assert forbidden_tracked_reason(Path("data/processed/.gitkeep")) is None
    assert forbidden_tracked_reason(Path("docs/backlog.md")) is None


def test_forbidden_platform_scan_ignores_docs_but_flags_implementation(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    app = tmp_path / "apps" / "api"
    docs.mkdir()
    app.mkdir(parents=True)
    forbidden_name = "Supa" + "base"
    (docs / "note.md").write_text(
        f"No {forbidden_name} implementation is allowed.\n",
        encoding="utf-8",
    )
    (app / "config.py").write_text(
        f"{forbidden_name.upper()}_URL = 'https://example.invalid'\n",
        encoding="utf-8",
    )

    result = check_forbidden_platform_refs(tmp_path)

    assert not result.passed
    assert result.violations == ("apps/api/config.py: forbidden platform reference",)
