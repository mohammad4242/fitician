#!/usr/bin/env python3
"""Explicit owner-approved format conversion. Never replaces the actual model key."""

from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
import re
import stat
import sys
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path("/opt/fitician-debug-runtime")
PLAN = "model-format-review.json"


def read_existing(root: Path, owner: tuple[int, int]) -> tuple[bytes, os.stat_result]:
    private = root / "private"
    if root.is_symlink() or private.is_symlink() or not (root / "current/runtime.env").is_file():
        raise ValueError("dedicated_germany_runtime_required")
    try:
        fd = os.open(private / "model-api.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise ValueError("credential_metadata_invalid") from None
    with os.fdopen(fd, "rb") as source:
        info = os.fstat(source.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o600
            or (info.st_uid, info.st_gid) != owner
            or info.st_size > 8192
        ):
            raise ValueError("credential_metadata_invalid")
        raw = source.read(8193)
    return raw, info


def review(root: Path, *, owner: tuple[int, int]) -> dict:
    raw, info = read_existing(root, owner)
    if not re.fullmatch(rb"sk-or-v1-[A-Za-z0-9_-]{32,128}", raw.strip()):
        raise ValueError("bare_openrouter_key_required")
    return {
        "version": 1,
        "digest": hashlib.sha256(raw).hexdigest(),
        "device": info.st_dev,
        "inode": info.st_ino,
        "review_id": str(uuid4()),
    }


def write_private(path: Path, raw: bytes, owner: tuple[int, int]) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as output:
        os.fchmod(output.fileno(), 0o600)
        if owner != (os.getuid(), os.getgid()):
            os.fchown(output.fileno(), *owner)
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())


def apply_repair(root: Path, plan: dict, *, owner: tuple[int, int]) -> dict:
    if (
        set(plan) != {"version", "digest", "device", "inode", "review_id"}
        or plan["version"] != 1
        or not re.fullmatch(r"[a-f0-9]{64}", plan["digest"])
    ):
        raise ValueError("format_review_invalid")
    review_id = str(UUID(plan["review_id"]))
    private = root / "private"
    lock_fd = os.open(private / "model-api.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(lock_fd, "rb") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        raw, info = read_existing(root, owner)
        if (info.st_dev, info.st_ino) != (plan["device"], plan["inode"]) or not hmac.compare_digest(
            hashlib.sha256(raw).hexdigest(), plan["digest"]
        ):
            raise ValueError("credential_changed_after_review")
        if not re.fullmatch(rb"sk-or-v1-[A-Za-z0-9_-]{32,128}", raw.strip()):
            raise ValueError("bare_openrouter_key_required")
        backup = private / (".model-api.pre-format-" + review_id)
        pending = private / (".model-api.normalized-" + review_id)
        # The exact original stays root-private in the existing Germany store.
        write_private(backup, raw, (os.getuid(), os.getgid()))
        payload = {
            "purpose": "fitician_debug_agent",
            "provider": "openrouter",
            "revision": str(uuid4()),
            "FITICIAN_DEBUG_OPENROUTER_API_KEY": raw.decode().strip(),
        }
        try:
            write_private(pending, (json.dumps(payload) + "\n").encode(), owner)
            current, current_info = read_existing(root, owner)
            if current != raw or (current_info.st_dev, current_info.st_ino) != (
                info.st_dev,
                info.st_ino,
            ):
                raise ValueError("credential_changed_after_review")
            os.replace(pending, private / "model-api.json")
            directory = os.open(private, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            pending.unlink(missing_ok=True)
    return {"repaired": True, "key_unchanged": True, "backup": backup.name}


def main() -> int:
    args = sys.argv[1:]
    if args not in (["--preview"], ["--apply", "--owner-approved"]) or os.geteuid() != 0:
        print(
            "Use root: --preview, or --apply --owner-approved after explicit owner authorization."
        )
        return 2
    try:
        plan_path = ROOT / "setup" / PLAN
        if args == ["--preview"]:
            value = review(ROOT, owner=(10001, 10001))
            write_private(plan_path, json.dumps(value).encode(), (0, 0))
            print("Review prepared. Existing credential bytes unchanged; no provider request sent.")
        else:
            if plan_path.is_symlink() or stat.S_IMODE(plan_path.stat().st_mode) != 0o600:
                raise ValueError("format_review_invalid")
            plan = json.loads(plan_path.read_bytes())
            result = apply_repair(ROOT, plan, owner=(10001, 10001))
            print(json.dumps(result))
        return 0
    except (ValueError, OSError, TypeError, KeyError, UnicodeError):
        print("Format action blocked. Inspect metadata/review state securely; raw values withheld.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
