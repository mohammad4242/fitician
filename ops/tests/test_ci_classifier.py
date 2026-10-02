from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("ci_classifier", ROOT / "ops/ci-classify.py")


def classifier():
    assert SPEC and SPEC.loader
    module = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(module)
    return module


class ClassifierTests(unittest.TestCase):
    def test_requested_examples(self):
        module = classifier()
        for path, expected in (
            ("frontend/src/features/workouts/WorkoutPlanPage.tsx", "frontend"),
            ("frontend/src/features/communication/conversationPanel.css", "frontend"),
            ("mobile/workouts/WorkoutPlansScreen.tsx", "mobile"),
            ("backend/app/workouts/service.py", "backend"),
            ("backend/app/nutrition/plan_service.py", "backend"),
            ("backend/alembic/versions/new.py", "full"),
            ("compose.prod.yaml", "full"),
            (".github/workflows/ci.yml", "full"),
            ("backend/app/auth/service.py", "full"),
            ("unknown/deployment.conf", "full"),
        ):
            with self.subTest(path=path):
                plan = module.classify([path], ROOT)
                self.assertEqual(plan["path"], expected)
                if expected == "mobile":
                    self.assertFalse(
                        any(
                            plan[k]
                            for k in (
                                "deploy_frontend",
                                "deploy_backend",
                                "deploy_agent",
                            )
                        )
                    )

    def test_high_risk_and_worker_dependencies(self):
        module = classifier()
        for path in (
            "backend/app/nutrition/models.py",
            "backend/app/nutrition/schemas.py",
            "backend/app/nutrition/security.py",
            "backend/app/nutrition/food_photo_service.py",
            "backend/app/nutrition/price_scheduler.py",
            "backend/app/entitlements/service.py",
            "backend/app/database/session.py",
            "backend/app/config.py",
            "frontend/Dockerfile",
            "frontend/nginx.conf",
            "frontend/vite.config.ts",
            "package-lock.json",
            "contracts/openapi.json",
            "packages/fitician-core/src/generated/api.ts",
            "ops/deploy-production.sh",
            "agent-service/app/main.py",
            "backend/app/new_domain/service.py",
        ):
            with self.subTest(path=path):
                self.assertTrue(module.classify([path], ROOT)["full_ci_required"])

    def test_medium_and_safe_shared(self):
        module = classifier()
        plan = module.classify(
            [
                "frontend/src/features/workouts/WorkoutPlanPage.tsx",
                "backend/app/workouts/service.py",
            ],
            ROOT,
        )
        self.assertEqual(plan["path"], "medium")
        self.assertTrue(plan["deploy_frontend"])
        self.assertTrue(plan["deploy_backend"])
        self.assertFalse(plan["deploy_agent"])
        plan = module.classify(
            ["mobile/screens/A.tsx", "packages/fitician-core/src/formatters.ts"], ROOT
        )
        self.assertEqual(plan["path"], "medium")
        self.assertTrue(plan["run_shared"])
        self.assertTrue(plan["run_frontend"])  # core is consumed by both clients
        self.assertTrue(plan["run_mobile"])

    def test_domain_suites_are_not_tiny_file_selection(self):
        module = classifier()
        workout = module.classify(["backend/app/workouts/service.py"], ROOT)
        self.assertTrue(
            {
                "tests/workouts",
                "tests/workout_cycles",
                "tests/workout_reviews",
                "tests/entitlements",
                "tests/test_openapi_mobile_contract.py",
            }
            <= set(workout["backend_tests"])
        )
        nutrition = module.classify(["backend/app/nutrition/plan_service.py"], ROOT)
        self.assertTrue(
            {"tests/nutrition", "tests/entitlements"} <= set(nutrition["backend_tests"])
        )

    def test_empty_and_docs_do_not_release(self):
        module = classifier()
        self.assertTrue(module.classify([], ROOT)["full_ci_required"])
        plan = module.classify(["docs/running-locally.md"], ROOT)
        self.assertEqual(plan["path"], "docs")
        self.assertFalse(plan["deploy_frontend"])

    def test_native_dependencies_and_release_config_never_deploy_vps(self):
        module = classifier()
        for path in ("mobile/package.json", "mobile/eas.json", "mobile/app.config.ts"):
            plan = module.classify([path], ROOT)
            self.assertEqual(plan["path"], "mobile")
            self.assertTrue(plan["run_android"])
            self.assertFalse(plan["deployable"])
        self.assertTrue(module.classify(["mobile/package.json"], ROOT)["run_dependencies"])

    def test_cli_preserves_base_and_nightly_disables_release(self):
        scratch = ROOT / ".codex-tmp"
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            output = Path(directory) / "plan.json"
            subprocess.run(
                [
                    "python3",
                    str(ROOT / "ops/ci-classify.py"),
                    "--base",
                    "HEAD",
                    "--full",
                    "--output",
                    str(output),
                ],
                check=True,
                env={**os.environ, "EVENT_NAME": "schedule"},
                capture_output=True,
            )
            plan = json.loads(output.read_text())
            self.assertEqual(plan["base_sha"], "HEAD")
            self.assertTrue(plan["full_ci_required"])
            self.assertFalse(plan["release_requested"])

    def test_order_and_duplicates_are_deterministic(self):
        module = classifier()
        paths = [
            "frontend/src/features/workouts/WorkoutPlanPage.tsx",
            "backend/app/workouts/service.py",
        ]
        self.assertEqual(module.classify(paths, ROOT), module.classify(paths[::-1] + paths, ROOT))


if __name__ == "__main__":
    unittest.main()
