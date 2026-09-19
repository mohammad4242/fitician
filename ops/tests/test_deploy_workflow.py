from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = ROOT / ".github/workflows/ci.yml"
DEPLOY_WORKFLOW = ROOT / ".github/workflows/deploy-production.yml"


class DeployWorkflowTests(unittest.TestCase):
    def test_main_ci_triggers_cd_but_first_scalability_release_requires_evidence(self) -> None:
        workflow = DEPLOY_WORKFLOW.read_text()

        self.assertIn("github.event.workflow_run.conclusion == 'success'", workflow)
        self.assertIn("github.event.workflow_run.event == 'push'", workflow)
        self.assertIn("github.event.workflow_run.head_branch == 'main'", workflow)
        self.assertIn("first_scalability_release_approved", workflow)
        self.assertIn("heavy_evidence_run_id", workflow)
        self.assertIn("Verify first scalability acceptance evidence", workflow)
        self.assertIn("Check automatic first scalability gate", workflow)
        self.assertIn(".scalability-foundation-accepted", workflow)
        self.assertIn("automatic_deploy_gate", workflow)
        self.assertIn("actions: read", workflow)

    def test_google_client_id_is_masked_before_validation_and_build(self) -> None:
        workflow = CI_WORKFLOW.read_text()
        mask_step = workflow.index("- name: Mask Google web client ID")
        validation_step = workflow.index("- name: Require Google web client ID")
        frontend_build_step = workflow.index("- name: Build frontend image for verification")

        self.assertIn('echo "::add-mask::$GOOGLE_CLIENT_ID"', workflow)
        self.assertLess(mask_step, validation_step)
        self.assertLess(mask_step, frontend_build_step)

    def test_deployment_copies_complete_production_verifier(self) -> None:
        workflow = DEPLOY_WORKFLOW.read_text()

        self.assertIn("ops/verify-production.sh", workflow)
        self.assertIn("ops/check-db-connection-budget.py", workflow)
        self.assertIn("ops/check-runtime-capacity.py", workflow)
        self.assertIn(".compose.prod.rollback.yaml", workflow)
        self.assertIn("ROLLBACK_COMPOSE_FILE=", workflow)


if __name__ == "__main__":
    unittest.main()
