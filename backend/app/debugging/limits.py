"""Shared declared limits; reject unsupported settings instead of silently clamping."""

from typing import Any, Literal, get_args

MIN_TIMEOUT = 10
MAX_TIMEOUT = 600
MIN_API_TOKENS = 128
MAX_API_TOKENS = 16384
RuntimeSetupError = Literal[
    "dedicated_codex_authentication_required",
    "unsupported_codex_protocol_version",
    "dedicated_codex_home_must_be_private",
    "dedicated_codex_home_configuration_not_allowed",
    "project_runtime_configuration_not_allowed",
    "codex_discovery_failed",
    "codex_discovery_timeout",
]
RUNTIME_SETUP_ERRORS = frozenset(get_args(RuntimeSetupError))
CONNECTOR_BLOCKERS = frozenset(
    {
        "workspace_capacity_reached",
        "repository_capacity_reached",
        "exact_release_commit_required",
        "release_commit_not_available",
        "workspace_identity_mismatch",
        "workspace_branch_mismatch",
        "workspace_release_mismatch",
        "workspace_not_clean",
        "workspace_branch_not_owned",
        "interrupted_call_requires_new_run",
        *RUNTIME_SETUP_ERRORS,
    }
)


def validate_runtime_config(config: dict[str, Any]) -> None:
    timeout = config.get("timeout_seconds", 420)
    if type(timeout) is not int or not MIN_TIMEOUT <= timeout <= MAX_TIMEOUT:
        raise ValueError("debug_runtime_options_unsupported")
    if config.get("execution_backend", "api") == "api":
        tokens = config.get("max_output_tokens", 4096)
        if type(tokens) is not int or not MIN_API_TOKENS <= tokens <= MAX_API_TOKENS:
            raise ValueError("debug_runtime_options_unsupported")
