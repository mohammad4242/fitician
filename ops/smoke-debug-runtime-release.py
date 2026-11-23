#!/usr/bin/env python3
"""Exercise the real release helper against an owned, network-isolated runtime fixture."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import tempfile
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def ownership_script(uid: int, gid: int, root: str = "/fixture") -> str:
    # Runtime-created links must never redirect privileged fixture cleanup outside its mount.
    return (
        "import os\n"
        "def failed(error):\n raise error\n"
        f"for path, directories, files in os.walk({root!r}, followlinks=False, onerror=failed):\n"
        f" os.chown(path, {uid}, {gid}, follow_symlinks=False)\n"
        " for name in directories + files:\n"
        f"  os.chown(os.path.join(path, name), {uid}, {gid}, follow_symlinks=False)\n"
    )


def broker_fixture_command(image: str, directory: Path) -> list[str]:
    return [
        "run",
        "--rm",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--user=10001:10001",
        "--mount",
        f"type=bind,src={directory},dst=/fixture",
        "--entrypoint=python",
        image,
        "-c",
        (
            "import os\n"
            "for name in ('worker.json','github.json'):\n"
            " fd=os.open('/fixture/'+name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)\n"
            " with os.fdopen(fd,'w') as output: output.write('{}')\n"
        ),
    ]


def run(directory: Path, commit: str, output: Path) -> dict:
    spec = importlib.util.spec_from_file_location(
        "runtime_release", ROOT / "ops/deploy-debug-runtime.py"
    )
    release = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release)
    original_project = release.PROJECT
    release.PROJECT = "fitician-runtime-release-test-" + str(uuid4())
    assert release.PROJECT.startswith("fitician-runtime-release-test-")
    proof = json.loads((directory / "smoke.json").read_text())
    assert proof["commit"] == commit and proof["cli_version"] == "0.167.2"
    image = "fitician-debug-runtime:" + commit
    image_id = proof["image_id"]
    assert release.config_digest_for_image(image) == image_id
    # CI fixture metadata only; no application images are deployed by this test.
    manifest = {
        "version": 1,
        "repository": "mohammad4242/fitician",
        "commit": commit,
        "ci_run_id": 1,
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
            "archive_sha256": hashlib.sha256(
                (directory / "image.tar.gz").read_bytes()
            ).hexdigest(),
            "image_id": image_id,
            "cli_version": "0.167.2",
        },
        "web_source_maps": {
            "release": "fitician-web@" + commit,
            "private_layers_checked": True,
            "upload_state": "disabled",
        },
    }
    others = release.non_runtime_identity()
    parent = ROOT / ".codex-tmp"
    parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="runtime-release-smoke-", dir=parent
    ) as name:
        root = Path(name)
        image_rows = []
        try:
            (root / "managed.json").write_text(
                json.dumps({"managed_by": release.PROJECT})
            )
            for child in (
                "state",
                "private",
                "automation-state",
                "automation-private",
                "current",
                "bundle",
                "incoming/ops",
            ):
                (root / child).mkdir(mode=0o700, parents=True, exist_ok=True)
            # The mount contains only this newly created test root, never the checkout or secrets.
            release.docker(
                "run",
                "--rm",
                "--network=none",
                "--read-only",
                "--cap-drop=ALL",
                "--cap-add=CHOWN",
                "--cap-add=DAC_OVERRIDE",
                "--user=0:0",
                "--mount",
                f"type=bind,src={root},dst=/fixture",
                "--entrypoint=python",
                image,
                "-c",
                "import os; from pathlib import Path; "
                "[os.chown('/fixture/'+name,10001,10001) for name in ('state','private','automation-state','automation-private')]",
            )
            compose = (
                (ROOT / "compose.debug-runtime.yaml")
                .read_text()
                .replace("driver: bridge", "driver: bridge\n    internal: true")
            )
            assert "internal: true" in compose
            (root / "incoming/compose.debug-runtime.yaml").write_text(compose)
            # Deploy uses this staged contract fixture, exactly as the SSH transfer path does.
            release.__file__ = str(root / "incoming/ops/deploy-debug-runtime.py")
            current = root / "current/compose.debug-runtime.yaml"
            current.write_text(compose)
            (current.parent / "runtime.env").write_text(
                f"FITICIAN_DEBUG_RUNTIME_IMAGE={image}\nFITICIAN_DEBUG_RUNTIME_ROOT={root}\n"
            )
            os.link(directory / "image.tar.gz", root / "bundle/image.tar.gz")
            raw = json.dumps(manifest).encode()
            (root / "bundle/manifest.json").write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            release.compose_up(current, ["connector"])
            release.verify_running(["connector"], image_id, commit)
            container = release.service_metadata("connector")["Id"]
            release.docker(
                "exec",
                container,
                "python",
                "-c",
                "from pathlib import Path; Path('/state/release-proof').write_text('retained')",
            )
            receipt = release.deploy(
                root,
                root / "bundle",
                digest,
                commit,
                1,
                root / "regional.lock",
                owner_approved=True,
            )
            assert receipt["state"] == "deployed"
            candidate = release.service_metadata("connector")["Id"]
            again = release.deploy(
                root,
                root / "bundle",
                digest,
                commit,
                1,
                root / "regional.lock",
                owner_approved=True,
            )
            assert (
                again == receipt
                and release.service_metadata("connector")["Id"] == candidate
            )
            failed = root / "failing"
            failed.mkdir()
            contract = failed / "compose.debug-runtime.yaml"
            contract.write_text(
                compose.replace(
                    "  connector:\n",
                    "  connector:\n    command: [unsupported-release-smoke-argument]\n",
                    1,
                )
            )
            (failed / "runtime.env").write_text(
                (current.parent / "runtime.env").read_text()
            )
            try:
                release.rollout(
                    contract,
                    Path(
                        json.loads((root / "active-release.json").read_text())[
                            "contract"
                        ]
                    ),
                    ["connector"],
                    image_id,
                    commit,
                    {"image_id": image_id, "commit": commit, "services": ["connector"]},
                )
            except ValueError as error:
                assert str(error) == "runtime_rollout_rolled_back", (
                    "Actual rollback was not verified"
                )
            else:
                raise ValueError("controlled_failure_did_not_fail")
            container = release.service_metadata("connector")["Id"]
            assert (
                release.docker(
                    "exec",
                    container,
                    "python",
                    "-c",
                    "from pathlib import Path; print(Path('/state/release-proof').read_text())",
                ).strip()
                == "retained"
            )
            assert release.non_runtime_identity() == others
            # Exercise Option A's broker-only component path using empty fixture
            # configuration, no real credentials, no outbound network or AI calls.
            release.docker(*broker_fixture_command(image, root / "automation-private"))
            protected = release.non_runtime_identity(["automation"])
            broker_receipt = release.deploy(
                root,
                root / "bundle",
                digest,
                commit,
                1,
                root / "regional.lock",
                owner_approved=True,
                automation_only=True,
            )
            assert broker_receipt["state"] == "deployed"
            broker_id = release.service_metadata("automation")["Id"]
            again_broker = release.deploy(
                root,
                root / "bundle",
                digest,
                commit,
                1,
                root / "regional.lock",
                owner_approved=True,
                automation_only=True,
            )
            assert again_broker == broker_receipt
            assert release.service_metadata("automation")["Id"] == broker_id
            assert release.non_runtime_identity(["automation"]) == protected
            broker_contract = Path(
                json.loads((root / "active-automation-release.json").read_text())[
                    "contract"
                ]
            )
            broker_failure = root / "failing-broker"
            broker_failure.mkdir()
            broken_broker = broker_failure / "compose.debug-runtime.yaml"
            broken_broker.write_text(
                compose.replace(
                    "command: [serve]",
                    "command: [unsupported-release-smoke-argument]",
                    1,
                )
            )
            (broker_failure / "runtime.env").write_text(
                (broker_contract.parent / "runtime.env").read_text()
            )
            try:
                release.rollout(
                    broken_broker,
                    broker_contract,
                    ["automation"],
                    image_id,
                    commit,
                    {
                        "image_id": image_id,
                        "commit": commit,
                        "services": ["automation"],
                    },
                )
            except ValueError as error:
                assert str(error) == "runtime_rollout_rolled_back"
            else:
                raise ValueError("controlled_broker_failure_did_not_fail")
            assert release.non_runtime_identity(["automation"]) == protected
            assert release.service_metadata("connector")["Id"] == container
            result = {
                "commit": commit,
                "image_id": image_id,
                "cli_version": "0.167.2",
                "exact_image_rollout": True,
                "idempotent_replay": True,
                "actual_rollback": True,
                "persistent_state_retained": True,
                "unrelated_services_unchanged": True,
                "broker_only_rollout": True,
                "broker_only_idempotent": True,
                "broker_only_rollback": True,
                "legacy_connector_unchanged": True,
                "broker_enrollment_verified": False,
                "production_deployment": False,
            }
        finally:
            # Remove only resources whose generated project identity is owned by this invocation.
            image_rows = release.docker(
                "ps",
                "-a",
                "--filter",
                f"label=com.docker.compose.project={release.PROJECT}",
                "-q",
            ).split()
            if image_rows:
                release.docker("rm", "-f", *image_rows)
            networks = release.docker(
                "network",
                "ls",
                "--filter",
                f"label=com.docker.compose.project={release.PROJECT}",
                "-q",
            ).split()
            if networks:
                release.docker("network", "rm", *networks)
            # Restore operator ownership for cleanup of this credential-free fixture alone.
            release.docker(
                "run",
                "--rm",
                "--network=none",
                "--read-only",
                "--user=0:0",
                "--cap-drop=ALL",
                "--cap-add=CHOWN",
                "--cap-add=DAC_OVERRIDE",
                "--mount",
                f"type=bind,src={root},dst=/fixture",
                "--entrypoint=python",
                image,
                "-c",
                ownership_script(os.getuid(), os.getgid()),
            )
            release.PROJECT = original_project
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, sort_keys=True))
    print(json.dumps(result))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.directory.resolve(), args.commit, args.output)


if __name__ == "__main__":
    main()
