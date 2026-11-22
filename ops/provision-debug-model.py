#!/usr/bin/env python3
"""Run interactively on Germany only. Secret input is never an argument or environment value."""

from __future__ import annotations

import getpass
import json
import os
import re
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path("/opt/fitician-debug-runtime")


def provision(root: Path, key: str, *, owner: tuple[int, int]) -> None:
    private = root / "private"
    if (
        root.is_symlink()
        or private.is_symlink()
        or not private.is_dir()
        or not (root / "runtime.env").is_file()
    ):
        raise ValueError("dedicated_germany_runtime_required")
    if not re.fullmatch(r"sk-or-v1-[A-Za-z0-9_-]{32,128}", key):
        raise ValueError("dedicated_openrouter_key_required")
    target = private / "model-api.json"
    if target.exists() or target.is_symlink():
        raise ValueError("credential_already_exists")
    temporary = private / (".model-api-" + uuid4().hex)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w") as output:
            os.fchmod(output.fileno(), 0o600)
            if owner != (os.getuid(), os.getgid()):
                os.fchown(output.fileno(), *owner)
            json.dump(
                {
                    "purpose": "fitician_debug_agent",
                    "provider": "openrouter",
                    "revision": str(uuid4()),
                    "FITICIAN_DEBUG_OPENROUTER_API_KEY": key,
                },
                output,
            )
            output.flush()
            os.fsync(output.fileno())
        # Exclusive publication, including a concurrent operator. Never overwrite/rotate.
        os.link(temporary, target, follow_symlinks=False)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    if len(sys.argv) != 1 or not sys.stdin.isatty() or os.geteuid() != 0:
        print(
            "Run this helper in an interactive root SSH session on Germany; no key arguments.",
            file=sys.stderr,
        )
        return 2
    try:
        if not (ROOT / "runtime.env").is_file():
            raise ValueError("dedicated_germany_runtime_required")
        key = getpass.getpass("Dedicated Fitician debug OpenRouter key (hidden): ")
        provision(ROOT, key, owner=(10001, 10001))
    except (OSError, ValueError, EOFError):
        print(
            "Credential was not provisioned. Check target, key type and existing file; nothing was overwritten.",
            file=sys.stderr,
        )
        return 1
    print(
        "Dedicated credential stored privately. Provider budget/auth verification is still required."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
