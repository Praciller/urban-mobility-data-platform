# Security Review — 2026-10-22

Scope: repository Git history and the Python/npm locked dependencies on branch `chatgpt/urban-mobility-correctness-20261022`. This is a time-bounded audit; it is not a guarantee that no secrets or vulnerabilities exist.

## Dependency checks

- `npm audit --audit-level=high`: **0 known vulnerabilities** after updating the frontend lockfile on 2026-10-22.
- `pip-audit` on runtime requirements exported with `uv export --locked --no-dev --no-emit-project`: **0 known vulnerabilities** on 2026-10-22.
- GitHub CI includes independent `dependency-security` and `python-dependency-security` jobs. These checks cannot verify vulnerabilities that are unpublished or missing from advisory databases.

## Gitleaks Git-history triage

Command used:

```powershell
gitleaks git . --no-banner --redact --log-opts="--all"
```

The scan inspected 32 historical commits and flagged 5 `generic-api-key` matches. Each match was checked against its original commit and line. They refer to **public Render service/deployment resource identifiers** embedded in historical documentation, not authentication tokens, bearer credentials, passwords, or API keys.

| Evidence group | Findings | Classification |
| --- | ---: | --- |
| Historical `docs/operations.md` | 4 | Benign Render deployment/service identifiers |
| Historical `docs/hosted_demo.md` | 1 | Benign Render service identifier |
| **Total** | **5** | **False positives after manual review** |

Raw identifiers are intentionally not reproduced here. No historic Git rewrite, rotation, broad path allowlist, or suppression was performed. Thus running Gitleaks with its default generic rule against complete history still exits nonzero for the documented findings. New or changed secrets must be triaged individually; this document is not an allowlist.

## Remaining controls

- Revisit findings if Render changes the semantics of its identifiers.
- Keep read-only, non-secret CI permissions and npm/Python audits.
- Consider a separate secret-scanning CI gate with carefully scoped, reviewed false-positive handling; do not disable the generic API-key rule.
- Do not mistake the absence of current dependency advisories for production security certification.
