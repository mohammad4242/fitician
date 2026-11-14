#!/usr/bin/env python3
"""Run fixed profiles in an ephemeral sandbox; never mount host credentials or Docker."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.debugging.ci_contract import validate_report, validation_spec

POSTGRES = "postgres:18-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15"


def extract_source(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as stream:
        size = 0
        for item in stream:
            path = Path(item.name)
            size += item.size
            if (
                path.is_absolute()
                or ".." in path.parts
                or ".git" in path.parts
                or not (item.isdir() or item.isfile())
                or size > 536870912
            ):
                raise ValueError("unsafe_candidate_archive")
            if any(p.startswith(".env") for p in path.parts):
                continue
            target = destination / path
            if item.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                source = stream.extractfile(item)
                assert source is not None
                with target.open("xb") as output:
                    shutil.copyfileobj(source, output)
                target.chmod(0o644)


def container_command(
    name: str,
    image: str,
    source: Path,
    profile: str,
    tests: list[str],
    *,
    network: str = "none",
) -> list[str]:
    validation_spec(profile, tests)
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", image):
        raise ValueError("immutable_validation_image_required")
    if not re.fullmatch(r"fitician-validation-[a-f0-9-]{36}", name):
        raise ValueError("isolated_validation_name_required")
    if network != "none" and network != name:
        raise ValueError("isolated_validation_network_required")
    args = [
        "docker",
        "run",
        "--name",
        name,
        "--pull=never",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--pids-limit=128",
        "--memory=2g",
        "--memory-swap=2g",
        "--cpus=2",
        "--user=10001:10001",
        "--network=" + network,
        "--tmpfs=/workspace:uid=10001,gid=10001,mode=0700,size=768m",
        "--tmpfs=/scratch:uid=10001,gid=10001,mode=0700,size=3g",
        "--mount",
        f"type=bind,src={source},dst=/source,readonly",
        "--tmpfs=/output:uid=10001,gid=10001,mode=0700,size=8m",
        "--env=APP_ENV=test",
        "--env=HOME=/scratch",
        "--env=PYTHONDONTWRITEBYTECODE=1",
        "--env=SENTRY_DSN=",
        "--env=SENTRY_TRACES_SAMPLE_RATE=0",
    ]
    if network != "none":
        url = "postgresql+psycopg://fitician:fitician_ci@db:5432/fitician_test"
        args += [
            "--env=DATABASE_URL=" + url,
            "--env=TEST_DATABASE_URL=" + url,
            "--env=NUTRITION_AUDIT_DATABASE_URL="
            + url.removesuffix("fitician_test") + "fitician_nutrition_audit",
        ]
    return [*args, image, profile, json.dumps(tests)]


def command(*args: str, timeout: int = 60) -> str:
    result = subprocess.run(
        args, capture_output=True, text=True, timeout=timeout, check=False
    )
    if result.returncode:
        raise ValueError("validation_infrastructure_command_failed")
    return result.stdout.strip()


def run(
    candidate: Path,
    image: str,
    profile: str,
    tests: list[str],
    output: Path,
    policy_sha: str,
) -> dict:
    spec = validation_spec(profile, tests)
    metadata = json.loads(command("docker", "image", "inspect", image))[0]
    if (
        metadata["Id"] != image
        or metadata["Config"].get("Labels", {}).get("io.fitician.validation-policy")
        != policy_sha
        or not re.fullmatch(r"[a-f0-9]{40}", policy_sha)
    ):
        raise ValueError("validation_policy_image_mismatch")
    commit = command("git", "-C", str(candidate), "rev-parse", "HEAD")
    if not re.fullmatch(r"[a-f0-9]{40}", commit) or command(
        "git", "-C", str(candidate), "status", "--porcelain", "--untracked-files=no"
    ):
        raise ValueError("clean_exact_candidate_required")
    name = "fitician-validation-" + str(uuid4())
    output.parent.mkdir(parents=True, exist_ok=True)
    network = name if spec["network"] == "isolated_postgres" else "none"
    database = name + "-db"
    result = {
        "candidate_commit": commit,
        "policy_commit": policy_sha,
        "profile": profile,
        "tests": tests,
        "image": image,
        "passed": False,
    }
    with tempfile.TemporaryDirectory(
        prefix=".debug-validation-", dir=output.parent
    ) as temporary:
        root = Path(temporary)
        # Only these synthetic sources/results cross the container boundary.
        root.chmod(0o755)
        source, archive = root / "source", root / "source.tar"
        with archive.open("wb") as stream:
            subprocess.run(
                ["git", "-C", str(candidate), "archive", "HEAD"],
                stdout=stream,
                stderr=subprocess.DEVNULL,
                timeout=30,
                check=True,
            )
        extract_source(archive, source)
        archive.unlink()
        try:
            if network != "none":
                command("docker", "network", "create", "--internal", network)
                command(
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    database,
                    "--network",
                    network,
                    "--network-alias=db",
                    "--memory=384m",
                    "--cpus=0.5",
                    "--pids-limit=96",
                    "--env=POSTGRES_USER=fitician",
                    "--env=POSTGRES_PASSWORD=fitician_ci",
                    "--env=POSTGRES_DB=fitician_test",
                    "--tmpfs=/var/lib/postgresql:size=384m",
                    POSTGRES,
                )
                for _ in range(60):
                    ready = subprocess.run(
                        ["docker", "exec", database, "pg_isready", "-U", "fitician"],
                        capture_output=True,
                        check=False,
                        timeout=5,
                    )
                    if ready.returncode == 0:
                        break
                    time.sleep(0.5)
                else:
                    raise ValueError("isolated_postgres_not_ready")
            with (root / "run.log").open("wb") as log:
                process = subprocess.Popen(
                    container_command(
                        name, image, source, profile, tests, network=network
                    ),
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
                deadline = time.monotonic() + spec["timeout_seconds"]
                try:
                    while process.poll() is None:
                        if (
                            time.monotonic() > deadline
                            or os.fstat(log.fileno()).st_size > 1048576
                        ):
                            raise ValueError("validation_time_or_output_limit")
                        time.sleep(0.2)
                    result["exit_code"] = process.returncode
                finally:
                    if process.poll() is None:
                        subprocess.run(
                            ["docker", "rm", "-f", name],
                            capture_output=True,
                            check=False,
                            timeout=15,
                        )
                        process.terminate()
                        process.wait(timeout=10)
            try:
                report = validate_report(
                    json.loads((root / "run.log").read_text().splitlines()[-1])
                )
            except (ValueError, IndexError):
                report = {"exercised": 0, "skipped": 0, "failures": 1}
            result.update(report)
            result["passed"] = (
                result["exit_code"] == 0
                and result["exercised"] > 0
                and result["failures"] == 0
            )
            # Do not publish raw test logs, which are untrusted content.
        finally:
            for container in (name, database):
                subprocess.run(
                    ["docker", "rm", "-f", container],
                    capture_output=True,
                    check=False,
                    timeout=15,
                )
            if network != "none":
                subprocess.run(
                    ["docker", "network", "rm", network],
                    capture_output=True,
                    check=False,
                    timeout=15,
                )
    output.write_text(json.dumps(result, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--image", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--tests-json", required=True)
    parser.add_argument("--policy-sha", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = run(
            args.candidate.resolve(),
            args.image,
            args.profile,
            json.loads(args.tests_json),
            args.output.resolve(),
            args.policy_sha,
        )
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        # Fixed operation code only, no model-produced output or host credentials.
        print(json.dumps({"state": "failed", "error_type": type(error).__name__}))
        raise SystemExit(1) from None
    print(json.dumps(result))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
