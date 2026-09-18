from __future__ import annotations

import argparse
import asyncio
import json
import os
import threading
import time
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager, suppress
from pathlib import Path


def write_heartbeat(path: Path, *, service: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    payload = {
        "pid": os.getpid(),
        "service": service,
        "timestamp": time.time(),
    }
    try:
        temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        temporary.replace(path)
    finally:
        with suppress(FileNotFoundError):
            temporary.unlink()


def heartbeat_is_healthy(
    path: Path,
    *,
    max_age_seconds: float,
    expected_service: str,
) -> bool:
    try:
        age = time.time() - path.stat().st_mtime
        payload = json.loads(path.read_text(encoding="utf-8"))
        pid = int(payload["pid"])
        service = str(payload["service"])
        if age < 0 or age > max_age_seconds or service != expected_service:
            return False
        os.kill(pid, 0)
    except (FileNotFoundError, KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
        return False
    return True


@asynccontextmanager
async def async_heartbeat(
    path: Path,
    *,
    service: str,
    interval_seconds: float,
) -> AsyncIterator[None]:
    write_heartbeat(path, service=service)

    async def pulse() -> None:
        while True:
            await asyncio.sleep(interval_seconds)
            write_heartbeat(path, service=service)

    task = asyncio.create_task(pulse(), name=f"{service}-heartbeat")
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


@contextmanager
def threaded_heartbeat(
    path: Path,
    *,
    service: str,
    interval_seconds: float,
) -> Iterator[None]:
    stopped = threading.Event()
    write_heartbeat(path, service=service)

    def pulse() -> None:
        while not stopped.wait(interval_seconds):
            write_heartbeat(path, service=service)

    thread = threading.Thread(target=pulse, name=f"{service}-heartbeat", daemon=True)
    thread.start()
    try:
        yield
    finally:
        stopped.set()
        thread.join(timeout=max(1.0, interval_seconds * 2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Fitician worker heartbeat")
    parser.add_argument(
        "--path",
        type=Path,
        default=Path(os.environ.get("JOB_HEARTBEAT_PATH", "/run/fitician/heartbeat.json")),
    )
    parser.add_argument(
        "--service",
        default=os.environ.get("JOB_HEARTBEAT_SERVICE", ""),
    )
    parser.add_argument(
        "--max-age-seconds",
        type=float,
        default=float(os.environ.get("JOB_HEARTBEAT_MAX_AGE_SECONDS", "20")),
    )
    arguments = parser.parse_args()
    if not arguments.service:
        return 2
    return int(
        not heartbeat_is_healthy(
            arguments.path,
            max_age_seconds=arguments.max_age_seconds,
            expected_service=arguments.service,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
