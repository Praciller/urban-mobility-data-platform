"""Versioned, snapshot-consistent local publication of validation artifacts.

A single pointer update makes a fully materialized immutable version visible.
Previous published versions are retained for active readers and manual rollback.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

_REVISION = re.compile(r"^[0-9a-f]{32}$")
_ARTIFACTS = ("validated.parquet", "rejected.parquet", "summary.json")


class PublicationError(RuntimeError):
    """An active publication is malformed, incomplete, or unreadable."""


def partition_root(data_dir: Path, year: int, month: int, service: str) -> Path:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", service):
        raise PublicationError("Invalid publication service name")
    if not 1 <= month <= 12 or year < 1:
        raise PublicationError("Invalid publication partition")
    return (
        data_dir
        / "processed"
        / "publications"
        / f"service={service}"
        / f"year={year:04d}"
        / f"month={month:02d}"
    )


@contextmanager
def partition_write_lock(data_dir: Path, year: int, month: int, service: str) -> Iterator[None]:
    """Reject concurrent publishers; automatically release the OS lock on crash.

    The lock file is intentionally never deleted. Unlinking it could allow two
    writers to lock different inodes for the same partition on POSIX systems.
    """
    root = partition_root(data_dir, year, month, service)
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / "publication.lock"
    with lock_path.open("a+b") as stream:
        locked = False
        try:
            if os.name == "nt":
                import msvcrt

                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except OSError as error:
            raise PublicationError(
                f"Concurrent validation publisher for {service} {year}-{month:02d}"
            ) from error
        try:
            yield
        finally:
            if locked:
                if os.name == "nt":
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def allocate_version(data_dir: Path, year: int, month: int, service: str) -> Path:
    version = partition_root(data_dir, year, month, service) / "versions" / uuid4().hex
    version.mkdir(parents=True, exist_ok=False)
    return version


def current_version(data_dir: Path, year: int, month: int, service: str) -> Path | None:
    root = partition_root(data_dir, year, month, service)
    pointer = root / "current.json"
    if not pointer.exists():
        return None
    try:
        payload = json.loads(pointer.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ValueError("Invalid publication manifest schema")
        revision = payload.get("revision")
        if not isinstance(revision, str) or _REVISION.fullmatch(revision) is None:
            raise ValueError("Invalid publication revision")
        version = root / "versions" / revision
        if not all((version / name).is_file() for name in _ARTIFACTS):
            raise ValueError("Referenced publication is incomplete")
        return version
    except (OSError, ValueError, TypeError) as error:
        raise PublicationError(
            f"Invalid active publication for {service} {year}-{month:02d}"
        ) from error


def activate_version(data_dir: Path, year: int, month: int, service: str, version: Path) -> None:
    root = partition_root(data_dir, year, month, service)
    if version.parent != root / "versions" or _REVISION.fullmatch(version.name) is None:
        raise PublicationError("Cannot activate a version outside the selected partition")
    if not all((version / name).is_file() for name in _ARTIFACTS):
        raise PublicationError("Cannot publish incomplete validation artifacts")
    # Force file data toward disk before publishing the pointer. Files are never
    # mutated after publication, so readers retain a consistent three-file view.
    for name in _ARTIFACTS:
        with (version / name).open("r+b") as source:
            os.fsync(source.fileno())

    root.mkdir(parents=True, exist_ok=True)
    pointer = root / "current.json"
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".tmp",
            prefix=".current-",
            dir=root,
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump({"schema_version": 1, "revision": version.name}, stream)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(pointer)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
