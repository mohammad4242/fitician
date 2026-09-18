from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class LoadContractTests(unittest.TestCase):
    def test_heavy_load_workflow_is_manual_or_scheduled_and_local_only(self) -> None:
        workflow = (ROOT / ".github/workflows/load-test.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("schedule:", workflow)
        self.assertIn("compose.multi.yaml", workflow)
        self.assertIn("failure-drills.sh all", workflow)
        self.assertIn("upload-artifact", workflow)
        self.assertNotIn("compose.prod.yaml", workflow)
        self.assertNotIn("FITICIAN_ALLOW_PRODUCTION_LOAD", workflow)

    def test_load_runner_is_local_only_and_provider_neutral(self) -> None:
        runner = (ROOT / "ops/load/run.sh").read_text()
        smoke = (ROOT / "ops/load/http_smoke.py").read_text()

        self.assertIn("FITICIAN_ALLOW_PRODUCTION_LOAD", runner)
        self.assertIn("127.0.0.1", runner)
        self.assertIn("p95", smoke)
        self.assertNotIn("openrouter", runner.lower())
        self.assertNotIn("sms", runner.lower())
        self.assertNotIn("smtp", runner.lower())

    def test_failure_drill_refuses_production_and_never_removes_volumes(self) -> None:
        script = (ROOT / "ops/load/failure-drills.sh").read_text()
        self.assertIn("FITICIAN_ALLOW_PRODUCTION_FAILURE_DRILL", script)
        self.assertIn("deadline", script.lower())
        self.assertIn("expire-body-lease", script)
        self.assertIn("result_version_count", script)
        self.assertIn(
            'BODY_ANALYSIS_LOCAL_FAKE_PROVIDER_ENABLED: "true"',
            (ROOT / "compose.multi.yaml").read_text(),
        )
        self.assertIn("seed-catalogue-member", script)
        self.assertIn("/api/v1/nutrition/foods", script)
        self.assertIn("/api/v1/products", script)
        self.assertIn("fitician_queue_oldest_job_age_seconds", script)
        self.assertIn("/readyz\" 503", script)
        self.assertIn("redis_has_key 'fitician:cache:v1:*'", script)
        self.assertIn("redis_has_key 'fitician:rate:v1:auth:*'", script)
        self.assertIn("wait_for_two_instances", script)
        self.assertIn("SIGKILL body-analysis-worker", script)
        self.assertIn("docker update --restart=no", script)
        self.assertIn("wait_for_body_reclaim", script)
        self.assertNotIn("down -v", script)
        self.assertNotIn("docker volume rm", script)
        self.assertNotIn("openrouter", script.lower())


if __name__ == "__main__":
    unittest.main()
