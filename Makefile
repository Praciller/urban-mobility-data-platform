.PHONY: setup download-sample profile-sample validate-sample load-duckdb dbt-run dbt-test \
	pipeline-sample api web dagster test lint format docker-up docker-down clean-generated

YEAR ?= 2026
MONTH ?= 1
SERVICE ?= yellow
SAMPLE_ROWS ?= 1000
API_HOST ?= 127.0.0.1
API_PORT ?= 8000

setup:
	uv sync --all-groups
	uv run pre-commit install

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

web:
	@echo "Phase 5 command scaffold: React is not implemented in Phase 1."

dagster:
	@echo "Phase 6 command scaffold: Dagster is not implemented in Phase 1."

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

docker-up:
	docker compose up --build

docker-down:
	docker compose down

clean-generated:
	uv run python scripts/clean_generated.py
