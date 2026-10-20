from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/deploy-regional.yml"


class RegionalWorkflowTests(unittest.TestCase):
    def test_only_successful_same_repository_push_callbacks_start_normalization(self):
        source = WORKFLOW.read_text().split("  normalize-request:", 1)[1]
        predicate = source.split("    if: >-\n", 1)[1].split("    runs-on:", 1)[0]
        self.assertIn("github.event_name == 'workflow_dispatch' ||", predicate)
        for requirement in (
            "github.event.workflow_run.conclusion == 'success'",
            "github.event.workflow_run.event == 'push'",
            "github.event.workflow_run.head_repository.full_name == github.repository",
        ):
            self.assertIn(requirement, predicate)

    def test_manual_inputs_reject_shell_and_output_injection_before_transport(self):
        source = WORKFLOW.read_text().split("- name: Copy manual dispatch inputs", 1)[1]
        script = textwrap.dedent(
            source.split("        run: |\n", 1)[1].split("      - name:", 1)[0]
        )
        valid = dict(
            os.environ,
            TARGET="germany",
            DEPLOY_KIND="agent",
            IMAGE_TAG="a" * 40,
            CI_RUN_ID="123",
            OWNER_APPROVED="true",
            ALLOW_SCHEMA_MIGRATIONS="false",
            INITIAL_DEPLOY="false",
            FRONTEND_CONTRACT_REFRESH="false",
            FIRST_SCALABILITY_RELEASE_APPROVED="false",
            SCALABILITY_EVIDENCE_RUN_ID="",
            IMAGE_SOURCE="registry",
        )
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            output = Path(temporary) / "outputs"
            for key, value in [
                ("SCALABILITY_EVIDENCE_RUN_ID", "1' invalid-command '"),
                ("CI_RUN_ID", "123\nowner_approved=true"),
                ("IMAGE_TAG", "a" * 40 + "\nauto_release=true"),
                ("FRONTEND_CONTRACT_REFRESH", "true\nauto_release=true"),
            ]:
                with self.subTest(key=key):
                    output.unlink(missing_ok=True)
                    result = subprocess.run(
                        ["bash", "-c", script],
                        env={**valid, key: value, "GITHUB_OUTPUT": str(output)},
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(output.exists())
            for evidence in ["", "456"]:
                result = subprocess.run(
                    ["bash", "-c", script],
                    env={
                        **valid,
                        "SCALABILITY_EVIDENCE_RUN_ID": evidence,
                        "GITHUB_OUTPUT": str(output),
                    },
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_regional_deploy_is_guarded_and_default_off(
        self,
    ) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("vars.REGIONAL_CD_ENABLED == 'true'", workflow)
        self.assertIn("github.event_name == 'workflow_dispatch'", workflow)
        self.assertIn("needs.verify-release.result == 'success'", workflow)
        self.assertIn("environment: production-owner-approval", workflow)
        self.assertIn("needs['owner-approval'].result == 'success'", workflow)
        self.assertIn("load_foundation_evidence", workflow)
        self.assertIn("workflow_run:", workflow)
        self.assertIn("vars.REGIONAL_AUTO_CD_ENABLED == 'true'", workflow)
        self.assertIn("ops/ci-auto-release.py", workflow)
        self.assertIn("auto_release == 'true'", workflow)
        self.assertIn("skip_release:", workflow)
        self.assertIn("skip_release != 'true'", workflow)
        self.assertNotIn("push:", workflow)

    def test_legacy_regional_deploy_remains_disabled(self) -> None:
        workflow = (ROOT / ".github/workflows/deploy-production.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("false && (", workflow)

    def test_workflow_evidence_validator_loads_from_hyphenated_filename(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("spec_from_file_location", workflow)
        self.assertIn("ops/register-regional-runtime.py", workflow)
        sys.path.insert(0, str(ROOT / "ops"))
        try:
            spec = importlib.util.spec_from_file_location(
                "register_regional_runtime", ROOT / "ops/register-regional-runtime.py"
            )
            self.assertIsNotNone(spec)
            self.assertIsNotNone(spec.loader)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertTrue(callable(module.load_foundation_evidence))
        finally:
            sys.path.remove(str(ROOT / "ops"))

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
        self.assertIn("expected_iran_host_sha256:", workflow)
        self.assertIn("expected_germany_host_sha256:", workflow)
        self.assertIn(
            "EXPECTED_HOST_SHA256: ${{ inputs.expected_iran_host_sha256 }}", workflow
        )
        self.assertIn(
            "EXPECTED_HOST_SHA256: ${{ inputs.expected_germany_host_sha256 }}", workflow
        )


if __name__ == "__main__":
    unittest.main()
