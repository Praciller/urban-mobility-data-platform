from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

MAX_TRACKED_FILE_BYTES = 1_048_576

REQUIRED_PATHS = (
    "PROJECT_REQUIREMENTS_NO_SUPABASE.md",
    "README.md",
    ".gitignore",
    ".env.example",
    "pyproject.toml",
    "uv.lock",
    ".github/workflows/ci.yml",
    "dbt/dbt_project.yml",
    "dbt/profiles.yml",
    "apps/api/app/repositories/quality.py",
    "apps/web/package.json",
    "scripts/run_demo.py",
    "docs/architecture.md",
    "docs/local_demo.md",
    "docs/portfolio_review.md",
    "docs/final_verification.md",
    "docs/backlog.md",
    "docs/publish_checklist.md",
    "docs/screenshots/dashboard-overview.png",
)

FORBIDDEN_TRACKED_SUFFIXES = {
    ".arrow",
    ".bundle",
    ".db",
    ".duckdb",
    ".feather",
    ".parquet",
    ".sqlite",
    ".sqlite3",
}

FORBIDDEN_TRACKED_PREFIXES = (
    ("data", "raw"),
    ("data", "processed"),
    ("data", "sample"),
    ("dbt", "target"),
    ("dbt", "logs"),
    (".dagster",),
    ("apps", "web", "dist"),
    ("node_modules",),
    ("apps", "web", "node_modules"),
)

IGNORE_PROBES = (
    ".env",
    ".venv/pyvenv.cfg",
    "data/raw/example.parquet",
    "data/sample/example.parquet",
    "data/processed/urban_mobility.duckdb",
    "reports/data_quality/example.json",
    "dbt/target/manifest.json",
    "dbt/logs/dbt.log",
    ".dagster/storage/test",
    ".tmp_dagster_home_test/storage/test",
    "apps/web/dist/index.html",
    "apps/web/node_modules/package.json",
    "apps/web/tsconfig.tsbuildinfo",
    ".playwright-cli/page.yml",
    "output/playwright/page.png",
)

IMPLEMENTATION_SCAN_PATHS = (
    "apps",
    "src",
    "pipelines",
    "tests",
    "dbt",
    ".github",
    "pyproject.toml",
    "docker-compose.yml",
    "apps/web/package.json",
    "apps/web/package-lock.json",
)

EXCLUDED_SCAN_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "dist",
    "node_modules",
    "target",
    "__pycache__",
}

GITHUB_CLASSIC_TOKEN_PREFIX = "gh" + "p_"
GITHUB_FINE_GRAINED_TOKEN_PREFIX = "github" + "_pat_"

SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(rf"\b{re.escape(GITHUB_CLASSIC_TOKEN_PREFIX)}[A-Za-z0-9_]{{20,}}\b"),
    re.compile(rf"\b{re.escape(GITHUB_FINE_GRAINED_TOKEN_PREFIX)}[A-Za-z0-9_]{{20,}}\b"),
)


@dataclass(frozen=True)
class CheckResult:
    name: str
    violations: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.violations


def run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=check,
        capture_output=True,
        text=True,
    )


def tracked_files(repo: Path) -> list[Path]:
    result = run_git(repo, "ls-files")
    return [Path(line) for line in result.stdout.splitlines() if line]


def check_required_paths(repo: Path) -> CheckResult:
    missing = tuple(path for path in REQUIRED_PATHS if not (repo / path).exists())
    return CheckResult("required_paths", missing)


def forbidden_tracked_reason(path: Path) -> str | None:
    normalized = tuple(part.lower() for part in path.parts)

    if path.name == ".env":
        return ".env must remain local-only"
    if path.suffix.lower() in FORBIDDEN_TRACKED_SUFFIXES:
        return f"{path.suffix} generated data/database artifacts must not be tracked"
    for prefix in FORBIDDEN_TRACKED_PREFIXES:
        if normalized[: len(prefix)] == prefix and path.name != ".gitkeep":
            return f"generated files under {'/'.join(prefix)} must not be tracked"
    return None


def check_tracked_artifacts(repo: Path, paths: list[Path]) -> CheckResult:
    violations: list[str] = []
    for path in paths:
        reason = forbidden_tracked_reason(path)
        if reason:
            violations.append(f"{path.as_posix()}: {reason}")
            continue

        absolute = repo / path
        if absolute.is_file() and absolute.stat().st_size > MAX_TRACKED_FILE_BYTES:
            violations.append(f"{path.as_posix()}: tracked file exceeds 1 MiB")

    return CheckResult("tracked_artifacts", tuple(violations))


def check_ignore_rules(repo: Path) -> CheckResult:
    violations = []
    for probe in IGNORE_PROBES:
        result = run_git(repo, "check-ignore", "-q", "--", probe, check=False)
        if result.returncode != 0:
            violations.append(f"{probe}: expected .gitignore to ignore this generated/local path")
    return CheckResult("ignore_rules", tuple(violations))


def iter_scan_files(repo: Path) -> list[Path]:
    files: list[Path] = []
    for raw_path in IMPLEMENTATION_SCAN_PATHS:
        path = repo / raw_path
        if not path.exists():
            continue
        if path.is_file():
            files.append(path)
            continue
        for child in path.rglob("*"):
            if not child.is_file():
                continue
            if EXCLUDED_SCAN_PARTS.intersection(child.relative_to(repo).parts):
                continue
            files.append(child)
    return files


def read_text_safely(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def check_forbidden_platform_refs(repo: Path) -> CheckResult:
    violations = []
    for path in iter_scan_files(repo):
        content = read_text_safely(path)
        if content is None:
            continue
        if "supabase" in content.casefold():
            violations.append(f"{path.relative_to(repo).as_posix()}: forbidden platform reference")
    return CheckResult("forbidden_platform_refs", tuple(violations))


def check_secret_markers(repo: Path, paths: list[Path]) -> CheckResult:
    violations = []
    for path in paths:
        content = read_text_safely(repo / path)
        if content is None:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                violations.append(f"{path.as_posix()}: possible secret marker")
                break
    return CheckResult("secret_markers", tuple(violations))


def run_checks(repo: Path) -> list[CheckResult]:
    tracked = tracked_files(repo)
    return [
        check_required_paths(repo),
        check_tracked_artifacts(repo, tracked),
        check_ignore_rules(repo),
        check_forbidden_platform_refs(repo),
        check_secret_markers(repo, tracked),
    ]


def print_results(results: list[CheckResult]) -> None:
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.name}")
        for violation in result.violations:
            print(f"  - {violation}")


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    results = run_checks(repo)
    print_results(results)
    if all(result.passed for result in results):
        print("Repository readiness checks passed.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
