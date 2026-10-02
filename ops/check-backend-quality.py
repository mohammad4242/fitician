#!/usr/bin/env python3
"""Run whole-domain quality checks, refusing new debt relative to the CI base SHA.

The repository has pre-existing Ruff/mypy/format debt outside its current typing
check scope. Report it explicitly; do not allow a release to increase it.
"""

from __future__ import annotations

import argparse
import collections
import io
import json
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def diagnostics(kind: str, text: str) -> collections.Counter:
    if kind == "ruff":
        return collections.Counter(
            (item["filename"].split("/app/", 1)[-1], item["code"], item["message"])
            for item in json.loads(text)
        )
    if kind == "format":
        return collections.Counter(
            item["filename"].split("/app/", 1)[-1] for item in json.loads(text)
        )
    return collections.Counter(
        re.sub(r":\d+(?::\d+)?: ", ": ", line) for line in text.splitlines() if ": error:" in line
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--domains", required=True, help="JSON array")
    args = parser.parse_args()
    domains = json.loads(args.domains)
    if not domains or not all(re.fullmatch("[a-z_]+", value) for value in domains):
        raise SystemExit("Invalid backend quality scope")
    uv_bin = ROOT / "backend/.venv/bin"
    directories = ["app/" + domain for domain in domains]
    scratch = ROOT / ".ci-scratch"
    scratch.mkdir(exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            base_root = Path(directory)
            archive = subprocess.check_output(["git", "archive", args.base, "backend"], cwd=ROOT)
            with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                tar.extractall(base_root, filter="data")
            checks = {
                "ruff": [
                    str(uv_bin / "ruff"),
                    "check",
                    "--output-format",
                    "json",
                    *directories,
                ],
                "format": [
                    str(uv_bin / "ruff"),
                    "format",
                    "--check",
                    "--output-format=json",
                    *directories,
                ],
                "mypy": [
                    str(uv_bin / "mypy"),
                    "--follow-imports=silent",
                    "--no-incremental",
                    *directories,
                ],
            }
            failed = False
            for name, command in checks.items():
                before = subprocess.run(
                    command, cwd=base_root / "backend", capture_output=True, text=True
                )
                after = subprocess.run(
                    command, cwd=ROOT / "backend", capture_output=True, text=True
                )
                if before.returncode not in (0, 1) or after.returncode not in (0, 1):
                    raise SystemExit(f"{name} could not complete: {after.stderr or before.stderr}")
                old = diagnostics(
                    name,
                    before.stdout if name in ("ruff", "format") else before.stdout + before.stderr,
                )
                new = diagnostics(
                    name,
                    after.stdout if name in ("ruff", "format") else after.stdout + after.stderr,
                )
                if after.returncode and not new:
                    raise SystemExit(
                        f"{name} failed without recognizable diagnostics: "
                        f"{after.stdout}{after.stderr}"
                    )
                added = new - old
                print(
                    f"{name}: existing diagnostics={sum(old.values())}; "
                    f"current={sum(new.values())}; new={sum(added.values())}"
                )
                for diagnostic, count in added.items():
                    print(f"NEW ({count}): {diagnostic}")
                failed |= bool(added)
            if failed:
                raise SystemExit("Backend quality regressed; release blocked")
    finally:
        # Keep all temporary artifacts inside the workspace, leaving no empty directory.
        try:
            scratch.rmdir()
        except OSError:
            pass


if __name__ == "__main__":
    main()
