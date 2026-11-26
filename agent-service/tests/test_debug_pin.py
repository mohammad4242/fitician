from pathlib import Path


def test_antigravity_1514_archive_is_pinned_without_changing_other_cli_versions():
    dockerfile = (Path(__file__).parents[1] / "Dockerfile").read_text()
    assert "ARG AGY_VERSION=1.5.14" in dockerfile
    assert (
        "ARG AGY_SHA256_AMD64=d58386322d2073e96b33f7cc32b4e9ae2db6228f58440369725967b2de48c7b5"
        in dockerfile
    )
    assert (
        "ARG AGY_SHA256_ARM64=e5f69a3123fac66974b303d9a201f381a0fb32b3ef869d9139da85d5caf67a2a"
        in dockerfile
    )
    assert "ARG CODEX_VERSION=0.151.0" in dockerfile
    assert "ARG CLAUDE_VERSION=2.1.220" in dockerfile


def test_pinned_cli_cannot_self_update_or_be_replaced_by_runtime_user():
    dockerfile = (Path(__file__).parents[1] / "Dockerfile").read_text()
    final_stage = dockerfile.rsplit("FROM ", 1)[1]
    assert "AGY_CLI_DISABLE_AUTO_UPDATE=true" in final_stage
    assert "CLAUDE_CODE_DISABLE_AUTOUPDATE=1" in final_stage
    assert "chown -R root:root /opt/fitician-agent" in dockerfile
    assert "chmod -R go-w /opt/fitician-agent" in dockerfile
    assert (
        "COPY --from=tools-builder --chown=root:root /opt/fitician-agent /opt/fitician-agent"
        in final_stage
    )
    assert final_stage.index("USER agent") > final_stage.index(
        "COPY --from=tools-builder --chown=root:root /opt/fitician-agent /opt/fitician-agent"
    )
    assert final_stage.index("COPY app ./app") > final_stage.index(
        "COPY --from=tools-builder --chown=root:root /opt/fitician-agent /opt/fitician-agent"
    )


def test_antigravity_subprocess_forces_update_opt_out(tmp_path, monkeypatch):
    from app.runners.antigravity import AntigravityRunner

    monkeypatch.setenv("AGY_CLI_DISABLE_AUTO_UPDATE", "false")
    assert (
        AntigravityRunner(tmp_path)._subprocess_environment()["AGY_CLI_DISABLE_AUTO_UPDATE"]
        == "true"
    )
