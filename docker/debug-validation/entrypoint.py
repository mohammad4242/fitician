"""Trusted image policy. Candidate code runs only in child processes inside this sandbox."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/policy")
from app.debugging.ci_contract import command_facts, test_result, validation_spec

profile, tests = sys.argv[1:]
spec = validation_spec(profile, json.loads(tests))
workspace = Path("/workspace")
shutil.copytree("/source", workspace, dirs_exist_ok=True, symlinks=False)
commands = []
if spec["cwd"] == "frontend":
    (workspace / "node_modules").symlink_to(
        "/deps/node_modules", target_is_directory=True
    )
    for relative in ("frontend", "packages/fitician-core"):
        dependencies = Path("/deps") / relative / "node_modules"
        if dependencies.is_dir():
            (workspace / relative / "node_modules").symlink_to(
                dependencies, target_is_directory=True
            )
    commands.append((workspace, ["python3", "frontend/scripts/export-exercises.py"]))
    commands.append(
        (
            workspace,
            [
                "node",
                "/policy/node-tool.cjs",
                "typescript",
                "-p",
                "packages/fitician-core/tsconfig.json",
            ],
        )
    )
    executable_path = "/usr/local/bin:/usr/bin:/bin"
else:
    executable_path = "/deps/" + spec["cwd"] + "/.venv/bin:/usr/local/bin:/usr/bin:/bin"
commands.extend((workspace / spec["cwd"], command) for command in spec["commands"])
# No host environment, provider credentials, auth session, GitHub token or Sentry token.
environment = {
    "PATH": executable_path,
    "HOME": "/scratch",
    "APP_ENV": "test",
    "PYTHONDONTWRITEBYTECODE": "1",
    "SENTRY_DSN": "",
    "SENTRY_TRACES_SAMPLE_RATE": "0",
    "PYTHONPATH": str(workspace / spec["cwd"]),
    "XDG_CACHE_HOME": "/scratch/cache",
    "MPLCONFIGDIR": "/scratch/matplotlib",
}
for key in ("DATABASE_URL", "TEST_DATABASE_URL"):
    if key in os.environ:
        environment[key] = os.environ[key]
exit_code = 0
for stage, (cwd, command) in enumerate(commands):
    with Path("/output/test.log").open("wb") as log:
        result = subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            check=False,
            stdout=log,
            stderr=log,
            timeout=spec["timeout_seconds"],
        )
    if result.returncode:
        exit_code = result.returncode
        break
report = test_result(Path("/output/results.xml"))
report["failed_stage"] = stage if exit_code else None
report["diagnostics"] = (
    command_facts(Path("/output/test.log").read_text(errors="replace"))
    if exit_code
    else []
)
print(json.dumps(report), flush=True)
raise SystemExit(
    exit_code or (1 if not report["exercised"] or report["failures"] else 0)
)
