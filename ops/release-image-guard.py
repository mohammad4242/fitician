#!/usr/bin/env python3
"""Pin local image aliases to the reviewed release and verify actual running image IDs."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
try:
    from app.debugging.release_contract import validate_release
except ModuleNotFoundError:
    # The release workflow ships this exact source beside the standalone helper.
    from release_contract import validate_release


def docker(*args: str) -> str:
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=False, timeout=180
    )
    if result.returncode:
        raise ValueError("release_image_operation_failed")
    return result.stdout.strip()


def selected_services(target: str, kind: str) -> dict[str, str]:
    if target == "germany" and kind == "agent":
        return {"agent-service": "agent"}
    if target == "iran" and kind == "full":
        return {
            **{
                name: "backend"
                for name in (
                    "backend",
                    "backend-2",
                    "food-photo-worker",
                    "body-analysis-worker",
                    "notification-worker",
                    "scheduler",
                )
            },
            "frontend": "frontend",
        }
    raise ValueError("release_image_target_not_authorized")


def verify_alias(role: str, image: dict, commit: str) -> None:
    alias = "mohammad4242/fitician-" + role + ":" + commit
    metadata = json.loads(docker("image", "inspect", alias))[0]
    if (
        metadata.get("Id") != image["image_id"]
        or metadata.get("Config", {})
        .get("Labels", {})
        .get("org.opencontainers.image.revision")
        != commit
        or metadata.get("Architecture") != "amd64"
        or metadata.get("Os") != "linux"
    ):
        raise ValueError("release_image_identity_mismatch")


def verify_service(project: str, service: str, image_id: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", project):
        raise ValueError("release_project_invalid")
    identifiers = docker(
        "ps",
        "--filter",
        "label=com.docker.compose.project=" + project,
        "--filter",
        "label=com.docker.compose.service=" + service,
        "--format",
        "{{.ID}}",
    ).splitlines()
    if len(identifiers) != 1 or not re.fullmatch(r"[a-f0-9]{12,64}", identifiers[0]):
        raise ValueError("release_running_service_missing_or_ambiguous")
    if docker("inspect", "--format", "{{.Image}}", identifiers[0]) != image_id:
        raise ValueError("release_running_image_mismatch")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--ci-run-id", type=int, required=True)
    parser.add_argument("--target", choices=("iran", "germany"), required=True)
    parser.add_argument("--kind", choices=("full", "agent"), required=True)
    parser.add_argument(
        "--mode",
        choices=("prepare-registry", "verify-local", "verify-running"),
        required=True,
    )
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    if args.manifest.stat().st_size > 16384:
        raise ValueError("release_manifest_invalid")
    manifest = validate_release(
        json.loads(args.manifest.read_text()),
        commit=args.commit,
        ci_run_id=args.ci_run_id,
    )
    services = selected_services(args.target, args.kind)
    for role in sorted(set(services.values())):
        image = manifest["images"][role]
        if args.mode == "prepare-registry":
            docker("pull", image["reference"])
            observed = json.loads(docker("image", "inspect", image["reference"]))[0]
            if observed.get("Id") != image["image_id"]:
                raise ValueError("release_image_identity_mismatch")
            docker(
                "tag",
                image["reference"],
                "mohammad4242/fitician-" + role + ":" + args.commit,
            )
        verify_alias(role, image, args.commit)
    if args.mode == "verify-running":
        for service, role in services.items():
            verify_service(args.project, service, manifest["images"][role]["image_id"])
    print("Release image identity verified: " + args.mode)


if __name__ == "__main__":
    main()
