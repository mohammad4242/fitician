from uuid import uuid4

import pytest

from app.debugging import ci_contract
from app.debugging.tools import RepositoryTools
from tests.test_debug_tools import repository


def test_snapshot_is_exact_bounded_and_does_not_mutate_the_source_checkout(tmp_path):
    source = tmp_path / "source"
    commit = repository(source)
    tools = RepositoryTools.create(
        source, tmp_path / "work", str(uuid4()), commit, allow_write=True
    )
    tools.write_file("bug.py", "def add(a, b):\n    return a + b\n")
    value = ci_contract.capture_snapshot(tools)
    assert value["base_commit"] == commit
    assert value["files"] == [{"path": "bug.py", "content": "def add(a, b):\n    return a + b\n"}]
    assert value == ci_contract.validate_snapshot(value)
    assert ci_contract.capture_snapshot(tools) == value
    assert "return a - b" in (source / "bug.py").read_text()
    assert tools.tree_digest() == value["tree_digest"]
    tools.write_file("bug.py", "def add(a, b):\n    return a + b + 1\n")
    assert ci_contract.capture_snapshot(tools)["snapshot_digest"] != value["snapshot_digest"]


@pytest.mark.parametrize(
    "path",
    [
        "../escape.py",
        "/root/key.py",
        ".github/workflows/ci.yml",
        "ops/deploy-production.sh",
        "backend/.env",
        "backend/pyproject.toml",
        "frontend/package.json",
        "package-lock.json",
        "compose.prod.iran.yaml",
        "docker/test.py",
        "backend/app/../auth.py",
        "a\\b.py",
    ],
)
def test_privileged_paths_cannot_enter_a_ci_snapshot(path):
    with pytest.raises(ValueError, match="snapshot_path_not_authorized"):
        ci_contract.validate_files([{"path": path, "content": "safe fixture"}])


def test_snapshot_rejects_secret_content_duplicate_paths_and_overflow():
    for files in [
        [{"path": "bug.py", "content": "token=private-token-fixture"}],
        [{"path": "bug.py", "content": "x"}] * 2,
        [{"path": "bug.py", "content": "x" * 131073}],
    ]:
        with pytest.raises(ValueError):
            ci_contract.validate_files(files)


def test_large_source_is_preserved_but_credentials_after_first_chunk_are_rejected():
    content = "# safe source fixture\n" * 2000
    assert (
        ci_contract.validate_files([{"path": "bug.py", "content": content}])[0]["content"]
        == content
    )
    with pytest.raises(ValueError, match="unsafe_or_oversized_snapshot"):
        ci_contract.validate_files(
            [{"path": "bug.py", "content": content + "token=private-fixture"}]
        )


@pytest.mark.parametrize(
    "profile,tests,cwd,command",
    [
        ("backend", ["backend/tests/test_debug_runs.py"], "backend", ["python", "-m", "pytest"]),
        ("agent", ["agent-service/tests/test_api.py"], "agent-service", ["python", "-m", "pytest"]),
        (
            "frontend",
            ["frontend/src/features/diagnostics/DebugConversation.test.tsx"],
            "frontend",
            ["node"],
        ),
        ("migrations", [], "backend", ["python", "-m", "alembic", "upgrade", "head"]),
    ],
)
def test_profiles_use_fixed_commands_and_relative_test_paths(profile, tests, cwd, command):
    value = ci_contract.validation_spec(profile, tests)
    assert value["cwd"] == cwd
    assert value["commands"][0][: len(command)] == command
    assert value["timeout_seconds"] <= 1200
    assert value["network"] in {"none", "isolated_postgres"}


@pytest.mark.parametrize(
    "profile,tests",
    [
        ("shell", []),
        ("backend", ["--override-ini=secret"]),
        ("backend", ["frontend/src/test.ts"]),
        ("agent", ["agent-service/tests/../app/main.py"]),
        ("frontend", ["frontend/src/main.tsx"]),
        ("backend", []),
        ("migrations", ["backend/tests/test_debug_runs.py"]),
    ],
)
def test_model_cannot_select_an_arbitrary_command_or_test_scope(profile, tests):
    with pytest.raises(ValueError, match="validation_profile_not_authorized"):
        ci_contract.validation_spec(profile, tests)
