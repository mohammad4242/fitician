import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("ci_required", ROOT / "ops/ci-required.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class RequiredCITests(unittest.TestCase):
    def test_ci_workflow_exposes_stable_aggregate_over_all_validation_jobs(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("required-ci:", workflow)
        required = workflow.split("  required-ci:", 1)[1]
        for job in module.ALL_JOBS:
            self.assertIn(f"needs.{job}.result", required)
        self.assertIn("if: always()", required)
        self.assertIn("ops/ci-required.py", required)

    def test_selected_jobs_and_security_gates_must_succeed(self):
        plan = {name: False for name in module.PLAN_JOBS}
        plan.update(run_backend=True, run_production_contract=True, full_ci_required=True)
        results = {name: "skipped" for name in module.ALL_JOBS}
        results.update(
            changes="success", secrets="success", backend="success", agent="success",
            **{"production-contract": "success"},
        )
        self.assertEqual(module.failures(plan, results, image_required=False), [])
        results["backend"] = "skipped"
        self.assertIn("backend", module.failures(plan, results, image_required=False))
        results["secrets"] = "failure"
        self.assertIn("secrets", module.failures(plan, results, image_required=False))

    def test_main_image_publication_is_required_only_when_requested(self):
        plan = {name: False for name in module.PLAN_JOBS}
        results = {name: "skipped" for name in module.ALL_JOBS}
        results.update(changes="success", secrets="success")
        self.assertEqual(module.failures(plan, results, image_required=False), [])
        self.assertIn(
            "container-images", module.failures(plan, results, image_required=True)
        )

    def test_any_selected_failure_fails_the_stable_gate(self):
        plan = {name: False for name in module.PLAN_JOBS}
        plan["run_android"] = True
        results = {name: "skipped" for name in module.ALL_JOBS}
        results.update(changes="success", secrets="success", android="failure")
        self.assertIn("android", module.failures(plan, results, image_required=False))


if __name__ == "__main__":
    unittest.main()
