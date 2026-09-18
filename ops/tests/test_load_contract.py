from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class LoadContractTests(unittest.TestCase):
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
        self.assertNotIn("down -v", script)
        self.assertNotIn("docker volume rm", script)


if __name__ == "__main__":
    unittest.main()
