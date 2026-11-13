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
            [
                "node",
                "/policy/node-tool.cjs",
                "typescript",
                "-b",
                "--pretty",
                "false",
            ],
            [
                "node",
                "/policy/node-tool.cjs",
                "vitest",
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


def test_result(path: Path) -> dict[str, Any]:
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
        failed_tests = []
        for case in root.findall(".//testcase"):
            failure = case.find("failure")
            if failure is None:
                failure = case.find("error")
            if failure is None:
                continue
            fields = {
                "class_name": case.get("classname", "unknown"),
                "name": case.get("name", "unknown").split("[")[0],
                "type": failure.get("type", "TestFailure"),
            }
            failed_tests.append(
                {
                    k: v
                    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,239}", v) and sanitize_text(v) == v
                    else "unknown"
                    for k, v in fields.items()
                }
            )
            if len(failed_tests) >= 20:
                break
        return {
            "exercised": tests - skipped,
            "skipped": skipped,
            "failures": failures,
            "failed_tests": failed_tests,
        }
    except (OSError, ValueError, ET.ParseError):
        return {"exercised": 0, "skipped": 0, "failures": 1, "failed_tests": []}


def command_facts(log: str) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for line in log[:1048576].splitlines():
        match = re.match(r"([A-Za-z0-9_./-]{1,240})\(([0-9]{1,7}),[0-9]+\): error (TS[0-9]+)", line)
        if match and not match[1].startswith("/") and ".." not in PurePosixPath(match[1]).parts:
            facts.append({"code": match[3], "file": match[1], "line": int(match[2])})
        module = re.search(
            r"ModuleNotFoundError: No module named '([A-Za-z_][A-Za-z0-9_.]{0,100})'", line
        )
        if module:
            facts.append({"code": "ModuleNotFoundError", "module": module[1]})
        if len(facts) >= 20:
            break
    return facts


def validate_report(value: Any) -> dict[str, Any]:
    keys = {"exercised", "skipped", "failures", "failed_tests", "failed_stage", "diagnostics"}
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("invalid_validation_report")
    if any(
        type(value[k]) is not int or not 0 <= value[k] <= 100000
        for k in ("exercised", "skipped", "failures")
    ):
        raise ValueError("invalid_validation_report")
    if value["failed_stage"] is not None and (
        type(value["failed_stage"]) is not int or not 0 <= value["failed_stage"] <= 10
    ):
        raise ValueError("invalid_validation_report")
    for key in ("failed_tests", "diagnostics"):
        if not isinstance(value[key], list) or len(value[key]) > 20:
            raise ValueError("invalid_validation_report")
    for case in value["failed_tests"]:
        if (
            not isinstance(case, dict)
            or set(case) != {"class_name", "name", "type"}
            or any(
                not isinstance(v, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,239}", v)
                for v in case.values()
            )
        ):
            raise ValueError("invalid_validation_report")
    for item in value["diagnostics"]:
        if not isinstance(item, dict):
            raise ValueError("invalid_validation_report")
        if item.get("code") == "ModuleNotFoundError":
            valid = (
                set(item) == {"code", "module"}
                and isinstance(item["module"], str)
                and bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,100}", item["module"]))
            )
        else:
            valid = (
                set(item) == {"code", "file", "line"}
                and isinstance(item["code"], str)
                and bool(re.fullmatch(r"TS[0-9]{1,5}", item["code"]))
                and isinstance(item["file"], str)
                and bool(re.fullmatch(r"[A-Za-z0-9_./-]{1,240}", item["file"]))
                and not item["file"].startswith("/")
                and ".." not in PurePosixPath(item["file"]).parts
                and type(item["line"]) is int
                and 0 < item["line"] <= 10000000
            )
        if not valid:
            raise ValueError("invalid_validation_report")
    return value
