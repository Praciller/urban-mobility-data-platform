# Operations

Use PowerShell commands from the repository root unless a step says otherwise. GNU Make targets are
optional convenience wrappers and are not required locally.

## Environment

Keep data outside OneDrive-backed source folders for real runs:

```powershell
$env:DATA_DIR = "C:/data/urban-mobility-data-platform"
$env:DUCKDB_PATH = "$env:DATA_DIR/processed/urban_mobility.duckdb"
$env:DAGSTER_HOME = "$PWD/.dagster"
```

## Offline Demo Run

```powershell
uv sync --locked --all-groups
npm install --prefix apps/web
uv run python scripts/create_demo_fixture.py --year 2026 --month 1 --service yellow --sample-rows 1000
uv run python -m urban_mobility.ingest inspect --year 2026 --month 1 --service yellow --mode sample --sample-rows 1000
uv run python -m urban_mobility.validate --year 2026 --month 1 --service yellow
uv run python -m urban_mobility.load_duckdb --year 2026 --month 1 --service yellow
uv run dbt parse --project-dir dbt --profiles-dir dbt
uv run dbt run --project-dir dbt --profiles-dir dbt
uv run dbt test --project-dir dbt --profiles-dir dbt
uv run dbt docs generate --project-dir dbt --profiles-dir dbt
```

The fixture command writes a tiny local sample and zone lookup. It does not call remote data
sources.

## Reruns

- Fixture creation overwrites the tiny demo fixture for the selected service/year/month.
- Validation overwrites the selected validated/rejected partition outputs.
- DuckDB loading deletes and reloads only the selected service/year/month in staging.
- dbt rebuilds marts from the current DuckDB staging state.
- Dagster materialization is idempotent for the same local files and month.

## Reset

Remove generated local outputs:

```powershell
uv run python scripts/clean_generated.py
```

For external data directories, remove generated content directly from the external `DATA_DIR` if
you need a clean warehouse. Do not delete raw full datasets unless that is intentional.

## dbt

```powershell
uv run dbt parse --project-dir dbt --profiles-dir dbt
uv run dbt run --project-dir dbt --profiles-dir dbt
uv run dbt test --project-dir dbt --profiles-dir dbt
uv run dbt docs generate --project-dir dbt --profiles-dir dbt
uv run dbt docs serve --project-dir dbt --profiles-dir dbt
```

## FastAPI

```powershell
uv run uvicorn apps.api.app.main:app --reload --host 127.0.0.1 --port 8000
```

Checks:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/metadata
Invoke-RestMethod http://127.0.0.1:8000/quality/summary
Invoke-RestMethod "http://127.0.0.1:8000/metrics/daily?limit=10"
```

## Dashboard

```powershell
cd apps/web
npm install
$env:VITE_API_BASE_URL = "http://localhost:8000"
npm run dev -- --host 127.0.0.1
```

Checks:

```powershell
npm test
npm run lint
npm run build
npm audit --omit=optional
```

## Readiness

```powershell
uv run python scripts/check_repo_guardrails.py
uv run python scripts/check_repo_readiness.py
```

Run these checks before staging or publishing the repository.

## Dagster

```powershell
uv run dagster definitions validate -m dagster_project.definitions
$env:DAGSTER_ASSETS = "taxi_zone_lookup,raw_yellow_trip_file,raw_trip_profile,validated_trip_data,duckdb_staging,dbt_models,data_quality_report,analytics_ready"
uv run dagster asset materialize --select $env:DAGSTER_ASSETS -m dagster_project.definitions
uv run dagster dev -m dagster_project.definitions
```

The local monthly schedule is stopped by default. It is for demos only.

## Docker

The default image starts FastAPI and expects a populated DuckDB database mounted at
`/data/processed/urban_mobility.duckdb`. Compose bind-mounts `DATA_DIR` to `/data`, so run the
offline demo against the same `DATA_DIR` before starting the container.

```powershell
docker compose config
docker compose up --build
Invoke-RestMethod http://127.0.0.1:8000/health
```

## Troubleshooting

See [troubleshooting.md](troubleshooting.md) for common local issues.
