.PHONY: setup demo download-sample profile-sample validate-sample load-duckdb dbt-run dbt-test \
	pipeline-sample api web-install web web-test web-build dagster-validate dagster \
	dagster-materialize test lint readiness format docker-up docker-down clean-generated

YEAR ?= 2026
MONTH ?= 1
SERVICE ?= yellow
SAMPLE_ROWS ?= 1000
API_HOST ?= 127.0.0.1
API_PORT ?= 8000
ASSET_SELECTION ?= taxi_zone_lookup,raw_yellow_trip_file,raw_trip_profile,validated_trip_data,duckdb_staging,dbt_models,data_quality_report,analytics_ready

setup:
	uv sync --all-groups
	uv run pre-commit install

demo:
	uv run python scripts/run_demo.py --year $(YEAR) --month $(MONTH) \
		--service $(SERVICE) --sample-rows $(SAMPLE_ROWS)

download-sample:
	uv run python -m urban_mobility.download --year $(YEAR) --month $(MONTH) \
		--service $(SERVICE) --sample-rows $(SAMPLE_ROWS)

profile-sample:
	uv run python -m urban_mobility.ingest inspect --year $(YEAR) --month $(MONTH) \
		--service $(SERVICE) --mode sample --sample-rows $(SAMPLE_ROWS)

validate-sample:
	uv run python -m urban_mobility.validate --year $(YEAR) --month $(MONTH) \
		--service $(SERVICE)

load-duckdb:
	uv run python -m urban_mobility.load_duckdb --year $(YEAR) --month $(MONTH) \
		--service $(SERVICE)

dbt-run:
	uv run dbt run --project-dir dbt --profiles-dir dbt

dbt-test:
	uv run dbt test --project-dir dbt --profiles-dir dbt

pipeline-sample:
	$(MAKE) download-sample
	$(MAKE) profile-sample
	$(MAKE) validate-sample
	$(MAKE) load-duckdb
	$(MAKE) dbt-run
	$(MAKE) dbt-test

api:
	uv run uvicorn apps.api.app.main:app --reload --host $(API_HOST) --port $(API_PORT)

web-install:
	cd apps/web && npm install

web:
	cd apps/web && npm run dev -- --host 127.0.0.1

web-test:
	cd apps/web && npm test

web-build:
	cd apps/web && npm run build

dagster-validate:
	uv run dagster definitions validate -m dagster_project.definitions

dagster:
	uv run dagster dev -m dagster_project.definitions

dagster-materialize:
	uv run dagster asset materialize --select "$(ASSET_SELECTION)" -m dagster_project.definitions

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

readiness:
	uv run python scripts/check_repo_guardrails.py
	uv run python scripts/check_repo_readiness.py

format:
	uv run ruff check --fix .
	uv run ruff format .

docker-up:
	docker compose up --build

docker-down:
	docker compose down

clean-generated:
	uv run python scripts/clean_generated.py
