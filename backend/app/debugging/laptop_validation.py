"""Laptop-only fixed test profiles using the existing credential-free CI sandbox."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any, cast

from .ci_contract import capture_snapshot, validation_spec
from .tools import RepositoryTools, _git


def load_policy() -> tuple[Any, Any]:
    # This is the installed worker's trusted policy, never candidate repository code.
    path = Path(__file__).resolve().parents[3] / "ops/debug-validation.py"
    spec = importlib.util.spec_from_file_location("fitician_laptop_validation_policy", path)
    if spec is None or spec.loader is None:
        raise ValueError("validation_policy_unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run, module.extract_source


def run_validation(
    tools: RepositoryTools,
    profile: str,
    tests: list[str],
    image: str,
    policy_sha: str,
    *,
    cancelled: threading.Event | None = None,
) -> dict[str, Any]:
    spec = validation_spec(profile, tests)
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", image):
        raise ValueError("immutable_validation_image_required")
    if not re.fullmatch(r"[a-f0-9]{40}", policy_sha):
        raise ValueError("validation_policy_image_mismatch")
    snapshot = capture_snapshot(tools)
    before = tools.tree_digest()
    sandbox, extract_source = load_policy()
    tools.test_evidence = None
    for suffix in (".tests.json", ".tested.json"):
        (tools.workspace.parent / (tools.workspace.name + suffix)).unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix=".validation-", dir=tools.workspace.parent) as folder:
        root = Path(folder)
        archive, source, output = root / "source.tar", root / "candidate", root / "result.json"
        with archive.open("wb") as stream:
            subprocess.run(
                [
                    "git",
                    "-c",
                    "core.hooksPath=/dev/null",
                    "-C",
                    str(tools.workspace),
                    "archive",
                    "--format=tar",
                    "HEAD",
                ],
                stdout=stream,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=30,
            )
        extract_source(archive, source)
        for item in snapshot["files"]:
            path = source / item["path"]
            if item["content"] is None:
                path.unlink(missing_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(item["content"])
        # An ephemeral local test snapshot is never the repair branch's commit
        # and is never published. It lets the unchanged CI policy test a clean tree.
        _git(source, "init", "-q")
        _git(source, "add", "--all")
        _git(
            source,
            "-c",
            "user.name=Fitician isolated validation",
            "-c",
            "user.email=validation@example.invalid",
            "commit",
            "-qm",
            "test: isolated snapshot",
        )
        result = sandbox(source, image, profile, tests, output, policy_sha, cancelled=cancelled)
    passed = bool(result.get("passed") and tools.tree_digest() == before)
    evidence = {
        **result,
        "passed": passed,
        "tree_digest": before,
        "snapshot_digest": snapshot["snapshot_digest"],
        "execution_target": "laptop",
        "commands": spec["commands"],
    }
    journal = tools.workspace.parent / (tools.workspace.name + ".tests.json")
    with journal.open("w") as stream:
        os.chmod(journal, 0o600)
        json.dump(evidence, stream)
    tools.test_evidence = evidence
    return cast(dict[str, Any], evidence)
