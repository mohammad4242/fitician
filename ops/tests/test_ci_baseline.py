"""Full CI reuse requires real evidence and an unchanged application/dependency tree."""

import importlib.util
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("ci_baseline", ROOT / "ops/ci-baseline.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
BASE = "a" * 40
HEAD = "b" * 40
NOW = datetime(2026, 10, 12, tzinfo=UTC)


def evidence():
    return {
        "run": {
            "id": 123,
            "name": "Fitician CI",
            "path": ".github/workflows/ci.yml",
            "head_sha": BASE,
            "status": "completed",
            "conclusion": "success",
            "event": "workflow_dispatch",
            "head_branch": "feat/regional",
            "head_repository": {"full_name": "owner/repo"},
            "created_at": (NOW - timedelta(days=1)).isoformat(),
        },
        "plan": {"sha": BASE, "full_ci_required": True},
        "jobs": [{"name": name, "conclusion": "success"} for name in module.FULL_JOBS],
    }


class BaselineTests(unittest.TestCase):
    def test_docs_only_changes_do_not_request_image_publication(self):
        self.assertFalse(module.ops_only(["docs/architecture.md"]))

    def test_reviewed_offline_ops_tools_reuse_only_unchanged_application_evidence(self):
        paths = [
            "ops/regional-cutover.py",
            "ops/rehearse-regional.py",
            "ops/compose.offline-rehearsal.yaml",
            "ops/Caddyfile.offline-rehearsal",
        ]
        self.assertTrue(module.ops_only(paths))
        self.assertFalse(module.ops_only(paths + ["backend/app/main.py"]))
        self.assertFalse(module.ops_only(paths + ["ops/unknown-command.py"]))

    def verify(self, data):
        with patch.object(module, "git_delta", return_value=["ops/deploy-regional.sh"]):
            return module.verify(data, "owner/repo", HEAD, ROOT, now=NOW)

    def test_complete_same_repo_feature_ancestor_is_valid(self):
        proof = self.verify(evidence())
        self.assertEqual(proof["run_id"], 123)
        self.assertEqual(proof["sha"], BASE)
        self.assertEqual(proof["changed_paths"], ["ops/deploy-regional.sh"])

    def test_failed_skipped_missing_duplicate_or_fork_evidence_is_rejected(self):
        variants = []
        for field, value in (
            ("conclusion", "failure"),
            ("event", "pull_request"),
            ("status", "in_progress"),
            ("path", ".github/workflows/other.yml"),
            ("head_repository", {"full_name": "fork/repo"}),
        ):
            data = evidence()
            data["run"][field] = value
            variants.append(data)
        for conclusion in ("skipped", "failure", "cancelled"):
            data = evidence()
            data["jobs"][0]["conclusion"] = conclusion
            variants.append(data)
        data = evidence()
        data["jobs"].pop()
        variants.append(data)
        data = evidence()
        data["jobs"].append(data["jobs"][0])
        variants.append(data)
        data = evidence()
        data["plan"]["sha"] = HEAD
        variants.append(data)
        data = evidence()
        data["plan"]["full_ci_required"] = False
        variants.append(data)
        for data in variants:
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.verify(data)

    def test_old_and_future_evidence_is_rejected(self):
        for age in (timedelta(days=8), timedelta(minutes=-10)):
            data = evidence()
            data["run"]["created_at"] = (NOW - age).isoformat()
            with self.assertRaises(ValueError):
                self.verify(data)

    def test_application_build_lock_schema_and_unknown_differences_require_full(self):
        for path in (
            "backend/app/main.py",
            "backend/tests/test_health.py",
            "agent-service/app/main.py",
            "frontend/src/main.tsx",
            "mobile/app.json",
            "package-lock.json",
            "backend/uv.lock",
            "frontend/Dockerfile",
            "backend/alembic/versions/new.py",
            ".github/workflows/unknown.yml",
            "ops/new-unreviewed-command.sh",
            "compose.prod.yaml",
        ):
            with self.subTest(path=path), patch.object(module, "git_delta", return_value=[path]):
                with self.assertRaises(ValueError):
                    module.verify(evidence(), "owner/repo", HEAD, ROOT, now=NOW)

    def test_non_ancestor_is_rejected_with_real_git(self):
        (ROOT / ".codex-tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp") as directory:

            def git(*args):
                return subprocess.check_output(["git", *args], cwd=directory, text=True).strip()

            git("init", "-q")
            git(
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "--allow-empty",
                "-qm",
                "first",
            )
            first = git("rev-parse", "HEAD")
            git("checkout", "--orphan", "other")
            git(
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "--allow-empty",
                "-qm",
                "other",
            )
            with self.assertRaises(ValueError):
                module.git_delta(first, "HEAD", Path(directory))
