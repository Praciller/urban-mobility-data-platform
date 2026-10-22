from __future__ import annotations

import concurrent.futures
import time
from pathlib import Path
from threading import Event

from urban_mobility.validation_store import (
    activate_version,
    allocate_version,
    current_version,
    partition_write_lock,
)


def test_pinned_readers_never_observe_mixed_artifacts_during_publication(
    tmp_path: Path,
) -> None:
    revisions: list[Path] = []
    for marker in (b"A", b"B"):
        version = allocate_version(tmp_path, 2026, 1, "yellow")
        for name in ("validated.parquet", "rejected.parquet", "summary.json"):
            (version / name).write_bytes(marker)
        revisions.append(version)
    activate_version(tmp_path, 2026, 1, "yellow", revisions[0])
    started = Event()

    def writer() -> None:
        started.set()
        for i in range(60):
            with partition_write_lock(tmp_path, 2026, 1, "yellow"):
                activate_version(tmp_path, 2026, 1, "yellow", revisions[i % 2])
            time.sleep(0.001)

    def reader() -> int:
        assert started.wait(timeout=3)
        read_count = 0
        for _ in range(180):
            version = current_version(tmp_path, 2026, 1, "yellow")
            assert version in revisions
            assert {
                (version / name).read_bytes()
                for name in ("validated.parquet", "rejected.parquet", "summary.json")
            } in ({b"A"}, {b"B"})
            read_count += 1
            time.sleep(0.0005)
        return read_count

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        write_future = pool.submit(writer)
        reads = [pool.submit(reader) for _ in range(4)]
        write_future.result(timeout=25)
        assert sum(result.result(timeout=25) for result in reads) == 720
    assert current_version(tmp_path, 2026, 1, "yellow") in revisions
