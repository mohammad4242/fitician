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
    def test_contract_refresh_needs_full_proof_and_only_generated_api_exception(self):
        classifier = load("classifier", "ops/ci-classify.py")
        guard = load("guard", "ops/check-component-release.py")
        paths = ["frontend/src/App.tsx", "packages/fitician-core/src/generated/api.ts"]
        plan = classifier.classify(paths, ROOT)
        with self.assertRaises(SystemExit):
            guard.check_plan(plan, "frontend", [], True, frontend_contract_verified=True)
        guard.check_plan(
            plan, "frontend", [], True,
            full_frontend_validated=True, frontend_contract_verified=True,
        )
        for path in ["packages/fitician-core/package.json", "vendor/a.ts", "backend/app/main.py"]:
            with self.subTest(path=path), self.assertRaises(SystemExit):
                guard.check_plan(
                    classifier.classify([*paths, path], ROOT), "frontend", [], True,
                    full_frontend_validated=True, frontend_contract_verified=True,
                )

    def test_contract_refresh_requires_live_api_ancestor_and_identical_backend_inputs(self):
        guard = load("guard", "ops/check-component-release.py")
        with (
            patch.object(guard.subprocess, "run") as ancestry,
            patch.object(guard.classifier, "git_paths", return_value=["agent-service/app/main.py"]),
        ):
            guard.verify_frontend_api_source("a" * 40, "b" * 40)
            ancestry.assert_called_once()
            self.assertEqual(ancestry.call_args.args[0][-2:], ["a" * 40, "b" * 40])
        for path in ["backend/app/main.py", "backend/alembic/a.py", "backend/pyproject.toml"]:
            with (
                self.subTest(path=path),
                patch.object(guard.subprocess, "run"),
                patch.object(guard.classifier, "git_paths", return_value=[path]),
                self.assertRaises(SystemExit),
            ):
                guard.verify_frontend_api_source("a" * 40, "b" * 40)

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
    def test_frontend_inputs_cover_dockerfile_copies_without_unrelated_backend_runtime(self):
        guard = load("guard", "ops/check-component-release.py")
        inputs = []
        for line in (ROOT / "frontend/Dockerfile").read_text().splitlines():
            if not line.startswith("COPY ") or line.startswith("COPY --from="):
                continue
            for source in line.split()[1:-1]:
                path = source + "/example.ts" if (ROOT / source).is_dir() else source
                inputs.append(path)
        self.assertEqual(guard.frontend_image_paths(inputs), inputs)
        self.assertEqual(
            guard.frontend_image_paths([
                "backend/app/exercises/service.py",
                "backend/app/exercises/router.py",
                "mobile/src/App.tsx",
            ]),
            [],
        )

    def test_observed_frontend_refresh_delta_excludes_api_only_service_comment(self):
        guard = load("guard", "ops/check-component-release.py")
        classifier = load("classifier", "ops/ci-classify.py")
        pending = [
            "backend/app/exercises/service.py",
            "frontend/e2e/ios-pwa-welcome.spec.ts",
            "frontend/src/features/admin/AdminTrainingTemplateEditorPage.test.tsx",
            "frontend/src/features/exercises/ExerciseDetailPage.test.tsx",
            "packages/fitician-core/src/generated/api.ts",
        ]
        plan = classifier.classify(guard.frontend_image_paths(pending), ROOT)
        guard.check_plan(
            plan, "frontend", [], False,
            full_frontend_validated=True, frontend_contract_verified=True,
        )

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
            patch.object(
                guard.subprocess,
                "run",
                side_effect=[Mock(returncode=1), Mock(returncode=0)],
            ) as run,
        ):
            filtered, verified = guard.backend_image_paths("a" * 40, "b" * 40, "c" * 40)
        controller.validate_role_source_compatibility.assert_called_once_with(
            "a" * 40, "b" * 40
        )
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0][-2:], ["b" * 40, "a" * 40])
        self.assertEqual(run.call_args_list[1].args[0][-2:], ["b" * 40, "c" * 40])
        delta.assert_called_once_with("b" * 40, "c" * 40)
        self.assertEqual(filtered, ["backend/app/workouts/service.py"])
        self.assertEqual(verified["source_compatibility"], proof)
        self.assertEqual(verified["cumulative_baseline_sha"], "b" * 40)
        self.assertEqual(verified["role_relation"], "worker-ahead-compatible")

    def test_api_ahead_of_unchanged_worker_uses_api_as_cumulative_baseline(self):
        guard = load("guard", "ops/check-component-release.py")
        controller = Mock()
        paths = ["backend/app/workouts/service.py"]
        with (
            patch.object(guard, "role_controller", return_value=controller),
            patch.object(guard.classifier, "git_paths", return_value=paths) as delta,
            patch.object(guard.subprocess, "run", return_value=Mock(returncode=0)) as run,
        ):
            filtered, proof = guard.backend_image_paths("b" * 40, "a" * 40, "c" * 40)
        controller.validate_role_source_compatibility.assert_not_called()
        self.assertEqual(run.call_args_list[0].args[0][-2:], ["a" * 40, "b" * 40])
        self.assertEqual(run.call_args_list[1].args[0][-2:], ["b" * 40, "c" * 40])
        delta.assert_called_once_with("b" * 40, "c" * 40)
        self.assertEqual(filtered, paths)
        self.assertEqual(proof["api_sha"], "b" * 40)
        self.assertEqual(proof["worker_sha"], "a" * 40)
        self.assertEqual(proof["cumulative_baseline_sha"], "b" * 40)
        self.assertEqual(proof["role_relation"], "api-ahead")
        self.assertIsNone(proof["source_compatibility"])

    def test_api_release_after_api_has_advanced_covers_everything_since_api_base(self):
        guard = load("guard", "ops/check-component-release.py")
        controller = Mock()
        changed = ["backend/app/nutrition/plan_service.py"]
        with (
            patch.object(guard, "role_controller", return_value=controller),
            patch.object(guard.classifier, "git_paths", return_value=changed) as delta,
            patch.object(guard.subprocess, "run", return_value=Mock(returncode=0)),
        ):
            paths, proof = guard.backend_image_paths("b" * 40, "a" * 40, "c" * 40)
        delta.assert_called_once_with("b" * 40, "c" * 40)
        self.assertEqual(paths, changed)
        self.assertEqual(proof["cumulative_baseline_sha"], "b" * 40)

    def test_unsafe_api_to_worker_source_advance_is_rejected(self):
        guard = load("guard", "ops/check-component-release.py")
        controller = Mock()
        controller.validate_role_source_compatibility.side_effect = ValueError(
            "Worker behavior differs outside startup initialization"
        )
        with (
            patch.object(guard, "role_controller", return_value=controller),
            patch.object(guard.subprocess, "run", return_value=Mock(returncode=1)),
            patch.object(guard.classifier, "git_paths") as delta,
            self.assertRaises(ValueError),
        ):
            guard.backend_image_paths("a" * 40, "b" * 40, "c" * 40)
        delta.assert_not_called()

    def test_backend_scope_accepts_identical_api_and_worker_source_shas(self):
        guard = load("guard", "ops/check-component-release.py")
        sha = "a" * 40
        controller = Mock()
        with (
            patch.object(guard, "role_controller", return_value=controller),
            patch.object(
                guard.classifier, "git_paths", return_value=["backend/app/main.py"]
            ),
            patch.object(guard.subprocess, "run", return_value=Mock(returncode=0)) as run,
        ):
            paths, proof = guard.backend_image_paths(sha, sha, "b" * 40)
        controller.validate_role_source_compatibility.assert_not_called()
        run.assert_called_once()
        self.assertEqual(paths, ["backend/app/main.py"])
        self.assertEqual(proof["api_sha"], sha)
        self.assertEqual(proof["worker_sha"], sha)
        self.assertEqual(proof["cumulative_baseline_sha"], sha)
        self.assertEqual(proof["role_relation"], "same")

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
