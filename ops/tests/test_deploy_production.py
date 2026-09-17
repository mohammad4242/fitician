from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "ops/deploy-production.sh"
OLD_TAG = "a" * 40
NEW_TAG = "b" * 40


class DeployProductionTests(unittest.TestCase):
    def setUp(self) -> None:
        (ROOT / ".codex-tmp").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp")
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.bin = self.workspace / "bin"
        self.bin.mkdir()
        (self.workspace / "compose.prod.yaml").touch()
        (self.workspace / ".env").write_text(f"IMAGE_TAG={OLD_TAG}\nOTHER_VALUE=keep\n")
        (self.workspace / ".deployed-image-tag").write_text(f"{OLD_TAG}\n")
        self._command(
            "docker",
            """#!/bin/sh
printf '%s\\n' "$*" >> "$FAKE_STATE_DIR/calls"
case "$*" in
  *' up '*)
    if [ "${FAKE_UP_FAIL_NEW:-}" = true ] && [ "$IMAGE_TAG" = "${FAKE_NEW_TAG}" ]; then
      exit 3
    fi
    ;;
  *' exec '*'db '*'SELECT count(*) FROM users'*) printf '1\\n' ;;
  *' run '*'alembic heads'*) printf '%s (head)\\n' "${FAKE_SCHEMA_HEAD:-20260915_155}" ;;
  *' exec '*'db '* ) printf '20260915_155\\n' ;;
  *' exec '*'caddy '* ) printf 'example.com' ;;
esac
""",
        )
        self._command("curl", "#!/bin/sh\nexit 0\n")
        (self.workspace / "backup-production.sh").write_text(
            '#!/bin/sh\nprintf "backup\\n" >> "$FAKE_STATE_DIR/calls"\n'
        )
        self.env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "COMPOSE_FILE": str(self.workspace / "compose.prod.yaml"),
            "IMAGE_TAG": NEW_TAG,
            "FAKE_STATE_DIR": str(self.workspace),
            "FAKE_NEW_TAG": NEW_TAG,
        }

    def _command(self, name: str, body: str) -> None:
        path = self.bin / name
        path.write_text(body)
        path.chmod(0o755)

    def _run(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["sh", str(SCRIPT)], env=self.env, capture_output=True, text=True)

    def test_backup_precedes_rollout_and_success_persists_its_tag(self) -> None:
        result = self._run()

        self.assertEqual(result.returncode, 0, result.stderr)
        calls = (self.workspace / "calls").read_text().splitlines()
        self.assertLess(calls.index("backup"), next(i for i, call in enumerate(calls) if " up " in call))
        self.assertEqual((self.workspace / ".deployed-image-tag").read_text(), NEW_TAG + "\n")
        self.assertIn("OTHER_VALUE=keep", (self.workspace / ".env").read_text())
        self.assertIn("IMAGE_TAG=" + NEW_TAG, (self.workspace / ".env").read_text())
        self.assertTrue(any(" exec -T backend python -c " in call for call in calls))

    def test_pending_schema_change_blocks_automatic_rollout_after_backup(self) -> None:
        self.env["FAKE_SCHEMA_HEAD"] = "20260918_156"
        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.workspace / ".deployed-image-tag").read_text(), OLD_TAG + "\n")
        self.assertNotIn(" up ", (self.workspace / "calls").read_text())

    def test_failed_rollout_restores_previous_image_without_changing_release_marker(self) -> None:
        self.env["FAKE_UP_FAIL_NEW"] = "true"

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.workspace / ".deployed-image-tag").read_text(), OLD_TAG + "\n")
        self.assertIn("IMAGE_TAG=" + OLD_TAG, (self.workspace / ".env").read_text())
        calls = (self.workspace / "calls").read_text().splitlines()
        self.assertEqual(sum(" up " in call for call in calls), 2)

    def test_initial_deploy_waits_for_database_health_before_checking_users(self) -> None:
        (self.workspace / ".deployed-image-tag").unlink()
        self.env["INITIAL_DEPLOY"] = "true"

        result = self._run()

        self.assertEqual(result.returncode, 0, result.stderr)
        calls = (self.workspace / "calls").read_text().splitlines()
        database_start = next(i for i, call in enumerate(calls) if " up " in call)
        restored_users_check = next(
            i for i, call in enumerate(calls) if "SELECT count(*) FROM users" in call
        )
        self.assertIn("up -d --wait db", calls[database_start])
        self.assertLess(database_start, restored_users_check)


if __name__ == "__main__":
    unittest.main()
