# Repository Instructions

- Treat `PROJECT_REQUIREMENTS_NO_SUPABASE.md` as authoritative.
- Keep implementation local-first and bounded to the active phase.
- Never add Supabase code, configuration, SDKs, auth, storage, or deployment guidance.
- Keep raw data, generated reports, databases, secrets, caches, and build output out of Git.
- Use `DATA_DIR` for data storage so full runs can live outside OneDrive.
- Use deterministic sample-mode checks in CI; never download full monthly datasets in CI.
- Prefer Python 3.12, `uv`, typed functions, focused modules, and PowerShell-friendly commands.
