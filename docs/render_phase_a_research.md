# Render Phase A research

Checked 2026-09-05 against current first-party Render documentation.

## Provider fit

Render documents free web services and free static sites as available for
testing, hobby, and portfolio-style use. Its web-service documentation names
Python and FastAPI as supported frameworks and documents Docker-based deploys.
Free web services are not production infrastructure: they spin down after 15
minutes without inbound traffic, take about a minute to wake, and have an
ephemeral filesystem. This project therefore bundles a deterministic sample
snapshot in the API image and does not require a persistent disk.

- [Deploy for Free](https://render.com/docs/free)
- [Web Services](https://render.com/docs/web-services)
- [Static Sites](https://render.com/docs/static-sites)
- [Docker on Render](https://render.com/docs/docker)

## Blueprint facts

The current Blueprint specification supports `autoDeployTrigger: checksPass`,
`fromService`, and service references to `RENDER_EXTERNAL_URL`. Render
documents `RENDER_EXTERNAL_URL` as the full `onrender.com` URL for web services
and static sites. The dashboard may therefore receive its API base URL from the
API service through `fromService`.

The API CORS value is deliberately `sync: false` in Phase A instead of a
reverse `fromService` reference to the dashboard. That keeps the dependency
one-way and makes the final dashboard origin an explicit Phase B owner setting.
No public service URL is guessed or committed.

- [Blueprint YAML Reference](https://render.com/docs/blueprint-spec)
- [Default Environment Variables](https://render.com/docs/environment-variables)

## Validation boundary

The official Render CLI was not installed in the local environment, so
`render blueprints validate render.yaml` could not be run locally. The current
Render documentation says Blueprint validation is available in CLI v2.7.0+
and through an authenticated API endpoint; Phase A therefore performs static
schema/YAML validation without requesting or storing credentials. Render auth
is required for Phase B service creation and owner-context validation.

- [Render CLI](https://render.com/docs/cli)
- [Validate Blueprint API](https://api-docs.render.com/reference/validate-blueprint)
