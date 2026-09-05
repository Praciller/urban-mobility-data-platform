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
npm run format:check
npm run lint
npm run typecheck
npm run test
npm run build
npm audit --audit-level=high
```

The deterministic browser gate creates the tiny sample dataset in the system temporary directory,
starts the local API and Vite server, and tests Chromium at desktop and mobile viewports:

```powershell
uv sync --locked --all-groups
npm run e2e:install
npm run e2e
```

If port `8000` is already in use, choose another API port for the local run:

```powershell
$env:URBAN_MOBILITY_E2E_API_PORT = "8002"
npm run e2e
```

Failure diagnostics are written to ignored `playwright-report/` and `test-results/` directories.
CI publishes those directories as the `playwright-report` artifact. The `web-format`, `web-lint`,
`web-typecheck`, `web-unit`, `web-build`, and `web-e2e` checks are intentionally independent.
The security job enforces `npm audit --audit-level=high`. GitHub dependency review was evaluated,
but this repository currently has Dependency Graph disabled; enabling it is an owner-controlled
repository setting and is outside this issue's scope.

## Main branch governance

The default `main` branch is governed by the active repository ruleset `main-quality-gate`, which
targets `refs/heads/main`.

- Changes must arrive through a pull request. This repository is maintained as a solo project, so
  zero human approvals are required; code-owner, last-push, stale-review, review-thread, and
  unattributed-change approval requirements are disabled.
- The required GitHub Actions checks are `python`, `web-format`, `web-lint`, `web-typecheck`,
  `web-unit`, `web-build`, `web-e2e`, `web-storybook`, and `dependency-security`. Each is tied to
  the GitHub Actions integration configured in the ruleset.
- The strict/up-to-date status policy is disabled because the suite includes expensive browser and
  Storybook jobs. A pull request must still pass every required check; it is not forced to rerun
  only because `main` advanced after the check completed.
- Branch deletion and non-fast-forward updates (including force pushes) are blocked. No permanent
  bypass actor is configured. Owner/admin recovery requires an explicit ruleset administration
  action and remains auditable.
- Squash is the preferred normal merge method. Merge and rebase remain allowed because the
  repository's existing merge methods are unchanged.

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
