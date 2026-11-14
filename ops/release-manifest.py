#!/usr/bin/env python3
"""Record exact published image identities and the already tested runtime archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.debugging.image_identity import config_digest_for_image
from app.debugging.release_contract import validate_release


def docker(*args: str) -> str:
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=False, timeout=180
    )
    if result.returncode:
        raise ValueError("release_image_readback_failed")
    return result.stdout.strip()


def image_identity(role: str, digest: str, commit: str) -> dict[str, str]:
    if role not in {"backend", "frontend", "agent"} or not re.fullmatch(
        r"sha256:[a-f0-9]{64}", digest
    ):
        raise ValueError("release_image_digest_required")
    reference = "mohammad4242/fitician-" + role + "@" + digest
    docker("pull", reference)
    metadata = json.loads(docker("image", "inspect", reference))[0]
    if (
        reference not in metadata.get("RepoDigests", [])
        or metadata.get("Architecture") != "amd64"
        or metadata.get("Os") != "linux"
        or metadata.get("Config", {})
        .get("Labels", {})
        .get("org.opencontainers.image.revision")
        != commit
    ):
        raise ValueError("release_image_readback_mismatch")
    return {"reference": reference, "image_id": config_digest_for_image(reference)}


def runtime_identity(root: Path, commit: str) -> dict:
    proof = json.loads((root / "smoke.json").read_text())
    if (
        proof.get("commit") != commit
        or proof.get("cli_version") != "0.167.2"
        or not all(
            proof.get(k) is True
            for k in ("isolated", "liveness", "persistent_state_after_restart")
        )
        or not all(
            proof.get("automation", {}).get(k) is True
            for k in (
                "isolated",
                "liveness",
                "graceful_shutdown",
                "persistent_state_after_restart",
            )
        )
    ):
        raise ValueError("release_runtime_smoke_required")
    expected = (root / "image.tar.gz.sha256").read_text().split()[0]
    digest = hashlib.sha256()
    with (root / "image.tar.gz").open("rb") as stream:
        size = 0
        while chunk := stream.read(1048576):
            size += len(chunk)
            if size > 536870912:
                raise ValueError("release_runtime_archive_too_large")
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise ValueError("release_runtime_archive_mismatch")
    return {
        "artifact_name": "fitician-debug-runtime-" + commit,
        "archive_sha256": expected,
        "image_id": proof["image_id"],
        "cli_version": "0.167.2",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    commit, run_id = os.environ["GITHUB_SHA"], int(os.environ["GITHUB_RUN_ID"])
    frontend_repository = "mohammad4242/fitician-frontend"
    digests = json.loads(
        docker(
            "image",
            "inspect",
            frontend_repository + ":" + commit,
            "--format",
            "{{json .RepoDigests}}",
        )
    )
    choices = {
        v.removeprefix(frontend_repository + "@")
        for v in digests
        if v.startswith(frontend_repository + "@")
    }
    if len(choices) != 1:
        raise ValueError("release_frontend_digest_required")
    value = {
        "version": 1,
        "repository": "mohammad4242/fitician",
        "commit": commit,
        "ci_run_id": run_id,
        "run_attempt": int(os.environ["GITHUB_RUN_ATTEMPT"]),
        "images": {
            "backend": image_identity("backend", os.environ["BACKEND_DIGEST"], commit),
            "frontend": image_identity("frontend", choices.pop(), commit),
            "agent": image_identity("agent", os.environ["AGENT_DIGEST"], commit),
        },
        "debug_runtime": runtime_identity(args.runtime_directory, commit),
        "web_source_maps": {
            "release": "fitician-web@" + commit,
            "private_layers_checked": True,
            "upload_state": "uploaded"
            if os.environ.get("WEB_SENTRY_ENABLED") == "true"
            else "disabled",
        },
    }
    validate_release(value, commit=commit, ci_run_id=run_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    print("Exact published image references and tested runtime archive recorded")


if __name__ == "__main__":
    main()
