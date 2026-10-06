import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "gate", Path(__file__).resolve().parents[1] / "ci-release-gate.py"
)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
SHA = "b" * 40


def success(*names):
    return [{"name": name, "conclusion": "success"} for name in names]


class ReleaseGateTests(unittest.TestCase):
    def test_frontend_fast_does_not_require_full_images(self):
        plan = dict(
            sha=SHA,
            release_requested=True,
            deployable=True,
            full_ci_required=False,
            deploy_frontend=True,
            deploy_backend=False,
            deploy_agent=False,
        )
        jobs = success(
            "Secret scan",
            "Frontend component / Frontend verification",
            "Frontend component / Build, verify, and push frontend image",
        )
        self.assertEqual(module.release_path(plan, jobs, SHA), "component")
        with self.assertRaises(ValueError):
            module.release_path(plan, jobs[:-1], SHA)

    def test_sha_mismatch_and_missing_full_images_fail_closed(self):
        plan = dict(
            sha=SHA, release_requested=True, deployable=True, full_ci_required=True
        )
        with self.assertRaises(ValueError):
            module.release_path(plan, success("Secret scan"), SHA)
        with self.assertRaises(ValueError):
            module.release_path(plan, [], "a" * 40)
        self.assertEqual(
            module.release_path(
                plan,
                success("Secret scan", "Build and publish immutable production images"),
                SHA,
            ),
            "full",
        )

    def test_nightly_manual_validation_and_mobile_never_release(self):
        for requested, deployable in [(False, True), (True, False)]:
            self.assertEqual(
                module.release_path(
                    dict(sha=SHA, release_requested=requested, deployable=deployable),
                    [],
                    SHA,
                ),
                "none",
            )


if __name__ == "__main__":
    unittest.main()


class FullFrontendReleaseTests(unittest.TestCase):
    def test_full_validated_frontend_routes_only_to_frontend(self):
        plan = dict(
            sha=SHA,
            release_requested=True,
            deployable=True,
            full_ci_required=True,
            changed_paths=[
                "frontend/nginx.conf",
                "frontend/src/main.tsx",
                ".github/workflows/public-seo.yml",
                "package-lock.json",
            ],
        )
        jobs = success("Secret scan", "Build and publish immutable production images")
        self.assertEqual(module.release_path(plan, jobs, SHA), "frontend-full")
        with self.assertRaises(ValueError):
            module.release_path(plan, success("Secret scan"), SHA)

    def test_full_backend_or_unknown_input_never_uses_frontend_only(self):
        for path in [
            "backend/app/main.py",
            "backend/alembic/versions/new.py",
            "compose.prod.yaml",
            "Caddyfile",
            "agent-service/app.py",
            "mobile/app/index.tsx",
            "unknown-file",
        ]:
            plan = dict(
                sha=SHA,
                release_requested=True,
                deployable=True,
                full_ci_required=True,
                changed_paths=["frontend/src/main.tsx", path],
            )
            self.assertEqual(
                module.release_path(
                    plan,
                    success(
                        "Secret scan", "Build and publish immutable production images"
                    ),
                    SHA,
                ),
                "full",
            )


class ExactMainEvidenceTests(unittest.TestCase):
    def test_successful_branch_fork_old_sha_and_failed_runs_are_refused(self):
        run = dict(
            head_sha=SHA,
            conclusion="success",
            name="Fitician CI",
            head_branch="main",
            event="push",
            head_repository={"full_name": "owner/repo"},
        )
        self.assertTrue(module.trusted_run(run, SHA, "owner/repo", "Fitician CI"))
        for key, value in [
            ("head_sha", "a" * 40),
            ("conclusion", "failure"),
            ("head_branch", "feat/public-seo"),
            ("event", "pull_request"),
            ("head_repository", {"full_name": "fork/repo"}),
        ]:
            self.assertFalse(
                module.trusted_run(
                    {**run, key: value}, SHA, "owner/repo", "Fitician CI"
                )
            )

    def test_seo_evidence_requires_successful_exact_main_sha(self):
        import json
        from unittest.mock import patch

        run = dict(
            head_sha=SHA,
            conclusion="success",
            name="Public SEO delivery",
            head_branch="main",
            event="push",
            head_repository={"full_name": "owner/repo"},
        )
        with patch.object(
            module.subprocess,
            "check_output",
            return_value=json.dumps({"workflow_runs": [run]}),
        ):
            module.require_seo_evidence("owner/repo", SHA)
        for bad in [
            {**run, "head_sha": "a" * 40},
            {**run, "head_branch": "feature"},
            {**run, "conclusion": "failure"},
        ]:
            with (
                patch.object(
                    module.subprocess,
                    "check_output",
                    return_value=json.dumps({"workflow_runs": [bad]}),
                ),
                self.assertRaises(SystemExit),
            ):
                module.require_seo_evidence("owner/repo", SHA)
