from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/deploy-regional.yml"


class RegionalWorkflowTests(unittest.TestCase):
    def test_regional_deploy_job_remains_disabled_in_source(
        self,
    ) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("      false && (", workflow)
        self.assertIn("needs.verify-release.result == 'success'", workflow)
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

    def test_future_regional_ssh_requires_pinned_host_key_and_hardened_client_config(
        self,
    ) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        pin_step = workflow.split("- name: Pin regional VPS host key", 1)[1].split(
            "- name: Prepare immutable candidate contract directory", 1
        )[0]

        self.assertIn('ssh-keygen -F "[$VPS_HOST]:$VPS_SSH_PORT"', pin_step)
        self.assertIn('chmod 700 "$HOME/.ssh"', pin_step)
        self.assertIn('chmod 600 "$HOME/.ssh/known_hosts"', pin_step)
        self.assertIn('chmod 600 "$HOME/.ssh/config"', pin_step)
        for setting in (
            "Host *",
            "BatchMode yes",
            "StrictHostKeyChecking yes",
            "GlobalKnownHostsFile /dev/null",
            "ConnectionAttempts 1",
            "ConnectTimeout 10",
        ):
            self.assertIn(setting, pin_step)

    def test_ssh_diagnostic_workflow_is_manual_and_uses_isolated_environments(
        self,
    ) -> None:
        workflow = (ROOT / ".github/workflows/diagnose-regional-ssh.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("production-iran", workflow)
        self.assertIn("production-germany", workflow)
        self.assertIn("workflow_dispatch", workflow)
        self.assertNotIn("workflow_run:", workflow)
        self.assertNotIn("push:", workflow)
        self.assertIn("contents: read", workflow)


if __name__ == "__main__":
    unittest.main()
