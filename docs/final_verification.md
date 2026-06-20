# Final Verification

Use this checklist before publishing the repository or cutting a local-demo tag. Commands are
PowerShell-friendly and assume the repository root as the starting directory.

## Verification Snapshot

The full baseline was verified locally on 2026-06-20 before the latest quality/API gap closure:

- 62 Python tests passed; Ruff lint and format checks passed.
- The offline demo completed twice with 2 validated staging/fact rows, proving month-level
  idempotency.
- 14 dbt models built, 40 dbt tests passed, and dbt docs generated.
- All 8 Dagster assets materialized from the local fixture with remote downloads disabled.
- 6 frontend tests, TypeScript checking, and the Vite production build passed.
- Browser checks covered Overview, Anomaly Explorer, Data Quality, and FastAPI OpenAPI with no
  console errors; evidence is under `docs/screenshots/`.
- The Docker image built from the lockfile and the Compose API returned `status=ok`, 2 trips, and
  $47.00 revenue from the bind-mounted demo database.

The latest gap-closure pass verified on 2026-06-20 at 14:42 +07:00:

- Git history is restored at `6a9d99f`; `recovered.bundle` is ignored and no longer required.
- `uv sync --locked --all-groups` completed against the existing environment.
- 10 frontend tests, TypeScript checking, and the route-split Vite production build.
- 5 focused Python tests for repository readiness and validation-summary sanitization.
- Repository readiness, tracked and 138-file workspace guardrail scans, and
  `docker compose config`.

Native verification was rerun outside the restricted shell with temporary files, the virtual
environment, data, and DuckDB stored outside the repository:

```text
TEMP=C:\tmp\urban-temp
TMP=C:\tmp\urban-temp
PYTEST_ADDOPTS=--basetemp=C:\tmp\pytest-urban
UV_PROJECT_ENVIRONMENT=C:\venvs\urban-mobility-data-platform
DATA_DIR=C:\data\urban-mobility-data-platform
DUCKDB_PATH=C:\data\urban-mobility-data-platform\processed\urban_mobility.duckdb
```

The native verification completed successfully:

- `uv sync --locked --all-groups` passed using the external virtual environment.
- 66 pytest tests passed; the only warning was inability to write pytest cache data.
- `ruff check .` passed.
- `ruff format --check .` passed with all 52 files already formatted.
- Repository guardrails passed for 107 tracked files, repository readiness passed, and
  `git diff --check` passed.
- Persisted dbt results show 40 passing tests.
- Frontend tests, TypeScript checking, and the production build passed.
- `/health` and `/quality/summary` were manually verified successfully.
- The accidental `tmppytest-urban/` directory is absent.

The pytest cache warning is non-blocking because cache output is ignored and untracked.

## Environment

Use an external data directory for the full pipeline verification:

```powershell
$env:DATA_DIR = "C:/data/urban-mobility-data-platform"
$env:DUCKDB_PATH = "$env:DATA_DIR/processed/urban_mobility.duckdb"
$env:DAGSTER_HOME = "$PWD/.dagster"
```

For one-off verification, a temporary external directory is also valid as long as it is outside the
repository.

## Required Commands

```powershell
uv sync --locked --all-groups
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python scripts/check_repo_guardrails.py
uv run python scripts/check_repo_readiness.py
```

## Demo Pipeline And dbt

```powershell
uv run python scripts/run_demo.py --data-dir $env:DATA_DIR --year 2026 --month 1 --service yellow --sample-rows 1000
uv run dbt docs generate --project-dir dbt --profiles-dir dbt
```

Expected dbt result for the local demo fixture:

- 14 models build successfully.
- 40 data tests pass.
- `dbt/target/` and `dbt/logs/` remain ignored.

## Dagster

```powershell
uv run dagster definitions validate -m dagster_project.definitions
uv run dagster asset materialize --select "taxi_zone_lookup,raw_yellow_trip_file,raw_trip_profile,validated_trip_data,duckdb_staging,dbt_models,data_quality_report,analytics_ready" -m dagster_project.definitions
```

The current Dagster CLI prints a deprecation warning for this command. Treat that as non-blocking;
future work can migrate to the newer `dg check defs` command after confirming local compatibility.

## Frontend

```powershell
cd apps/web
npm test -- --run
npm run lint
npm run build
cd ../..
```

Dashboard pages and Recharts are route-split. The initial production chunk remains below 500 kB,
and the current build emits no chunk-size warning.

## Repository Hygiene

Confirm these conditions before staging:

- no `.env` files are tracked
- no raw Parquet files are tracked
- no DuckDB, SQLite, or database files are tracked
- no `dbt/target/` or `dbt/logs/` output is tracked
- no `.dagster/` or temporary Dagster storage is tracked
- no `.playwright-cli/` or `output/playwright/` browser artifacts are tracked
- no `apps/web/dist/`, `node_modules/`, or TypeScript build info is tracked
- no large generated reports are tracked
- no secrets or tokens are present
- no forbidden platform implementation/config references are present
- docs links resolve locally

Useful checks:

```powershell
git status --short
git ls-files | Select-String -Pattern "\.env$|\.parquet$|\.duckdb$|dbt/target|dbt/logs|apps/web/dist|node_modules"
uv run python scripts/check_repo_readiness.py
```

## Publish Gate

The repository is ready for a local-demo publish when:

- all required commands above pass
- generated artifacts remain ignored
- the local demo works from an external `DATA_DIR`
- README and docs describe no cloud account, paid service, auth, or API write requirement
- screenshots are small intentional images under `docs/screenshots/`
