#!/usr/bin/env python3
"""Dry-run-first regional cutover preparation and evidence gate."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import shlex
import stat
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SHA256 = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
SOURCE = "mohammad@141.11.0.99"
ZONE = "fitician.fit"
POSTGRES_IMAGE = "postgres:18-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15"
FREEZE_SERVICES = {
    "backend",
    "backend-2",
    "food-photo-worker",
    "body-analysis-worker",
    "notification-worker",
    "scheduler",
}


def _mapping(value: Any, name: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{name} must be an object")
        return {}
    return value


def check_sha256(path: Path, expected: str) -> str:
    """Stream-hash a local artifact and fail closed on an invalid or different digest."""
    if not SHA256.fullmatch(expected):
        raise ValueError("expected SHA-256 must be lowercase hex")
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != expected:
        raise ValueError("artifact SHA-256 mismatch")
    return actual


def https_probe_command(domain: str, address: str) -> list[str]:
    if (
        not re.fullmatch(r"[a-z0-9.-]+", domain)
        or ".." in domain
        or domain.startswith(".")
    ):
        raise ValueError("domain must be a plain DNS name")
    ip = ipaddress.ip_address(address)
    return [
        "curl",
        "--fail",
        "--silent",
        "--show-error",
        "--max-time",
        "10",
        "--noproxy",
        "*",
        "--resolve",
        f"{domain}:443:{ip}",
        f"https://{domain}/healthz",
    ]


def plan_dns_updates(snapshot: dict[str, Any], target_ipv4: str) -> dict[str, Any]:
    """Build exact in-scope Cloudflare record patches from a sanitized zone export."""
    address = str(ipaddress.IPv4Address(target_ipv4))
    if snapshot.get("zone") != ZONE:
        raise ValueError(f"snapshot zone must be exactly {ZONE}")
    records = snapshot.get("records")
    if not isinstance(records, list):
        raise TypeError("snapshot records must be a list")
    expected_names = {ZONE, f"api.{ZONE}", f"www.{ZONE}"}
    seen_ids: set[str] = set()
    selected: dict[str, list[dict[str, Any]]] = {name: [] for name in expected_names}
    unrelated = 0
    for record in records:
        if not isinstance(record, dict):
            raise TypeError("each DNS record must be an object")
        name = str(record.get("name", "")).rstrip(".").lower()
        if name not in expected_names:
            unrelated += 1
            continue
        record_type = record.get("type")
        if record_type in {"MX", "TXT", "NS", "SRV", "CAA"}:
            unrelated += 1
            continue
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id or record_id in seen_ids:
            raise ValueError(
                "every in-scope DNS record needs a unique provider record ID"
            )
        seen_ids.add(record_id)
        if record_type == "AAAA":
            raise ValueError(
                f"unexpected {name} AAAA record; IPv6 must be explicitly qualified"
            )
        if name == f"www.{ZONE}" and record_type == "CNAME":
            if str(record.get("content", "")).rstrip(".").lower() != ZONE:
                raise ValueError(
                    "www CNAME must already point to the apex; manual review required"
                )
            selected[name].append(record)
        elif record_type == "A":
            selected[name].append(record)
        else:
            raise ValueError(
                f"unsupported in-scope record type for {name}: {record_type}"
            )

    if not selected[ZONE] or not selected[f"api.{ZONE}"] or not selected[f"www.{ZONE}"]:
        raise ValueError(
            "apex, api, and www records must all be present in the zone snapshot"
        )
    updates = []
    for name in (ZONE, f"api.{ZONE}", f"www.{ZONE}"):
        for record in selected[name]:
            if record["type"] == "A" and record.get("content") != address:
                patch = {
                    key: record[key]
                    for key in ("type", "name", "content", "ttl", "proxied")
                    if key in record
                }
                patch["content"] = address
                updates.append({"record_id": record["id"], "patch": patch})
    return {
        "zone": ZONE,
        "target_ipv4": address,
        "updates": updates,
        "preserved_unrelated_record_count": unrelated,
        "www_cname_preserved": any(
            record["type"] == "CNAME" for record in selected[f"www.{ZONE}"]
        ),
        "writes_performed": False,
    }


def plan_dns_rollback(
    before: dict[str, Any], current: dict[str, Any]
) -> dict[str, Any]:
    """Plan restoration of owned DNS fields from a pre-cutover snapshot only."""
    if before.get("zone") != ZONE or current.get("zone") != ZONE:
        raise ValueError(f"both DNS snapshots must be for exactly {ZONE}")
    names = {ZONE, f"api.{ZONE}", f"www.{ZONE}"}

    def normalize_name(value: Any) -> str:
        return str(value).rstrip(".").lower()

    def owned(snapshot: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], int]:
        records = snapshot.get("records")
        if not isinstance(records, list):
            raise TypeError("DNS snapshot records must be a list")
        indexed: dict[str, dict[str, Any]] = {}
        owner_types: dict[str, set[str]] = {}
        unrelated = 0
        for record in records:
            if not isinstance(record, dict):
                raise TypeError("each DNS record must be an object")
            name = normalize_name(record.get("name", ""))
            if name not in names or record.get("type") in {
                "MX",
                "TXT",
                "NS",
                "SRV",
                "CAA",
            }:
                unrelated += 1
                continue
            record_id = record.get("id")
            if not isinstance(record_id, str) or not record_id or record_id in indexed:
                raise ValueError("owned DNS records need unique provider record IDs")
            if record.get("type") == "AAAA":
                raise ValueError(
                    "unexpected owned AAAA record; manual rollback review required"
                )
            if record.get("type") not in {"A", "CNAME"}:
                raise ValueError("unsupported owned DNS record type")
            if record.get("type") == "CNAME" and name != f"www.{ZONE}":
                raise ValueError("only www may use CNAME in the owned rollback set")
            indexed[record_id] = record
            owner_types.setdefault(name, set()).add(str(record["type"]))
        if any({"A", "CNAME"} <= types for types in owner_types.values()):
            raise ValueError("owned DNS owner has conflicting A and CNAME records")
        return indexed, unrelated

    old, _ = owned(before)
    new, new_unrelated = owned(current)
    if not old or set(old) != set(new):
        raise ValueError(
            "owned DNS record IDs differ between before and current snapshots"
        )
    if {normalize_name(record["name"]) for record in old.values()} != names:
        raise ValueError("before snapshot must include apex, api, and www records")
    updates = []
    for record_id, original in old.items():
        live = new[record_id]
        if (normalize_name(live.get("name")), live.get("type")) != (
            normalize_name(original.get("name")),
            original.get("type"),
        ):
            raise ValueError(
                "owned DNS record identity changed; manual rollback review required"
            )
        fields = ("content", "ttl", "proxied")
        if any(live.get(field) != original.get(field) for field in fields):
            patch = {
                key: original[key]
                for key in ("type", "name", *fields)
                if key in original
            }
            updates.append({"record_id": record_id, "patch": patch})
    return {
        "zone": ZONE,
        "updates": updates,
        "preserved_unrelated_record_count": new_unrelated,
        "writes_performed": False,
        "data_reconciliation_required_after_writes": True,
    }


def _load_restore_snapshot(path: Path) -> dict[str, Any]:
    value = _load_manifest(path)
    return _validate_restore_snapshot(value)


def _validate_restore_snapshot(value: dict[str, Any]) -> dict[str, Any]:
    counts = value.get("counts")
    fingerprints = value.get("fingerprints")
    alembic = value.get("alembic")
    if (
        not isinstance(counts, dict)
        or not counts
        or not isinstance(fingerprints, dict)
        or not fingerprints
    ):
        raise ValueError(
            "expected snapshot must include nonempty counts and fingerprints maps"
        )
    for table, count in counts.items():
        if (
            not re.fullmatch(r"[a-z_][a-z0-9_]*", str(table))
            or type(count) is not int
            or count < 0
        ):
            raise ValueError("snapshot table names/counts are invalid")
    for table, fingerprint in fingerprints.items():
        if (
            table not in counts
            or not isinstance(fingerprint, str)
            or not re.fullmatch(r"[0-9a-f]{32}", fingerprint)
        ):
            raise ValueError("snapshot fingerprints are invalid")
    if (
        not isinstance(alembic, list)
        or not alembic
        or any(not isinstance(item, str) for item in alembic)
    ):
        raise ValueError("snapshot Alembic revision list is invalid")
    return value


def build_verify_sql(snapshot: dict[str, Any]) -> str:
    expected = _validate_restore_snapshot(snapshot)
    counts = expected["counts"]
    fingerprints = expected["fingerprints"]
    count_rows = [
        "SELECT "
        + _sql_literal(table)
        + " AS tablename, count(*)::bigint AS row_count "
        + f'FROM public."{table}"'
        for table in sorted(counts)
    ]
    fingerprint_rows = [
        "SELECT " + _sql_literal(table) + " AS tablename, "
        "md5(coalesce(string_agg(h, '' ORDER BY h),'')) AS fingerprint "
        f'FROM (SELECT md5(row_to_json(t)::text) h FROM public."{table}" t) s'
        for table in sorted(fingerprints)
    ]
    counts_sql = " UNION ALL ".join(count_rows)
    fingerprints_sql = (
        " UNION ALL ".join(fingerprint_rows)
        or "SELECT NULL::text tablename, NULL::text fingerprint WHERE false"
    )
    return (
        "SELECT json_build_object("
        "'counts',(SELECT json_object_agg(tablename,row_count) FROM ("
        + counts_sql
        + ") c),"
        "'tables',(SELECT json_agg(tablename ORDER BY tablename) FROM pg_tables "
        "WHERE schemaname='public'),"
        "'fingerprints',(SELECT json_object_agg(tablename,fingerprint) FROM ("
        + fingerprints_sql
        + ") f),"
        "'alembic',(SELECT json_agg(version_num ORDER BY version_num) FROM alembic_version),"
        "'unvalidated_foreign_keys',(SELECT count(*) FROM pg_constraint "
        "WHERE contype='f' AND NOT convalidated)"
        ")::text"
    )


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _ssh_command(remote_parts: list[str]) -> list[str]:
    return [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "iran",
        shlex.join(remote_parts),
    ]


RESTORE_SCRIPT = (
    "exec pg_restore --single-transaction --exit-on-error --no-owner --no-acl "
    '-U "$POSTGRES_USER" -d "$POSTGRES_DB"'
)
EMPTY_TABLE_SQL = (
    "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
    "WHERE n.nspname='public' AND c.relkind IN ('r','p')"
)


def _restore_container_valid(name: str) -> bool:
    return bool(re.fullmatch(r"fitician-[a-z0-9-]+-restore-[a-z0-9-]+", name))


def _inspect_target(container: str, timeout: int = 30) -> None:
    if not _restore_container_valid(container):
        raise ValueError("restore target must match fitician-*-restore-*")
    template = (
        "{{.State.Running}}|{{.HostConfig.NetworkMode}}|"
        "{{json .NetworkSettings.Ports}}|{{json .Mounts}}|{{.Config.Image}}"
    )
    result = subprocess.run(
        _ssh_command(
            [
                "docker",
                "inspect",
                "--type",
                "container",
                "--format",
                template,
                container,
            ]
        ),
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError("destination restore container could not be inspected")
    try:
        running, network, raw_ports, raw_mounts, image = result.stdout.strip().split(
            "|", 4
        )
        ports = json.loads(raw_ports)
        mounts = json.loads(raw_mounts)
    except (ValueError, json.JSONDecodeError):
        raise RuntimeError(
            "destination restore container inspection was invalid"
        ) from None
    no_ports = ports is None or (
        isinstance(ports, dict) and all(not bindings for bindings in ports.values())
    )
    valid_mount = (
        isinstance(mounts, list)
        and len(mounts) == 1
        and isinstance(mounts[0], dict)
        and mounts[0].get("Type") == "volume"
        and re.fullmatch(
            r"fitician[_-][a-z0-9_-]*restore[_-][a-z0-9_-]+",
            str(mounts[0].get("Name", "")),
        )
        and mounts[0].get("Destination") == "/var/lib/postgresql"
        and mounts[0].get("RW") is True
    )
    if running != "true" or network != "none" or not no_ports:
        raise RuntimeError(
            "restore target must be running with network=none and no published ports"
        )
    if image != POSTGRES_IMAGE or not valid_mount:
        raise RuntimeError(
            "restore target must use the pinned PostgreSQL 18 image and one dedicated "
            "restore volume"
        )
    volume_name = str(mounts[0]["Name"])
    attached = subprocess.run(
        _ssh_command(
            [
                "docker",
                "ps",
                "--all",
                "--filter",
                f"volume={volume_name}",
                "--format",
                "{{.Names}}",
            ]
        ),
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    if attached.returncode != 0 or attached.stdout.strip().splitlines() != [container]:
        raise RuntimeError(
            "restore volume must be attached only to the named restore container"
        )


def _target_table_count(container: str, timeout: int = 30) -> int:
    remote_script = 'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "$1"'
    command = _ssh_command(
        [
            "docker",
            "exec",
            container,
            "sh",
            "-c",
            remote_script,
            "regional-empty-check",
            EMPTY_TABLE_SQL,
        ]
    )
    result = subprocess.run(
        command, capture_output=True, text=True, check=False, timeout=timeout
    )
    if result.returncode != 0:
        raise RuntimeError("restore target empty-database check failed")
    try:
        count = int(result.stdout.strip())
    except ValueError:
        raise RuntimeError("restore target empty-database check was invalid") from None
    if count != 0:
        raise RuntimeError("restore target contains public tables; restore refused")
    return count


def _remote_verify(container: str, sql: str, timeout: int = 120) -> dict[str, Any]:
    remote_script = 'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "$1"'
    result = subprocess.run(
        _ssh_command(
            [
                "docker",
                "exec",
                container,
                "sh",
                "-c",
                remote_script,
                "regional-verify",
                sql,
            ]
        ),
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError("restored database validation query failed")
    try:
        actual = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        raise RuntimeError("restored database validation output was invalid") from None
    if not isinstance(actual, dict):
        raise TypeError("restored database validation output was invalid")
    return actual


def _compare_restore(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    if sorted(actual.get("tables") or []) != sorted(expected["counts"]):
        raise RuntimeError(
            "restored public table inventory differs from source snapshot"
        )
    checks = (
        actual.get("counts") == expected["counts"],
        actual.get("fingerprints") == expected["fingerprints"],
        sorted(actual.get("alembic") or []) == sorted(expected["alembic"]),
        actual.get("unvalidated_foreign_keys") == 0,
    )
    if not all(checks):
        raise RuntimeError(
            "restored counts, fingerprints, Alembic head, or foreign-key validation differ"
        )


def execute_restore(
    *,
    identity_file: Path,
    encrypted_file: Path,
    expected_snapshot: Path,
    expected_sha256: str,
    container: str,
    confirmation: str,
) -> dict[str, Any]:
    if not _restore_container_valid(container) or confirmation != container:
        raise ValueError(
            "execute requires exact confirmation of a fitician-*-restore-* target"
        )
    if not identity_file.is_file() or identity_file.is_symlink():
        raise ValueError("local age identity file is missing or unsafe")
    if stat.S_IMODE(identity_file.stat().st_mode) != 0o600:
        raise ValueError("local age identity file permissions must be exactly 0600")
    if not encrypted_file.is_file():
        raise ValueError("encrypted snapshot file is missing")
    check_sha256(encrypted_file, expected_sha256)
    snapshot = _load_restore_snapshot(expected_snapshot)

    _inspect_target(container)
    _target_table_count(container)

    remote_restore = shlex.join(
        ["docker", "exec", "-i", container, "sh", "-c", RESTORE_SCRIPT]
    )
    age = subprocess.Popen(
        ["age", "--decrypt", "--identity", str(identity_file), str(encrypted_file)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert age.stdout is not None
    ssh: subprocess.Popen[bytes] | None = None
    try:
        ssh = subprocess.Popen(
            [
                "ssh",
                "-o",
                "BatchMode=yes",
                "-o",
                "StrictHostKeyChecking=yes",
                "iran",
                remote_restore,
            ],
            stdin=age.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        age.stdout.close()
        ssh_status = ssh.wait(timeout=3600)
        age_status = age.wait(timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        if ssh is not None:
            ssh.kill()
            ssh.wait()
        age.kill()
        age.wait()
        raise RuntimeError("encrypted snapshot restore pipeline failed") from None
    assert ssh is not None
    if ssh_status != 0 or age_status != 0:
        raise RuntimeError("encrypted snapshot restore pipeline failed")

    actual = _remote_verify(container, build_verify_sql(snapshot))
    _compare_restore(actual, snapshot)
    return {
        "restore_succeeded": True,
        "tables_verified": len(snapshot["counts"]),
        "fingerprints_verified": len(snapshot["fingerprints"]),
        "alembic_verified": True,
        "unvalidated_foreign_keys": 0,
        "target_container": container,
        "age_identity_sent_to_destination": False,
        "volumes_deleted": False,
    }


def validate_manifest(manifest: dict[str, Any], action: str = "cutover") -> list[str]:
    """Return missing or inconsistent evidence; never executes operator commands."""
    errors: list[str] = []
    if action not in {"inventory", "cutover", "rollback"}:
        return ["action must be inventory, cutover, or rollback"]
    if action == "inventory":
        _mapping(manifest.get("source"), "source", errors)
        _mapping(manifest.get("evidence", {}), "evidence", errors)
        return errors

    if action == "cutover" and manifest.get("mode") != "final":
        errors.append("mode must be final; rehearsal evidence cannot be promoted")
    source = _mapping(manifest.get("source"), "source", errors)
    if source.get("host") != SOURCE:
        errors.append(f"source.host must remain {SOURCE}")
    if source.get("live_preserved") is not True:
        errors.append("source.live_preserved must be true")
    preserved = _mapping(
        source.get("preserved_services"), "source.preserved_services", errors
    )
    for service in ("postgres", "redis", "agent"):
        if preserved.get(service) is not True:
            errors.append(f"source.preserved_services.{service} must be true")

    evidence = _mapping(manifest.get("evidence"), "evidence", errors)
    if action == "cutover":
        ids = _mapping(
            source.get("frozen_container_ids"), "source.frozen_container_ids", errors
        )
        has_invalid_id = any(
            not isinstance(value, str) or not value.strip() for value in ids.values()
        )
        if set(ids) != FREEZE_SERVICES or has_invalid_id:
            errors.append(
                "source.frozen_container_ids must contain exactly verified backend "
                "and four consumer IDs"
            )
        for field in (
            "external_network_authenticated",
            "destination_https_dns_ready",
            "source_writes_frozen",
            "all_writers_drained",
            "agent_writes_quiesced",
        ):
            if evidence.get(field) is not True:
                errors.append(f"evidence.{field} must be true")
        for name, validation_field in (
            ("database", "data_validation_passed"),
            ("agent", "auth_validation_passed"),
        ):
            snapshot = _mapping(evidence.get(name), f"evidence.{name}", errors)
            for field in ("encrypted", "restore_verified", validation_field):
                if snapshot.get(field) is not True:
                    errors.append(f"evidence.{name}.{field} must be true")
            digest = snapshot.get("sha256")
            expected = snapshot.get("expected_sha256")
            if not isinstance(digest, str) or not SHA256.fullmatch(digest):
                errors.append(f"evidence.{name}.sha256 must be lowercase SHA-256")
            elif digest != expected:
                errors.append(f"{name} SHA-256 mismatch")
            artifact = snapshot.get("artifact_path")
            if artifact is not None:
                path = Path(str(artifact))
                if not path.is_file():
                    errors.append(f"evidence.{name}.artifact_path is missing")
                else:
                    try:
                        check_sha256(path, str(digest))
                    except (OSError, ValueError):
                        errors.append(f"{name} artifact SHA-256 mismatch")
        dns = _mapping(manifest.get("dns"), "dns", errors)
        if set(dns.get("owned_records_only", [])) != {"@", "api", "www"}:
            errors.append("dns.owned_records_only must be exactly @, api, www")

    if action == "rollback" and manifest.get("writes_started") is True:
        rollback = _mapping(manifest.get("rollback"), "rollback", errors)
        for field in ("target_writes_frozen", "reconciliation_complete"):
            if rollback.get(field) is not True:
                errors.append(f"rollback.{field} must be true after destination writes")
    if action == "rollback" and not isinstance(manifest.get("writes_started"), bool):
        errors.append("writes_started must be explicitly true or false")
    if action == "cutover":
        candidate_sha = manifest.get("candidate_sha")
        ci = _mapping(manifest.get("ci"), "ci", errors)
        if not isinstance(candidate_sha, str) or not GIT_SHA.fullmatch(candidate_sha):
            errors.append("candidate_sha must be a full lowercase Git SHA")
        if ci.get("passed") is not True:
            errors.append("ci.passed must be true")
        candidate_type = manifest.get("candidate_type", "application")
        if candidate_type == "application":
            if ci.get("commit_sha") != candidate_sha:
                errors.append("CI commit SHA must exactly match candidate_sha")
        elif candidate_type == "stable-config":
            stable_sha = manifest.get("stable_application_sha")
            if not isinstance(stable_sha, str) or not GIT_SHA.fullmatch(stable_sha):
                errors.append("stable_application_sha must be a full lowercase Git SHA")
            elif ci.get("commit_sha") != stable_sha:
                errors.append("CI commit SHA must exactly match stable_application_sha")
        else:
            errors.append("candidate_type must be application or stable-config")
        run_id = ci.get("run_id")
        if not isinstance(run_id, str) or not run_id.strip():
            errors.append("ci.run_id is required")
        try:
            completed = datetime.fromisoformat(str(ci.get("completed_at_utc", "")))
            if completed.tzinfo is None:
                raise ValueError
            age = datetime.now(UTC) - completed.astimezone(UTC)
            if (
                candidate_type == "application" and age > timedelta(days=7)
            ) or age < timedelta(minutes=-10):
                errors.append(
                    "application CI evidence must be no older than 7 days and not over "
                    "10 minutes in the future"
                    if candidate_type == "application"
                    else "CI evidence must not be over 10 minutes in the future"
                )
        except ValueError:
            errors.append("ci.completed_at_utc must be a timezone-aware ISO timestamp")
    return errors


def _load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("manifest root must be an object")
    return value


def _inventory(manifest: dict[str, Any]) -> None:
    source = manifest.get("source", {})
    evidence = manifest.get("evidence", {})
    db = evidence.get("database", {}) if isinstance(evidence, dict) else {}
    agent = evidence.get("agent", {}) if isinstance(evidence, dict) else {}
    print(
        f"source={source.get('host', 'UNKNOWN')} "
        f"live_preserved={source.get('live_preserved', 'UNKNOWN')}"
    )
    print(
        f"mode={manifest.get('mode', 'UNKNOWN')} "
        f"writes_started={manifest.get('writes_started', 'UNKNOWN')}"
    )
    for label, item in (("database", db), ("agent", agent)):
        if isinstance(item, dict):
            validated = item.get(
                "data_validation_passed", item.get("auth_validation_passed", "UNKNOWN")
            )
            print(
                f"{label}: encrypted={item.get('encrypted', 'UNKNOWN')} "
                f"restored={item.get('restore_verified', 'UNKNOWN')} "
                f"validated={validated}"
            )
    print("This is manifest-only inventory; no host, DNS, or service was contacted.")


def _print_plan() -> None:
    phases = [
        (
            "Read-only inventory",
            [
                "python3",
                "ops/regional-cutover.py",
                "inventory",
                "--manifest",
                "<sanitized-evidence.json>",
            ],
        ),
        (
            "Read-only source writer inventory after gates",
            [
                "ssh",
                SOURCE,
                (
                    "docker ps --all --no-trunc --filter label=com.docker.compose.project=fitician "
                    "--format '{{.ID}} {{.State}} {{.Names}} {{.Label \"com.docker.compose.service\"}}'"
                ),
            ],
        ),
        (
            "Freeze the two verified APIs after ingress drain",
            [
                "ssh",
                SOURCE,
                "docker",
                "stop",
                "--time",
                "60",
                "VERIFIED_API_ID",
                "VERIFIED_API_2_ID",
            ],
        ),
        (
            "Confirm both APIs exited before draining workers",
            [
                "ssh",
                SOURCE,
                (
                    "docker inspect --format '{{.State.Status}}' VERIFIED_API_ID "
                    "VERIFIED_API_2_ID"
                ),
            ],
        ),
        (
            "Drain and freeze the four verified workers",
            [
                "ssh",
                SOURCE,
                "docker",
                "stop",
                "--time",
                "450",
                "VERIFIED_FOOD_WORKER_ID",
                "VERIFIED_BODY_WORKER_ID",
                "VERIFIED_NOTIFICATION_WORKER_ID",
                "VERIFIED_SCHEDULER_ID",
            ],
        ),
        (
            "Confirm all six writers exited; keep DB, Redis and Agent running",
            [
                "ssh",
                SOURCE,
                (
                    "docker inspect --format '{{.State.Status}}' VERIFIED_API_ID "
                    "VERIFIED_API_2_ID VERIFIED_FOOD_WORKER_ID VERIFIED_BODY_WORKER_ID "
                    "VERIFIED_NOTIFICATION_WORKER_ID VERIFIED_SCHEDULER_ID"
                ),
            ],
        ),
        (
            "Encrypted final PostgreSQL snapshot",
            [
                "ssh",
                SOURCE,
                "FINAL_SYNC=1",
                "FINAL_FREEZE_MANIFEST=/opt/fitician/diagnostics/final-freeze.json",
                "COMPOSE_FILE=/opt/fitician/compose.prod.yaml",
                "COMPOSE_PROJECT_NAME=fitician",
                "BACKUP_ENV_FILE=/opt/fitician/backup.env",
                "bash",
                "/opt/fitician/backup-production.sh",
            ],
        ),
        (
            "Local encrypted snapshot integrity",
            [
                "python3",
                "ops/regional-cutover.py",
                "integrity",
                "--file",
                "<snapshot.dump.age>",
                "--sha256",
                "<expected-sha256>",
            ],
        ),
        (
            "Isolated database restore pipeline",
            [
                "python3",
                "ops/regional-cutover.py",
                "restore-plan",
                "--identity-file",
                "<secure-key-path>",
                "--encrypted-file",
                "<snapshot.dump.age>",
                "--expected-snapshot",
                "<snapshot.json>",
                "--sha256",
                "<expected-sha256>",
                "--restore-container",
                "fitician-regional-restore-run-id",
            ],
        ),
        (
            "Target health after an approved deployment",
            ["bash", "ops/verify-regional.sh"],
        ),
        (
            "Pinned HTTPS probe plan",
            [
                "python3",
                "ops/regional-cutover.py",
                "https-plan",
                "--address",
                "<verified-target-ipv4>",
            ],
        ),
        (
            "Cloudflare DNS patch plan",
            [
                "python3",
                "ops/regional-cutover.py",
                "dns-plan",
                "--snapshot",
                "<sanitized-cloudflare-zone.json>",
                "--target-ipv4",
                "<verified-target-ipv4>",
            ],
        ),
        (
            "Rollback DNS patch plan",
            [
                "python3",
                "ops/regional-cutover.py",
                "dns-rollback-plan",
                "--manifest",
                "<rollback-evidence.json>",
                "--before",
                "<pre-cutover-zone.json>",
                "--current",
                "<current-zone.json>",
            ],
        ),
        (
            "Cutover gate only",
            [
                "python3",
                "ops/regional-cutover.py",
                "validate",
                "--action",
                "cutover",
                "--manifest",
                "<final-evidence.json>",
            ],
        ),
    ]
    print(
        "DRY RUN ONLY. Commands are examples for later operator review; none were executed."
    )
    for title, argv in phases:
        print(f"\n{title}:\n  {shlex.join(argv)}")
    print(
        "DNS write scope: exact owned @, api, www records; preserve MX/TXT/mail "
        "and unrelated records."
    )
    print(
        "Rollback after target writes: freeze target writes, reconcile data, then "
        "consider DNS; DNS-only is unsafe."
    )
    print(
        "No command above was executed. Drain ingress first; replace IDs only with "
        "freshly inventoried IDs and confirm all six show exited before the final dump."
    )


def _restore_pipeline(identity_file: Path, encrypted_file: Path, container: str) -> str:
    if not _restore_container_valid(container):
        raise ValueError("restore target must match fitician-*-restore-*")
    remote_restore = shlex.join(
        ["docker", "exec", "-i", container, "sh", "-c", RESTORE_SCRIPT]
    )
    script = 'age --decrypt --identity "$1" "$2" | ssh -o BatchMode=yes iran "$3"'
    return shlex.join(
        [
            "bash",
            "-o",
            "pipefail",
            "-c",
            script,
            "regional-restore",
            str(identity_file),
            str(encrypted_file),
            remote_restore,
        ]
    )


def _print_restore_plan(args: argparse.Namespace) -> None:
    if not _restore_container_valid(args.restore_container):
        raise ValueError("restore target must match fitician-*-restore-*")
    snapshot = _load_restore_snapshot(args.expected_snapshot)
    if not SHA256.fullmatch(args.sha256):
        raise ValueError("--sha256 must be a lowercase SHA-256 digest")
    inspect_format = (
        "{{.State.Running}}|{{.HostConfig.NetworkMode}}|"
        "{{json .NetworkSettings.Ports}}|{{json .Mounts}}|{{.Config.Image}}"
    )
    inspect = _ssh_command(
        [
            "docker",
            "inspect",
            "--type",
            "container",
            "--format",
            inspect_format,
            args.restore_container,
        ]
    )
    empty_script = 'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "$1"'
    empty = _ssh_command(
        [
            "docker",
            "exec",
            args.restore_container,
            "sh",
            "-c",
            empty_script,
            "regional-empty-check",
            EMPTY_TABLE_SQL,
        ]
    )
    verify_script = 'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "$1"'
    verify = _ssh_command(
        [
            "docker",
            "exec",
            args.restore_container,
            "sh",
            "-c",
            verify_script,
            "regional-verify",
            build_verify_sql(snapshot),
        ]
    )
    print(
        "DRY RUN ONLY. No SSH, decryption, restore, or verification query was executed."
    )
    print(
        "Preflight (requires network=none, no published ports, PostgreSQL 18, "
        "dedicated restore volume):"
    )
    print(shlex.join(inspect))
    print("Volume attachment check (must list only the named restore container):")
    print(
        "The execute path derives the verified volume name from docker inspect "
        "and checks all attachments."
    )
    print("Empty target gate (must return 0 public tables):")
    print(shlex.join(empty))
    print(f"Encrypted SHA-256 expected: {args.sha256}")
    print("Local age identity path (identity bytes stay on this machine):")
    print(str(args.identity_file))
    print(
        "Restore pipeline (destination name must be confirmed explicitly with --execute):"
    )
    print(
        _restore_pipeline(
            args.identity_file, args.encrypted_file, args.restore_container
        )
    )
    print("Post-restore verification query:")
    print(shlex.join(verify))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan", help="print a dry-run operator sequence")
    integrity = sub.add_parser(
        "integrity", help="stream-verify a local encrypted artifact"
    )
    integrity.add_argument("--file", type=Path, required=True)
    integrity.add_argument("--sha256", required=True)
    https = sub.add_parser(
        "https-plan", help="print a pinned HTTPS health probe; does not run it"
    )
    https.add_argument("--domain", default=ZONE)
    https.add_argument("--address", required=True)
    dns = sub.add_parser(
        "dns-plan", help="print exact in-scope Cloudflare updates; never writes"
    )
    dns.add_argument("--snapshot", type=Path, required=True)
    dns.add_argument("--target-ipv4", required=True)
    dns_rollback = sub.add_parser(
        "dns-rollback-plan",
        help="print owned DNS restoration patches after rollback gates",
    )
    dns_rollback.add_argument("--manifest", type=Path, required=True)
    dns_rollback.add_argument("--before", type=Path, required=True)
    dns_rollback.add_argument("--current", type=Path, required=True)
    restore = sub.add_parser(
        "restore-plan", help="print a restore pipeline for an isolated container"
    )
    restore.add_argument("--identity-file", type=Path, required=True)
    restore.add_argument("--encrypted-file", type=Path, required=True)
    restore.add_argument("--expected-snapshot", type=Path, required=True)
    restore.add_argument("--sha256", required=True)
    restore.add_argument("--restore-container", required=True)
    restore.add_argument(
        "--execute", action="store_true", help="execute the guarded restore workflow"
    )
    restore.add_argument(
        "--confirm-target", help="must exactly equal --restore-container when executing"
    )
    inventory = sub.add_parser(
        "inventory", help="display sanitized local evidence only"
    )
    inventory.add_argument("--manifest", type=Path, required=True)
    validate = sub.add_parser(
        "validate", help="validate a cutover or rollback evidence manifest"
    )
    validate.add_argument("--manifest", type=Path, required=True)
    validate.add_argument("--action", choices=("cutover", "rollback"), required=True)
    args = parser.parse_args(argv)
    if args.command == "plan":
        _print_plan()
        return 0
    if args.command == "integrity":
        try:
            digest = check_sha256(args.file, args.sha256)
        except (OSError, ValueError) as exc:
            print(f"INTEGRITY FAILED: {exc}", file=sys.stderr)
            return 1
        print(
            json.dumps(
                {"sha256": digest, "bytes": args.file.stat().st_size, "matched": True}
            )
        )
        return 0
    if args.command == "https-plan":
        try:
            print(shlex.join(https_probe_command(args.domain, args.address)))
        except ValueError as exc:
            print(f"Invalid HTTPS probe: {exc}", file=sys.stderr)
            return 2
        print("Dry run only: this command was not executed.")
        return 0
    if args.command == "dns-plan":
        try:
            plan = plan_dns_updates(_load_manifest(args.snapshot), args.target_ipv4)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            print(f"DNS plan blocked: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    if args.command == "dns-rollback-plan":
        try:
            gate = validate_manifest(_load_manifest(args.manifest), action="rollback")
            if gate:
                raise ValueError("rollback gate blocked: " + "; ".join(gate))
            plan = plan_dns_rollback(
                _load_manifest(args.before), _load_manifest(args.current)
            )
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            print(f"DNS rollback plan blocked: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(plan, indent=2, sort_keys=True))
        print(
            "DNS patches only; this command does not write DNS or reconcile application data."
        )
        return 0
    if args.command == "restore-plan":
        try:
            if not args.execute:
                _print_restore_plan(args)
                return 0
            if args.confirm_target != args.restore_container:
                raise ValueError(
                    "--execute requires --confirm-target to exactly match the restore container"
                )
            result = execute_restore(
                identity_file=args.identity_file,
                encrypted_file=args.encrypted_file,
                expected_snapshot=args.expected_snapshot,
                expected_sha256=args.sha256,
                container=args.restore_container,
                confirmation=args.confirm_target,
            )
        except (
            OSError,
            TypeError,
            ValueError,
            RuntimeError,
            subprocess.SubprocessError,
        ) as exc:
            print(f"Restore plan blocked: {exc}", file=sys.stderr)
            return 2
        if args.execute:
            print(json.dumps(result, sort_keys=True))
            return 0
    try:
        manifest = _load_manifest(args.manifest)
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        print(f"Invalid evidence manifest: {exc}", file=sys.stderr)
        return 2
    if args.command == "inventory":
        errors = validate_manifest(manifest, action="inventory")
        if errors:
            print("Invalid evidence manifest: " + "; ".join(errors), file=sys.stderr)
            return 2
        _inventory(manifest)
        return 0
    errors = validate_manifest(manifest, action=args.action)
    if errors:
        print("BLOCKED: " + "; ".join(errors), file=sys.stderr)
        return 1
    print(
        f"Manifest consistency checks passed for {args.action}; "
        "operator evidence truth and live readiness were not independently verified."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
