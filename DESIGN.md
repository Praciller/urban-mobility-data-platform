---
version: 1.0.0
name: Urban Mobility Operations
purpose: Data-dense analytics dashboard for trustworthy local mobility pipeline evidence
principles:
  - data-first
  - calm-and-operational
  - accessible-by-default
  - consistent-over-decorative
  - evidence-not-theater
colors:
  canvas: "#F5F7FA"
  surface: "#FFFFFF"
  surfaceMuted: "#F8FAFC"
  sidebar: "#0B1220"
  sidebarText: "#CBD5E1"
  ink: "#0F172A"
  textMuted: "#64748B"
  hairline: "#E2E8F0"
  primary: "#2563EB"
  primaryHover: "#1D4ED8"
  accent: "#F59E0B"
  success: "#15803D"
  successSurface: "#F0FDF4"
  warning: "#B45309"
  warningSurface: "#FFF7ED"
  danger: "#B91C1C"
  dangerSurface: "#FEF2F2"
typography:
  fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
  monoFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
  sizes:
    xs: 12px
    sm: 14px
    base: 16px
    lg: 20px
    xl: 24px
    display: 32px
  weights:
    regular: 400
    medium: 500
    semibold: 600
    bold: 700
spacing:
  xs: 4px
  sm: 8px
  md: 12px
  base: 16px
  lg: 24px
  xl: 32px
  section: 48px
radius:
  sm: 8px
  md: 12px
  lg: 16px
  pill: 999px
elevation:
  panel: "0 1px 2px rgba(15, 23, 42, 0.05), 0 8px 24px rgba(15, 23, 42, 0.04)"
layout:
  sidebarWidth: 248px
  contentMaxWidth: 1600px
  desktopGutter: 28px
  mobileGutter: 16px
breakpoints:
  wide: 1200px
  compact: 900px
  mobile: 640px
---

# DESIGN.md

## Design intent

Urban Mobility Operations is an **analytics/operations interface**, not a marketing site. It should feel precise, calm, and credible when a recruiter or engineer inspects pipeline health, mobility trends, anomalies, and data-quality evidence. Information hierarchy and scanning speed take priority over decoration.

The visual direction is an original system tailored to this repository: dense analytics hierarchy inspired by mature BI/data products, combined with the project's existing dark navigation, blue action color, and restrained amber mobility accent. Do not clone another product's branding or layout.

## Core rules

1. **One primary action color.** `{colors.primary}` owns links, selected navigation, focus states, and primary buttons.
2. **Amber is semantic/accent, not a second CTA color.** `{colors.accent}` is for mobility emphasis, warnings, or a single chart highlight.
3. **Surfaces are quiet.** Prefer hairline borders and subtle elevation over large shadows, gradients, glassmorphism, or glowing effects.
4. **Density is deliberate.** A dashboard may show a lot of data, but spacing and alignment must establish groups before adding more cards.
5. **Numbers are first-class content.** KPI values and numeric table columns use tabular numerals where supported.
6. **States are explicit.** Loading, empty, warning, stale-data, API-unavailable, and error states must be distinguishable without relying on color alone.

## Color system

- **Canvas** `{colors.canvas}`: application background.
- **Surface** `{colors.surface}`: cards, panels, controls, tables.
- **Sidebar** `{colors.sidebar}`: persistent navigation on desktop.
- **Ink** `{colors.ink}`: primary text and high-confidence values.
- **Muted** `{colors.textMuted}`: secondary labels, timestamps, supporting metadata.
- **Hairline** `{colors.hairline}`: dividers and default borders.
- **Primary blue** `{colors.primary}`: interactive emphasis and selected state.
- **Accent amber** `{colors.accent}`: restrained mobility/attention accent.
- **Success / warning / danger** are semantic only. Pair them with an icon, label, or text state.

All text/control combinations must meet WCAG 2.2 AA contrast. Never introduce a raw hex value in a component/page when an existing semantic token fits.

## Typography

Use the system Inter stack above. Avoid decorative display faces in the application shell.

- Page title: 24–32px, 600–700 weight, compact line-height.
- Section title: 20–24px, 600.
- Card/panel title: 14–16px, 600.
- Body/control: 14–16px, 400–500.
- Labels/captions: 12–14px, 500–600.
- KPI value: 24–32px, 600–700, `font-variant-numeric: tabular-nums`.
- Code, IDs, paths, and technical artifacts: mono stack.

Avoid all-caps except short metadata labels or table headers. Do not use oversized hero typography inside the operational dashboard.

## Spacing and layout

Use the spacing scale from front matter. Do not invent 13px/19px/27px one-offs without a documented reason.

- Desktop shell: 248px sidebar + fluid content column.
- Main content should remain readable on large displays; use `contentMaxWidth` and center when appropriate.
- Default panel gap: 16–24px.
- Section gap: 32–48px.
- Controls in one logical filter group should be 8–16px apart.
- Prefer 12–16px panel radii. Avoid excessive 24–32px rounding that makes a technical dashboard feel toy-like.

### Responsive behavior

- **>=1200px:** full sidebar; KPI grids may use 4–6 columns where labels remain readable.
- **900–1199px:** reduce KPI columns, collapse wide two-panel layouts to one column when necessary.
- **641–899px:** navigation becomes compact/collapsible; controls wrap predictably; tables may scroll horizontally.
- **<=640px:** single-column content, 16px gutters, touch targets >=44px, no clipped chart labels or off-screen controls.

## Component contract

### App shell and navigation

- Sidebar contains product identity, seven dashboard destinations, and only persistent navigation.
- Selected nav item must expose `aria-current` or equivalent state and remain visible without hover.
- On small screens use a keyboard-accessible disclosure/drawer rather than stacking a full desktop sidebar above content.

### Top bar / context header

Show page context, freshness/health state, and high-value actions. Do not duplicate navigation. Status text must state what is healthy/stale/unavailable, not only show a colored dot.

### Filter bar

- Group related date/zone/service filters in one surface.
- Every input has a visible label.
- Preserve selected values while data reloads.
- Loading must not make controls jump in size.

### Buttons

- `primary`: one dominant action per local region.
- `secondary`: neutral surface/border treatment.
- `danger`: destructive only; this read-only dashboard should rarely need it.
- Disabled state must remain legible and non-interactive.
- Visible focus ring is mandatory.

### KPI / stat card

A stat card contains label, primary value, optional comparison/context, and optional semantic state. It is not a mini dashboard. Keep one metric per card and avoid decorative icons unless they add meaning.

### Panels / chart cards

Every chart panel has a clear title, optional short explanation, chart, and data/empty/error state. Use consistent internal padding. Avoid unrelated controls inside the plot region.

### Tables

- Header remains visually distinct; sticky header is preferred for long tables.
- Text left aligned; numeric values right aligned with tabular numerals.
- Long identifiers may wrap or truncate with an accessible title/label.
- Empty state appears inside the table region and explains why data is absent.
- Horizontal scrolling is acceptable on narrow screens; shrinking text below 12px is not.

### Loading / empty / error

- Prefer skeletons/placeholders for known dashboard geometry; a spinner may supplement but should not be the only context.
- Empty state states the filter/data reason where known and offers a next action only when one exists.
- Error/API-unavailable state includes a retry action and a concise technical-safe message.

## Charts and data visualization

- Keep chart colors semantically stable across pages.
- Primary series: `{colors.primary}`; comparison/secondary series use muted neutrals; `{colors.accent}` is a deliberate highlight, not a default second series.
- Never use 3D charts, ornamental gradients, or rainbow palettes.
- Axes, units, and time grain must be explicit.
- Tooltips must use readable labels and formatted values.
- Do not encode category/state by color alone; use labels, shapes, line styles, or direct annotation where practical.
- Avoid pie/donut charts when a sorted bar/table communicates comparison more accurately.
- Test charts at compact widths and with empty/single-point/long-label data.

## Accessibility and interaction

- Semantic HTML first; ARIA only where native semantics are insufficient.
- All interactive controls must be keyboard reachable with a visible focus indicator.
- Minimum interactive target: 44x44px on touch layouts.
- Do not remove outlines without an equivalent focus style.
- Respect `prefers-reduced-motion` for nonessential animation.
- Loading announcements and errors should be exposed to assistive technology where appropriate.
- Charts require a textual/table summary or accessible fallback for critical information.

## Motion

Motion is functional and subtle: 120–200ms for hover/disclosure transitions. No parallax, bouncing KPIs, count-up theater, or page-entry animation that delays reading data.

## Implementation rules

- Centralize tokens as CSS custom properties (or an equivalent typed token module) and consume semantic names from components.
- Page files compose primitives; they should not define their own visual language.
- Shared components should own variants/states rather than pages adding one-off class combinations.
- New components need tests for meaningful behavior/state. Storybook stories are the target catalog for reusable primitives once Storybook is introduced.
- Material UI changes must be verified in a real browser at desktop and compact/mobile widths.

## Forbidden patterns

- Raw color/radius/shadow values scattered through page/component files.
- Multiple competing primary colors.
- Giant rounded cards, excessive pills, glow effects, glassmorphism, or gradients used as default decoration.
- Icon-only controls without accessible names.
- Placeholder dashboards that show fabricated production/live values.
- Removing loading/error/empty handling to simplify visuals.
- Adding a large UI framework solely to obtain styling without an ADR and bundle/maintenance justification.

## Known gaps / next design-system work

- Current CSS has hard-coded values that must be migrated to semantic tokens.
- The project does not yet have Storybook, automated accessibility checks, or visual/browser regression evidence.
- Compact navigation needs a purposeful mobile pattern rather than simply stacking desktop navigation.
- Dark mode is optional future work, not a prerequisite for the first standardized system.
