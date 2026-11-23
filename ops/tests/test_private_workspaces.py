import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class PrivateWorkspaceTests(unittest.TestCase):
    def test_fresh_clone_ignores_private_state_without_operator_git_exclusions(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp") as name:
            repository = Path(name)
            subprocess.run(
                ["git", "init", "-q", str(repository)], check=True, capture_output=True
            )
            (repository / ".gitignore").write_bytes((ROOT / ".gitignore").read_bytes())
            for path in (
                ".codex-tmp/laptop-connector.json",
                ".codex-tmp/release/backup-evidence.json",
                ".codex-tmp/sentry-setup/automation-tokens.json",
            ):
                with self.subTest(path=path):
                    result = subprocess.run(
                        [
                            "git",
                            "-c",
                            "core.excludesFile=/dev/null",
                            "check-ignore",
                            "--no-index",
                            "-q",
                            path,
                        ],
                        cwd=repository,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0)
            result = subprocess.run(
                [
                    "git",
                    "-c",
                    "core.excludesFile=/dev/null",
                    "check-ignore",
                    "--no-index",
                    "-q",
                    "backend/app/main.py",
                ],
                cwd=repository,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
