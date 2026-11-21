import gzip
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ops.tests.test_release_image_guard import release_manifest

ROOT = Path(__file__).resolve().parents[2]


def module():
    spec = importlib.util.spec_from_file_location(
        "runtime_release", ROOT / "ops/deploy-debug-runtime.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def bundle(folder):
    config = json.dumps(
        {
            "architecture": "amd64",
            "os": "linux",
            "config": {"Labels": {"org.opencontainers.image.revision": "c" * 40}},
            "rootfs": {},
        }
    ).encode()
    image_id = "sha256:" + hashlib.sha256(config).hexdigest()
    archive = folder / "image.tar.gz"
    with (
        gzip.open(archive, "wb") as output,
        tarfile.open(fileobj=output, mode="w|") as tar,
    ):
        for name, content in [
            (image_id[7:] + ".json", config),
            (
                "manifest.json",
                json.dumps([{"Config": image_id[7:] + ".json", "Layers": []}]).encode(),
            ),
        ]:
            item = tarfile.TarInfo(name)
            item.size = len(content)
            tar.addfile(item, io.BytesIO(content))
    manifest = release_manifest()
    manifest["ci_run_id"] = 42
    manifest["debug_runtime"].update(
        image_id=image_id,
        archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
    )
    file = folder / "manifest.json"
    file.write_text(json.dumps(manifest))
    return manifest, hashlib.sha256(file.read_bytes()).hexdigest()


class RuntimeReleaseTests(unittest.TestCase):
    def test_fixture_cleanup_does_not_follow_runtime_symlinks_outside_the_fixture(self):
        spec = importlib.util.spec_from_file_location(
            "runtime_smoke", ROOT / "ops/smoke-debug-runtime-release.py"
        )
        smoke = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(smoke)
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp") as name:
            parent = Path(name)
            fixture = parent / "fixture"
            fixture.mkdir()
            outside = parent / "outside"
            outside.write_text("must remain untouched")
            link = fixture / "runtime-link"
            link.symlink_to(outside)
            before = outside.stat().st_ctime_ns
            subprocess.run(
                [
                    sys.executable,
                    "-c",
                    smoke.ownership_script(
                        os.getuid(),
                        os.getgid(),
                        str(fixture),
                    ),
                ],
                check=True,
                capture_output=True,
            )
            self.assertEqual(outside.stat().st_ctime_ns, before)
            self.assertTrue(link.is_symlink())

    def test_ci_runs_actual_runtime_rollout_and_rollback_before_export_is_publishable(
        self,
    ):
        ci = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertTrue(
            "ops/smoke-debug-runtime-release.py" in ci,
            "Actual rollout/rollback smoke is missing",
        )
        self.assertLess(
            ci.index("Export the exact tested runtime"),
            ci.index("ops/smoke-debug-runtime-release.py"),
        )
        self.assertTrue((ROOT / "ops/smoke-debug-runtime-release.py").is_file())
        publisher = (ROOT / "ops/release-manifest.py").read_text()
        self.assertTrue(
            '"release-smoke.json"' in publisher, "Runtime rollout proof is not required"
        )

    def test_capacity_uses_all_bounded_services_and_preserves_memory_headroom(self):
        release = module()
        others = [
            {"HostConfig": {"Memory": memory * 1024**2, "NanoCpus": int(cpu * 1e9)}}
            for memory, cpu in [(448, 0.4), (96, 0.25), (96, 0.2)]
        ]
        result = release.capacity_budget(
            1967 * 1024**2, 1392 * 1024**2, 1, others, True
        )
        self.assertEqual(result["planned_memory_mib"], 1344)
        for total, available, cpus, services in [
            (1500 * 1024**2, 1392 * 1024**2, 1, others),
            (1967 * 1024**2, 512 * 1024**2, 1, others),
            (
                1967 * 1024**2,
                1392 * 1024**2,
                1,
                others
                + [{"HostConfig": {"Memory": 64 * 1024**2, "NanoCpus": 900000000}}],
            ),
            (
                1967 * 1024**2,
                1392 * 1024**2,
                1,
                [{"HostConfig": {"Memory": 0, "NanoCpus": 0}}],
            ),
        ]:
            with self.assertRaises(ValueError):
                release.capacity_budget(total, available, cpus, services, True)

    def test_decompressed_archive_limit_applies_even_after_valid_image_metadata(self):
        release = module()
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp") as name:
            folder = Path(name)
            _, digest = bundle(folder)
            release.MAX_UNPACKED = 1024
            with self.assertRaisesRegex(ValueError, "runtime_archive_size_limit"):
                release.verify_bundle(folder, digest, "c" * 40, 42)

    def test_failed_remote_capacity_gate_stops_before_staging_or_scp(self):
        text = (ROOT / ".github/workflows/deploy-regional.yml").read_text()
        section = text.split(
            "      - name: Stage verified runtime without touching application services\n"
        )[1]
        body = section.split("        run: |\n", 1)[1].split("      - name:", 1)[0]
        script = "\n".join(line[10:] for line in body.splitlines())
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp") as name:
            folder = Path(name)
            binary = folder / "bin"
            binary.mkdir()
            for executable, content in {
                "ssh": '#!/bin/bash\nfor argument; do remote="$argument"; done\nexec /bin/bash -c "$remote"\n',
                "python3": "#!/bin/bash\nexit 7\n",
                "scp": '#!/bin/bash\ntouch "$STAGING_SENTINEL"\n',
            }.items():
                path = binary / executable
                path.write_text(content)
                path.chmod(0o700)
            archive = folder / ".ci-evidence/runtime-bundle/image.tar.gz"
            archive.parent.mkdir(parents=True)
            archive.write_bytes(b"fixture")
            destination = folder / "runtime"
            destination.mkdir()
            sentinel = folder / "unexpected-copy"
            result = subprocess.run(
                ["/bin/bash", "-c", script],
                cwd=folder,
                capture_output=True,
                check=False,
                env={
                    **os.environ,
                    "PATH": str(binary) + ":/usr/bin:/bin",
                    "DEBUG_RUNTIME_ROOT": str(destination),
                    "IMAGE_TAG": "c" * 40,
                    "VPS_SSH_PORT": "9011",
                    "VPS_USER": "test",
                    "VPS_HOST": "test.invalid",
                    "STAGING_SENTINEL": str(sentinel),
                },
            )
            self.assertNotEqual(result.returncode, 0, "Remote failure was ignored")
            self.assertFalse(sentinel.exists())
            self.assertFalse((destination / "incoming").exists())

    def test_verified_bundle_binds_compressed_archive_and_canonical_image_identity(
        self,
    ):
        release = module()
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp") as name:
            folder = Path(name)
            manifest, digest = bundle(folder)
            self.assertEqual(
                release.verify_bundle(folder, digest, "c" * 40, 42)["debug_runtime"],
                manifest["debug_runtime"],
            )
            (folder / "image.tar.gz").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "runtime_archive_mismatch"):
                release.verify_bundle(folder, digest, "c" * 40, 42)

    def test_manifest_hash_and_ci_identity_are_checked_before_loading(self):
        release = module()
        with tempfile.TemporaryDirectory(dir=ROOT / ".codex-tmp") as name:
            folder = Path(name)
            _, digest = bundle(folder)
            for commit, run, hash_value in [
                ("d" * 40, 42, digest),
                ("c" * 40, 43, digest),
                ("c" * 40, 42, "f" * 64),
            ]:
                with self.assertRaises(ValueError):
                    release.verify_bundle(folder, hash_value, commit, run)

    def test_no_authorization_cannot_touch_docker_or_runtime(self):
        release = module()
        with patch.object(release, "docker") as docker:
            with self.assertRaisesRegex(ValueError, "runtime_owner_approval_required"):
                release.deploy(
                    Path("/missing"),
                    Path("/missing"),
                    "f" * 64,
                    "c" * 40,
                    42,
                    Path("/missing/lock"),
                    owner_approved=False,
                )
            docker.assert_not_called()

    def test_rollout_only_updates_selected_service_and_restores_old_contract_on_failure(
        self,
    ):
        release = module()
        calls = []

        def execute(contract, services):
            calls.append((contract, services))

        with (
            patch.object(release, "compose_up", side_effect=execute),
            patch.object(
                release,
                "verify_running",
                side_effect=[ValueError("runtime_readiness_failed"), {"healthy": True}],
            ),
            self.assertRaisesRegex(ValueError, "runtime_rollout_rolled_back"),
        ):
            release.rollout(
                Path("candidate"),
                Path("previous"),
                ["connector"],
                "sha256:" + "a" * 64,
                "c" * 40,
                {"image_id": "sha256:" + "b" * 64, "commit": "d" * 40},
            )
        self.assertEqual(
            calls,
            [(Path("candidate"), ["connector"]), (Path("previous"), ["connector"])],
        )

    def test_rollback_failure_is_uncertain_and_never_removes_state(self):
        release = module()
        with (
            patch.object(release, "compose_up") as up,
            patch.object(
                release, "verify_running", side_effect=ValueError("unavailable")
            ),
            self.assertRaisesRegex(ValueError, "runtime_rollback_unconfirmed"),
        ):
            release.rollout(
                Path("candidate"),
                Path("previous"),
                ["connector"],
                "sha256:" + "a" * 64,
                "c" * 40,
                {"image_id": "sha256:" + "b" * 64, "commit": "d" * 40},
            )
        self.assertEqual(up.call_count, 2)

    def test_existing_workflow_retains_owner_gate_and_germany_concurrency_for_runtime(
        self,
    ):
        workflow = (ROOT / ".github/workflows/deploy-regional.yml").read_text()
        self.assertTrue(
            "debug_runtime" in workflow, "Missing controlled runtime release"
        )
        job = workflow.split("\n  deploy-debug-runtime:\n", 1)[1]
        self.assertIn("production-germany", job)
        self.assertIn("needs['owner-approval'].result == 'success'", job)
        self.assertIn("group: fitician-production-germany", job)
        self.assertIn("cancel-in-progress: false", job)
        self.assertIn("github.ref == 'refs/heads/main'", job)
        self.assertIn("fitician-debug-runtime-", job)
        self.assertIn("ops/deploy-debug-runtime.py", job)
        self.assertNotIn("docker compose down", job)
