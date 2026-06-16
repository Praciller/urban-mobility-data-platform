# Urban Mobility Data Platform

Local-first data engineering platform for NYC Taxi and Limousine Commission trip data.
The target system will ingest bounded monthly Parquet data, validate it, build DuckDB/dbt
analytical marts, expose FastAPI metrics, and present them in a React dashboard.

## Phase 4 Status

The repository now supports a local sample data pipeline:

- Python 3.12 package and `uv` development environment
- externalizable `DATA_DIR` configuration
- official Yellow Taxi and taxi zone lookup URL construction
- atomic HTTP downloads with skip-if-exists, `--force`, checksums, and manifest tracking
- DuckDB-backed bounded Parquet sample creation
- metadata-first Parquet profiles with key null counts, date ranges, and numeric statistics
- rule-based valid, warning, and rejected record classification
- deterministic duplicate detection and derived trip metrics
- partitioned validated/rejected Parquet outputs and JSON quality reports
- idempotent persisted DuckDB staging for trips and taxi zones
- dbt staging, dimensions, trip fact, analytical marts, documentation, and tests
- read-only FastAPI repository and service layers over persisted DuckDB marts
- typed overview, trend, zone, route, revenue, anomaly, metadata, and CSV endpoints
- bounded pagination, date/zone filters, and whitelisted sorting
- explicit errors for unavailable data, missing marts, invalid dates, and unknown zones
- local PostgreSQL Compose profile
- lint, test, pre-commit, repository guardrails, and minimal GitHub Actions CI

CI uses tiny generated fixtures and downloads no official NYC TLC data.

## Architecture

```text
NYC TLC files -> ingestion/validation -> DuckDB -> dbt marts
                                                -> FastAPI -> React dashboard
Optional local PostgreSQL supports future serving and metadata use cases.
```

## Stack

Python 3.12, uv, DuckDB, PostgreSQL, dbt, Dagster, FastAPI, React, Docker Compose,
pytest, Ruff, and GitHub Actions. Later phases add runtime dependencies only when used.

## Quickstart

PowerShell:

```powershell
uv sync --all-groups
uv run pre-commit install
uv run python -m urban_mobility
uv run python -m urban_mobility.download --year 2026 --month 1 --service yellow --sample-rows 1000
uv run python -m urban_mobility.ingest inspect --year 2026 --month 1 --service yellow
uv run python -m urban_mobility.validate --year 2026 --month 1 --service yellow
uv run python -m urban_mobility.load_duckdb --year 2026 --month 1 --service yellow
uv run dbt run --project-dir dbt --profiles-dir dbt
uv run dbt test --project-dir dbt --profiles-dir dbt
uv run uvicorn apps.api.app.main:app --reload --host 127.0.0.1 --port 8000
uv run ruff check .
uv run ruff format --check .
uv run pytest
docker compose config
docker compose up --build
```

`make` is optional on Windows. The `Makefile` mirrors these commands for environments
where GNU Make is installed.

To keep full datasets outside OneDrive, copy `.env.example` to `.env` and set:

```env
DATA_DIR=C:/data/urban-mobility-data-platform
DUCKDB_PATH=C:/data/urban-mobility-data-platform/processed/urban_mobility.duckdb
```

## Commands

| Command | Behavior |
|---|---|
| `make setup` | Sync development dependencies and install pre-commit |
| `make download-sample` | Materialize a bounded official Parquet sample and zone lookup |
| `make profile-sample` | Profile the bounded sample |
| `make validate-sample` | Classify sample rows and write quality artifacts |
| `make load-duckdb` | Idempotently load the selected month into DuckDB staging |
| `make dbt-run` | Build local dbt models |
| `make dbt-test` | Run dbt source and model tests |
| `make pipeline-sample` | Run acquisition, profiling, validation, load, dbt run, and dbt test |
| `make api` | Start the read-only FastAPI analytics API |
| `make lint` | Run Ruff lint and format checks |
| `make format` | Apply Ruff fixes and formatting |
| `make test` | Run pytest |
| `make docker-up` | Build and run the local API container |
| `make docker-down` | Stop Compose services |
| `make clean-generated` | Remove generated processed/report files only |

GNU Make is optional. The documented `uv` commands are the supported Windows PowerShell path.

## Dataset

The pipeline uses official NYC TLC Yellow Taxi Trip Record Parquet files and the Taxi Zone Lookup
CSV. Full files are stored under `DATA_DIR/raw`; bounded files are stored under
`DATA_DIR/sample`. See [docs/data_source.md](docs/data_source.md).

## Portfolio Review

Phase 4 reviewers should inspect validation rule coverage, idempotent DuckDB loading, dbt
lineage/tests, read-only API query boundaries, typed OpenAPI responses, and fixture-only CI.

## Limitations

- Dagster orchestration and the web UI are not implemented
- Docker Compose starts the API container and optional local PostgreSQL profile
- CI intentionally runs no dataset downloads
- remote sample creation requires DuckDB's free `httpfs` extension on first use
- only Yellow Taxi monthly data is supported
- screenshots will be added after user-facing services exist

## Roadmap

Phase 5 adds the React dashboard over the FastAPI API. Later phases add Dagster orchestration
and documentation polish.
