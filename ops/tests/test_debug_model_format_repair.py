import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
KEY = "sk-or-v1-" + "a" * 64


def helper():
    spec = importlib.util.spec_from_file_location(
        "repair_model_format", ROOT / "ops/repair-debug-model-format.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FormatRepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "private").mkdir(mode=0o700)
        (self.root / "current").mkdir()
        (self.root / "current/runtime.env").write_text("fixture marker")
        self.path = self.root / "private/model-api.json"
        self.path.write_text(KEY + "\n")
        self.path.chmod(0o600)
        self.owner = (os.getuid(), os.getgid())

    def test_review_never_changes_or_exports_the_existing_key(self):
        m = helper()
        before = self.path.read_bytes()
        review = m.review(self.root, owner=self.owner)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertNotIn(KEY, json.dumps(review))
        self.assertEqual(list((self.root / "private").iterdir()), [self.path])

    def test_explicit_repair_preserves_original_bytes_and_key_in_same_secure_store(self):
        m = helper()
        review = m.review(self.root, owner=self.owner)
        before = self.path.read_bytes()
        result = m.apply_repair(self.root, review, owner=self.owner)
        value = json.loads(self.path.read_text())
        self.assertEqual(value["FITICIAN_DEBUG_OPENROUTER_API_KEY"], KEY)
        self.assertEqual(value["purpose"], "fitician_debug_agent")
        self.assertEqual(value["provider"], "openrouter")
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        backup = self.root / "private" / result["backup"]
        self.assertEqual(backup.read_bytes(), before)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertNotIn(KEY, json.dumps(result))
        with self.assertRaises(ValueError):
            m.apply_repair(self.root, review, owner=self.owner)
        self.assertEqual(backup.read_bytes(), before)

    def test_rotation_after_review_is_rejected_without_replacing_operator_changes(self):
        m = helper()
        review = m.review(self.root, owner=self.owner)
        other = "sk-or-v1-" + "b" * 64
        self.path.write_text(other)
        with self.assertRaisesRegex(ValueError, "credential_changed_after_review"):
            m.apply_repair(self.root, review, owner=self.owner)
        self.assertEqual(self.path.read_text(), other)
        self.assertEqual(list((self.root / "private").iterdir()), [self.path])

    def test_wrong_format_symlink_and_insecure_permissions_fail_closed(self):
        m = helper()
        for content in [
            json.dumps({"token": "test-not-this-service"}),
            "github_pat_" + "a" * 64,
            KEY + "\nextra",
        ]:
            self.path.write_text(content)
            with self.assertRaises(ValueError):
                m.review(self.root, owner=self.owner)
        self.path.write_text(KEY)
        self.path.chmod(0o644)
        with self.assertRaises(ValueError):
            m.review(self.root, owner=self.owner)
        self.path.unlink()
        self.path.symlink_to(self.root / "current/runtime.env")
        with self.assertRaises(ValueError):
            m.review(self.root, owner=self.owner)

    def test_change_during_repair_retains_new_value_and_original_backup(self):
        m = helper()
        plan = m.review(self.root, owner=self.owner)
        rotated = "sk-or-v1-" + "c" * 64
        original_write = m.write_private

        def write(path, raw, owner):
            original_write(path, raw, owner)
            if path.name.startswith(".model-api.normalized-"):
                self.path.write_text(rotated)

        with patch.object(m, "write_private", side_effect=write):
            with self.assertRaisesRegex(ValueError, "credential_changed_after_review"):
                m.apply_repair(self.root, plan, owner=self.owner)
        self.assertEqual(self.path.read_text(), rotated)
        backups = list((self.root / "private").glob(".model-api.pre-format-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), KEY + "\n")
        self.assertEqual(list((self.root / "private").glob(".model-api.normalized-*")), [])

    def test_cli_never_echoes_unknown_secret_arguments_or_applies_without_approval(self):
        m = helper()
        before = self.path.read_bytes()
        for args in [["repair", "--apply"], ["repair", KEY]]:
            output = io.StringIO()
            with patch("sys.argv", args), contextlib.redirect_stdout(output):
                self.assertEqual(m.main(), 2)
            self.assertNotIn(KEY, output.getvalue())
            self.assertEqual(self.path.read_bytes(), before)
