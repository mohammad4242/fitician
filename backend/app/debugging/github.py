"""Narrow laptop-side GitHub broker. Publication is bound to tested local Git history."""

from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any

from .tools import RepositoryTools, _git

REPOSITORY = "mohammad4242/fitician"


def _gh(arguments: list[str], *, payload: dict[str, Any] | None = None) -> Any:
    result = subprocess.run(
        ["gh", "api", *arguments, *(["--input", "-"] if payload is not None else [])],
        input=json.dumps(payload) if payload is not None else None,
        capture_output=True,
        text=True,
        timeout=45,
    )
    if result.returncode:
        raise ValueError("github_operation_failed")
    return json.loads(result.stdout)


def publish_tested_pr(tools: RepositoryTools, title: str, *, base: str = "main") -> dict[str, str]:
    if not re.fullmatch(r"main|debug/seed-[a-f0-9-]{36}", base):
        raise ValueError("pull_request_base_not_authorized")
    if not tools.allow_write:
        raise ValueError("mutation_not_authorized")
    if not re.fullmatch(r"debug/run-[a-f0-9-]{36}", tools.branch):
        raise ValueError("debug_branch_required")
    # A clean worktree alone is insufficient; the local journal must bind tests to this commit.
    journal = tools.workspace.parent / (tools.workspace.name + ".tested.json")
    if not journal.is_file():
        raise ValueError("matching_successful_tests_required")
    evidence = json.loads(journal.read_text())
    commit = _git(tools.workspace, "rev-parse", "HEAD").strip()
    if evidence.get("commit") != commit or _git(tools.workspace, "status", "--porcelain").strip():
        raise ValueError("matching_successful_tests_required")
    if not re.fullmatch(r"(fix|feat|test|refactor)\([A-Za-z0-9_-]+\): [^\r\n]{5,120}", title):
        raise ValueError("specific_pr_title_required")
    base_ref = _gh([f"repos/{REPOSITORY}/git/ref/heads/{base}"])
    base_commit = base_ref.get("object", {}).get("sha", "")
    if not re.fullmatch(r"[a-f0-9]{40}", base_commit):
        raise ValueError("pull_request_base_unavailable")
    try:
        _git(tools.workspace, "merge-base", "--is-ancestor", base_commit, commit)
    except ValueError:
        # Never publish an old-release branch that would revert subsequent main changes.
        raise ValueError("repair_requires_current_base") from None
    environment = dict(
        os.environ,
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL="/dev/null",
        GIT_TERMINAL_PROMPT="0",
        GH_HOST="github.com",
    )
    result = subprocess.run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "credential.helper=",
            "-c",
            "credential.helper=!gh auth git-credential",
            "-C",
            str(tools.workspace),
            "push",
            "https://github.com/" + REPOSITORY + ".git",
            "HEAD:refs/heads/" + tools.branch,
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=90,
    )
    if result.returncode:
        raise ValueError("github_branch_push_failed")
    observed = _gh([f"repos/{REPOSITORY}/git/ref/heads/{tools.branch}"])
    if observed.get("object", {}).get("sha") != commit:
        raise ValueError("github_commit_mismatch")
    body = (
        "Prepared by the issue-scoped Fitician debug agent.\n\n"
        f"Tested commit: `{commit}`.\n\n"
        f"Sandbox test image: `{evidence.get('image', 'unknown')}`.\n\n"
        "Review the focused diff and CI before merge. "
        "Deployment requires separate artifact-bound authorization."
    )
    existing = _gh([f"repos/{REPOSITORY}/pulls?state=open&head=mohammad4242:{tools.branch}"])
    if existing:
        if existing[0].get("base", {}).get("ref") != base:
            raise ValueError("pull_request_base_mismatch")
        pr = _gh(
            ["--method", "PATCH", f"repos/{REPOSITORY}/pulls/{existing[0]['number']}"],
            payload={"title": title, "body": body},
        )
    else:
        pr = _gh(
            ["--method", "POST", f"repos/{REPOSITORY}/pulls"],
            payload={
                "head": tools.branch,
                "base": base,
                "title": title,
                "body": body,
                "draft": True,
            },
        )
    return {"commit": commit, "branch": tools.branch, "base": base, "pr_url": pr["html_url"]}
