#!/usr/bin/env python3
"""Pin local image aliases to the reviewed release and verify actual running image IDs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
try:
    from app.debugging.image_identity import config_digest_for_image
    from app.debugging.release_contract import validate_release
except ModuleNotFoundError:
    # The release workflow ships this exact source beside the standalone helper.
    from image_identity import config_digest_for_image
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


def verify_alias(role: str, image: dict, commit: str) -> str:
    alias = "mohammad4242/fitician-" + role + ":" + commit
    metadata = json.loads(docker("image", "inspect", alias))[0]
    if (
        config_digest_for_image(alias) != image["image_id"]
        or metadata.get("Config", {}).get("Labels", {}).get("org.opencontainers.image.revision")
        != commit
        or metadata.get("Architecture") != "amd64"
        or metadata.get("Os") != "linux"
    ):
        raise ValueError("release_image_identity_mismatch")
    identifier = metadata.get("Id")
    if not isinstance(identifier, str) or not re.fullmatch(r"sha256:[a-f0-9]{64}", identifier):
        raise ValueError("release_image_identity_mismatch")
    return identifier


def verify_service(project: str, service: str, image_id: str) -> str:
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
    return identifiers[0]


def running_proof(
    manifest: dict,
    target: str,
    kind: str,
    operation_id: str,
    observed: dict[str, str],
    manifest_sha256: str,
) -> dict:
    services = selected_services(target, kind)
    if (
        str(UUID(operation_id)) != operation_id
        or set(observed) != set(services)
        or not re.fullmatch("[a-f0-9]{64}", manifest_sha256)
        or any(not re.fullmatch("[a-f0-9]{12,64}", identifier) for identifier in observed.values())
    ):
        raise ValueError("release_readback_invalid")
    return {
        "schema_version": 1,
        "operation_id": operation_id,
        "target_environment": "production-" + target,
        "commit": manifest["commit"],
        "manifest_sha256": manifest_sha256,
        "ci_run_id": manifest["ci_run_id"],
        "captured_at": datetime.now(UTC).isoformat(),
        "images": {role: manifest["images"][role] for role in set(services.values())},
        "services": {
            name: {"container_id": observed[name], "image_role": role, "healthy": True}
            for name, role in services.items()
        },
        "provenance": "fixed_running_image_guard",
        "business_outcome_verified": False,
    }


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
    parser.add_argument("--operation-id")
    parser.add_argument("--evidence-output", type=Path)
    args = parser.parse_args()
    if args.manifest.stat().st_size > 16384:
        raise ValueError("release_manifest_invalid")
    manifest = validate_release(
        json.loads(args.manifest.read_text()),
        commit=args.commit,
        ci_run_id=args.ci_run_id,
    )
    services = selected_services(args.target, args.kind)
    local_identifiers = {}
    for role in sorted(set(services.values())):
        image = manifest["images"][role]
        if args.mode == "prepare-registry":
            docker("pull", image["reference"])
            if config_digest_for_image(image["reference"]) != image["image_id"]:
                raise ValueError("release_image_identity_mismatch")
            docker(
                "tag",
                image["reference"],
                "mohammad4242/fitician-" + role + ":" + args.commit,
            )
        local_identifiers[role] = verify_alias(role, image, args.commit)
    if args.mode == "verify-running":
        observed = {}
        for service, role in services.items():
            identifier = verify_service(args.project, service, local_identifiers[role])
            if args.evidence_output:
                health = docker(
                    "inspect",
                    "--format",
                    '{{if index .State "Health"}}{{.State.Health.Status}}{{else}}missing{{end}}',
                    identifier,
                )
                if health != "healthy":
                    raise ValueError("release_readback_unhealthy")
                observed[service] = identifier
        if args.evidence_output:
            proof = running_proof(
                manifest,
                args.target,
                args.kind,
                args.operation_id,
                observed,
                hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
            )
            fd = os.open(
                args.evidence_output, os.O_CREAT | os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW, 0o600
            )
            with os.fdopen(fd, "w") as output:
                os.fchmod(output.fileno(), 0o600)
                output.write(json.dumps(proof, sort_keys=True) + "\n")
    elif args.evidence_output or args.operation_id:
        raise ValueError("release_readback_requires_running_mode")
    print("Release image identity verified: " + args.mode)


if __name__ == "__main__":
    main()
