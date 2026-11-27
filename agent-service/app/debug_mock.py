"""Explicit, deterministic debug simulation; never an authenticated Claude model."""

from hashlib import sha256
from typing import TYPE_CHECKING

from .errors import AgentServiceError
from .schemas import AgentModelProfile, AgentName, AgentTaskKind, ErrorCode

if TYPE_CHECKING:
    from .debug_turn import DebugTurnInput, DebugTurnOutput


def mock_profile() -> AgentModelProfile:
    return AgentModelProfile(
        profile_id="claude-mock-debug",
        agent=AgentName.CLAUDE,
        display_name="Claude MOCK — no model execution",
        model_id="mock-claude",
        task_kinds=(AgentTaskKind.DEBUG_AGENT,),
        fingerprint=sha256(b"claude-mock-debug:analysis-only:v1").hexdigest()[:16],
    )


def mock_turn(request: "DebugTurnInput", request_id: str) -> "DebugTurnOutput":
    from .debug_turn import DebugAction, DebugTurnOutput

    profile = mock_profile()
    if (
        request.profile_id != profile.profile_id
        or request.model_id != profile.model_id
        or request.profile_fingerprint != profile.fingerprint
    ):
        raise AgentServiceError(ErrorCode.INVALID_REQUEST, "Claude debugging is MOCK only", 422)
    return DebugTurnOutput(
        payload=DebugAction(
            kind="diagnosis",
            happened="MOCK (Claude): این پاسخ شبیه‌سازی است؛ هیچ مدل یا ابزاری اجرا نشده است.",
            missing_evidence=["تحلیل واقعی، بررسی کد و آزمون در این حالت انجام نمی‌شود."],
            next_checks=["برای بررسی واقعی، Antigravity یا Codex را انتخاب کنید."],
        ).model_dump(),
        agent=AgentName.CLAUDE,
        model_id=profile.model_id,
        profile_id=profile.profile_id,
        execution_mode="mock",
        request_id=request_id,
        input_tokens=0,
        output_tokens=0,
        duration_seconds=0,
    )
