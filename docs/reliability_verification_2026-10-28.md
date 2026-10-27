# Reliability verification — 2026-10-28

## Scope and prior coverage

Audited `main` at `0ffcfc3ae4acc4bd33447affba829ad8c88d9877`. There were no open PRs at audit time. The repository already has immutable validation publications, guarded restore, lock/concurrent reader tests, transactional DuckDB partition reloads, dbt reconciliation/duplicate tests, API tests, a synthetic batch throughput benchmark, and Python/React/Playwright CI. No new infrastructure, hosted demo, production dataset, deployment, or data retention/garbage-collection behavior was changed.

This change adds **missing end-to-end evidence**, not a second restore implementation. All datasets/database paths are isolated `pytest tmp_path` or `TemporaryDirectory` synthetic data.

## Phase 2 — deterministic restore and reconciliation

Run `uv run pytest tests/integration/test_recovery_drill.py -v`.

The drill builds a three-record January 2026 fixture with one valid, one duplicate warning and one rejected record; validates and publishes revision A; loads DuckDB and runs `dbt run` plus `dbt test`. A fourth independent valid record is introduced and revision B is published and loaded. The guarded restore activates A while deliberately leaving B in the warehouse. Finally the drill pins A's `validated.parquet`, reloads the same DuckDB partition, reruns dbt, and checks the quality/analytics API and stored marts.

| Step | Quality valid/warning/rejected | Staging | Curated facts / API trips | Daily revenue | Duplicate anomalies |
| --- | --- | ---: | ---: | ---: | ---: |
| A baseline | 1 / 1 / 1 | 2 | 1 | 23.5 | 1 |
| B update | 2 / 1 / 1 | 3 | 2 | 59.5 | 1 |
| Restore A pointer only | 1 / 1 / 1 | **3 (stale)** | **2 (stale)** | **59.5 (stale)** | 1 |
| Reload A + rebuild/test dbt | 1 / 1 / 1 | 2 | 1 | 23.5 | 1 |

The drill explicitly verifies a real discrepancy **after pointer-only restore** and consistency after reconciliation, including quality summary, overview, daily mart, anomaly list, API metadata and row counts. Old immutable revisions remain on disk while the drill runs. Normal `TemporaryDirectory` and pytest fixture cleanup removes only isolated test data.

**Limit:** Restore is not an atomic cross-layer transaction. There is a visible inconsistency window between pointer restore and warehouse/dbt reconciliation. Operators must pause dependent readers/jobs or mark the dashboard unavailable during recovery and verify all layers before resuming. This drill does not implement an automatic multi-layer rollback or coordinated reader fencing.

## Phase 3 — NYC TLC timezone and DST semantics

Run `uv run pytest tests/integration/test_timezone_dst.py -v`.

NYC TLC pickup and dropoff columns currently enter the pipeline as **timezone-naive wall-clock timestamps**. The validator uses `try_cast(... as timestamp)` and naive `date_diff`, and dbt groups by pickup **wall-clock** date/hour. The event times are never automatically converted to UTC. `ingested_at` is an independently recorded UTC wall-time value stored without zone (historical compatibility).

Regression inputs include the 2026 New York spring transition, nonexistent local 02:20, repeated fall 01:15, backward-looking fall 01:50→01:10, missing/invalid timestamps, day/month crossings, event time versus ingestion time, preserved staging timestamps, and dbt/API date-hour grouping.

| Example | Current expected behavior (not a physical elapsed-time claim) |
| --- | --- |
| Spring 01:55→03:05 | Accepted, naive 70-minute duration |
| Spring nonexistent 02:20→03:00 | Accepted, naive 40-minute duration; impossible time not identifiable from source |
| Fall repeated 01:15→01:45 | Accepted, naive 30 minutes; no `fold` metadata |
| Fall 01:50→01:10 | Rejected as pickup after dropoff (even if actual trip might cross fold) |
| Jan 31→Feb 1 | Accepted, attributed to Jan 31 pickup date |
| Null / invalid timestamp | Rejected with existing missing-timestamp reason |

An ambiguous fall clock time maps to **two UTC instants one hour apart**. The input lacks offset/fold metadata, so inferring either instant would silently change business logic. **Known limitation:** duration near DST can differ from actual elapsed time; add an authoritative time-zone/offset field or source policy before introducing any UTC conversion or DST correction.

## Phase 4 — DuckDB SQL execution baseline

`scripts/benchmark_pipeline.py` already measures synthetic ingestion/validation/load/dbt throughput. The additional `scripts/benchmark_sql.py` specifically records `EXPLAIN`, `EXPLAIN ANALYZE`, a full plan SHA-256 fingerprint, and repeated local timings for five reader-critical SQL queries. It reuses the existing deterministic fixture generator, runs dbt locally, and removes the disposable database itself.

```powershell
uv run python scripts/benchmark_sql.py --rows 3000 --repetitions 3 --summary-only
# Omit --summary-only to include the full EXPLAIN and EXPLAIN ANALYZE plans.
uv run pytest tests/integration/test_sql_profile.py -v
```

Measured Windows 11 / Python 3.12.14 / DuckDB 1.5.3 with **3,001 source/staging rows** (3,000 distinct trips plus one duplicate warning) and **3,000 curated fact rows**; three warmed executions per query. The deliberate duplicate keeps the anomaly mart nonempty, avoiding an unrealistic `EMPTY_RESULT` query plan. Times are **milliseconds**, local observations only:

| Query | Rows targeted | Median ms | EXPLAIN plan SHA-256 prefix |
| --- | ---: | ---: | --- |
| Filtered fact overview | 3,000 | 0.720 | `b63134bc0495` |
| Date-filtered daily mart | 3,000 input | 0.631 | `7dac404c207c` |
| Date-filtered hourly mart | 3,000 input | 0.573 | `2b13e42a4ee5` |
| Route / two zone joins | 3,000 input | 1.409 | `841255c9b1c` |
| Date-filtered anomaly page | 3,001 input | 0.525 | `3fe8316847af` |

Actual `EXPLAIN` plans were inspected: the fact overview uses a sequential scan plus ungrouped aggregation; date-limited daily/hourly/anomaly mart reads use sequential scans and bounded `TOP_N`; route metrics join taxi zones with two hash joins and a bounded `TOP_N`. There is no partitioned DuckDB storage to prune; the small local tables make sequential scanning unsurprising. Existing queries already filter date where applicable, aggregate from prepared marts, and use bounded pagination. Route/zone joins are the most expensive of the measured five, but their absolute timing on this tiny dataset does **not** demonstrate a scalable bottleneck. **No SQL changes were made**, so before/after optimization is not applicable. Do not mistake the five plan fingerprints for universal stable plan snapshots; version or optimizer changes may alter them. The CI structural test checks that each query executes and yields a plan, not fragile millisecond/plan-hash thresholds. To compare later, keep row count, warmup, repetitions, DuckDB/dbt versions and hardware fixed and test a representative larger dataset.

## Verification and cleanup

Local verification on Windows 11, Python 3.12.14, DuckDB 1.5.3, and Node 24-equivalent frontend tooling:

- `uv run pytest -q`: **114 passed** (includes 13 newly added recovery / DST / SQL tests). One existing Starlette/httpx deprecation warning; not introduced by these tests.
- `uv run ruff check .`, `uv run ruff format --check .`, repository guardrails and readiness: **passed**.
- React Prettier, ESLint, TypeScript typecheck, Vitest (13 passed), and Vite build: **passed**.
- Isolated browser E2E sample fixture: **9 passed, 1 skipped** across desktop and mobile Chromium; pipeline dbt tests: **42 passed**.
- `docker compose config --quiet`: **passed**. `npm audit --prefix apps/web --audit-level=high`: **0 vulnerabilities**.
- SQL synthetic baseline of 3,000 rows / 5 statements / 3 repetitions: completed successfully with full EXPLAIN and EXPLAIN ANALYZE plans; no SQL optimization was justified on this workload.

The GitHub PR check results remain the authoritative hosted CI evidence. Tests do not delete active publication revisions or backups.

Only temporary resources created for this audit may be removed; do **not** run broad data-cleanup commands or touch an external `DATA_DIR`/`DUCKDB_PATH`. Verify the PR's exact-head CI checks and confirm that no temporary test process/workspace remains before closeout.
