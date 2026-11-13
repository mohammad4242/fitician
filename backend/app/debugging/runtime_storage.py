"""Fixed-origin, exact-commit fetches for the bounded independent runtime checkout."""

import re
import shutil
from pathlib import Path

from .tools import _git

ORIGIN = "https://github.com/mohammad4242/fitician.git"


def ensure_release(repository: Path, commit: str) -> None:
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("exact_release_commit_required")
    try:
        _git(repository, "cat-file", "-e", commit + "^{commit}")
        return
    except ValueError:
        pass
    if shutil.disk_usage(repository).free < 1_610_612_736:
        raise ValueError("repository_capacity_reached")
    _git(
        repository,
        "-c",
        "credential.helper=",
        "-c",
        "protocol.file.allow=never",
        "-c",
        "protocol.ext.allow=never",
        "-c",
        "fetch.recurseSubmodules=false",
        "fetch",
        "--depth=1",
        "--no-tags",
        "--no-recurse-submodules",
        ORIGIN,
        commit,
    )
    if _git(repository, "rev-parse", "--verify", commit + "^{commit}").strip() != commit:
        raise ValueError("release_commit_mismatch")


def initialize_repository(repository: Path, commit: str) -> None:
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("exact_release_commit_required")
    if repository.is_symlink():
        raise ValueError("private_repository_required")
    repository.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not (repository / ".git").exists():
        if any(repository.iterdir()):
            raise ValueError("empty_runtime_repository_required")
        _git(repository, "init", "--initial-branch=runtime-source")
    ensure_release(repository, commit)
    try:
        _git(repository, "rev-parse", "--verify", "HEAD")
    except ValueError:
        # Also recovers a restart between repository initialization and its first fetch.
        # No full primary checkout or laptop Git history; only isolated worktrees hold files.
        _git(repository, "update-ref", "refs/heads/runtime-source", commit)
