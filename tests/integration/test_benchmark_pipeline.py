from __future__ import annotations

import pytest

from scripts.benchmark_pipeline import MAX_ROWS, benchmark


def test_benchmark_is_bounded_and_runs_offline() -> None:
    result = benchmark(120, include_dbt=False)
    assert result["rows"] == 120
    assert result["loaded_rows"] == 120
    assert result["valid_rows"] == 120
    assert result["warning_rows"] == 0
    assert result["dbt_included"] is False


@pytest.mark.parametrize("rows", [0, -1, MAX_ROWS + 1])
def test_benchmark_rejects_unsafe_sizes(rows: int) -> None:
    with pytest.raises(ValueError, match="between"):
        benchmark(rows, include_dbt=False)
