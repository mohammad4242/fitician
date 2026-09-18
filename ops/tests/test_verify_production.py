from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "ops/verify-production.sh"
TAG = "b" * 40


class VerifyProductionTests(unittest.TestCase):
    def setUp(self) -> None:
        (ROOT / ".codex-tmp").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp")
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.bin = self.workspace / "bin"
        self.bin.mkdir()
        (self.workspace / "compose.prod.yaml").touch()
        ops = self.workspace / "ops"
        ops.mkdir()
        for name in ("check-db-connection-budget.py", "check-runtime-capacity.py"):
            script = ops / name
            script.write_text("#!/usr/bin/env python3\nraise SystemExit(0)\n")
            script.chmod(0o755)
        self._command(
            "docker",
            """#!/bin/sh
case "$*" in
  *' ps -q '*) for argument do service=$argument; done; printf 'container-%s\n' "$service" ;;
  *State.Health.Status*) printf '%s\n' "${FAKE_HEALTH:-healthy}" ;;
  *Config.Image*) printf 'registry/fitician:%s\n' "$IMAGE_TAG" ;;
  *' exec -T db '*'SELECT version_num'*) printf '20260918_158\n' ;;
  *' run --rm --no-deps migrations alembic heads'*) printf '20260918_158 (head)\n' ;;
  *' exec -T caddy '*) printf 'example.com' ;;
esac
exit 0
""",
        )
        self._command("curl", "#!/bin/sh\nexit 0\n")
        self.env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "COMPOSE_FILE": str(self.workspace / "compose.prod.yaml"),
            "IMAGE_TAG": TAG,
        }

    def _command(self, name: str, body: str) -> None:
        path = self.bin / name
        path.write_text(body)
        path.chmod(0o755)

    def _run(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["sh", str(SCRIPT)], env=self.env, capture_output=True, text=True)

    def test_complete_topology_verification_succeeds(self) -> None:
        result = self._run()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Production topology verified", result.stdout)

    def test_unhealthy_worker_fails_deployment_verification(self) -> None:
        self.env["FAKE_HEALTH"] = "unhealthy"

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Required service is unhealthy", result.stderr)


if __name__ == "__main__":
    unittest.main()
