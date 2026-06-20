# Troubleshooting

## `/health` Reports `unavailable`

Confirm the same `DUCKDB_PATH` was used for loading, dbt, and API:

```powershell
$env:DUCKDB_PATH
Test-Path $env:DUCKDB_PATH
```

If the file is missing, rerun the local demo pipeline through DuckDB loading and dbt.

## `/health` Reports `degraded`

Required marts are missing. Rebuild dbt against the same DuckDB file:

```powershell
uv run dbt run --project-dir dbt --profiles-dir dbt
uv run dbt test --project-dir dbt --profiles-dir dbt
```

## Validation Fails With Missing Zone Lookup

Create the offline fixture or download the zone lookup into `DATA_DIR`:

```powershell
uv run python scripts/create_demo_fixture.py --year 2026 --month 1 --service yellow --sample-rows 1000
```

## Dagster Fails With Remote Download Disabled

The default Dagster config does not fetch remote files. Create local files first:

```powershell
uv run python scripts/create_demo_fixture.py --year 2026 --month 1 --service yellow --sample-rows 1000
```

Then rerun materialization:

```powershell
$env:DAGSTER_ASSETS = "taxi_zone_lookup,raw_yellow_trip_file,raw_trip_profile,validated_trip_data,duckdb_staging,dbt_models,data_quality_report,analytics_ready"
uv run dagster asset materialize --select $env:DAGSTER_ASSETS -m dagster_project.definitions
```

## PowerShell Expands `*` In Dagster Asset Selection

Use the explicit comma-separated selection documented in this repo. Do not use `--select *` in
PowerShell from the repository root.

## React Dashboard Shows API Unavailable

Start FastAPI first and confirm the base URL:

```powershell
uv run uvicorn apps.api.app.main:app --reload --host 127.0.0.1 --port 8000
cd apps/web
$env:VITE_API_BASE_URL = "http://localhost:8000"
npm run dev -- --host 127.0.0.1
```

## Recharts Chunk Warning During Build

The dashboard currently bundles Recharts in the main chunk. The warning is known and acceptable for
the local portfolio demo. Future work can add code splitting if needed.

## Dagster Definition Validation Deprecation Warning

`uv run dagster definitions validate -m dagster_project.definitions` currently passes but may print
a deprecation warning recommending `dg check defs`. Keep using the documented command until the
newer `dg` command is verified locally and in CI.

## Readiness Check Fails

Run the readiness script directly to see the failing check:

```powershell
uv run python scripts/check_repo_readiness.py
```

Common causes are tracked generated files, missing final docs, missing ignore rules, or forbidden
implementation/config references.

## Reset Generated Local Outputs

Repository-local generated files:

```powershell
uv run python scripts/clean_generated.py
```

External `DATA_DIR` outputs must be removed from that external directory if a full reset is needed.
