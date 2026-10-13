#!/usr/bin/env python3
"""Create an encrypted, transaction-matched final database snapshot after an attested freeze."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SOURCE = "mohammad@141.11.0.99"
WRITERS = {
    "backend",
    "backend-2",
    "food-photo-worker",
    "body-analysis-worker",
    "notification-worker",
    "scheduler",
}
PRESERVED = {"db", "redis", "agent-service"}
FINGERPRINT_TABLES = {
    "users",
    "user_profiles",
    "sessions",
    "mobile_access_tokens",
    "mobile_refresh_tokens",
    "mobile_token_families",
    "ai_provider_credentials",
    "ai_agent_service_proxy_settings",
    "notification_device_tokens",
    "exercise_media_assets",
    "body_photos",
}
CONTAINER_ID = re.compile(r"^[0-9a-f]{64}$")


def compose_args(compose_file: Path, project: str) -> list[str]:
    return [
        "docker",
        "compose",
        "--project-name",
        project,
        "--project-directory",
        str(compose_file.resolve().parent),
        "-f",
        str(compose_file.resolve()),
    ]


def validate_freeze_manifest(manifest: Any) -> dict[str, str]:
    if not isinstance(manifest, dict) or manifest.get("source_host") != SOURCE:
        raise ValueError(f"freeze manifest source_host must be exactly {SOURCE}")
    if (
        manifest.get("ingress_drained") is not True
        or manifest.get("freeze_complete") is not True
    ):
        raise ValueError("ingress_drained and freeze_complete must both be true")
    writers = manifest.get("frozen_container_ids")
    if not isinstance(writers, dict) or set(writers) != WRITERS:
        raise ValueError(
            "frozen_container_ids must contain the two APIs and four workers"
        )
    ids = list(writers.values())
    if any(
        not isinstance(value, str) or not CONTAINER_ID.fullmatch(value) for value in ids
    ):
        raise ValueError("every frozen container ID must be a full lowercase Docker ID")
    if len(set(ids)) != len(ids):
        raise ValueError("frozen container IDs must be unique")
    preserved = manifest.get("preserved_services")
    if not isinstance(preserved, dict) or set(preserved) != PRESERVED:
        raise ValueError("preserved_services must contain db, redis, and agent-service")
    if any(value is not True for value in preserved.values()):
        raise ValueError("db, redis, and agent-service must remain live")
    return writers


def _docker_json(container_ids: list[str]) -> list[dict[str, Any]]:
    result = subprocess.run(
        ["docker", "inspect", *container_ids],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("source container inspection failed")
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError("source container inspection output was invalid") from None
    if not isinstance(value, list):
        raise TypeError("source container inspection output was invalid")
    return value


def verify_source_state(project: str, writers: dict[str, str]) -> dict[str, str]:
    frozen = _docker_json(list(writers.values()))
    for container in frozen:
        labels = container.get("Config", {}).get("Labels") or {}
        service = labels.get("com.docker.compose.service")
        if (
            labels.get("com.docker.compose.project") != project
            or service not in writers
            or writers[service] != container.get("Id")
            or container.get("State", {}).get("Running") is not False
        ):
            raise RuntimeError(
                "a frozen writer ID, Compose label, or stopped state differs"
            )
    if len(frozen) != len(WRITERS):
        raise RuntimeError("not all six frozen writers could be verified")

    result = subprocess.run(
        [
            "docker",
            "ps",
            "--all",
            "--no-trunc",
            "--filter",
            f"label=com.docker.compose.project={project}",
            "--format",
            '{{.ID}} {{.State}} {{.Label "com.docker.compose.service"}}',
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("preserved source service inventory failed")
    live: dict[str, str] = {}
    found_writers: dict[str, str] = {}
    for line in result.stdout.splitlines():
        pieces = line.split()
        if len(pieces) != 3:
            continue
        container_id, state, service = pieces
        if service in WRITERS:
            if (
                service in found_writers
                or container_id != writers[service]
                or state != "exited"
            ):
                raise RuntimeError("an unlisted or still-running source writer exists")
            found_writers[service] = container_id
        elif service in PRESERVED and state == "running":
            if service in live:
                raise RuntimeError(
                    "multiple live instances of a preserved source service exist"
                )
            live[service] = container_id
    if set(found_writers) != WRITERS:
        raise RuntimeError("every source writer must be inventoried and stopped")
    if set(live) != PRESERVED:
        raise RuntimeError(
            "the source db, redis, and agent-service must remain running"
        )
    return live


def _metadata_query(fingerprints: set[str]) -> str:
    fingerprint_array = (
        "ARRAY["
        + ",".join(
            "'" + table.replace("'", "''") + "'" for table in sorted(fingerprints)
        )
        + "]::text[]"
    )
    return f"""
SELECT
 'SELECT json_build_object(''counts'', json_build_object('
 || string_agg(format('%L, (SELECT count(*) FROM public.%I)', tablename, tablename), ',')
 || '), ''tables'', (SELECT json_agg(tablename ORDER BY tablename) FROM pg_tables WHERE schemaname=''public''), '
 || '''fingerprints'', json_build_object('
 || coalesce(string_agg(
      format('%L, (SELECT md5(coalesce(string_agg(h, %L ORDER BY h), %L)) FROM (SELECT md5(row_to_json(t)::text) h FROM public.%I t) s)',
             tablename, '', '', tablename), ',') FILTER (WHERE tablename = ANY({fingerprint_array})), '')
 || '), ''alembic'', (SELECT json_agg(version_num ORDER BY version_num) FROM public.alembic_version), '
 || '''unvalidated_foreign_keys'', (SELECT count(*) FROM pg_constraint WHERE contype=''f'' AND NOT convalidated))::text'
FROM pg_tables WHERE schemaname = 'public'
\\gexec
"""


def _read_psql_line(process: subprocess.Popen[str], message: str) -> str:
    assert process.stdout is not None
    line = process.stdout.readline()
    if not line:
        raise RuntimeError(message)
    return line.rstrip("\n")


def _write_private_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("metadata output must not be a symlink")
    fd, temporary = tempfile.mkstemp(prefix=".final-snapshot-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(value, output, indent=2, sort_keys=True)
            output.write("\n")
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def execute_snapshot(
    *,
    compose_file: Path,
    project: str,
    manifest_file: Path,
    encrypted_output: Path,
    metadata_output: Path,
) -> dict[str, Any]:
    if manifest_file.is_symlink() or not manifest_file.is_file():
        raise ValueError("freeze manifest must be a local regular file")
    if manifest_file.stat().st_mode & 0o077:
        raise ValueError("freeze manifest permissions must be 0600 or stricter")
    if not compose_file.is_file() or compose_file.is_symlink():
        raise ValueError("production Compose file is missing or unsafe")
    recipient = os.environ.get("DB_BACKUP_AGE_RECIPIENT", "")
    if not recipient.startswith("age1"):
        raise ValueError("DB_BACKUP_AGE_RECIPIENT must be configured")

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    writers = validate_freeze_manifest(manifest)
    preserved_ids = verify_source_state(project, writers)
    compose = compose_args(compose_file, project)
    psql_script = (
        'exec psql -X -qAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
    )
    exporter = subprocess.Popen(
        [*compose, "exec", "-T", "db", "sh", "-c", psql_script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    pg_dump: subprocess.Popen[bytes] | None = None
    age: subprocess.Popen[bytes] | None = None
    try:
        assert exporter.stdin is not None
        exporter.stdin.write("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;\n")
        exporter.stdin.write("SELECT pg_export_snapshot();\n")
        exporter.stdin.flush()
        snapshot_id = _read_psql_line(
            exporter, "PostgreSQL did not export a transaction snapshot"
        )
        if not re.fullmatch(r"[0-9A-Fa-f-]+-[0-9]+", snapshot_id):
            raise RuntimeError("exported PostgreSQL snapshot ID was invalid")

        exporter.stdin.write(_metadata_query(FINGERPRINT_TABLES))
        exporter.stdin.flush()
        metadata = json.loads(
            _read_psql_line(exporter, "source snapshot metadata query failed")
        )
        if not isinstance(metadata, dict) or not metadata.get("counts"):
            raise RuntimeError("source snapshot metadata was empty or invalid")

        output_dir = encrypted_output.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        if encrypted_output.is_symlink() or metadata_output.is_symlink():
            raise ValueError("snapshot outputs must not be symlinks")
        for path in (encrypted_output, metadata_output):
            if path.exists() and (not path.is_file() or path.stat().st_size != 0):
                raise ValueError(
                    "snapshot output paths must be absent or empty regular files"
                )
        age_fd, age_tmp_name = tempfile.mkstemp(
            prefix=".final-database-", suffix=".age", dir=output_dir
        )
        os.fchmod(age_fd, 0o600)
        try:
            with os.fdopen(age_fd, "wb") as ciphertext:
                dump_command = [
                    *compose,
                    "exec",
                    "-T",
                    "db",
                    "sh",
                    "-c",
                    'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-acl --snapshot="$1"',
                    "final-db-snapshot",
                    snapshot_id,
                ]
                pg_dump = subprocess.Popen(
                    dump_command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
                )
                assert pg_dump.stdout is not None
                age = subprocess.Popen(
                    ["age", "-r", recipient],
                    stdin=pg_dump.stdout,
                    stdout=ciphertext,
                    stderr=subprocess.DEVNULL,
                )
                pg_dump.stdout.close()
                age_status = age.wait(timeout=3600)
                dump_status = pg_dump.wait(timeout=3600)
            if age_status or dump_status or Path(age_tmp_name).stat().st_size == 0:
                raise RuntimeError("encrypted snapshot pipeline failed")
            os.replace(age_tmp_name, encrypted_output)
        finally:
            Path(age_tmp_name).unlink(missing_ok=True)

        exporter.stdin.write("ROLLBACK;\\q\n")
        exporter.stdin.flush()
        exporter.stdin.close()
        if exporter.wait(timeout=30) != 0:
            raise RuntimeError("read-only snapshot transaction did not exit cleanly")
        if verify_source_state(project, writers) != preserved_ids:
            raise RuntimeError(
                "source writer freeze or preserved container set changed during snapshot"
            )

        metadata["sha256"] = hashlib.sha256(encrypted_output.read_bytes()).hexdigest()
        metadata["encrypted_bytes"] = encrypted_output.stat().st_size
        metadata["source_host"] = SOURCE
        metadata["source_project"] = project
        metadata["preserved_service_ids"] = preserved_ids
        _write_private_json(metadata_output, metadata)
        return {
            "encrypted_bytes": metadata["encrypted_bytes"],
            "sha256": metadata["sha256"],
            "tables": len(metadata["counts"]),
            "fingerprints": len(metadata["fingerprints"]),
            "metadata_path": str(metadata_output),
            "age_identity_sent_to_destination": False,
        }
    except BaseException:
        if pg_dump is not None and pg_dump.poll() is None:
            pg_dump.kill()
            pg_dump.wait()
        if age is not None and age.poll() is None:
            age.kill()
            age.wait()
        raise
    finally:
        if exporter.poll() is None:
            if exporter.stdin and not exporter.stdin.closed:
                exporter.stdin.write("ROLLBACK;\\q\n")
                exporter.stdin.flush()
                exporter.stdin.close()
            try:
                exporter.wait(timeout=30)
            except subprocess.TimeoutExpired:
                exporter.kill()
                exporter.wait()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--compose-file", type=Path, default=Path("/opt/fitician/compose.prod.yaml")
    )
    parser.add_argument("--project-name", default="fitician")
    parser.add_argument("--freeze-manifest", type=Path, required=True)
    parser.add_argument("--encrypted-output", type=Path, required=True)
    parser.add_argument("--metadata-output", type=Path, required=True)
    parser.add_argument("--confirm-source")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        print("DRY RUN ONLY. No host, database, or Docker state was inspected.")
        print(
            "Freeze evidence will be validated before a read-only PostgreSQL transaction."
        )
        print("Encrypted output: " + str(args.encrypted_output))
        print("Metadata output: " + str(args.metadata_output))
        print("No writer is stopped or restarted by this command.")
        return 0
    if args.confirm_source != SOURCE:
        print(f"BLOCKED: --confirm-source must exactly equal {SOURCE}", file=sys.stderr)
        return 2
    try:
        result = execute_snapshot(
            compose_file=args.compose_file,
            project=args.project_name,
            manifest_file=args.freeze_manifest,
            encrypted_output=args.encrypted_output,
            metadata_output=args.metadata_output,
        )
    except (
        OSError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
        RuntimeError,
        subprocess.SubprocessError,
    ) as error:
        print(f"BLOCKED: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
