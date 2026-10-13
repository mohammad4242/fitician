from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "ops/diagnose-regional-ssh.sh"
PRIVATE_KEY = (
    "-----BEGIN OPENSSH PRIVATE KEY-----\r\n"
    "KEY-DATA-MUST-NOT-LEAK\r\n"
    "-----END OPENSSH PRIVATE KEY-----"
)
HOST_KEY = "HOST-KEY-MUST-NOT-LEAK"


class RegionalSSHDiagnosticTests(unittest.TestCase):
    def setUp(self) -> None:
        scratch = ROOT / ".codex-tmp"
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.bin = self.workspace / "bin"
        self.bin.mkdir()
        self.calls = self.workspace / "calls"
        self.calls.touch()
        self.remote_script = self.workspace / "remote-script"
        self.command(
            "ssh-keygen",
            "#!/bin/sh\n"
            'printf \'ssh-keygen %s\\n\' "$(stat -c %a "$4")" >> "$FAKE_CALLS"\n'
            '[ "${FAKE_HOSTKEY_PRESENT:-true}" = true ]\n',
        )
        self.command(
            "ssh-agent",
            "#!/bin/sh\n"
            "printf 'SSH_AUTH_SOCK=/tmp/fake-agent.sock; export SSH_AUTH_SOCK;\\n'\n"
            "printf 'SSH_AGENT_PID=12345; export SSH_AGENT_PID;\\n'\n",
        )
        self.command(
            "ssh-add",
            "#!/bin/sh\n"
            'printf \'ssh-add %s\\n\' "$(stat -c %a "$2")" >> "$FAKE_CALLS"\n'
            'if LC_ALL=C grep -q "$(printf \'\\r\')" "$2"; then printf \'ssh-add_crlf=yes\\n\' >> "$FAKE_CALLS"; fi\n'
            'if [ -z "${VPS_SSH_PRIVATE_KEY:-}" ] && [ -z "${VPS_KNOWN_HOSTS:-}" ]; then printf \'secret_env_cleared=yes\\n\' >> "$FAKE_CALLS"; fi\n'
            "[ \"${FAKE_SSH_ADD_STATUS:-0}\" = 0 ] || { echo 'private key parse detail'; exit 1; }\n",
        )
        self.command(
            "ssh",
            "#!/bin/sh\n"
            'printf \'%s\\n\' "$@" >> "$FAKE_CALLS"\n'
            'cat > "$FAKE_REMOTE_SCRIPT"\n'
            'if [ -n "${FAKE_SSH_ERROR:-}" ]; then echo "$FAKE_SSH_ERROR" >&2; exit 255; fi\n'
            'if [ -z "${VPS_SSH_PRIVATE_KEY:-}" ] && [ -z "${VPS_KNOWN_HOSTS:-}" ]; then printf \'secret_env_cleared=yes\\n\' >> "$FAKE_CALLS"; fi\n'
            'printf \'remote_uid=0\\napp_dir_readable=%s\\napp_dir_writable=%s\\ndocker_access=%s\\n\' "${FAKE_REMOTE_READABLE:-yes}" "${FAKE_REMOTE_WRITABLE:-yes}" "${FAKE_REMOTE_DOCKER:-available}"\n',
        )
        self.env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "GITHUB_WORKSPACE": str(self.workspace),
            "FAKE_CALLS": str(self.calls),
            "FAKE_REMOTE_SCRIPT": str(self.remote_script),
            "VPS_HOST": "vps.example.test",
            "VPS_USER": "fitician",
            "VPS_APP_DIR": "/opt/fitician-iran",
            "VPS_SSH_PORT": "9011",
            "VPS_SSH_PRIVATE_KEY": PRIVATE_KEY,
            "VPS_KNOWN_HOSTS": f"[vps.example.test]:9011 ssh-ed25519 {HOST_KEY}",
        }

    def command(self, name: str, contents: str) -> None:
        path = self.bin / name
        path.write_text(contents)
        path.chmod(0o755)

    def run_diagnostic(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPT)],
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_success_uses_pinned_batch_ssh_and_only_read_only_remote_checks(
        self,
    ) -> None:
        result = self.run_diagnostic()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ssh=connected", result.stdout)
        self.assertIn("app_dir_writable=yes", result.stdout)
        calls = self.calls.read_text()
        self.assertIn("ssh-keygen 600", calls)
        self.assertIn("ssh-add 600", calls)
        self.assertIn("ssh-add_crlf=yes", calls)
        self.assertEqual(calls.count("secret_env_cleared=yes"), 2)
        self.assertIn("-p\n9011\n", calls)
        self.assertIn("BatchMode=yes", calls)
        self.assertIn("StrictHostKeyChecking=yes", calls)
        self.assertIn("IdentitiesOnly=yes", calls)
        self.assertIn("IdentityAgent=/tmp/fake-agent.sock", calls)
        self.assertIn("UserKnownHostsFile=", calls)
        self.assertIn("GlobalKnownHostsFile=/dev/null", calls)
        self.assertIn("ConnectTimeout=8", calls)
        self.assertIn("ServerAliveCountMax=2", calls)
        remote = self.remote_script.read_text().lower()
        for forbidden in (
            "docker compose",
            "migrations",
            "dns",
            "up -d",
            "restart",
            "touch ",
            "mkdir ",
            "rm ",
        ):
            self.assertNotIn(forbidden, remote)
        self.assertNotIn(PRIVATE_KEY, result.stdout + result.stderr + calls)
        self.assertNotIn(HOST_KEY, result.stdout + result.stderr + calls)

    def test_missing_pinned_host_key_stops_before_ssh(self) -> None:
        self.env["FAKE_HOSTKEY_PRESENT"] = "false"

        result = self.run_diagnostic()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("class=host_key", result.stdout)
        self.assertNotIn("BatchMode", self.calls.read_text())
        self.assertNotIn(HOST_KEY, result.stdout + result.stderr)

    def test_ssh_failures_are_classified_without_raw_diagnostics(self) -> None:
        cases = (
            ("Connection timed out", "network"),
            ("Permission denied (publickey)", "authentication"),
            ("Host key verification failed", "host_key"),
            ("No RSA host key is known for the server", "host_key"),
        )
        for error, classification in cases:
            with self.subTest(classification=classification):
                self.calls.write_text("")
                self.env["FAKE_SSH_ERROR"] = error + " " + HOST_KEY

                result = self.run_diagnostic()

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"class={classification}", result.stdout)
                self.assertNotIn(error, result.stdout + result.stderr)
                self.assertNotIn(HOST_KEY, result.stdout + result.stderr)

    def test_invalid_key_is_classified_without_printing_key_material(self) -> None:
        self.env["FAKE_SSH_ADD_STATUS"] = "1"

        result = self.run_diagnostic()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("class=key", result.stdout)
        self.assertNotIn(PRIVATE_KEY, result.stdout + result.stderr)
        self.assertNotIn("private key parse detail", result.stdout + result.stderr)
        self.assertNotIn("BatchMode", self.calls.read_text())

    def test_missing_required_remote_capability_fails_after_sanitized_report(
        self,
    ) -> None:
        for env_name, value in (
            ("FAKE_REMOTE_READABLE", "no"),
            ("FAKE_REMOTE_WRITABLE", "no"),
            ("FAKE_REMOTE_DOCKER", "unavailable"),
        ):
            with self.subTest(capability=env_name):
                self.calls.write_text("")
                self.env[env_name] = value

                result = self.run_diagnostic()

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("ssh=connected", result.stdout)
                self.assertIn("class=remote_capabilities", result.stdout)
                self.assertNotIn(PRIVATE_KEY, result.stdout + result.stderr)

    def test_workflow_is_dispatch_only_read_only_and_environment_isolated(self) -> None:
        workflow = (ROOT / ".github/workflows/diagnose-regional-ssh.yml").read_text()

        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("push:", workflow)
        self.assertNotIn("workflow_run:", workflow)
        self.assertIn("production-iran", workflow)
        self.assertIn("production-germany", workflow)
        self.assertIn("ops/diagnose-regional-ssh.sh", workflow)
        self.assertIn("contents: read", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertIn("secrets.VPS_SSH_PRIVATE_KEY", workflow)


if __name__ == "__main__":
    unittest.main()
