from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/deploy-regional.yml"


class RegionalWorkflowTests(unittest.TestCase):
    def test_regional_deploy_is_manual_guarded_and_uses_isolated_environments(
        self,
    ) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("github.event_name == 'workflow_dispatch'", workflow)
        self.assertIn("needs.verify-release.result == 'success'", workflow)
        self.assertIn("inputs.owner_approved", workflow)
        self.assertIn(
            "environment: ${{ inputs.target == 'iran' && 'production-iran' || 'production-germany' }}",
            workflow,
        )
        self.assertNotIn("workflow_run:", workflow)
        self.assertNotIn("push:", workflow)

    def test_ssh_port_defaults_to_9011_for_all_transfer_and_remote_commands(
        self,
    ) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("VPS_SSH_PORT: ${{ vars.VPS_SSH_PORT || '9011' }}", workflow)
        self.assertIn('ssh -p "$VPS_SSH_PORT"', workflow)
        self.assertIn('scp -P "$VPS_SSH_PORT"', workflow)
        self.assertIn('test "$VPS_SSH_PORT" -le 65535', workflow)


if __name__ == "__main__":
    unittest.main()
