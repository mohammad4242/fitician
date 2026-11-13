import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parents[2]


def module():
    spec = importlib.util.spec_from_file_location(
        "release_guard", ROOT / "ops/release-image-guard.py"
    )
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class ReleaseImageGuardTests(unittest.TestCase):
    def test_mutable_alias_must_match_the_manifest_image_id_and_commit(self):
        guard = module()
        image = {
            "reference": "mohammad4242/fitician-backend@sha256:" + "a" * 64,
            "image_id": "sha256:" + "b" * 64,
        }
        metadata = {
            "Id": image["image_id"],
            "Architecture": "amd64",
            "Os": "linux",
            "Config": {"Labels": {"org.opencontainers.image.revision": "c" * 40}},
        }
        with (
            patch.object(guard, "docker", return_value=json.dumps([metadata])),
            patch.object(
                guard, "config_digest_for_image", return_value=image["image_id"]
            ),
        ):
            guard.verify_alias("backend", image, "c" * 40)
        metadata["Config"]["Labels"]["org.opencontainers.image.revision"] = "d" * 40
        with (
            patch.object(guard, "docker", return_value=json.dumps([metadata])),
            patch.object(guard, "config_digest_for_image", return_value=image["image_id"]),
            self.assertRaisesRegex(ValueError, "release_image_identity_mismatch"),
        ):
            guard.verify_alias("backend", image, "c" * 40)

    def test_containerd_store_id_can_differ_from_the_canonical_config_identity(self):
        guard = module()
        image = {
            "reference": "mohammad4242/fitician-backend@sha256:" + "a" * 64,
            "image_id": "sha256:" + "b" * 64,
        }
        metadata = {
            "Id": "sha256:" + "a" * 64,
            "Architecture": "amd64",
            "Os": "linux",
            "Config": {"Labels": {"org.opencontainers.image.revision": "c" * 40}},
        }
        with (
            patch.object(guard, "docker", return_value=json.dumps([metadata])),
            patch.object(
                guard,
                "config_digest_for_image",
                return_value=image["image_id"],
                create=True,
            ),
        ):
            self.assertEqual(
                guard.verify_alias("backend", image, "c" * 40), metadata["Id"]
            )

    def test_running_container_is_checked_by_actual_image_id_not_its_tag(self):
        guard = module()
        calls = []

        def docker(*args):
            calls.append(args)
            return "a" * 64 if args[0] == "ps" else "sha256:" + "b" * 64

        with patch.object(guard, "docker", side_effect=docker):
            guard.verify_service("fitician-iran", "backend", "sha256:" + "b" * 64)
            with self.assertRaisesRegex(ValueError, "release_running_image_mismatch"):
                guard.verify_service("fitician-iran", "backend", "sha256:" + "c" * 64)
        self.assertTrue(any("{{.Image}}" in command for command in calls))
        self.assertFalse(any("{{.Config.Env}}" in command for command in calls))

    def test_target_mapping_preserves_unrelated_services(self):
        guard = module()
        self.assertEqual(
            guard.selected_services("germany", "agent"), {"agent-service": "agent"}
        )
        self.assertEqual(
            set(guard.selected_services("iran", "full")),
            {
                "backend",
                "backend-2",
                "food-photo-worker",
                "body-analysis-worker",
                "notification-worker",
                "scheduler",
                "frontend",
            },
        )
        with self.assertRaises(ValueError):
            guard.selected_services("germany", "full")


def release_manifest():
    commit = "c" * 40
    return {
        "version": 1,
        "repository": "mohammad4242/fitician",
        "commit": commit,
        "ci_run_id": 123,
        "run_attempt": 1,
        "images": {
            role: {
                "reference": f"mohammad4242/fitician-{role}@sha256:" + "a" * 64,
                "image_id": "sha256:" + "b" * 64,
            }
            for role in ("backend", "frontend", "agent")
        },
        "debug_runtime": {
            "artifact_name": "fitician-debug-runtime-" + commit,
            "archive_sha256": "d" * 64,
            "image_id": "sha256:" + "e" * 64,
            "cli_version": "0.167.2",
        },
        "web_source_maps": {
            "release": "fitician-web@" + commit,
            "private_layers_checked": True,
            "upload_state": "uploaded",
        },
    }


class OfflineReleaseTests(unittest.TestCase):
    def test_archive_hash_manifest_and_decompressed_size_are_verified_before_docker(
        self,
    ):
        import gzip
        import hashlib
        import tempfile

        spec = importlib.util.spec_from_file_location(
            "offline", ROOT / "ops/load-offline-release.py"
        )
        offline = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(offline)
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp") as folder:
            root = Path(folder)
            raw = json.dumps(release_manifest()).encode()
            (root / "manifest.json").write_bytes(raw)
            manifest_digest = hashlib.sha256(raw).hexdigest()
            archive = gzip.compress(b"isolated-image-archive-fixture")
            (root / "image.tar.gz").write_bytes(archive)
            (root / "image.tar.gz.sha256").write_text(
                hashlib.sha256(archive).hexdigest() + "  image.tar.gz\n"
            )
            self.assertEqual(
                offline.archive_size(root, manifest_digest, "c" * 40, 123),
                len(b"isolated-image-archive-fixture"),
            )
            with self.assertRaisesRegex(
                ValueError, "offline_release_manifest_mismatch"
            ):
                offline.archive_size(root, "0" * 64, "c" * 40, 123)
            (root / "image.tar.gz").write_bytes(archive + b"tamper")
            with patch.object(offline.subprocess, "Popen") as docker:
                with self.assertRaisesRegex(
                    ValueError, "offline_release_archive_mismatch"
                ):
                    offline.load(root, manifest_digest, "c" * 40, 123)
                docker.assert_not_called()

    def test_exact_ci_manifest_hash_is_enforced_after_download(self):
        import tempfile

        spec = importlib.util.spec_from_file_location(
            "gate_with_manifest", ROOT / "ops/ci-release-gate.py"
        )
        gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gate)
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp") as folder:
            root = Path(folder)
            (root / "manifest.json").write_text(json.dumps(release_manifest()))
            with (
                patch.object(gate.subprocess, "run") as download,
                patch.dict(gate.os.environ, {"EXPECTED_MANIFEST_SHA256": "0" * 64}),
            ):
                download.return_value.returncode = 0
                with self.assertRaisesRegex(ValueError, "no longer matches"):
                    gate.require_release_manifest(
                        "mohammad4242/fitician", 123, "c" * 40, root
                    )
                self.assertIn(
                    "fitician-release-manifest-" + "c" * 40, download.call_args.args[0]
                )
