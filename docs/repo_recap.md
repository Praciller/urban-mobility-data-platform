# Repository Recap

## Current State

The repository contains a local-first urban mobility analytics platform for NYC TLC Yellow Taxi
data. The working path is:

```text
offline fixture or bounded sample
-> raw profile
-> validation and rejected rows
-> DuckDB staging
-> dbt dimensions, fact, and marts
-> read-only FastAPI analytics API
-> React dashboard
-> local Dagster orchestration
```

## Implemented Components

- Python package and `uv` workflow for local development.
- External `DATA_DIR` and `DUCKDB_PATH` support.
- Tiny offline demo fixture for repeatable screenshots and review.
- Metadata-first profiling and rule-based validation.
- Validated/rejected Parquet outputs under local data directories.
- Idempotent DuckDB load for one service/year/month.
- dbt staging, dimensions, fact table, marts, documentation, and tests.
- Read-only FastAPI API over DuckDB/dbt models.
- React TypeScript dashboard over the API.
- Dagster assets, jobs, and stopped local schedule.
- Repository guardrails and readiness checks.
- PowerShell-friendly local demo, portfolio review, and publish docs.

## Verification Baseline

Latest local baseline for the Phase 8 handoff:

- Python tests: 56 passing before Phase 8 additions.
- dbt: 14 models build and 40 data tests pass with the offline fixture.
- Frontend: Vitest, typecheck, and build pass.
- Dagster definitions validate.
- Generated artifacts are ignored.

## Review Focus

Reviewers should inspect:

- `src/urban_mobility/validate.py` for data quality rules.
- `src/urban_mobility/load_duckdb.py` for idempotent loading.
- `dbt/models/` for analytics modeling and tests.
- `apps/api/app/repositories/analytics.py` for read-only query boundaries.
- `apps/web/src/api/client.ts` for dashboard/API contract.
- `pipelines/dagster_project/dagster_project/assets/tlc_pipeline.py` for orchestration.
- `scripts/check_repo_guardrails.py` and `scripts/check_repo_readiness.py` for publish safety.

## Known Warnings

- Dashboard pages and Recharts are route-split; the initial build chunk stays below 500 kB.
- Dagster definition validation currently emits a CLI deprecation warning.
- The offline fixture is intentionally tiny and not representative of full TLC volume.
