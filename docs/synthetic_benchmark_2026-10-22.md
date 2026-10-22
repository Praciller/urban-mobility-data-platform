# Synthetic Batch Benchmark — 2026-10-22

Local-only baseline for the Python/PyArrow/DuckDB/dbt pipeline on the authorized Windows 11 developer workstation, using Python 3.12. This is a **single pass per size**, not a statistically significant performance evaluation or a representative real NYC TLC workload.

The `scripts/benchmark_pipeline.py` generator writes January 2026 synthetic taxi rows in bounded PyArrow batches, with unique timestamps, valid pickup/dropoff zones and no rejected rows. Each benchmark uses a fresh temporary folder outside the repository and removes all intermediate data and databases after completion. The measured phases are source file creation, Validation, DuckDB load, `dbt run`, and `dbt test`.

| Rows | Input generation (s) | Validation (s) | DuckDB Load (s) | dbt run (s) | dbt test (s) | Total (s) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1,000 | 0.008 | 0.057 | 0.039 | 3.389 | 3.731 | 7.224 |
| 10,000 | 0.035 | 0.121 | 0.082 | 3.793 | 3.080 | 7.111 |
| 50,000 | 0.138 | 0.315 | 0.189 | 3.434 | 2.767 | 6.843 |

All benchmark rows were valid and loaded; dbt run/test returned success for all three input sizes. Re-run with:

```powershell
uv sync --locked --all-groups
uv run python scripts/benchmark_pipeline.py --rows 1000
uv run python scripts/benchmark_pipeline.py --rows 10000
uv run python scripts/benchmark_pipeline.py --rows 50000
```

The script enforces 1–50,000 rows. `--skip-dbt` runs only input creation, Validation and DuckDB load; do not compare this option with full end-to-end results. The durations include dbt CLI startup and can fluctuate with filesystem cache, system load, antivirus, PowerShell process startup, and hardware conditions.

**Interpretation:** The 1k and 50k measured totals are close because dbt process-start overhead dominates this short synthetic workload. Do **not** infer linear scaling, a sustainable rows/second rate, SLA, peak memory, or performance on real full-month taxi data. For defensible capacity results, run multiple warm/cold trials, observe memory/CPU, sample real files, and report distributions such as p50/p95 and machine details.
