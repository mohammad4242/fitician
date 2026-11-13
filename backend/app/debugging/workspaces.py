"""Bounded managed checkouts; only clean read-only caches may be recycled."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any
from uuid import UUID

from .tools import _git


def _manifests(root: Path) -> list[Path]:
    return [p for p in root.glob("*.json") if re.fullmatch(r"[a-f0-9-]{36}", p.stem)]


def _available(root: Path, limit: int, minimum: int) -> bool:
    return (
        sum((root / p.stem).exists() for p in _manifests(root)) < limit
        and shutil.disk_usage(root).free >= minimum
    )


def _metadata(path: Path) -> dict[str, Any] | None:
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_mode & 0o077
        or path.stat().st_size > 16384
    ):
        return None
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else None
    except (ValueError, OSError):
        return None


def _recycle(repository: Path, root: Path, limit: int, minimum: int) -> None:
    candidates = sorted(
        (p for p in _manifests(root) if p.is_file() and not p.is_symlink()),
        key=lambda p: p.stat().st_mtime_ns,
    )
    for manifest in candidates:
        if _available(root, limit, minimum):
            return
        workspace = root / manifest.stem
        if workspace.is_symlink() or not workspace.is_dir() or manifest.stat().st_mode & 0o077:
            continue
        try:
            identifier = str(UUID(manifest.stem))
            metadata = _metadata(manifest)
            if metadata is None:
                continue
            branch = "debug/run-" + identifier
            if (
                metadata.get("repository") != str(repository)
                or metadata.get("allow_write") is not False
                or metadata.get("branch") != branch
                or not isinstance(metadata.get("commit"), str)
                or not re.fullmatch(r"[a-f0-9]{40}", metadata["commit"])
                or _git(workspace, "branch", "--show-current").strip() != branch
                or _git(workspace, "rev-parse", "HEAD").strip() != metadata["commit"]
                or _git(workspace, "status", "--porcelain").strip()
            ):
                continue
            # Git performs its own dirty/untracked check. Never force, delete a branch,
            # remove a repair workspace, or touch conversation/test/session journals.
            _git(repository, "worktree", "remove", str(workspace))
        except (ValueError, OSError):
            continue


def prepare_workspace(
    repository: Path,
    root: Path,
    identifier: str,
    commit: str,
    *,
    allow_write: bool,
    max_workspaces: int,
    min_free_bytes: int,
    evict_readonly: bool,
) -> tuple[Path, str]:
    if (
        type(max_workspaces) is not int
        or not 1 <= max_workspaces <= 40
        or type(min_free_bytes) is not int
        or min_free_bytes < 1_073_741_824
        or type(evict_readonly) is not bool
    ):
        raise ValueError("invalid_workspace_capacity_policy")
    identifier = str(UUID(identifier))
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("exact_release_commit_required")
    repository = repository.resolve(strict=True)
    if _git(repository, "rev-parse", "--show-toplevel").strip() != str(repository):
        raise ValueError("repository_root_required")
    try:
        available = _git(repository, "rev-parse", "--verify", commit + "^{commit}").strip()
    except ValueError:
        raise ValueError("release_commit_not_available") from None
    if available != commit:
        raise ValueError("release_commit_not_available")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root = root.resolve()
    workspace = root / identifier
    manifest = root / (identifier + ".json")
    branch = "debug/run-" + identifier
    identity: dict[str, Any] = {
        "repository": str(repository),
        "commit": commit,
        "allow_write": allow_write,
        "branch": branch,
    }
    if workspace.is_symlink() or manifest.is_symlink():
        raise ValueError("workspace_identity_mismatch")
    owned = manifest.is_file()
    if manifest.exists() and _metadata(manifest) != identity:
        raise ValueError("workspace_identity_mismatch")
    if workspace.exists():
        if not owned:
            raise ValueError("workspace_identity_mismatch")
        if _git(workspace, "branch", "--show-current").strip() != branch:
            raise ValueError("workspace_branch_mismatch")
        if not allow_write:
            if _git(workspace, "rev-parse", "HEAD").strip() != commit:
                raise ValueError("workspace_release_mismatch")
            if _git(workspace, "status", "--porcelain").strip():
                raise ValueError("workspace_not_clean")
    else:
        if not _available(root, max_workspaces, min_free_bytes) and evict_readonly:
            _recycle(repository, root, max_workspaces, min_free_bytes)
        if not _available(root, max_workspaces, min_free_bytes):
            raise ValueError("workspace_capacity_reached")
        try:
            existing = _git(repository, "rev-parse", "--verify", "refs/heads/" + branch).strip()
        except ValueError:
            existing = None
        if existing is not None and (not owned or existing != commit):
            raise ValueError("workspace_branch_not_owned")
        if not owned:
            with manifest.open("x") as stream:
                os.chmod(manifest, 0o600)
                json.dump(identity, stream)
        if existing is None:
            _git(repository, "worktree", "add", "-b", branch, str(workspace), commit)
        else:
            _git(repository, "worktree", "add", str(workspace), branch)
    manifest.touch()
    return workspace, branch
