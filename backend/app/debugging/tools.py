"""Laptop-side repository gateway. Model text never becomes a host shell command."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from .privacy import sanitize_text

_ALLOWED_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".md",
    ".css",
    ".html",
    ".sql",
    ".lock",
    ".txt",
}
_DENIED_PARTS = {".git", ".venv", "node_modules", "var", "artifacts", "__pycache__"}
_SECRET = re.compile(
    r"\b(?:sk-|gh[pousr]_)[A-Za-z0-9_-]{12,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
)


def _git(root: Path, *arguments: str) -> str:
    environment = dict(
        os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null", GIT_TERMINAL_PROMPT="0"
    )
    result = subprocess.run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "core.fsmonitor=false",
            "-C",
            str(root),
            *arguments,
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode:
        raise ValueError("repository_operation_failed")
    return result.stdout


class RepositoryTools:
    def __init__(self, workspace: Path, *, allow_write: bool, branch: str) -> None:
        self.workspace = workspace.resolve()
        self.allow_write = allow_write
        self.branch = branch
        journal = self.workspace.parent / (self.workspace.name + ".tests.json")
        self.test_evidence: dict[str, Any] | None = (
            json.loads(journal.read_text()) if journal.is_file() else None
        )

    @classmethod
    def create(
        cls,
        repository: Path,
        workspace_root: Path,
        run_id: str,
        commit: str,
        *,
        allow_write: bool,
        max_workspaces: int = 40,
        min_free_bytes: int = 2_147_483_648,
        evict_readonly: bool = False,
    ) -> RepositoryTools:
        from .workspaces import prepare_workspace

        workspace, branch = prepare_workspace(
            repository,
            workspace_root,
            run_id,
            commit,
            allow_write=allow_write,
            max_workspaces=max_workspaces,
            min_free_bytes=min_free_bytes,
            evict_readonly=evict_readonly,
        )
        return cls(workspace, allow_write=allow_write, branch=branch)

    def safe_path(self, relative: str) -> Path:
        path = Path(relative)
        if (
            path.is_absolute()
            or not path.parts
            or any(
                part in _DENIED_PARTS
                or part in {"..", "."}
                or part.startswith(".env")
                or part.startswith(".codex")
                for part in path.parts
            )
        ):
            raise ValueError("path_not_authorized")
        if (
            path.name in {"auth.json", "credentials.json", "package-lock.json.bak"}
            or path.suffix not in _ALLOWED_SUFFIXES
        ):
            raise ValueError("file_type_not_authorized")
        candidate = self.workspace / path
        if any(
            (self.workspace / Path(*path.parts[:index])).is_symlink()
            for index in range(1, len(path.parts) + 1)
        ):
            raise ValueError("symlink_not_authorized")
        if not candidate.resolve().is_relative_to(self.workspace):
            raise ValueError("path_not_authorized")
        return candidate

    def read_file(self, path: str, start: int = 1, count: int = 120) -> str:
        candidate = self.safe_path(path)
        if (
            candidate.stat().st_size > 2_097_152
            or not 1 <= start <= 100000
            or not 1 <= count <= 200
        ):
            raise ValueError("evidence_bound_exceeded")
        lines = candidate.read_text().splitlines()[start - 1 : start - 1 + count]
        return sanitize_text(
            "\n".join(f"{index + start}: {line[:1000]}" for index, line in enumerate(lines))
        )

    def search_code(self, query: str, prefix: str) -> str:
        if (
            not query
            or len(query) > 100
            or not prefix
            or ".." in Path(prefix).parts
            or Path(prefix).is_absolute()
        ):
            raise ValueError("invalid_search")
        results = []
        for name in _git(self.workspace, "ls-files", "-z", "--", prefix).split("\0"):
            if not name:
                continue
            try:
                path = self.safe_path(name)
                if path.stat().st_size > 524288:
                    continue
                for number, line in enumerate(path.read_text().splitlines(), 1):
                    if query.lower() in line.lower():
                        results.append(f"{name}:{number}: {line[:300]}")
                        if len(results) >= 30:
                            return sanitize_text("\n".join(results))
            except (ValueError, UnicodeError, OSError):
                continue
        return sanitize_text("\n".join(results))

    def write_file(self, path: str, content: str) -> str:
        if not self.allow_write:
            raise ValueError("mutation_not_authorized")
        candidate = self.safe_path(path)
        if len(content.encode()) > 131072 or _SECRET.search(content):
            raise ValueError("unsafe_or_oversized_patch")
        if path.startswith((".github/", "ops/")):
            raise ValueError("privileged_release_files_require_separate_review")
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text(content)
        self.test_evidence = None
        return "file_written"

    def diff(self) -> str:
        return sanitize_text(_git(self.workspace, "diff", "--no-ext-diff", "--no-textconv", "HEAD"))

    def tree_digest(self) -> str:
        digest = hashlib.sha256(
            _git(self.workspace, "diff", "--no-ext-diff", "--no-textconv", "HEAD").encode()
        )
        for name in sorted(
            _git(self.workspace, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
        ):
            if name:
                path = self.safe_path(name)
                digest.update(name.encode())
                digest.update(path.read_bytes())
        return digest.hexdigest()

    def run_python_tests(
        self,
        path: str,
        image: str,
        *,
        timeout: int = 120,
        cancelled: threading.Event | None = None,
    ) -> dict[str, Any]:
        candidate = self.safe_path(path)
        if (
            not candidate.is_file()
            or not candidate.name.startswith("test_")
            or candidate.suffix != ".py"
        ):
            raise ValueError("test_file_required")
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", image):
            raise ValueError("pinned_test_image_required")
        before = self.tree_digest()
        name = "fitician-debug-test-" + self.workspace.name
        command = [
            "docker",
            "run",
            "--rm",
            "--pull=never",
            "--name",
            name,
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "64",
            "--memory",
            "512m",
            "--cpus",
            "1",
            "--user",
            "1000:1000",
            "--mount",
            f"type=bind,src={self.workspace},dst=/workspace,readonly",
            "--tmpfs",
            "/scratch:rw,nosuid,size=64m,mode=1777",
            "--workdir",
            "/workspace",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            "--env",
            "PYTHONPATH=/workspace",
            "--entrypoint",
            "python",
            image,
            "-m",
            "unittest",
            "discover",
            "-s",
            str(Path(path).parent),
            "-p",
            candidate.name,
        ]
        self.test_evidence = None
        for suffix in (".tests.json", ".tested.json"):
            (self.workspace.parent / (self.workspace.name + suffix)).unlink(missing_ok=True)
        if cancelled is not None and cancelled.is_set():
            raise ValueError("test_cancelled")
        with tempfile.TemporaryFile(dir=self.workspace.parent) as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + min(max(timeout, 1), 300)
            try:
                while True:
                    if cancelled is not None and cancelled.is_set():
                        raise ValueError("test_cancelled")
                    if time.monotonic() >= deadline:
                        raise ValueError("test_timeout")
                    if os.fstat(log.fileno()).st_size > 1_048_576:
                        raise ValueError("test_output_limit_exceeded")
                    try:
                        exit_code = process.wait(timeout=0.2)
                        break
                    except subprocess.TimeoutExpired:
                        continue
            finally:
                if process.poll() is None:
                    subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=10)
                    process.terminate()
                    process.wait(timeout=10)
            log.seek(max(0, os.fstat(log.fileno()).st_size - 32000))
            output = sanitize_text(log.read().decode("utf-8", errors="replace"))
        exercised = bool(re.search(r"Ran [1-9][0-9]* tests?", output))
        success = exit_code == 0 and exercised and before == self.tree_digest()
        self.test_evidence = {
            "passed": success,
            "tree_digest": before,
            "image": image,
            "command": command[-9:],
            "output": output,
            "exit_code": exit_code,
        }
        journal = self.workspace.parent / (self.workspace.name + ".tests.json")
        with journal.open("w") as stream:
            os.chmod(journal, 0o600)
            json.dump(self.test_evidence, stream)
        return self.test_evidence

    def commit_tested_patch(self, title: str) -> str:
        if not self.allow_write:
            raise ValueError("mutation_not_authorized")
        if (
            not self.test_evidence
            or not self.test_evidence["passed"]
            or self.test_evidence["tree_digest"] != self.tree_digest()
        ):
            raise ValueError("matching_successful_tests_required")
        names = _git(self.workspace, "diff", "--name-only", "HEAD").splitlines()
        names += [
            name
            for name in _git(
                self.workspace, "ls-files", "--others", "--exclude-standard", "-z"
            ).split("\0")
            if name
        ]
        if not names or len(names) > 30:
            raise ValueError("focused_patch_required")
        for name in names:
            self.safe_path(name)
            if name.startswith((".github/", "ops/")):
                raise ValueError("privileged_release_files_require_separate_review")
            if _SECRET.search((self.workspace / name).read_text()):
                raise ValueError("credential_in_patch")
        if not re.fullmatch(r"(fix|feat|test|refactor)\([A-Za-z0-9_-]+\): [^\r\n]{5,120}", title):
            raise ValueError("specific_commit_title_required")
        _git(self.workspace, "add", "--", *names)
        _git(
            self.workspace,
            "-c",
            "user.name=Fitician debug_agent",
            "-c",
            "user.email=debug-agent@users.noreply.github.com",
            "commit",
            "-m",
            title,
        )
        commit = _git(self.workspace, "rev-parse", "HEAD").strip()
        journal = self.workspace.parent / (self.workspace.name + ".tested.json")
        with journal.open("w") as stream:
            os.chmod(journal, 0o600)
            json.dump({"commit": commit, **self.test_evidence}, stream)
        return commit
