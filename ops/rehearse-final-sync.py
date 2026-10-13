#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".codex-tmp/regional-completion"
AGE = shutil.which("age") or str(ROOT / "artifacts/regional-cutover/tools/age")
AGE_KEYGEN = shutil.which("age-keygen") or str(
    ROOT / "artifacts/regional-cutover/tools/age-keygen"
)
IMAGE = (
    "postgres:18-alpine@sha256:"
    "9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15"
)
RUN_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,30}$")
PASSWORD = "synthetic-only-password"
SNAPSHOT_SCRIPT = ROOT / "ops/final-database-snapshot.py"
SNAPSHOT_SPEC = importlib.util.spec_from_file_location(
    "final_database_snapshot", SNAPSHOT_SCRIPT
)
assert SNAPSHOT_SPEC and SNAPSHOT_SPEC.loader
FINAL_SNAPSHOT = importlib.util.module_from_spec(SNAPSHOT_SPEC)
SNAPSHOT_SPEC.loader.exec_module(FINAL_SNAPSHOT)
CUTOVER_SCRIPT = ROOT / "ops/regional-cutover.py"
CUTOVER_SPEC = importlib.util.spec_from_file_location(
    "regional_cutover", CUTOVER_SCRIPT
)
assert CUTOVER_SPEC and CUTOVER_SPEC.loader
REGIONAL_CUTOVER = importlib.util.module_from_spec(CUTOVER_SPEC)
CUTOVER_SPEC.loader.exec_module(REGIONAL_CUTOVER)


def resource_names(run_id: str) -> tuple[str, str, str, str]:
    if not RUN_ID.fullmatch(run_id):
        raise ValueError(
            "run ID must be lowercase letters, numbers, or hyphens (31 chars max)"
        )
    prefix = f"fitician-final-sync-{run_id}"
    return (
        f"{prefix}-source",
        f"{prefix}-restore",
        f"fitician_final_sync_{run_id.replace('-', '_')}_source",
        f"fitician_final_sync_{run_id.replace('-', '_')}_restore",
    )


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, capture_output=True, **kwargs)


def state(container: str) -> str:
    return run(
        [
            "docker",
            "inspect",
            "--format",
            "{{.State.Running}}|{{.HostConfig.NetworkMode}}|{{json .NetworkSettings.Ports}}|{{json .Mounts}}|{{.Config.Image}}",
            container,
        ],
        text=True,
    ).stdout.strip()


def snapshot(container: str) -> dict:
    sql = "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;\n"
    sql += FINAL_SNAPSHOT._metadata_query(FINAL_SNAPSHOT.FINGERPRINT_TABLES)
    sql += "ROLLBACK;\\q\n"
    result = run(
        [
            "docker",
            "exec",
            "-i",
            container,
            "psql",
            "-X",
            "-qAt",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "postgres",
            "-d",
            "fitician_qa",
        ],
        input=sql.encode(),
    )
    return json.loads(result.stdout.decode().splitlines()[0])


def rehearse(run_id: str, evidence_path: Path) -> dict:
    source, target, source_volume, target_volume = resource_names(run_id)
    if not Path(AGE).is_file() or not Path(AGE_KEYGEN).is_file():
        raise RuntimeError("the local age and age-keygen tools are required")
    for resource in (source, target):
        if (
            subprocess.run(
                ["docker", "inspect", resource], capture_output=True, check=False
            ).returncode
            == 0
        ):
            raise SystemExit(f"refusing existing QA container: {resource}")
    existing = run(
        ["docker", "volume", "ls", "--format", "{{.Name}}"], text=True
    ).stdout.splitlines()
    for volume in (source_volume, target_volume):
        if volume in existing:
            raise SystemExit(f"refusing existing QA volume: {volume}")
    project = f"fitician-final-sync-{run_id}"
    existing_project_containers = run(
        [
            "docker",
            "ps",
            "--all",
            "--filter",
            f"label=com.docker.compose.project={project}",
            "--format",
            "{{.ID}}",
        ],
        text=True,
    ).stdout.splitlines()
    if existing_project_containers:
        raise SystemExit(f"refusing existing QA Compose project: {project}")

    created_volumes: list[str] = []
    created_containers: list[str] = []
    WORK.mkdir(parents=True, exist_ok=True)
    identity = WORK / f"{run_id}.synthetic.agekey"
    encrypted = WORK / f"{run_id}.synthetic.dump.age"
    compose_file = WORK / f"{run_id}.compose.yaml"
    manifest_file = WORK / f"{run_id}.freeze.json"
    metadata_file = WORK / f"{run_id}.snapshot.json"
    if any(
        path.exists()
        for path in (
            identity,
            encrypted,
            compose_file,
            manifest_file,
            metadata_file,
            evidence_path,
        )
    ):
        raise RuntimeError("run ID or evidence path already exists")
    try:
        for volume in (source_volume, target_volume):
            run(["docker", "volume", "create", volume], text=True)
            created_volumes.append(volume)
        compose_file.write_text(
            f"""services:
  db:
    image: {IMAGE}
    container_name: {source}
    network_mode: none
    mem_limit: 512m
    cpus: 0.75
    environment:
      POSTGRES_PASSWORD: {PASSWORD}
      POSTGRES_USER: postgres
      POSTGRES_DB: fitician_qa
    volumes:
      - {source_volume}:/var/lib/postgresql
volumes:
  {source_volume}:
    name: {source_volume}
    external: true
""",
            encoding="utf-8",
        )
        compose_file.chmod(0o600)
        compose = FINAL_SNAPSHOT.compose_args(compose_file, project)
        run([*compose, "up", "--detach", "db"], text=True)
        created_containers.append(source)
        run(
            [
                "docker",
                "run",
                "--detach",
                "--name",
                target,
                "--network",
                "none",
                "--memory",
                "512m",
                "--cpus",
                "0.75",
                "--env",
                "POSTGRES_PASSWORD=" + PASSWORD,
                "--env",
                "POSTGRES_USER=postgres",
                "--env",
                "POSTGRES_DB=fitician_qa",
                "--volume",
                target_volume + ":/var/lib/postgresql",
                IMAGE,
            ],
            text=True,
        )
        created_containers.append(target)
        for container in (source, target):
            for _ in range(60):
                ready = subprocess.run(
                    [
                        "docker",
                        "exec",
                        container,
                        "pg_isready",
                        "-U",
                        "postgres",
                        "-d",
                        "fitician_qa",
                    ],
                    capture_output=True,
                    check=False,
                )
                if ready.returncode == 0:
                    break
                time.sleep(1)
            else:
                raise RuntimeError("synthetic PostgreSQL did not become ready")

        fixture_sql = """
        CREATE TABLE public.alembic_version (version_num varchar(32) NOT NULL PRIMARY KEY);
        INSERT INTO public.alembic_version VALUES ('synthetic_final_sync_head');
        CREATE TABLE public.users (id integer PRIMARY KEY, display_name text NOT NULL);
        INSERT INTO public.users VALUES (1, 'Synthetic User A'), (2, 'Synthetic User B');
        CREATE TABLE public.profiles (
          id integer PRIMARY KEY, user_id integer NOT NULL REFERENCES public.users(id),
          label text NOT NULL
        );
        INSERT INTO public.profiles VALUES (10, 1, 'Synthetic profile');
        CREATE TABLE public.sessions (id integer PRIMARY KEY, user_id integer REFERENCES public.users(id));
        """
        run(
            [
                "docker",
                "exec",
                "-i",
                source,
                "psql",
                "-v",
                "ON_ERROR_STOP=1",
                "-U",
                "postgres",
                "-d",
                "fitician_qa",
            ],
            input=fixture_sql.encode(),
        )

        run([str(AGE_KEYGEN), "-o", str(identity)], text=True)
        identity.chmod(0o600)
        recipient = run(
            [str(AGE_KEYGEN), "-y", str(identity)], text=True
        ).stdout.strip()
        if identity.stat().st_mode & 0o077:
            raise RuntimeError("synthetic age identity permissions are too broad")

        manifest = {
            "source_host": FINAL_SNAPSHOT.SOURCE,
            "ingress_drained": True,
            "freeze_complete": True,
            "frozen_container_ids": {
                name: f"{index:064x}"
                for index, name in enumerate(sorted(FINAL_SNAPSHOT.WRITERS), 1)
            },
            "preserved_services": {
                name: True for name in sorted(FINAL_SNAPSHOT.PRESERVED)
            },
        }
        manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
        manifest_file.chmod(0o600)

        def qa_source_check(
            actual_project: str, writers: dict[str, str]
        ) -> dict[str, str]:
            if actual_project != project or set(writers) != FINAL_SNAPSHOT.WRITERS:
                raise RuntimeError("synthetic source verification scope changed")
            details = run(
                [
                    "docker",
                    "inspect",
                    "--format",
                    "{{.State.Running}}|{{.HostConfig.NetworkMode}}|{{.Config.Image}}|{{.Config.Labels}}",
                    source,
                ],
                text=True,
            ).stdout.strip()
            if (
                "true|none|" + IMAGE not in details
                or "com.docker.compose.service:db" not in details
            ):
                raise RuntimeError("synthetic Compose source isolation check failed")
            return {
                service: f"synthetic-{service}-{run_id}"
                for service in FINAL_SNAPSHOT.PRESERVED
            }

        path_env = os.pathsep.join([str(Path(AGE).parent), os.environ.get("PATH", "")])
        with (
            patch.object(
                FINAL_SNAPSHOT, "verify_source_state", side_effect=qa_source_check
            ),
            patch.dict(
                os.environ,
                {"DB_BACKUP_AGE_RECIPIENT": recipient, "PATH": path_env},
            ),
        ):
            result = FINAL_SNAPSHOT.execute_snapshot(
                compose_file=compose_file,
                project=project,
                manifest_file=manifest_file,
                encrypted_output=encrypted,
                metadata_output=metadata_file,
            )
        if result["age_identity_sent_to_destination"] is not False:
            raise RuntimeError("synthetic age identity crossed the source boundary")
        before = json.loads(metadata_file.read_text(encoding="utf-8"))
        if metadata_file.stat().st_mode & 0o077 or encrypted.stat().st_mode & 0o077:
            raise RuntimeError("synthetic snapshot output permissions are too broad")
        REGIONAL_CUTOVER._validate_restore_snapshot(before)
        encrypted_sha256 = hashlib.sha256(encrypted.read_bytes()).hexdigest()
        decrypted = run(
            [str(AGE), "--decrypt", "--identity", str(identity), str(encrypted)]
        ).stdout
        run(
            [
                "docker",
                "exec",
                "-i",
                target,
                "pg_restore",
                "--single-transaction",
                "--exit-on-error",
                "--no-owner",
                "--no-acl",
                "-U",
                "postgres",
                "-d",
                "fitician_qa",
            ],
            input=decrypted,
        )
        after = snapshot(target)
        expected_data = {
            key: before[key]
            for key in (
                "counts",
                "tables",
                "fingerprints",
                "alembic",
                "unvalidated_foreign_keys",
            )
        }
        if expected_data != after or after["unvalidated_foreign_keys"] != 0:
            raise RuntimeError("restored snapshot differed from synthetic source")
        states = {name: state(name).split("|", 4) for name in (source, target)}
        expected_volumes = {source: source_volume, target: target_volume}
        for container, parts in states.items():
            running, network, ports, mounts, image = parts
            port_bindings = json.loads(ports) if ports != "null" else None
            volume_mounts = json.loads(mounts)
            no_published_ports = port_bindings is None or all(
                not bindings for bindings in port_bindings.values()
            )
            isolated_volume = (
                len(volume_mounts) == 1
                and volume_mounts[0].get("Type") == "volume"
                and volume_mounts[0].get("Name") == expected_volumes[container]
                and volume_mounts[0].get("RW") is True
            )
            if (
                running != "true"
                or network != "none"
                or not no_published_ports
                or not isolated_volume
                or image != IMAGE
            ):
                raise RuntimeError("QA container isolation or image pin did not match")

        evidence = {
            "mode": "synthetic-final-sync-rehearsal",
            "source_container": source,
            "restore_container": target,
            "postgres_image": IMAGE,
            "network_mode": "none",
            "published_ports": 0,
            "age_identity_permissions": "0600",
            "age_identity_sent_to_destination": False,
            "encrypted_archive_bytes": encrypted.stat().st_size,
            "encrypted_archive_sha256": encrypted_sha256,
            "table_counts": after["counts"],
            "tables_verified": len(after["tables"]),
            "fingerprints_verified": len(before["fingerprints"]),
            "alembic": after["alembic"],
            "unvalidated_foreign_keys": after["unvalidated_foreign_keys"],
            "source_equals_restore": expected_data == after,
            "source_or_production_changed": False,
        }
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
        return evidence
    finally:
        identity.unlink(missing_ok=True)
        encrypted.unlink(missing_ok=True)
        compose_file.unlink(missing_ok=True)
        manifest_file.unlink(missing_ok=True)
        metadata_file.unlink(missing_ok=True)
        for container in reversed(created_containers):
            subprocess.run(
                ["docker", "rm", "--force", container], capture_output=True, check=False
            )
        for volume in reversed(created_volumes):
            subprocess.run(
                ["docker", "volume", "rm", volume], capture_output=True, check=False
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args(argv)
    try:
        source, target, source_volume, target_volume = resource_names(args.run_id)
        evidence = args.evidence or WORK / f"{args.run_id}.evidence.json"
        result = rehearse(args.run_id, evidence)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"BLOCKED: {type(error).__name__}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    print(f"Sanitized evidence: {evidence}")
    print(
        f"Cleaned QA containers {source}, {target}; volumes {source_volume}, {target_volume}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
