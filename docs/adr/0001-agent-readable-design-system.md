# ADR-0001 — Adopt an agent-readable dashboard design system

- **Status:** Accepted
- **Date:** 2026-09-05
- **Decider:** Repository owner
- **Related:** `DESIGN.md`, `apps/web/`, issue #6

## Context

The React dashboard already has useful page/component boundaries, responsive CSS, loading/error handling, and a consistent dark-sidebar/blue-action visual direction. However, its visual rules currently live mostly as hard-coded CSS values. There is no machine-readable design contract describing semantic colors, typography, spacing, component states, chart/table behavior, responsive rules, accessibility expectations, or forbidden patterns.

This makes visual changes easy to implement locally but harder to keep consistent across pages and across coding-agent sessions. The attached SDLC guidance recommends `DESIGN.md` as durable design context, design tokens instead of scattered hard-coded values, component reuse, and browser verification.

The dashboard is an analytics/operations surface for a data engineering portfolio, so the design should prioritize information density, trust, scanning, and evidence rather than consumer-app decoration.

## Options considered

### 1. Keep the existing CSS as the only design source

**Pros:** no migration work; no new documentation.

**Cons:** visual intent remains implicit; future agents can introduce one-off values and inconsistent components; accessibility/chart rules are not encoded.

### 2. Adopt a large component framework as the design system

Examples could include general-purpose React UI suites.

**Pros:** broad component inventory and established accessibility work.

**Cons:** adds a large dependency and a second design language; may produce a generic portfolio appearance; migration cost is high relative to this small dashboard; not required by current product requirements.

### 3. Define a repository-owned `DESIGN.md`, semantic tokens, and focused primitives

**Pros:** preserves the existing identity and stack; gives humans and agents one readable design contract; allows incremental migration; keeps dependencies small; fits the project-specific analytics domain.

**Cons:** the team owns token/component discipline; Storybook and browser/a11y automation still require follow-up implementation.

## Decision

Choose **Option 3**.

- Root `DESIGN.md` is the canonical visual/interaction contract for `apps/web`.
- Preserve React + TypeScript + Vite + Recharts; do not introduce a large UI framework merely to restyle the application.
- Preserve the existing core identity (dark navigation, blue primary interaction, restrained amber mobility accent) while standardizing it into semantic tokens.
- Migrate raw CSS values toward semantic CSS custom properties and reusable component variants in a bounded frontend follow-up.
- Add Storybook for reusable component states and browser/a11y/E2E evidence as a subsequent quality step.
- Significant future changes to the design philosophy, UI framework, or token architecture require a new ADR that supersedes this one.

## Consequences

### Positive

- Frontend agents have durable machine-readable design context.
- Pages can be reviewed against explicit rules rather than taste alone.
- Design tokens reduce drift and make responsive/accessibility work easier to audit.
- The visual system remains domain-appropriate and portfolio-distinct without copying another product.

### Trade-offs

- There is an intentional migration period where legacy hard-coded CSS and new tokens may coexist; new work should not add further raw visual values.
- Storybook, accessibility automation, and Playwright/browser regression are not delivered by this ADR alone.
- Dark mode is explicitly deferred; standardized light content + dark navigation is sufficient for the first design-system iteration.
