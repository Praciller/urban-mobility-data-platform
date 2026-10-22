# Bounded Real-Source Validation — 2026-10-22

This is **local, reproducible evidence**, not a production SLA or a full-dataset benchmark.
All inputs came from the official NYC TLC Yellow Taxi January and February 2026 Parquet files and the taxi-zone lookup. Each Parquet sample contains the **first 1,000 rows**, not a statistically representative random sample. No generated data, database, downloaded Parquet, or logs were committed.

## Environment and test scope

- Workstation: Windows 11, Python 3.12, DuckDB 1.5.3, dbt-duckdb 1.10.1.
- Run: 2026-10-22 (Asia/Bangkok), branch `chatgpt/urban-mobility-correctness-20261022`.
- External local data directory: temporary directory outside the repository.
- Official source: `https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2026-01.parquet` and `yellow_tripdata_2026-02.parquet`.
- Source file sizes (HTTP HEAD): January 64,165,080 bytes; February 58,683,353 bytes.
- January used DuckDB HTTPFS remote Parquet sampling.
- February's HTTPFS sampling failed; the public full Parquet was downloaded using the project's downloader and a local 1,000-row sample was then generated. Both approaches were run locally without paid infrastructure.

## Validated results

| Month | Input | Valid | Warning | Rejected | Loaded staging |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2026-01 | 1,000 | 973 | 20 | 7 | 993 |
| 2026-02 | 1,000 | 966 | 28 | 6 | 994 |
| **Total** | **2,000** | **1,939** | **48** | **13** | **1,987** |

January rule counts: 7 `negative_fare_amount`, 7 `negative_total_amount` (same rejected records), and 20 `zero_duration_positive_distance` warnings.
February: 5 `negative_fare_amount`, 6 `negative_total_amount`, and 28 `zero_duration_positive_distance` warnings. Rule counts overlap, so they must not be summed to obtain rejected-row counts.

- `dbt run`: **14/14 models passed**, zero warnings/errors (measured dbt run stage: 0.49 s).
- `dbt test`: **42/42 passed**, zero warnings/errors (measured dbt test stage: 0.70 s).
- Warehouse: **1,987** staging records, **1,987** curated facts, **4** populated daily-mart dates, **68** anomaly-mart rows.
- Curated total revenue on these bounded samples: **$50,640.85**.
- Confirmed duplicate-warning count: **0** in these samples. The synthetic duplicate fixture separately tests exclusion from curated KPIs.
- All writes were isolated to the temporary local data directory, with no changes to hosted Render services.

## Reproduction (PowerShell)

From the repo root, choose an **external** disposable data directory.

```powershell
$env:DATA_DIR = Join-Path $env:TEMP "urban-mobility-real-sample"
$env:DUCKDB_PATH = Join-Path $env:DATA_DIR "processed/urban_mobility.duckdb"
uv sync --locked --all-groups

# Try a bounded HTTPFS sample for both months.
uv run python -m urban_mobility.download --year 2026 --month 1 --service yellow --sample-rows 1000
uv run python -m urban_mobility.download --year 2026 --month 2 --service yellow --sample-rows 1000
```

When HTTPFS cannot read the remote February file, a local fallback is possible by downloading the full source **outside the repository**. This transfers the entire source Parquet; use only if the additional bandwidth/disk consumption is acceptable. Then use `materialize_sample` to create a bounded file from the local raw Parquet (see `src/urban_mobility/download.py`).

```powershell
uv run python -m urban_mobility.download --year 2026 --month 2 --service yellow
# Produce the 1000-row sample from the downloaded raw file using
# urban_mobility.download.materialize_sample(raw_path, sample_path, 1000).
```

Then:

```powershell
foreach ($month in 1,2) {
    uv run python -m urban_mobility.validate --year 2026 --month $month --service yellow --mode sample
    uv run python -m urban_mobility.load_duckdb --year 2026 --month $month --service yellow
}
uv run dbt run  --project-dir dbt --profiles-dir dbt
uv run dbt test --project-dir dbt --profiles-dir dbt
```

## Limitations and follow-ups

- Two 1,000-row sequential extracts **cannot establish** production ingestion throughput, memory limits, representativeness, or historical data quality.
- HTTPFS network-read reliability is not proven; January passed but February required local-file fallback.
- Validate against larger and intentionally overlapping monthly partitions before enabling unattended backfills.
- Current Parquet publication handles ordinary failures with rollback but is not crash-atomic across the validated, rejected, and summary files.
