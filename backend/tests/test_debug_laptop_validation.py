import pytest

from app.debugging.catalog import tool_catalog
from app.debugging.tools import RepositoryTools
from tests.test_debug_tools import repository


def test_laptop_validation_uses_trusted_profiles_and_binds_exact_patch(tmp_path, monkeypatch):
    from app.debugging.laptop_validation import run_validation

    repo = tmp_path / "source"
    commit = repository(repo)
    tools = RepositoryTools.create(
        repo, tmp_path / "worktrees", str(__import__("uuid").uuid4()), commit, allow_write=True
    )
    tools.write_file("bug.py", "def add(a,b): return a+b\n")

    def sandbox(candidate, image, profile, tests, output, policy_sha, **kwargs):
        assert candidate != tools.workspace
        assert (candidate / "bug.py").read_text() == "def add(a,b): return a+b\n"
        assert not (candidate / ".env").exists()
        assert image == "sha256:" + "a" * 64 and profile == "backend"
        return {"passed": True, "exit_code": 0, "exercised": 1, "failures": 0}

    from app.debugging.laptop_validation import load_policy

    _, extract_source = load_policy()
    monkeypatch.setattr(
        "app.debugging.laptop_validation.load_policy", lambda: (sandbox, extract_source)
    )
    result = run_validation(
        tools, "backend", ["backend/tests/test_example.py"], "sha256:" + "a" * 64, "b" * 40
    )
    assert result["passed"] and result["tree_digest"] == tools.tree_digest()
    assert (repo / "bug.py").read_text().endswith("return a - b\n")
    with pytest.raises(ValueError, match="validation_profile_not_authorized"):
        run_validation(tools, "shell", ["id"], "sha256:" + "a" * 64, "b" * 40)


def test_validation_tool_is_exposed_only_for_enrolled_laptop_policy():
    ordinary = {t["name"] for t in tool_catalog(allow_write=False)}
    assert "fitician_validate" not in ordinary
    configured = {t["name"] for t in tool_catalog(allow_write=True, supports_validation=True)}
    assert "fitician_validate" in configured


def test_laptop_catalog_advertises_only_configured_validation_profiles():
    selected = next(
        t
        for t in tool_catalog(
            allow_write=True, supports_validation=True, validation_profiles=["backend"]
        )
        if t["name"] == "fitician_validate"
    )
    assert selected["inputSchema"]["properties"]["profile"]["enum"] == ["backend"]
