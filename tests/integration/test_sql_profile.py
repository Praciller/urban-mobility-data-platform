"""Non-flaky structural smoke test for the five query plans.

Runtime observations are recorded, never enforced as hard timing budgets.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_local_sql_profile_produces_explain_baselines_without_artifacts() -> None:
    project = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_sql.py",
            "--rows",
            "30",
            "--repetitions",
            "1",
            "--summary-only",
        ],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["rows"] == report["staging_rows"] == report["facts_rows"] == 30
    assert set(report["queries"]) == {
        "filtered_overview",
        "daily_mart_page",
        "hourly_mart_page",
        "route_zone_joins",
        "anomaly_page",
    }
    for observed in report["queries"].values():
        assert observed["plan_sha256"] and len(observed["plan_sha256"]) == 64
        assert observed["samples_ms"] and observed["median_ms"] >= 0
        assert "plan" not in observed  # --summary-only leaves fingerprints, not megabytes
