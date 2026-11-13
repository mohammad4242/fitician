import subprocess
from uuid import uuid4

import pytest

from app.debugging.tools import RepositoryTools


def repository(path):
    path.mkdir()
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / "bug.py").write_text("def add(a, b):\n    return a - b\n")
    (path / ".env").write_text("PRIVATE_FIXTURE=not-for-export\n")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "-c",
            "user.name=Debug fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "test: seed isolated bug",
        ],
        check=True,
    )
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def test_tools_preserve_checkout_and_reject_secrets_traversal_and_unauthorized_writes(tmp_path):
    original = tmp_path / "original"
    commit = repository(original)
    tools = RepositoryTools.create(
        original, tmp_path / "worktrees", str(uuid4()), commit, allow_write=False
    )
    assert "return a - b" in tools.read_file("bug.py")
    for name in ["../original/.env", ".env", "/etc/passwd", ".git"]:
        with pytest.raises(ValueError):
            tools.read_file(name)
    with pytest.raises(ValueError, match="mutation_not_authorized"):
        tools.write_file("bug.py", "changed")
    assert (original / "bug.py").read_text().endswith("return a - b\n")


def test_repair_changes_only_its_own_worktree(tmp_path):
    original = tmp_path / "original"
    commit = repository(original)
    tools = RepositoryTools.create(
        original, tmp_path / "worktrees", str(uuid4()), commit, allow_write=True
    )
    tools.write_file("bug.py", "def add(a, b):\n    return a + b\n")
    assert "+    return a + b" in tools.diff()
    assert "return a - b" in (original / "bug.py").read_text()


def test_server_workspace_limit_counts_workspaces_not_test_journals(tmp_path):
    original = tmp_path / "original"
    commit = repository(original)
    root = tmp_path / "worktrees"
    first_id = str(uuid4())
    options = {"allow_write": False, "max_workspaces": 2}
    first = RepositoryTools.create(original, root, first_id, commit, **options)
    # Test evidence is not a workspace, and reuse must not consume another slot.
    (root / (first_id + ".tests.json")).write_text("{}")
    assert (
        RepositoryTools.create(original, root, first_id, commit, **options).workspace
        == first.workspace
    )
    RepositoryTools.create(original, root, str(uuid4()), commit, **options)
    with pytest.raises(ValueError, match="workspace_capacity_reached"):
        RepositoryTools.create(original, root, str(uuid4()), commit, **options)


def test_workspace_disk_admission_is_checked_before_git_mutation(tmp_path, monkeypatch):
    from collections import namedtuple

    original = tmp_path / "original"
    commit = repository(original)
    root = tmp_path / "worktrees"
    usage = namedtuple("usage", "total used free")
    monkeypatch.setattr(
        "app.debugging.tools.shutil.disk_usage", lambda _: usage(10**10, 0, 2**30 - 1)
    )
    identifier = str(uuid4())
    with pytest.raises(ValueError, match="workspace_capacity_reached"):
        RepositoryTools.create(
            original, root, identifier, commit, allow_write=False, min_free_bytes=2**30
        )
    assert not (root / (identifier + ".json")).exists()
    assert not (root / identifier).exists()


@pytest.mark.parametrize(
    "options", [{"max_workspaces": 0}, {"max_workspaces": 41}, {"min_free_bytes": 1}]
)
def test_workspace_policy_cannot_disable_capacity_limits(tmp_path, options):
    original = tmp_path / "original"
    commit = repository(original)
    with pytest.raises(ValueError, match="invalid_workspace_capacity_policy"):
        RepositoryTools.create(
            original, tmp_path / "worktrees", str(uuid4()), commit, allow_write=False, **options
        )


def test_seeded_bug_is_repaired_tested_and_committed_in_an_isolated_container(tmp_path):
    import os

    image = os.environ.get("FITICIAN_DEBUG_TEST_IMAGE")
    if not image:
        pytest.skip("An explicitly pinned local test image is required")
    original = tmp_path / "original"
    repository(original)
    (original / "tests").mkdir()
    (original / "tests/test_bug.py").write_text(
        "import unittest\nfrom bug import add\n"
        "class AdditionTest(unittest.TestCase):\n    def test_add(self):\n"
        "        self.assertEqual(add(2, 3), 5)\n"
    )
    subprocess.run(["git", "-C", str(original), "add", "tests/test_bug.py"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(original),
            "-c",
            "user.name=Debug fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "test: exercise isolated addition",
        ],
        check=True,
    )
    commit = subprocess.check_output(
        ["git", "-C", str(original), "rev-parse", "HEAD"], text=True
    ).strip()
    tools = RepositoryTools.create(
        original, tmp_path / "worktrees", str(uuid4()), commit, allow_write=True
    )
    assert not tools.run_python_tests("tests/test_bug.py", image)["passed"]
    tools.write_file("bug.py", "def add(a, b):\n    return a + b\n")
    assert tools.run_python_tests("tests/test_bug.py", image)["passed"]
    fixed = tools.commit_tested_patch("fix(fixture): correct isolated addition")
    assert fixed != commit
    assert "return a - b" in (original / "bug.py").read_text()


def test_cancellation_stops_own_test_container_without_successful_test_evidence(tmp_path):
    import os
    import threading
    import time
    from concurrent.futures import ThreadPoolExecutor

    image = os.environ.get("FITICIAN_DEBUG_TEST_IMAGE")
    if not image:
        pytest.skip("An explicitly pinned local test image is required")
    original = tmp_path / "original"
    commit = repository(original)
    tools = RepositoryTools.create(
        original, tmp_path / "worktrees", str(uuid4()), commit, allow_write=True
    )
    tools.write_file(
        "tests/test_slow.py",
        "import unittest, time\nclass Slow(unittest.TestCase):\n"
        "    def test_wait(self):\n        time.sleep(60)\n",
    )
    cancelled = threading.Event()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            tools.run_python_tests, "tests/test_slow.py", image, cancelled=cancelled
        )
        name = "fitician-debug-test-" + tools.workspace.name
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not future.done():
            running = subprocess.run(
                ["docker", "ps", "-q", "--filter", "name=^/" + name + "$"],
                capture_output=True,
                text=True,
                check=True,
            )
            if running.stdout.strip():
                break
            time.sleep(0.1)
        cancelled.set()
        with pytest.raises(ValueError, match="test_cancelled"):
            future.result(timeout=10)
    assert not subprocess.check_output(
        ["docker", "ps", "-aq", "--filter", "name=^/" + name + "$"], text=True
    ).strip()
    assert tools.test_evidence is None
