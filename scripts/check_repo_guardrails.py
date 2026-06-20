from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

MAX_FILE_BYTES = 1_048_576
BLOCKED_SUFFIXES = {
    ".arrow",
    ".bundle",
    ".db",
    ".duckdb",
    ".feather",
    ".parquet",
    ".sqlite",
    ".sqlite3",
}
BLOCKED_DIRECTORIES = {
    ("data", "processed"),
    ("data", "raw"),
}
SECRET_MARKERS = (
    "-----BEGIN " + "PRIVATE KEY-----",
    "gh" + "p_",
    "github_pat" + "_",
)
AWS_ACCESS_KEY = re.compile(r"\bAKIA[0-9A-Z]{16}\b")


def git_tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def is_blocked_path(path: Path) -> str | None:
    normalized = tuple(part.lower() for part in path.parts)

    if path.name == ".env":
        return "local .env files must not be committed"
    if path.suffix.lower() in BLOCKED_SUFFIXES:
        return f"{path.suffix} artifacts must not be committed"

    for blocked in BLOCKED_DIRECTORIES:
        if normalized[: len(blocked)] == blocked and path.name != ".gitkeep":
            return f"generated files under {'/'.join(blocked)} must not be committed"

    return None


def find_secret_marker(path: Path) -> str | None:
    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None

    for marker in SECRET_MARKERS:
        if marker in content:
            return f"possible secret marker {marker!r}"
    if AWS_ACCESS_KEY.search(content):
        return "possible AWS access key"
    return None


def validate(paths: list[str]) -> list[str]:
    violations: list[str] = []

    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_file():
            continue

        blocked_reason = is_blocked_path(path)
        if blocked_reason:
            violations.append(f"{path}: {blocked_reason}")
            continue

        if path.stat().st_size > MAX_FILE_BYTES:
            violations.append(f"{path}: exceeds the 1 MiB repository file limit")
            continue

        secret_reason = find_secret_marker(path)
        if secret_reason:
            violations.append(f"{path}: {secret_reason}")

    return violations


def main() -> int:
    paths = sys.argv[1:] or git_tracked_files()
    violations = validate(paths)
    if not violations:
        print(f"Repository guardrails passed for {len(paths)} file(s).")
        return 0

    print("Repository guardrails failed:", file=sys.stderr)
    for violation in violations:
        print(f"- {violation}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
