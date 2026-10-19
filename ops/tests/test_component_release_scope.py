import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CumulativeScopeTests(unittest.TestCase):
    def test_cancelled_predecessor_schema_and_uncovered_domain_are_refused(self):
        classifier = load("classifier", "ops/ci-classify.py")
        guard = load("guard", "ops/check-component-release.py")
        migration = classifier.classify(
            [
                "frontend/src/features/workouts/WorkoutPlanPage.tsx",
                "backend/alembic/versions/new.py",
            ],
            ROOT,
        )
        with self.assertRaises(SystemExit):
            guard.check_plan(migration, "frontend", [], False)
        workout = classifier.classify(["backend/app/workouts/service.py"], ROOT)
        nutrition = classifier.classify(["backend/app/nutrition/plan_service.py"], ROOT)
        with self.assertRaises(SystemExit):
            guard.check_plan(nutrition, "backend", workout["backend_tests"], True)
        guard.check_plan(workout, "backend", workout["backend_tests"], True)

    def test_pending_shared_source_requires_shared_checks(self):
        classifier = load("classifier", "ops/ci-classify.py")
        guard = load("guard", "ops/check-component-release.py")
        plan = classifier.classify(["packages/fitician-core/src/formatters.ts"], ROOT)
        with self.assertRaises(SystemExit):
            guard.check_plan(plan, "frontend", [], False)
        guard.check_plan(plan, "frontend", [], True)


class FullValidatedFrontendScopeTests(unittest.TestCase):
    def test_full_proof_allows_only_frontend_build_inputs(self):
        classifier = load("classifier", "ops/ci-classify.py")
        guard = load("guard", "ops/check-component-release.py")
        plan = classifier.classify(
            ["frontend/nginx.conf", "frontend/src/main.tsx"], ROOT
        )
        with self.assertRaises(SystemExit):
            guard.check_plan(plan, "frontend", [], False)
        guard.check_plan(plan, "frontend", [], True, full_frontend_validated=True)
        for path in [
            "backend/alembic/new.py",
            "backend/app/main.py",
            "compose.prod.yaml",
            "agent-service/app.py",
            "packages/fitician-core/src/generated/api.ts",
        ]:
            unsafe = classifier.classify(["frontend/src/main.tsx", path], ROOT)
            with self.assertRaises(SystemExit):
                guard.check_plan(
                    unsafe, "frontend", [], True, full_frontend_validated=True
                )


class RegionalCumulativeScopeTests(unittest.TestCase):
    def test_frontend_keeps_shared_package_build_metadata_in_cumulative_scope(self):
        guard = load("guard", "ops/check-component-release.py")
        paths = [
            "packages/fitician-core/package.json",
            "packages/fitician-core/tsconfig.json",
        ]
        self.assertEqual(guard.frontend_image_paths(paths), paths)

    def test_auto_agent_refuses_pending_bootstrap_script_changes(self):
        guard = load("guard", "ops/check-component-release.py")
        paths = ["agent-service/app/main.py", "agent-service/docker/entrypoint.sh"]
        self.assertEqual(guard.agent_image_paths(paths), paths)
        with self.assertRaises(SystemExit):
            guard.strict_agent_image_paths(paths)

    def test_frontend_cumulative_scope_filters_unrelated_image_roles(self):
        guard = load("guard", "ops/check-component-release.py")
        paths = guard.frontend_image_paths(
            [
                "frontend/src/App.tsx",
                "packages/fitician-core/src/formatters.ts",
                "vendor/library/file.ts",
                "backend/app/exercises/seed_data.py",
                "backend/app/notifications/worker.py",
                "ops/deploy-regional.sh",
            ]
        )
        self.assertEqual(
            paths,
            [
                "frontend/src/App.tsx",
                "packages/fitician-core/src/formatters.ts",
                "vendor/library/file.ts",
                "backend/app/exercises/seed_data.py",
            ],
        )

    def test_agent_scope_requires_only_source_tests_and_docs(self):
        guard = load("guard", "ops/check-component-release.py")
        allowed = [
            "agent-service/app/main.py",
            "agent-service/tests/test_main.py",
            "docs/agent.md",
        ]
        self.assertEqual(guard.agent_image_paths(allowed), [allowed[0]])
        for path in ("agent-service/Dockerfile", "agent-service/pyproject.toml"):
            with self.subTest(path=path), self.assertRaises(SystemExit):
                guard.strict_agent_image_paths(["agent-service/app/main.py", path])
        self.assertEqual(
            guard.agent_image_paths(
                [
                    "agent-service/app/main.py",
                    "compose.prod.germany.yaml",
                    "ops/deploy-regional.sh",
                    "backend/alembic/versions/new.py",
                ]
            ),
            ["agent-service/app/main.py"],
        )

    def test_agent_cumulative_scope_filters_unrelated_region_and_rejects_auto_image_inputs(
        self,
    ):
        guard = load("guard", "ops/check-component-release.py")
        changed = [
            "agent-service/app/main.py",
            "agent-service/pyproject.toml",
            "agent-service/uv.lock",
            "agent-service/Dockerfile",
            "backend/app/workouts/service.py",
            "ops/deploy-regional.sh",
        ]
        self.assertEqual(
            guard.agent_image_paths(changed),
            changed[:4],
        )
        self.assertEqual(
            guard.strict_agent_image_paths(["agent-service/app/main.py"]),
            ["agent-service/app/main.py"],
        )
        for path in changed[1:4]:
            with self.subTest(path=path), self.assertRaises(SystemExit):
                guard.strict_agent_image_paths(["agent-service/app/main.py", path])

    def test_backend_scope_uses_verified_worker_sha_and_worker_based_delta(self):
        guard = load("guard", "ops/check-component-release.py")
        proof = {"api_sha": "a" * 40, "worker_sha": "b" * 40}
        controller = Mock()
        controller.validate_role_source_compatibility.return_value = proof
        paths = [
            "backend/app/workouts/service.py",
            "ops/irrelevant.py",
            "frontend/src/App.tsx",
        ]
        with (
            patch.object(guard, "role_controller", return_value=controller),
            patch.object(guard.classifier, "git_paths", return_value=paths) as delta,
            patch.object(guard.subprocess, "run") as run,
        ):
            filtered, verified = guard.backend_image_paths("a" * 40, "b" * 40, "c" * 40)
        controller.validate_role_source_compatibility.assert_called_once_with(
            "a" * 40, "b" * 40
        )
        run.assert_called_once()
        delta.assert_called_once_with("b" * 40, "c" * 40)
        self.assertEqual(filtered, ["backend/app/workouts/service.py"])
        self.assertEqual(verified, proof)

    def test_backend_scope_accepts_identical_api_and_worker_source_shas(self):
        guard = load("guard", "ops/check-component-release.py")
        sha = "a" * 40
        controller = Mock()
        with (
            patch.object(guard, "role_controller", return_value=controller),
            patch.object(
                guard.classifier, "git_paths", return_value=["backend/app/main.py"]
            ),
            patch.object(guard.subprocess, "run") as run,
        ):
            paths, proof = guard.backend_image_paths(sha, sha, "b" * 40)
        controller.validate_role_source_compatibility.assert_not_called()
        run.assert_called_once()
        self.assertEqual(paths, ["backend/app/main.py"])
        self.assertEqual(proof["api_sha"], sha)
        self.assertEqual(proof["worker_sha"], sha)

    def test_agent_full_ci_scope_accepts_only_source_tests_and_docs(self):
        classifier = load("classifier", "ops/ci-classify.py")
        guard = load("guard", "ops/check-component-release.py")
        paths = [
            "agent-service/app/main.py",
            "agent-service/tests/test_main.py",
            "docs/agent.md",
        ]
        plan = classifier.classify(paths, ROOT)
        self.assertTrue(plan["full_ci_required"])
        guard.check_plan(plan, "agent", [], False, full_agent_validated=True)
        unsafe = classifier.classify(paths + ["agent-service/pyproject.toml"], ROOT)
        guard.check_plan(unsafe, "agent", [], False, full_agent_validated=True)
        with self.assertRaises(SystemExit):
            guard.check_plan(plan, "backend", [], True, full_frontend_validated=True)
