import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from ops.tests.test_debug_runtime_release import bundle

ROOT = Path(__file__).resolve().parents[2]


def builder():
    spec = importlib.util.spec_from_file_location(
        "runtime_manifest", ROOT / "ops/runtime-release-manifest.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def evidence(directory):
    value, _ = bundle(directory)
    identity = {
        "commit": value["commit"],
        "image_id": value["debug_runtime"]["image_id"],
        "cli_version": "0.167.2",
    }
    smoke = {
        **identity,
        "isolated": True,
        "liveness": True,
        "persistent_state_after_restart": True,
        "automation": {
            "isolated": True,
            "liveness": True,
            "graceful_shutdown": True,
            "persistent_state_after_restart": True,
        },
    }
    rollout = {
        **identity,
        "exact_image_rollout": True,
        "idempotent_replay": True,
        "actual_rollback": True,
        "persistent_state_retained": True,
        "unrelated_services_unchanged": True,
        "production_deployment": False,
    }
    for name, payload in [("smoke.json", smoke), ("release-smoke.json", rollout)]:
        (directory / name).write_text(json.dumps(payload))
    (directory / "image.tar.gz.sha256").write_text(
        value["debug_runtime"]["archive_sha256"]
    )
    return value


class IndependentManifestTests(unittest.TestCase):
    def test_prepares_only_the_exact_runtime_from_recorded_smoke_and_rollout(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp") as name:
            path = Path(name)
            expected = evidence(path)
            observed = builder().build_manifest(path, "c" * 40, 42, 1)
            self.assertEqual(observed["kind"], "debug-runtime")
            self.assertEqual(observed["debug_runtime"], expected["debug_runtime"])
            self.assertNotIn("images", observed)
            self.assertNotIn("web_source_maps", observed)

    def test_refuses_missing_evidence_and_symlinked_metadata(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp") as name:
            path = Path(name)
            evidence(path)
            (path / "smoke.json").unlink()
            with self.assertRaises(ValueError):
                builder().build_manifest(path, "c" * 40, 42, 1)
            (path / "smoke.json").symlink_to(path / "release-smoke.json")
            with self.assertRaises(ValueError):
                builder().build_manifest(path, "c" * 40, 42, 1)

    def test_refuses_incomplete_rollback_or_wrong_commit(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp") as name:
            path = Path(name)
            evidence(path)
            with self.assertRaises(ValueError):
                builder().build_manifest(path, "d" * 40, 42, 1)
            file = path / "release-smoke.json"
            value = json.loads(file.read_text())
            value["actual_rollback"] = False
            file.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                builder().build_manifest(path, "c" * 40, 42, 1)

    def test_refuses_archive_changes_and_fabricated_matching_image_proofs(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp") as name:
            path = Path(name)
            evidence(path)
            for name in ["smoke.json", "release-smoke.json"]:
                file = path / name
                value = json.loads(file.read_text())
                value["image_id"] = "sha256:" + "f" * 64
                file.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                builder().build_manifest(path, "c" * 40, 42, 1)
            with (path / "image.tar.gz").open("ab") as output:
                output.write(b"changed")
            with self.assertRaises(ValueError):
                builder().build_manifest(path, "c" * 40, 42, 1)
