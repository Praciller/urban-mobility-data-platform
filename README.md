# Urban Mobility Data Platform

Local-first data engineering platform for NYC Taxi and Limousine Commission trip data.
The target system will ingest bounded monthly Parquet data, validate it, build DuckDB/dbt
analytical marts, expose FastAPI metrics, and present them in a React dashboard.

## Phase 1 Status

This repository currently contains the bootstrap only:

- Python 3.12 package and `uv` development environment
- externalizable `DATA_DIR` configuration
- placeholder API, web, Dagster, dbt, data, report, and documentation trees
- local PostgreSQL Compose profile
- lint, test, pre-commit, repository guardrails, and minimal GitHub Actions CI
- a small Docker bootstrap image that verifies package and data-path configuration

No NYC TLC Parquet data is downloaded during Phase 1.

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
```

## Commands

| Command | Phase 1 behavior |
|---|---|
| `make setup` | Sync development dependencies and install pre-commit |
| `make lint` | Run Ruff lint and format checks |
| `make format` | Apply Ruff fixes and formatting |
| `make test` | Run pytest |
| `make docker-up` | Build and run the bootstrap service |
| `make docker-down` | Stop Compose services |
| `make clean-generated` | Remove generated processed/report files only |

The remaining required Make targets are explicit phase placeholders and do not download data.

## Dataset

Future phases use official NYC TLC Yellow Taxi Trip Record Parquet files and the Taxi Zone
Lookup CSV. See [docs/data_source.md](docs/data_source.md).

## Portfolio Review

Phase 1 reviewers should inspect the repository layout, guardrails, CI workflow, Compose
configuration, and bootstrap tests. The complete reviewer path is tracked in
[docs/portfolio_review.md](docs/portfolio_review.md).

## Limitations

- ingestion, validation, dbt models, Dagster orchestration, API endpoints, and web UI are not implemented
- Compose currently provides the bootstrap image and optional local PostgreSQL only
- CI intentionally runs no dataset downloads
- screenshots will be added after user-facing services exist

## Roadmap

Phase 2 adds bounded sample download and profiling. Later phases add DuckDB/dbt, FastAPI,
React, Dagster, complete CI smoke coverage, and documentation polish.
