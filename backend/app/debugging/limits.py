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
APISetupError = Literal[
    "dedicated_model_credential_required",
    "dedicated_model_credential_invalid",
    "dedicated_model_credential_changed",
    "dedicated_model_spending_policy_required",
    "dedicated_model_rate_state_invalid",
    "provider_unreachable",
    "provider_rejected",
    "provider_rate_limited",
    "provider_invalid_response",
]
API_SETUP_ERRORS = frozenset(get_args(APISetupError))
API_RUN_ERRORS = API_SETUP_ERRORS | {
    "provider_billing_mode_unverified",
    "selected_model_not_available",
    "model_not_configured",
    "provider_timeout",
    "provider_response_too_large",
    "provider_usage_invalid",
    "model_capability_discovery_failed",
    "tool_run_budget_exhausted",
    "repair_executor_not_configured",
    "debug_provider_not_supported",
}
CONNECTOR_BLOCKERS = frozenset(
    {
        "agent_authentication_required",
        "agent_profile_unavailable",
        "native_tool_isolation_unavailable",
        "repository_worker_required",
        "execution_target_offline",
        "pinned_validation_policy_required",
        "validation_policy_unavailable",
        "immutable_validation_image_required",
        "laptop_model_execution_forbidden",
        "workspace_capacity_reached",
        "repository_capacity_reached",
        "exact_release_commit_required",
        "release_commit_not_available",
        "trusted_main_unavailable",
        "workspace_identity_mismatch",
        "workspace_branch_mismatch",
        "workspace_release_mismatch",
        "workspace_not_clean",
        "workspace_branch_not_owned",
        "interrupted_call_requires_new_run",
        *RUNTIME_SETUP_ERRORS,
        "dedicated_model_credential_required",
        "dedicated_model_credential_invalid",
        "dedicated_model_credential_changed",
        "dedicated_model_spending_policy_required",
        "dedicated_model_rate_state_invalid",
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
