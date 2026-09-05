# Urban Mobility Domain Context

This file defines concise project language that is useful across agent sessions and code review. Keep it focused on decisions and vocabulary that are not reliably inferable from one source file.

## Product boundary

This repository is a **local-first portfolio-grade urban mobility analytics platform**, not a live transport service. It demonstrates bounded data ingestion, validation, modeling, orchestration, read-only analytical serving, and dashboard consumption using NYC TLC Yellow Taxi data.

The canonical requirements are in `PROJECT_REQUIREMENTS_NO_SUPABASE.md`.

## Ubiquitous language

- **Service month** — the `(service, year, month)` partition being processed, for example Yellow Taxi January 2026. It is the primary bounded unit for ingestion/rerun reasoning.
- **Sample mode** — deterministic small-data execution intended for development, CI, and reproducible portfolio evidence. It must not require a full monthly download.
- **Full-month mode** — local analysis against an official monthly TLC file. It may be slower/larger and should use external `DATA_DIR` storage.
- **Validated trip** — a record that passes rejection rules and can proceed into analytical loading. Warning flags may remain attached.
- **Rejected trip** — a record deliberately excluded from analytical loading with an explainable rejection reason; rejected records are never silently dropped.
- **Quality status** — the explicit valid/warning/rejected classification and rule-level evidence associated with a trip or run.
- **Partition replacement** — idempotent replacement of one service month in DuckDB staging. A failed replacement must not leave partial target data or damage unrelated partitions.
- **Mart** — a dbt-produced analytical model shaped for a specific read/query purpose such as daily metrics, hourly demand, route metrics, revenue, or anomalies.
- **Bounded pipeline** — execution limited to an explicit service/month/sample size so local development and CI remain deterministic and inexpensive.
- **Data freshness** — metadata that tells consumers which source/service month/run produced the persisted analytical output. It is not a claim of real-time data.
- **Anomaly** — a deterministic and explainable suspicious-trip condition first; optional ML is secondary and must not replace a human-readable reason.
- **Quality artifact** — generated evidence such as a raw profile, validation summary, rejected-row output, dbt test result, or freshness metadata. Most generated artifacts remain outside Git.
- **Operational dashboard** — the React UI used to inspect analytics and data/pipeline quality. It is a read-only analytical surface, not an admin console.

## Invariants

- Local sample mode must work without a paid service, cloud account, or Supabase.
- Rerunning a service month must not duplicate rows.
- Raw source data is immutable after download; transformed/rejected outputs are separate.
- API inputs are validated and cannot expose arbitrary SQL execution.
- Public API errors and dashboard messages do not reveal local filesystem paths or secrets.
- Claims in README/screenshots must match reproducible repository evidence.

## Non-goals unless requirements are explicitly changed

- Authentication or user management.
- API write endpoints.
- Real-time NYC transport tracking.
- Production SLA claims.
- Supabase-specific database, auth, storage, functions, or deployment.
- A proprietary/paid BI dependency.

## Context pointers

- Architecture: `docs/architecture.md`
- Data model: `docs/data_model.md`
- API: `docs/api.md`
- Dashboard behavior: `docs/dashboard.md`
- Operations: `docs/operations.md`
- Design system: `DESIGN.md`
- Durable decisions: `docs/adr/`
