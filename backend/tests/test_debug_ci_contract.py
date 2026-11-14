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


def test_failure_evidence_contains_codes_and_test_names_without_private_values(tmp_path):
    xml = tmp_path / "result.xml"
    xml.write_text(
        '<testsuites><testsuite tests="1" failures="1">'
        '<testcase classname="tests.test_bug" name="test_example[private-health-fixture]">'
        '<failure type="AssertionError" message="private-secret-fixture">'
        "private-medical-value</failure></testcase></testsuite></testsuites>"
    )
    result = ci_contract.test_result(xml)
    assert result["failed_tests"] == [
        {"class_name": "tests.test_bug", "name": "test_example", "type": "AssertionError"}
    ]
    assert "private-" not in str(result)
    facts = ci_contract.command_facts(
        "src/issue.tsx(13,2): error TS2307: private-fixture\n"
        "ModuleNotFoundError: No module named 'safe_module'\nprivate-token"
    )
    assert facts == [
        {"code": "TS2307", "file": "src/issue.tsx", "line": 13},
        {"code": "ModuleNotFoundError", "module": "safe_module"},
    ]
    assert "private-" not in str(facts)


def test_ci_report_cannot_add_raw_output_or_fabricate_boolean_test_counts():
    report = {
        "exercised": 3,
        "skipped": 0,
        "failures": 0,
        "failed_tests": [],
        "failed_stage": None,
        "diagnostics": [],
    }
    assert ci_contract.validate_report(report) == report
    for invalid in [
        {**report, "output": "private-fixture"},
        {**report, "exercised": True},
        {**report, "diagnostics": [{"code": "TS2307", "file": "../escape.ts", "line": 1}]},
        {
            **report,
            "diagnostics": [{"code": "ModuleNotFoundError", "module": "private@example.invalid"}],
        },
    ]:
        with pytest.raises(ValueError, match="invalid_validation_report"):
            ci_contract.validate_report(invalid)
