import importlib.util
import unittest
from pathlib import Path

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
