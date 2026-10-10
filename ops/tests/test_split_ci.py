"""Split-network smoke must block full image publication, without slowing component releases."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class SplitCITests(unittest.TestCase):
    def test_full_release_images_require_complete_agent_suite(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        job = workflow.split("  container-images:", 1)[1]
        self.assertIn("needs.agent.result == 'success'", job)
        self.assertRegex(job, r"(?m)^      - agent$")
        agent = re.search(r"(?ms)^  agent:\n(.*?)(?=^  [\w-]+:|\Z)", workflow).group(1)
        self.assertIn("needs.changes.outputs.full_ci_required == 'true'", agent)
        self.assertIn("uv run pytest", agent)
        self.assertNotIn("-k ", agent)
        self.assertNotIn("continue-on-error", agent)

    def test_full_release_images_require_split_network_smoke(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertIn("  split-region-smoke:", workflow)
        job = workflow.split("  container-images:", 1)[1]
        self.assertIn("needs.split-region-smoke.result == 'success'", job)
        self.assertRegex(job, r"(?m)^      - split-region-smoke$")
        smoke = re.search(r"(?ms)^  split-region-smoke:\n(.*?)(?=^  [\w-]+:|\Z)", workflow).group(1)
        self.assertIn("needs.changes.outputs.full_ci_required == 'true'", smoke)
        self.assertIn("bash ops/split-test.sh", smoke)
        self.assertNotIn("secrets.", smoke)


if __name__ == "__main__":
    unittest.main()
