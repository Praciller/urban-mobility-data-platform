from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class ManifestError(RuntimeError):
    """Raised when the download manifest cannot be read or written."""


def append_manifest_entry(path: Path, entry: Mapping[str, Any]) -> None:
    """Append one entry using an atomic file replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _read_manifest(path)
    payload["downloads"].append(dict(entry))

    temporary = path.with_suffix(f"{path.suffix}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise ManifestError(f"Unable to write manifest: {path}") from exc


def _read_manifest(path: Path) -> dict[str, list[dict[str, Any]]]:
    if not path.exists():
        return {"downloads": []}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"Unable to read manifest: {path}") from exc

    downloads = payload.get("downloads")
    if not isinstance(downloads, list):
        raise ManifestError(f"Manifest downloads must be a list: {path}")
    return {"downloads": downloads}
