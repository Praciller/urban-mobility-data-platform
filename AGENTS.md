# Repository Instructions

## Source of truth

- Treat `PROJECT_REQUIREMENTS_NO_SUPABASE.md` as the authoritative product and architecture requirement.
- Read `CONTEXT.md` for domain language that is not obvious from code.
- Read `DESIGN.md` before any frontend or visual change.
- Read relevant records under `docs/adr/` before changing an architectural decision.
- Prefer the smallest change that satisfies the active issue or specification. Do not broaden scope silently.

## Operating model

- Start each bounded task by gathering only the context required for that task, then state the plan before editing.
- Reuse existing modules and components before creating new abstractions or dependencies.
- When requirements are ambiguous or conflict with the source of truth, stop and surface the conflict instead of guessing.
- Treat acceptance criteria as the stop condition. A task is complete only when the criteria are satisfied and the relevant verification commands pass.
- Keep generated evidence reproducible: tests, screenshots, reports, or command output must come from the implementation being reviewed.

## Non-negotiable boundaries

- Keep the implementation local-first and free to run without a cloud account.
- Never add Supabase code, configuration, SDKs, auth, storage, edge functions, or deployment guidance.
- Keep the API read-only unless the authoritative requirements are explicitly changed.
- Keep raw data, generated reports, databases, secrets, caches, virtual environments, and build output out of Git.
- Use `DATA_DIR` for full data runs so large artifacts can live outside the repository/OneDrive.
- CI must use deterministic sample/generated fixtures; never download full monthly TLC datasets in CI.
- Never commit credentials, tokens, `.env`, local paths, or user-specific machine state.
- Do not claim production readiness, real-time behavior, or deployment evidence that the repository does not actually prove.

## Current verification commands

Run the smallest relevant checks while iterating, then the full affected gate before declaring completion.

### Python / pipeline

```powershell
uv sync --locked --all-groups
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run python scripts/check_repo_guardrails.py
uv run python scripts/check_repo_readiness.py
uv run python scripts/run_demo.py --data-dir C:/data/urban-mobility-data-platform
uv run dbt parse --project-dir dbt --profiles-dir dbt
uv run dbt run --project-dir dbt --profiles-dir dbt
uv run dbt test --project-dir dbt --profiles-dir dbt
uv run dagster definitions validate -m dagster_project.definitions
docker compose config
```

Use a temporary/external `DATA_DIR` when the canonical local path is not appropriate.

### Frontend

```powershell
npm ci --prefix apps/web
npm --prefix apps/web test -- --run
npm --prefix apps/web run lint
npm --prefix apps/web run build
```

`apps/web` currently names its TypeScript no-emit check `lint`; do not describe it as ESLint until an actual ESLint gate exists.

## Frontend rules

- `DESIGN.md` is the design contract. Implement its tokens in code rather than introducing new hard-coded visual values.
- Preserve clear loading, empty, error, and API-unavailable states.
- Keep charts responsive and accessible; color must not be the only carrier of meaning.
- Prefer small reusable primitives over page-specific duplicated markup.
- Verify material UI changes in a real browser at desktop and narrow viewports and capture evidence when the issue requires it.

## Data/API rules

- Prefer Python 3.12, `uv`, typed functions, focused modules, and PowerShell-friendly commands.
- Preserve deterministic, explainable validation/anomaly rules and idempotent month/service partition behavior.
- Validate external inputs at boundaries; never expose arbitrary SQL or local filesystem paths through the API.
- Structured logs and public errors must not contain secrets.

## Git and review

- One issue/specification should map to a reviewable bounded branch/PR whenever practical.
- PR descriptions must state scope, out-of-scope items, verification evidence, and any contract/data/UI impact.
- For architecture or durable workflow decisions, add or supersede an ADR instead of leaving rationale only in chat or a PR comment.
- A reviewer should be able to reproduce the claimed result from repository commands; if not, classify the result as a limitation rather than a pass.
