from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "ops/backup-production.sh"


class BackupProductionTests(unittest.TestCase):
    def setUp(self) -> None:
        (ROOT / ".codex-tmp").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp")
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.bin = self.workspace / "bin"
        self.bin.mkdir()
        self.compose = self.workspace / "compose.prod.yaml"
        self.compose.touch()
        self._command("docker", '#!/bin/sh\nprintf "PGDUMP"\n')
        self._command("age", '#!/bin/sh\nprintf "AGE:"\ncat\n')
        self._command(
            "aws",
            """#!/bin/sh
if [ "$3" = "s3" ] && [ "$4" = "cp" ]; then
  cp "$5" "$FAKE_STATE_DIR/uploaded.age"
elif [ "$3" = "s3api" ] && [ "$4" = "head-object" ]; then
  wc -c < "$FAKE_STATE_DIR/uploaded.age"
else
  exit 2
fi
""",
        )
        self.env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "COMPOSE_FILE": str(self.compose),
            "DB_BACKUP_BUCKET": "backup-only",
            "DB_BACKUP_AGE_RECIPIENT": "age1example",
            "S3_ENDPOINT": "https://s3.example.test",
            "AWS_ACCESS_KEY_ID": "test",
            "AWS_SECRET_ACCESS_KEY": "test",
            "AWS_DEFAULT_REGION": "test",
            "FAKE_STATE_DIR": str(self.workspace),
        }

    def _command(self, name: str, body: str) -> None:
        path = self.bin / name
        path.write_text(body)
        path.chmod(0o755)

    def _run(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["bash", str(SCRIPT)], env=self.env, capture_output=True, text=True)

    def test_uploads_only_encrypted_bytes_and_removes_temporary_file(self) -> None:
        result = self._run()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.workspace / "uploaded.age").read_bytes(), b"AGE:PGDUMP")
        self.assertEqual(list(self.workspace.glob(".db-backup.*.age")), [])

    def test_failed_encryption_never_uploads(self) -> None:
        self._command("age", "#!/bin/sh\nexit 9\n")

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.workspace / "uploaded.age").exists())
        self.assertEqual(list(self.workspace.glob(".db-backup.*.age")), [])


if __name__ == "__main__":
    unittest.main()
