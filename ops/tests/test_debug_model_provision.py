import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def helper():
    spec = importlib.util.spec_from_file_location(
        "provision_debug_model", ROOT / "ops/provision-debug-model.py"
    )
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class ProvisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "runtime.env").write_text("synthetic marker")
        (self.root / "private").mkdir(mode=0o700)

    def test_atomic_private_creation_does_not_export_to_environment_or_overwrite(self):
        m = helper()
        before = dict(os.environ)
        key = "sk-or-v1-" + "a" * 64
        m.provision(self.root, key, owner=(os.getuid(), os.getgid()))
        path = self.root / "private/model-api.json"
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        value = json.loads(path.read_text())
        self.assertEqual(value["FITICIAN_DEBUG_OPENROUTER_API_KEY"], key)
        self.assertEqual(value["purpose"], "fitician_debug_agent")
        self.assertEqual(dict(os.environ), before)
        with self.assertRaisesRegex(ValueError, "credential_already_exists"):
            m.provision(self.root, key, owner=(os.getuid(), os.getgid()))

    def test_other_service_tokens_and_wrong_target_are_rejected_before_storage(self):
        m = helper()
        for key in ["github_pat_" + "a" * 64, "a" * 64, "sk-or-v1-short"]:
            with self.assertRaises(ValueError):
                m.provision(self.root, key, owner=(os.getuid(), os.getgid()))
        self.assertFalse((self.root / "private/model-api.json").exists())
        (self.root / "runtime.env").unlink()
        with self.assertRaisesRegex(ValueError, "dedicated_germany_runtime_required"):
            m.provision(
                self.root, "sk-or-v1-" + "a" * 64, owner=(os.getuid(), os.getgid())
            )
