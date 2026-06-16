# Operations

Full dataset runs should set `DATA_DIR` to a directory outside OneDrive, such as
`C:/data/urban-mobility-data-platform`.

```powershell
$env:DATA_DIR = "C:/data/urban-mobility-data-platform"
$env:DUCKDB_PATH = "$env:DATA_DIR/processed/urban_mobility.duckdb"
uv sync --all-groups
uv run python -m urban_mobility.download --year 2026 --month 1 --service yellow --sample-rows 1000
uv run python -m urban_mobility.ingest inspect --year 2026 --month 1 --service yellow
uv run python -m urban_mobility.validate --year 2026 --month 1 --service yellow
uv run python -m urban_mobility.load_duckdb --year 2026 --month 1 --service yellow
uv run dbt run --project-dir dbt --profiles-dir dbt
uv run dbt test --project-dir dbt --profiles-dir dbt
uv run dbt docs generate --project-dir dbt --profiles-dir dbt
uv run uvicorn apps.api.app.main:app --reload --host 127.0.0.1 --port 8000
```

Rerunning reuses an existing readable file and appends a `reused` manifest entry. Add
`--force` to replace it atomically. The manifest is written to
`DATA_DIR/processed/download_manifest.json`; profiles are written to
`DATA_DIR/reports/data_quality/`.

Validation overwrites only the selected output partitions. DuckDB loading deletes and reloads
only the matching service/year/month, so reruns do not duplicate staged trips.

Generated samples, manifests, reports, validated/rejected partitions, and DuckDB files can be
removed without touching raw files:

```powershell
uv run python scripts/clean_generated.py
```

If a month does not exist remotely, the downloader returns an actionable error and leaves no
partial destination file. Full backfill and Dagster orchestration procedures remain deferred.

## API Checks

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/metadata
Invoke-RestMethod "http://127.0.0.1:8000/metrics/daily?limit=10"
```

If `/health` reports `unavailable`, confirm `DUCKDB_PATH` points to an existing database. If it
reports `degraded`, rerun `dbt run` and `dbt test` against the same `DUCKDB_PATH`. The API never
creates or modifies database objects.

## Docker Image

The default image starts the FastAPI app on port 8000 and expects a populated DuckDB file at
`/data/processed/urban_mobility.duckdb`.

```powershell
docker build -t pracill1997/urban-mobility-data-platform:phase4 .
docker run --rm -p 8000:8000 -v C:/data/urban-mobility-data-platform:/data pracill1997/urban-mobility-data-platform:phase4
```
