# Local Demo Workflow

This workflow runs without a real official dataset download. It uses a tiny local fixture under
external `DATA_DIR`, then exercises validation, DuckDB, dbt, Dagster, FastAPI, and React.

## 1. Configure Environment

```powershell
$env:DATA_DIR = "C:/data/urban-mobility-data-platform"
$env:DUCKDB_PATH = "$env:DATA_DIR/processed/urban_mobility.duckdb"
$env:DAGSTER_HOME = "$PWD/.dagster"
```

## 2. Install Dependencies

```powershell
uv sync --locked --all-groups
npm install --prefix apps/web
```

## 3. Run The One-Command Demo

```powershell
uv run python scripts/run_demo.py --data-dir $env:DATA_DIR --year 2026 --month 1 --service yellow --sample-rows 1000
```

The command creates the offline fixture, profiles and validates it, writes valid/rejected
Parquet, replaces the selected month in DuckDB staging, builds dbt models, and runs dbt tests.
It is idempotent for the selected service/year/month. It never invokes the official downloader.

GNU Make users can run the same path with `make demo` after setting `DATA_DIR` and
`DUCKDB_PATH`.

Expected outputs:

```text
{DATA_DIR}/sample/tlc/service=yellow/year=2026/month=01/yellow_tripdata_2026-01_sample_1000.parquet
{DATA_DIR}/raw/tlc/taxi_zone_lookup.csv
```

## 4. Inspect Or Run Individual Pipeline Steps

```powershell
uv run python -m urban_mobility.ingest inspect --year 2026 --month 1 --service yellow --mode sample --sample-rows 1000
uv run python -m urban_mobility.validate --year 2026 --month 1 --service yellow
uv run python -m urban_mobility.load_duckdb --year 2026 --month 1 --service yellow
uv run dbt parse --project-dir dbt --profiles-dir dbt
uv run dbt run --project-dir dbt --profiles-dir dbt
uv run dbt test --project-dir dbt --profiles-dir dbt
uv run dbt docs generate --project-dir dbt --profiles-dir dbt
```

## 5. Run Dagster

```powershell
uv run dagster definitions validate -m dagster_project.definitions
$env:DAGSTER_ASSETS = "taxi_zone_lookup,raw_yellow_trip_file,raw_trip_profile,validated_trip_data,duckdb_staging,dbt_models,data_quality_report,analytics_ready"
uv run dagster asset materialize --select $env:DAGSTER_ASSETS -m dagster_project.definitions
uv run dagster dev -m dagster_project.definitions
```

Open Dagster at the URL printed by the command and inspect:

- asset graph
- `analytics_ready` materialization
- asset metadata paths and row counts
- stopped `local_monthly_tlc_schedule`

## 6. Start FastAPI

```powershell
uv run uvicorn apps.api.app.main:app --reload --host 127.0.0.1 --port 8000
```

Check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/metadata
Invoke-RestMethod "http://127.0.0.1:8000/metrics/overview"
```

Open `http://127.0.0.1:8000/docs`.

## 7. Start Dashboard

```powershell
cd apps/web
$env:VITE_API_BASE_URL = "http://localhost:8000"
npm run dev -- --host 127.0.0.1
```

Open the local Vite URL printed by the command.

## 8. Screenshot Checklist

Save small screenshots under `docs/screenshots/`:

- `fastapi-openapi.png`: FastAPI docs page
- `dashboard-overview.png`: Overview page with KPIs and charts
- `dashboard-anomalies.png`: Anomaly Explorer table
- `dashboard-quality.png`: Data Quality / Pipeline Status
- `dagster-assets.png`: Dagster asset graph
- `dagster-analytics-ready.png`: `analytics_ready` materialization metadata

The repository currently includes verified local captures for the Overview, Anomaly Explorer,
and Data Quality pages. Regenerate them after material dashboard changes.

Do not commit raw data, DuckDB files, dbt targets, Dagster storage, or large images.

## 9. Final Verification

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python scripts/check_repo_guardrails.py
uv run python scripts/check_repo_readiness.py
cd apps/web
npm test
npm run lint
npm run build
cd ../..
```

See [final_verification.md](final_verification.md) before publishing or tagging the repository.
