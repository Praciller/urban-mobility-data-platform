from __future__ import annotations

from urllib.parse import urlparse

DEFAULT_CORS_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


def get_allowed_origins(raw: str | None) -> list[str]:
    """Return exact HTTP(S) origins, keeping local defaults when unset."""
    if raw is None or not raw.strip():
        return list(DEFAULT_CORS_ORIGINS)
    origins: list[str] = []
    for candidate in raw.split(","):
        origin = candidate.strip().rstrip("/")
        parsed = urlparse(origin)
        invalid_parts = (
            parsed.path or parsed.params or parsed.query or parsed.fragment or "*" in origin
        )
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or invalid_parts:
            continue
        if origin not in origins:
            origins.append(origin)
    return origins
