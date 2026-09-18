from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "ops/check-db-connection-budget.py"


class DbConnectionBudgetTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_default_two_replica_budget_is_below_limit(self) -> None:
        result = self._run("--replicas", "2")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertLess(payload["possible_connections"], payload["budget"])

    def test_budget_fails_before_an_unsafe_scale_up(self) -> None:
        result = self._run("--replicas", "3")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("connection budget exceeded", result.stderr)


if __name__ == "__main__":
    unittest.main()
