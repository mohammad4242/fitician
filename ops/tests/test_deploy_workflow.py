from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DEPLOY_WORKFLOW = ROOT / ".github/workflows/deploy-production.yml"


class DeployWorkflowTests(unittest.TestCase):
    def test_successful_main_push_ci_always_triggers_deploy(self) -> None:
        workflow = DEPLOY_WORKFLOW.read_text()

        self.assertIn("github.event.workflow_run.conclusion == 'success'", workflow)
        self.assertIn("github.event.workflow_run.event == 'push'", workflow)
        self.assertIn("github.event.workflow_run.head_branch == 'main'", workflow)
        self.assertNotIn("PRODUCTION_DEPLOY_ENABLED", workflow)

    def test_google_client_id_is_masked_before_validation_and_build(self) -> None:
        workflow = CI_WORKFLOW.read_text()
        mask_step = workflow.index("- name: Mask Google web client ID")
        validation_step = workflow.index("- name: Require Google web client ID")
        frontend_build_step = workflow.index("- name: Build frontend image for verification")

        self.assertIn('echo "::add-mask::$GOOGLE_CLIENT_ID"', workflow)
        self.assertLess(mask_step, validation_step)
        self.assertLess(mask_step, frontend_build_step)


if __name__ == "__main__":
    unittest.main()
