#!/usr/bin/env python3
"""Exercise an encrypted backup and failed migration on a disposable Iran-like stack."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
IMAGE = (
    "postgres@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15"
)
SOURCE = "20261018_175"
TARGET = "20261121_187"
WRITERS = (
    "backend",
    "backend-2",
    "scheduler",
    "food-photo-worker",
    "body-analysis-worker",
    "notification-worker",
    "diagnostics-worker",
    "diagnostics-sync-worker",
    "diagnostics-alert-worker",
)

# The AWS CLI fixture implements only the upload, readback, and size checks used
# by backup-production.sh. The database dump, age encryption and SHA checks are real.
AWS_FIXTURE = """#!/usr/bin/env python3
import os, shutil, sys
from pathlib import Path
args = sys.argv[1:]
assert args[:2] == ['--endpoint-url', 'https://isolated.invalid']
assert args[4:][-1] in ('--only-show-errors', 'text')
storage = Path(os.environ['FIXTURE_OBJECTS'])
if args[2:4] == ['s3', 'cp']:
    source, target = args[4:6]
    if source.startswith('s3://fitician-fixture/'):
        shutil.copyfile(storage / Path(source).name, target)
    else:
        assert target.startswith('s3://fitician-fixture/')
        shutil.copyfile(source, storage / Path(target).name)
elif args[2:4] == ['s3api', 'head-object']:
    assert args[args.index('--bucket') + 1] == 'fitician-fixture'
    print((storage / Path(args[args.index('--key') + 1]).name).stat().st_size)
else:
    raise SystemExit('Unsupported fixture command')
"""


FAILING_REVISION = """
from alembic import op

revision = "drill_failed_migration"
down_revision = "20261121_187"


def upgrade():
    with op.get_context().autocommit_block():
        op.execute("CREATE TABLE drill_candidate_write (id integer)")
    op.execute("SELECT 1 / 0")
"""


def run(*args: str | Path, **kwargs: object) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=True, capture_output=True, timeout=240, **kwargs)


def rehearse(work: Path, alembic: Path, age_dir: Path) -> dict:
    work.mkdir(mode=0o700)
    socket = work / "socket"
    socket.mkdir()
    socket.chmod(0o777)
    if len(os.fsencode(socket / ".s.PGSQL.5432")) >= 104:
        raise ValueError("Use a shorter workspace path for the PostgreSQL socket")
    objects = work / "objects"
    objects.mkdir(mode=0o700)
    bin_dir = work / "bin"
    bin_dir.mkdir()
    aws = bin_dir / "aws"
    aws.write_text(AWS_FIXTURE)
    aws.chmod(0o700)
    age = age_dir / "age"
    identity = work / "fixture-identity.txt"
    run(age_dir / "age-keygen", "-o", identity)
    recipient = run(age_dir / "age-keygen", "-y", identity, text=True).stdout.strip()
    shutil.copytree(ROOT / "backend/alembic", work / "alembic")
    shutil.copyfile(ROOT / "backend/alembic.ini", work / "alembic.ini")
    (work / "alembic/versions/drill_failed_migration.py").write_text(FAILING_REVISION)
    project = "fitician-schema-drill-" + uuid4().hex[:12]
    contract = work / "compose.json"
    env_file = work / ".env"
    env_file.touch(mode=0o600)
    writer = r"""
trap 'exit 0' TERM
while true; do
  psql -X -q -v ON_ERROR_STOP=1 -h db -U postgres -d fitician_fixture \
    -c "INSERT INTO drill_writes(service) VALUES ('$DRILL_SERVICE')" || exit 1
  sleep 0.3 &
  wait $!
done
"""
    contract.write_text(
        json.dumps(
            {
                "services": {
                    "db": {
                        "image": IMAGE,
                        "environment": {
                            "POSTGRES_HOST_AUTH_METHOD": "trust",
                            "POSTGRES_DB": "fitician_fixture",
                            "POSTGRES_USER": "postgres",
                            "PGDATA": "/var/lib/postgresql/18/docker",
                        },
                        "tmpfs": ["/var/lib/postgresql"],
                        "volumes": [f"{socket}:/var/run/postgresql"],
                    },
                    "caddy": {"image": IMAGE, "entrypoint": ["sleep", "infinity"]},
                    **{
                        name: {
                            "image": IMAGE,
                            "entrypoint": ["sh", "-c", writer.replace("$", "$$")],
                            "environment": {"DRILL_SERVICE": name},
                        }
                        for name in WRITERS
                    },
                },
                "networks": {"default": {"internal": True}},
            }
        )
    )
    env = {
        "PATH": f"{bin_dir}:{age_dir}:{os.environ['PATH']}",
        "HOME": str(work),
        "FIXTURE_OBJECTS": str(objects),
        "COMPOSE_PROJECT_NAME": project,
        "COMPOSE_FILE": str(contract),
        "FITICIAN_ENV_FILE": str(env_file),
        "DB_BACKUP_AGE_RECIPIENT": recipient,
        "DB_BACKUP_BUCKET": "fitician-fixture",
        "S3_ENDPOINT": "https://isolated.invalid",
        "AWS_ACCESS_KEY_ID": "isolated",
        "AWS_SECRET_ACCESS_KEY": "isolated",
        "AWS_DEFAULT_REGION": "us-east-1",
        "APP_ENV": "test",
        "PYTHONPATH": str(ROOT / "backend"),
        "DATABASE_URL": f"postgresql+psycopg://postgres@/fitician_fixture?host={socket}",
    }
    # Fixed paths and a unique project keep all operations inside this fixture.
    compose = ("docker", "compose", "--project-name", project, "-f", str(contract))

    def sql(statement: str, database: str = "fitician_fixture") -> str:
        return run(
            *compose,
            "exec",
            "-T",
            "db",
            "psql",
            "-XqAt",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "postgres",
            "-d",
            database,
            "-c",
            statement,
            text=True,
        ).stdout.strip()

    def migrate(revision: str) -> None:
        run(alembic, "-c", work / "alembic.ini", "upgrade", revision, env=env, cwd=work)

    def wait_for_writers() -> None:
        for _ in range(50):
            if int(sql("SELECT count(DISTINCT service) FROM drill_writes")) == len(
                WRITERS
            ):
                return
            time.sleep(0.2)
        raise RuntimeError("Not all fixture writers became ready")

    evidence: dict = {}
    try:
        run(*compose, "up", "-d", "--pull", "never", "db")
        for _ in range(50):
            if (
                subprocess.run(
                    (*compose, "exec", "-T", "db", "pg_isready", "-U", "postgres"),
                    check=False,
                    capture_output=True,
                    timeout=5,
                ).returncode
                == 0
            ):
                try:
                    sql("SELECT 1")
                    break
                except subprocess.CalledProcessError:
                    pass
            time.sleep(0.2)
        else:
            raise RuntimeError("Fixture database did not become ready")
        migrate(SOURCE)
        sql(
            "CREATE TABLE drill_writes(id bigint GENERATED ALWAYS AS IDENTITY, service text NOT NULL)"
        )
        sql("CREATE EXTENSION pgcrypto")
        sql(
            "CREATE TABLE drill_payload AS SELECT gen_random_bytes(1024) AS data FROM generate_series(1, 48000)"
        )
        run(*compose, "up", "-d", "--pull", "never", "caddy", *WRITERS)
        wait_for_writers()

        began = time.monotonic()
        run(*compose, "stop", "caddy")
        run(*compose, "stop", *WRITERS)
        assert not run(
            *compose, "ps", "--status", "running", "-q", "caddy", *WRITERS
        ).stdout.strip()
        assert (
            sql(
                "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                "AND pid<>pg_backend_pid() AND backend_type='client backend'"
            )
            == "0"
        )
        frozen = time.monotonic()
        expected = sql(
            "SELECT count(*) || ':' || md5(string_agg(service, ',' ORDER BY id)) FROM drill_writes"
        )
        payload = sql(
            "SELECT count(*) || ':' || md5(string_agg(md5(data), '' ORDER BY md5(data))) FROM drill_payload"
        )

        try:
            backup = run(
                "bash", ROOT / "ops/backup-production.sh", env=env, text=True
            ).stdout
        except subprocess.CalledProcessError as error:
            raise RuntimeError(error.stderr.strip()) from error
        (ciphertext,) = objects.glob("*.dump.age")
        checksum = hashlib.file_digest(ciphertext.open("rb"), "sha256").hexdigest()
        assert checksum in backup and str(ciphertext.stat().st_size) in backup
        backed_up = time.monotonic()

        failure = subprocess.run(
            (alembic, "-c", work / "alembic.ini", "upgrade", "head"),
            check=False,
            env=env,
            cwd=work,
            capture_output=True,
            timeout=240,
            text=True,
        )
        assert failure.returncode != 0 and "division by zero" in failure.stderr
        assert sql("SELECT version_num FROM alembic_version") == TARGET
        assert (
            sql("SELECT to_regclass('drill_candidate_write')")
            == "drill_candidate_write"
        )
        assert not run(
            *compose, "ps", "--status", "running", "-q", "caddy", *WRITERS
        ).stdout.strip()
        failed = time.monotonic()

        sql("CREATE DATABASE fitician_restore", "postgres")
        assert (
            hashlib.file_digest(ciphertext.open("rb"), "sha256").hexdigest() == checksum
        )
        with subprocess.Popen(
            [age, "-d", "-i", identity, ciphertext], stdout=subprocess.PIPE
        ) as decrypt:
            try:
                run(
                    *compose,
                    "exec",
                    "-T",
                    "db",
                    "pg_restore",
                    "--exit-on-error",
                    "--no-owner",
                    "--no-acl",
                    "-U",
                    "postgres",
                    "-d",
                    "fitician_restore",
                    stdin=decrypt.stdout,
                )
            finally:
                assert decrypt.stdout is not None
                decrypt.stdout.close()
            assert decrypt.wait(timeout=10) == 0
        assert (
            sql("SELECT version_num FROM alembic_version", "fitician_restore") == SOURCE
        )
        assert not sql(
            "SELECT to_regclass('drill_candidate_write')", "fitician_restore"
        )
        assert (
            sql(
                "SELECT count(*) || ':' || md5(string_agg(service, ',' ORDER BY id)) FROM drill_writes",
                "fitician_restore",
            )
            == expected
        )
        assert (
            sql(
                "SELECT count(*) || ':' || md5(string_agg(md5(data), '' ORDER BY md5(data))) FROM drill_payload",
                "fitician_restore",
            )
            == payload
        )
        assert (
            sql(
                "SELECT count(*) FROM pg_constraint WHERE contype='f' AND NOT convalidated",
                "fitician_restore",
            )
            == "0"
        )
        sql(
            "BEGIN; ALTER DATABASE fitician_fixture RENAME TO fitician_failed; "
            "ALTER DATABASE fitician_restore RENAME TO fitician_fixture; COMMIT",
            "postgres",
        )
        last_restored_id = sql("SELECT max(id) FROM drill_writes")
        restored = time.monotonic()
        run(*compose, "up", "-d", "--pull", "never", *WRITERS)
        run(*compose, "up", "-d", "--pull", "never", "caddy")
        for _ in range(50):
            if int(
                sql(
                    "SELECT count(DISTINCT service) FROM drill_writes WHERE id > "
                    + last_restored_id
                )
            ) == len(WRITERS):
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("Fixture did not resume writes after restore")
        resumed = time.monotonic()
        evidence = {
            "writer_processes": len(WRITERS),
            "open_sessions_at_freeze": 0,
            "encrypted_bytes": ciphertext.stat().st_size,
            "backup_sha256": checksum,
            "source_revision": SOURCE,
            "candidate_revision": TARGET,
            "restored_revision": SOURCE,
            "row_and_payload_fingerprints_match": True,
            "unvalidated_foreign_keys": 0,
            "alembic_failure_after_durable_schema_change": True,
            "writes_resumed": True,
            "seconds": {
                "drain": round(frozen - began, 2),
                "backup_local_fixture": round(backed_up - frozen, 2),
                "migrate": round(failed - backed_up, 2),
                "restore_and_verify": round(restored - failed, 2),
                "restart": round(resumed - restored, 2),
                "outage_with_restore": round(resumed - began, 2),
            },
        }
    finally:
        run(*compose, "down", "--volumes")
        identity.unlink()
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--alembic", type=Path, required=True)
    parser.add_argument("--age-dir", type=Path, required=True)
    args = parser.parse_args()
    result = rehearse(
        args.work.resolve(), args.alembic.resolve(), args.age_dir.resolve()
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
