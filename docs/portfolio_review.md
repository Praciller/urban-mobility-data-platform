# Portfolio Review

This path is designed for a quick reviewer pass without cloud setup or a full official dataset.

## Fast Review Path

1. Clone the repository.
2. Read `README.md`, `docs/architecture.md`, and `docs/local_demo.md`.
3. Install dependencies:

   ```powershell
   uv sync --locked --all-groups
   npm install --prefix apps/web
   ```

4. Run tests and static checks:

   ```powershell
   uv run pytest
   uv run ruff check .
   uv run ruff format --check .
   uv run python scripts/check_repo_readiness.py
   cd apps/web
   npm run build
   cd ../..
   ```

5. Run the bounded offline demo:

   ```powershell
   $env:DATA_DIR = "C:/data/urban-mobility-data-platform"
   $env:DUCKDB_PATH = "$env:DATA_DIR/processed/urban_mobility.duckdb"
   uv run python scripts/run_demo.py --data-dir $env:DATA_DIR --year 2026 --month 1 --service yellow --sample-rows 1000
   ```

   The fixture contains three physical rows: one valid trip, one duplicate warning retained for
   analytics, and one negative-fare record written to the rejected partition. It demonstrates
   behavior and lineage, not production volume or performance.

6. Start FastAPI:

   ```powershell
   uv run uvicorn apps.api.app.main:app --reload --host 127.0.0.1 --port 8000
   ```

7. Start React dashboard:

   ```powershell
   cd apps/web
   $env:VITE_API_BASE_URL = "http://localhost:8000"
   npm run dev -- --host 127.0.0.1
   ```

8. Start Dagster UI:

   ```powershell
   $env:DAGSTER_HOME = "$PWD/.dagster"
   uv run dagster dev -m dagster_project.definitions
   ```

9. Inspect generated outputs under external `DATA_DIR`, not the repository:
   raw profile JSON, validation summary JSON, validated/rejected Parquet, DuckDB database, dbt docs.

10. Review limitations and future improvements in `README.md`.
11. Review [publish_checklist.md](publish_checklist.md) and [backlog.md](backlog.md) for the
    final portfolio handoff.

## What To Inspect

- `src/urban_mobility/validate.py`: validation rules and duplicate handling
- `src/urban_mobility/load_duckdb.py`: idempotent month replacement
- `dbt/models/`: staging, dimensions, fact, and marts
- `apps/api/app/repositories/analytics.py`: read-only query boundary
- `apps/api/app/repositories/quality.py`: bounded, sanitized validation artifact reader
- `apps/web/src/api/client.ts`: dashboard API contract
- `pipelines/dagster_project/dagster_project/assets/tlc_pipeline.py`: orchestration wrappers
- `tests/`: generated fixture tests and API/dashboard/Dagster coverage

## Screenshot Checklist

Use the local demo workflow, then capture:

- FastAPI OpenAPI page at `http://127.0.0.1:8000/docs`
- Dashboard Overview page
- Dashboard Anomaly Explorer page
- Dashboard Data Quality / Pipeline Status page
- Dagster asset graph page
- Dagster materialization metadata for `analytics_ready`

Verified local dashboard captures are stored under `docs/screenshots/`. Save only small,
intentional images there and never capture secrets, browser chrome, or raw dataset contents.
