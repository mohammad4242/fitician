"""Cheap liveness only: no provider, repository, network or configuration imports."""

from __future__ import annotations

import argparse
import json
import math
import os
import stat
import time
from pathlib import Path


def healthy(path: Path, *, now: float | None = None) -> bool:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_size > 65536:
                return False
            value = json.loads(source.read(65537))
        stamp = value["heartbeat"]
        return (
            type(stamp) in (int, float)
            and math.isfinite(stamp)
            and 0 <= (time.time() if now is None else now) - stamp < 45
        )
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status-file", type=Path, default=Path("/state/status.json"))
    args = parser.parse_args()
    raise SystemExit(0 if healthy(args.status_file) else 1)


if __name__ == "__main__":
    main()
