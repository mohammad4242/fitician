import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]


class RegionalBackupTests(unittest.TestCase):
    def test_uses_the_running_database_contract_and_existing_region_env(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp") as folder:
            root = Path(folder)
            contract = root / "releases" / ("a" * 40) / "compose.prod.iran.yaml"
            contract.parent.mkdir(parents=True)
            contract.touch()
            (root / ".env").touch()
            (root / "ops").mkdir()
            (root / "bin").mkdir()
            docker = root / "bin/docker"
            docker.write_text(
                '#!/bin/sh\nif [ "$1" = ps ]; then printf "%s\\n" aaaaaaaaaaaa; else printf "%s\\n" "$FAKE_CONTRACT"; fi\n'
            )
            docker.chmod(0o755)
            helper = root / "ops/backup-production.sh"
            helper.write_text(
                '#!/bin/sh\npython3 -c \'import json,os; print(json.dumps({k:os.environ[k] for k in ["COMPOSE_FILE","FITICIAN_ENV_FILE","COMPOSE_PROJECT_NAME","DB_BACKUP_LOCK_FILE"]}))\'\n'
            )
            environment = dict(
                os.environ,
                APP_DIR=str(root),
                FAKE_CONTRACT=str(contract),
                PATH=str(root / "bin") + ":" + os.environ["PATH"],
            )
            first = subprocess.run(
                ["bash", str(ROOT / "ops/backup-regional.sh")],
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            actual = json.loads(first.stdout)
            self.assertEqual(actual["COMPOSE_FILE"], str(contract))
            self.assertEqual(actual["FITICIAN_ENV_FILE"], str(root / ".env"))
            self.assertEqual(actual["COMPOSE_PROJECT_NAME"], "fitician-iran")
            self.assertEqual(
                actual["DB_BACKUP_LOCK_FILE"], str(root / ".database-backup.lock")
            )
            environment["FAKE_CONTRACT"] = "/etc/passwd"
            refused = subprocess.run(
                ["bash", str(ROOT / "ops/backup-regional.sh")],
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertNotIn("COMPOSE_FILE", refused.stdout)
