"""Immutable repair snapshots and fixed validation profiles shared with trusted CI."""

from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import Any

from .privacy import sanitize_text
from .tools import RepositoryTools, _git

PROFILES = ("backend", "migrations", "frontend", "frontend_build", "agent")


def validate_files(files: Any) -> list[dict[str, Any]]:
    if not isinstance(files, list) or not 0 <= len(files) <= 30:
        raise ValueError("focused_snapshot_required")
    result = []
    seen: set[str] = set()
    size = 0
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "content"}:
            raise ValueError("invalid_snapshot_file")
        name, content = item["path"], item["content"]
        if not isinstance(name, str):
            raise ValueError("snapshot_path_not_authorized")
        path = PurePosixPath(name)
        if (
            len(name) > 240
            or not re.fullmatch(r"[A-Za-z0-9_./-]+", name)
            or str(path) != name
            or path.is_absolute()
            or any(
                p.startswith(".") or p in {"var", "node_modules", "__pycache__"} for p in path.parts
            )
            or name.startswith(("ops/", "docker/", "compose"))
            or path.name in {"package.json", "pyproject.toml"}
            or path.suffix not in {".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".sql"}
        ):
            raise ValueError("snapshot_path_not_authorized")
        if name in seen:
            raise ValueError("duplicate_snapshot_file")
        seen.add(name)
        if content is not None:
            if not isinstance(content, str) or "\x00" in content:
                raise ValueError("invalid_snapshot_file")
            if len(content.encode()) > 131072 or sanitize_text(content, limit=131072) != content:
                raise ValueError("unsafe_or_oversized_snapshot")
            size += len(content.encode())
        result.append({"path": name, "content": content})
    if size > 1_048_576:
        raise ValueError("snapshot_size_exceeded")
    return sorted(result, key=lambda item: item["path"])


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def validate_snapshot(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {
        "base_commit",
        "tree_digest",
        "files",
        "snapshot_digest",
    }:
        raise ValueError("invalid_snapshot")
    for key, length in (("base_commit", 40), ("tree_digest", 64), ("snapshot_digest", 64)):
        if not isinstance(payload[key], str) or not re.fullmatch(
            rf"[a-f0-9]{{{length}}}", payload[key]
        ):
            raise ValueError("invalid_snapshot_identity")
    canonical = {key: payload[key] for key in ("base_commit", "tree_digest")}
    canonical["files"] = validate_files(payload["files"])
    if payload["snapshot_digest"] != _digest(canonical):
        raise ValueError("snapshot_digest_mismatch")
    return {**canonical, "snapshot_digest": payload["snapshot_digest"]}


def capture_snapshot(tools: RepositoryTools) -> dict[str, Any]:
    before = tools.tree_digest()
    names = _git(tools.workspace, "diff", "--name-only", "-z", "HEAD").split("\0")
    names += _git(tools.workspace, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
    files = []
    for name in sorted(set(filter(None, names))):
        path = tools.safe_path(name)
        if path.exists() and (not path.is_file() or path.stat().st_size > 131072):
            raise ValueError("unsafe_or_oversized_snapshot")
        files.append({"path": name, "content": path.read_text() if path.exists() else None})
    canonical = {
        "base_commit": _git(tools.workspace, "rev-parse", "HEAD").strip(),
        "tree_digest": before,
        "files": validate_files(files),
    }
    if tools.tree_digest() != before:
        raise ValueError("workspace_changed_during_snapshot")
    return {**canonical, "snapshot_digest": _digest(canonical)}


def validation_spec(profile: str, tests: list[str]) -> dict[str, Any]:
    valid = profile in PROFILES and isinstance(tests, list) and len(tests) <= 16
    if not valid:
        raise ValueError("validation_profile_not_authorized")
    root = "agent-service" if profile == "agent" else "backend"
    if profile.startswith("frontend"):
        root = "frontend"
    for path in tests:
        if (
            not isinstance(path, str)
            or len(path) > 240
            or not re.fullmatch(r"[A-Za-z0-9_./-]+", path)
            or str(PurePosixPath(path)) != path
            or any(part.startswith(".") for part in PurePosixPath(path).parts)
            or not path.startswith(root + "/")
            or (
                root == "frontend"
                and not re.fullmatch(r"frontend/(src|tests)/.+\.test\.tsx?", path)
            )
            or (
                root != "frontend"
                and not re.fullmatch(root + r"/tests/(.*/)?test_[A-Za-z0-9_]+\.py", path)
            )
        ):
            raise ValueError("validation_profile_not_authorized")
    if (profile == "migrations" and tests) or (profile != "migrations" and not tests):
        raise ValueError("validation_profile_not_authorized")
    selected = [path.removeprefix(root + "/") for path in dict.fromkeys(tests)]
    if root == "frontend":
        commands = [
            ["node", "/workspace/node_modules/typescript/bin/tsc", "-b", "--pretty", "false"],
            [
                "node",
                "/workspace/node_modules/vitest/vitest.mjs",
                "run",
                *selected,
                "--reporter=junit",
                "--outputFile=/output/results.xml",
            ],
        ]
        if profile == "frontend_build":
            commands.append(["npm", "run", "build"])
    else:
        commands = [
            [
                "python",
                "-m",
                "pytest",
                *selected,
                "-q",
                "--tb=short",
                "--junitxml=/output/results.xml",
                "--basetemp=/scratch/pytest",
            ]
        ]
        if profile == "migrations":
            commands = [
                ["python", "-m", "alembic", "upgrade", "head"],
                [
                    "python",
                    "-m",
                    "pytest",
                    "tests/database",
                    "-q",
                    "--tb=short",
                    "--junitxml=/output/results.xml",
                    "--basetemp=/scratch/pytest",
                ],
            ]
    return {
        "profile": profile,
        "tests": list(dict.fromkeys(tests)),
        "cwd": root,
        "commands": commands,
        "timeout_seconds": 1200,
        "network": "isolated_postgres" if root == "backend" else "none",
    }


def test_result(path: Path) -> dict[str, int]:
    try:
        if path.stat().st_size > 1048576:
            raise ValueError("result_too_large")
        root = ET.parse(path).getroot()
        suites = [root] if root.tag == "testsuite" else list(root.findall(".//testsuite"))
        tests = sum(int(s.get("tests", "0")) for s in suites)
        skipped = sum(int(s.get("skipped", "0")) for s in suites)
        failures = sum(int(s.get("failures", "0")) + int(s.get("errors", "0")) for s in suites)
        if min(tests, skipped, failures) < 0 or skipped > tests:
            raise ValueError("invalid_test_counts")
        return {"exercised": tests - skipped, "skipped": skipped, "failures": failures}
    except (OSError, ValueError, ET.ParseError):
        return {"exercised": 0, "skipped": 0, "failures": 1}
