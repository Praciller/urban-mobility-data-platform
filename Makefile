.PHONY: setup download-sample profile-sample validate-sample dbt-run dbt-test \
	pipeline-sample api web dagster test lint format docker-up docker-down clean-generated

setup:
	uv sync --all-groups
	uv run pre-commit install

download-sample:
	@echo "Phase 2 command scaffold: dataset download is not implemented in Phase 1."

profile-sample:
	@echo "Phase 2 command scaffold: sample profiling is not implemented in Phase 1."

validate-sample:
	@echo "Phase 2 command scaffold: sample validation is not implemented in Phase 1."

dbt-run:
	@echo "Phase 3 command scaffold: dbt models are not implemented in Phase 1."

dbt-test:
	@echo "Phase 3 command scaffold: dbt tests are not implemented in Phase 1."

pipeline-sample:
	@echo "Phase 2 command scaffold: sample pipeline is not implemented in Phase 1."

api:
	@echo "Phase 4 command scaffold: FastAPI is not implemented in Phase 1."

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
