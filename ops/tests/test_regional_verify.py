from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "ops/verify-regional.sh"
IMAGE_TAG = "a" * 40


class RegionalVerifyTests(unittest.TestCase):
    def setUp(self) -> None:
        scratch = ROOT / ".codex-tmp"
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.bin = self.directory / "bin"
        self.bin.mkdir()
        self.env_file = self.directory / ".env"
        self.env_file.write_text("DOCKERHUB_USERNAME=example\n")
        self.compose_file = self.directory / "compose.yaml"
        self.compose_file.touch()
        self.command(
            "docker",
            "#!/bin/sh\n"
            'case "$*" in\n'
            "  *' ps -q frontend'*) printf 'frontend-container\\n' ;;\n"
            "  *State.Health.Status*) printf 'healthy\\n' ;;\n"
            "  *Config.Image*) printf '%s\\n' \"${FAKE_RUNNING_IMAGE:?}\" ;;\n"
            "esac\n",
        )
        self.command("curl", "#!/bin/sh\nexit 0\n")
        self.env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "REGION": "iran",
            "DEPLOY_KIND": "frontend",
            "IMAGE_TAG": IMAGE_TAG,
            "FRONTEND_IMAGE_TAG": IMAGE_TAG,
            "COMPOSE_FILE": str(self.compose_file),
            "COMPOSE_PROJECT_NAME": "fitician_iran",
            "FITICIAN_ENV_FILE": str(self.env_file),
            "FAKE_RUNNING_IMAGE": f"example/fitician-frontend:{IMAGE_TAG}",
        }

    def command(self, name: str, contents: str) -> None:
        path = self.bin / name
        path.write_text(contents)
        path.chmod(0o755)

    def run_verification(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["sh", str(SCRIPT)],
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_accepts_expected_full_sha_and_registry(self) -> None:
        result = self.run_verification()

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_other_registry_even_when_repository_and_sha_match(self) -> None:
        self.env["FAKE_RUNNING_IMAGE"] = f"untrusted/fitician-frontend:{IMAGE_TAG}"

        result = self.run_verification()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Immutable image mismatch", result.stderr)

    def test_rejects_same_repository_with_wrong_sha(self) -> None:
        self.env["FAKE_RUNNING_IMAGE"] = f"example/fitician-frontend:{'b' * 40}"

        result = self.run_verification()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Immutable image mismatch", result.stderr)

    def test_accepts_quoted_registry_owner_like_compose(self) -> None:
        self.env_file.write_text('DOCKERHUB_USERNAME="example"  \n')

        result = self.run_verification()

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
