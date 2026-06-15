# Portfolio Review

## Phase 1 Review Path

1. Inspect `PROJECT_REQUIREMENTS_NO_SUPABASE.md` and `docs/architecture.md`.
2. Review the external `DATA_DIR` configuration in `.env.example`.
3. Run `uv sync --all-groups`.
4. Run lint, format checks, and tests.
5. Run `docker compose config` and the bootstrap image.
6. Review `.github/workflows/ci.yml` and repository guardrails.

The complete product review path will expand as Dagster, dbt, API, and dashboard phases ship.
