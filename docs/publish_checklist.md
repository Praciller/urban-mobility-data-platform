# Publish Checklist

Use this checklist when preparing the repository for GitHub and portfolio review.

## Final Test Commands

```powershell
uv sync --locked --all-groups
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python scripts/check_repo_guardrails.py
uv run python scripts/check_repo_readiness.py
uv run python scripts/run_demo.py --data-dir $env:DATA_DIR
uv run dbt parse --project-dir dbt --profiles-dir dbt
uv run dbt run --project-dir dbt --profiles-dir dbt
uv run dbt test --project-dir dbt --profiles-dir dbt
uv run dbt docs generate --project-dir dbt --profiles-dir dbt
uv run dagster definitions validate -m dagster_project.definitions
cd apps/web
npm test -- --run
npm run lint
npm run build
cd ../..
```

Run the dbt commands after creating the offline fixture and loading DuckDB as documented in
[local_demo.md](local_demo.md).

## Screenshot Checklist

Only add small intentional screenshots under `docs/screenshots/`:

- `fastapi-openapi.png`
- `dashboard-overview.png`
- `dashboard-anomalies.png`
- `dashboard-quality.png`
- `dagster-assets.png`
- `dagster-analytics-ready.png`

Do not add raw data, database files, generated dbt output, local Dagster storage, or large images.

## README Review Checklist

- The opening summary explains the local-first data platform clearly.
- The architecture diagram renders on GitHub.
- Quickstart commands use PowerShell syntax.
- The local demo does not require official dataset downloads.
- The API is described as read-only.
- Limitations are explicit and current.
- Future improvements do not imply completed functionality.
- Documentation links work.

## GitHub Repository Settings Checklist

- Description: `Local-first NYC TLC mobility analytics platform with DuckDB, dbt, Dagster, FastAPI, and React.`
- Website: leave blank unless a verified portfolio page exists.
- Visibility: public only after final verification passes.
- Issues: enable if you want to track backlog items publicly.
- Wiki: disabled unless documentation moves there intentionally.
- Discussions: optional; not required for portfolio review.
- Actions: enabled for CI.

## Topics

Recommended topics:

- `data-engineering`
- `analytics-engineering`
- `duckdb`
- `dbt`
- `dagster`
- `fastapi`
- `react`
- `typescript`
- `nyc-tlc`
- `data-quality`
- `portfolio-project`

## Release Recommendation

Recommended tag:

```text
v0.1.0-local-demo
```

Suggested release title:

```text
v0.1.0 Local Demo
```

Attach no raw datasets, databases, generated reports, build outputs, or screenshots unless they are
small intentional portfolio images.

## Portfolio Summary Bullets

- Built a local-first urban mobility data platform using NYC TLC Taxi trip data, DuckDB, dbt,
  Dagster, FastAPI, and React.
- Implemented ingestion, profiling, validation, rejected-row handling, DuckDB loading, dbt marts,
  analytics API, dashboard, and local orchestration.
- Added fixture-based tests, guardrails, documentation, and reproducible PowerShell-friendly demo
  workflow without paid services or cloud accounts.
