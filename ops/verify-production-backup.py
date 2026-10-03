#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import threading
import time
import uuid
from pathlib import Path

parser = argparse.ArgumentParser(
    description="Run an encrypted backup and restore its uploaded object in isolated PostgreSQL."
)
parser.add_argument("--app-dir", type=Path, default=Path("/opt/fitician"))
args = parser.parse_args()
root = args.app_dir.resolve()
qa = root / "diagnostics"
qa.mkdir(mode=0o700, exist_ok=True)
work = qa / "backup-restore-validation"
work.mkdir(mode=0o700, exist_ok=False)
name = "fitician-backup-restore-validation-" + uuid.uuid4().hex[:12]


def run(*a, check=True, **kw):
    return subprocess.run(a, check=check, text=True, capture_output=True, **kw)


def inspect(n):
    return json.loads(run("docker", "inspect", n).stdout)[0]


def cg(field):
    return run("docker", "exec", "fitician-db-1", "cat", "/sys/fs/cgroup/" + field).stdout.strip()


assert not run("docker", "ps", "-aq", "--filter", "name=^/" + name + "$").stdout.strip()
base = inspect("fitician-db-1")
events = cg("memory.events")
stop = threading.Event()
samples = []
monitor_failures = 0


def terminate(_signum, _frame):
    raise SystemExit("Backup validation interrupted; cleaning temporary resources")


signal.signal(signal.SIGTERM, terminate)
signal.signal(signal.SIGINT, terminate)


def monitor():
    global monitor_failures
    while not stop.is_set():
        try:
            current = int(cg("memory.current"))
            swap = int(cg("memory.swap.current"))
            available = (
                int(
                    next(
                        line.split()[1]
                        for line in Path("/proc/meminfo").read_text().splitlines()
                        if line.startswith("MemAvailable:")
                    )
                )
                * 1024
            )
            samples.append((current, swap, available))
        except (subprocess.SubprocessError, OSError, ValueError, StopIteration):
            monitor_failures += 1
        stop.wait(0.2)


t = threading.Thread(target=monitor)
t.start()
try:
    key = work / "restore.agekey"
    run("age-keygen", "-o", str(key))
    recipient = run("age-keygen", "-y", str(key)).stdout.strip()
    bindir = work / "bin"
    bindir.mkdir()
    wrapper = bindir / "age"
    wrapper.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        '/usr/bin/age "$@" -r "$FITICIAN_VERIFY_RECIPIENT" '
        '| tee "$FITICIAN_VERIFY_COPY"\n'
    )
    wrapper.chmod(0o700)
    env = {
        **os.environ,
        "PATH": str(bindir) + ":" + os.environ["PATH"],
        "FITICIAN_VERIFY_RECIPIENT": recipient,
        "FITICIAN_VERIFY_COPY": str(work / "backup.age"),
        "COMPOSE_FILE": str(root / "compose.prod.yaml"),
    }
    result = run("bash", str(root / "backup-production.sh"), env=env, check=False)
    assert result.returncode == 0, (
        "Production backup failed; detailed output withheld to protect data"
    )
    match = re.search(r"verified: (s3://[^ ]+)", result.stdout)
    assert match, "Missing verified remote backup"
    uri = match.group(1)
    # Retrieve exact uploaded bytes with existing protected operator environment.
    download = work / "uploaded.age"
    script = (
        'set -euo pipefail; set -a; . "$FITICIAN_BACKUP_ENV"; set +a; '
        'aws --endpoint-url "$S3_ENDPOINT" s3 cp "$FITICIAN_VERIFIED_URI" '
        '"$FITICIAN_VERIFIED_DEST" --only-show-errors'
    )
    run(
        "bash",
        "-c",
        script,
        env={
            **os.environ,
            "FITICIAN_VERIFIED_URI": uri,
            "FITICIAN_VERIFIED_DEST": str(download),
            "FITICIAN_BACKUP_ENV": str(root / "backup.env"),
        },
    )

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    assert digest(download) == digest(work / "backup.age"), "Uploaded encrypted backup mismatch"
    print("Production backup and uploaded-byte SHA-256: PASS", flush=True)
    available = int(
        next(
            line.split()[1]
            for line in Path("/proc/meminfo").read_text().splitlines()
            if line.startswith("MemAvailable:")
        )
    )
    assert available > (768 + 750) * 1024, "Insufficient safe restore headroom"
    run(
        "docker",
        "run",
        "-d",
        "--name",
        name,
        "--network",
        "none",
        "--memory",
        "768m",
        "--memory-swap",
        "768m",
        "--cpus",
        "0.5",
        "--tmpfs",
        "/var/lib/postgresql:rw,size=16m",
        "-e",
        "PGDATA=/fitician-restore-data",
        "-e",
        "POSTGRES_HOST_AUTH_METHOD=trust",
        "-e",
        "POSTGRES_DB=fitician",
        base["Image"],
    )
    for _ in range(60):
        if run("docker", "exec", name, "pg_isready", "-U", "postgres", check=False).returncode == 0:
            break
        time.sleep(1)
    decrypt = subprocess.Popen(
        ["/usr/bin/age", "-d", "-i", str(key), str(download)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    restore = subprocess.Popen(
        [
            "docker",
            "exec",
            "-i",
            name,
            "pg_restore",
            "-U",
            "postgres",
            "-d",
            "fitician",
            "--exit-on-error",
            "--no-owner",
            "--no-acl",
        ],
        stdin=decrypt.stdout,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    decrypt.stdout.close()
    restore_errors = restore.communicate()[1]
    decrypt_errors = decrypt.communicate()[1]
    if restore.returncode != 0 or decrypt.returncode != 0:
        failed = inspect(name)
        failed_events = run(
            "docker", "exec", name, "cat", "/sys/fs/cgroup/memory.events", check=False
        ).stdout
        error_lines = restore_errors.decode(errors="replace").splitlines()
        error_text = "\n".join(error_lines)
        error_categories = {
            "connectionLost": "server closed" in error_text,
            "diskFull": "No space left" in error_text,
            "archiveInvalid": "valid archive" in error_text,
            "copyFailed": "COPY failed" in error_text,
        }
        print(
            json.dumps(
                {
                    "restoreExit": restore.returncode,
                    "decryptExit": decrypt.returncode,
                    "restoreOomKilled": failed["State"]["OOMKilled"],
                    "restoreMemoryEvents": failed_events,
                    "errorCategories": error_categories,
                }
            ),
            flush=True,
        )
    assert restore.returncode == 0 and decrypt.returncode == 0, (
        "Backup restore failed (data-bearing errors not printed)"
    )
    counts = run(
        "docker",
        "exec",
        name,
        "psql",
        "-X",
        "-U",
        "postgres",
        "-d",
        "fitician",
        "-At",
        "-v",
        "ON_ERROR_STOP=1",
        "-c",
        "SELECT (SELECT count(*) FROM workout_plan_generations), "
        "(SELECT count(*) FROM users), (SELECT version_num FROM alembic_version)",
    ).stdout.strip()
    restore_state = inspect(name)
    restored_events = run("docker", "exec", name, "cat", "/sys/fs/cgroup/memory.events").stdout
    after = inspect("fitician-db-1")
    after_events = cg("memory.events")
    assert (
        after["State"]["StartedAt"] == base["State"]["StartedAt"]
        and after["RestartCount"] == base["RestartCount"]
    )

    def parse_events(text):
        return dict(line.split() for line in text.splitlines())

    assert all(
        parse_events(after_events)[key] == parse_events(events)[key]
        for key in ["oom", "oom_kill", "oom_group_kill"]
    ), "New production DB OOM detected"
    assert not restore_state["State"]["OOMKilled"] and "oom_kill 0" in restored_events
    assert samples and monitor_failures == 0, "Memory monitoring was incomplete"
    assert int(counts.split("|")[1]) > 0, "Restored member database is empty"
    report = {
        "backup": "PASS",
        "uploadedEncryptedBytesMatch": True,
        "encryptedBackupSha256": digest(download),
        "encryptedBackupBytes": download.stat().st_size,
        "remoteBackupUri": uri,
        "restore": "PASS",
        "restoredCountsAndAlembicHead": counts,
        "productionDbNoNewOom": True,
        "productionDbNoRestart": True,
        "productionDbSampledPeakMiB": round(max(s[0] for s in samples) / 1048576, 2),
        "productionDbPeakSwapMiB": round(max(s[1] for s in samples) / 1048576, 2),
        "minimumHostAvailableMiB": round(min(s[2] for s in samples) / 1048576, 2),
        "restoreContainerNoOom": True,
        "memoryReclaimEventsDelta": int(parse_events(after_events)["max"])
        - int(parse_events(events)["max"]),
        "productionEventsBefore": events,
        "productionEventsAfter": after_events,
    }
    (qa / "backup-restore-result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)
finally:
    stop.set()
    t.join()
    run("docker", "rm", "-f", name, check=False)
    shutil.rmtree(work)
