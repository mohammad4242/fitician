"""Agent Service inference + backend authorization + outbound laptop tools."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any, cast
from uuid import UUID

import httpx
from jsonschema import ValidationError, validate
from sqlalchemy import select
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from app.body_analysis.admin_config.service import _agent_service_json
from app.config import Settings

from .catalog import tool_catalog
from .connectors import _authorize_run
from .gateway import call_connector
from .models import DebugRun, DebugRunEvent
from .privacy import sanitize_payload, sanitize_text
from .service import append_event

Inference = Callable[[list[dict[str, str]], list[dict[str, Any]], int], Awaitable[dict[str, Any]]]
Invocation = Callable[[str, dict[str, Any], int], Awaitable[dict[str, Any]]]


def bounded_context(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep the occurrence/policy and latest request; durable history is not deleted."""

    def excerpt(message: dict[str, str], maximum: int) -> dict[str, str]:
        data = message["content"].encode()
        if len(data) <= maximum:
            return dict(message)
        marker = "\n[context excerpt: truncated; request narrowly scoped evidence if needed]"
        content = data[: max(0, maximum - len(marker.encode()))].decode(errors="ignore") + marker
        return {"role": message["role"], "content": content}

    if not messages:
        raise ValueError("invalid_message")
    selected: dict[int, dict[str, str]] = {}
    if messages[0]["role"] == "system":
        selected[0] = excerpt(messages[0], 36000)
    latest_user = next(
        (i for i in range(len(messages) - 1, -1, -1) if messages[i]["role"] == "user"), None
    )
    if latest_user is not None:
        selected[latest_user] = excerpt(messages[latest_user], 24000)
    for index in range(len(messages) - 1, -1, -1):
        if index in selected:
            continue
        used = len(json.dumps(list(selected.values()), ensure_ascii=False).encode())
        remaining = 75000 - used - 100
        if remaining < 300:
            break
        selected[index] = excerpt(messages[index], min(12000, remaining))
    result = [value for _, value in sorted(selected.items())]
    if len(selected) < len(messages):
        result.insert(
            0,
            {
                "role": "system",
                "content": (
                    "[context excerpt: older messages omitted; "
                    "full conversation remains in the panel]"
                ),
            },
        )
    return result


async def tool_loop(
    messages: list[dict[str, str]],
    tools: list[dict[str, Any]],
    infer: Inference,
    invoke: Invocation,
) -> dict[str, Any]:
    catalog = {tool["name"]: tool for tool in tools}
    history = list(messages)
    for step in range(16):
        action = await infer(bounded_context(history), tools, step)
        if action.get("kind") == "diagnosis":
            return action
        name = action.get("tool")
        if action.get("kind") != "tool_call" or not isinstance(name, str) or name not in catalog:
            raise ValueError("tool_not_authorized")
        try:
            arguments = json.loads(action["arguments_json"])
            validate(arguments, catalog[name]["inputSchema"])
        except (ValueError, KeyError, TypeError, ValidationError) as exc:
            raise ValueError("invalid_tool_arguments") from exc
        # Validation precedes dispatch. The durable gateway rechecks the actor,
        # environment, target, lease, cancellation and mutation authority again.
        result = await invoke(name, arguments, step)
        history += [
            {"role": "assistant", "content": json.dumps(action, ensure_ascii=False)},
            {
                "role": "tool",
                "content": sanitize_text(json.dumps(result, ensure_ascii=False), limit=30000),
            },
        ]
    raise ValueError("tool_run_budget_exhausted")


async def run_agent(
    settings: Settings,
    engine: Connection | Engine,
    run_id: UUID,
    lease: UUID,
    config: dict[str, Any],
    messages: list[dict[str, str]],
) -> str:
    caps = config.get("connector_capabilities", {})
    tools = tool_catalog(
        allow_write=config.get("authorized_action") == "prepare_fix",
        supports_tests=bool(caps.get("supports_tests")),
        supports_validation=bool(caps.get("supports_validation")),
        validation_profiles=caps.get("validation_profiles", []),
        supports_github=False,
        supports_ci=bool(caps.get("supports_ci")),
    )
    # Publishing requires a separate human action bound to an exact tested snapshot.
    tools = [
        t
        for t in tools
        if t["name"] not in {"fitician_commit", "fitician_create_pr", "fitician_ci_publish_pr"}
    ]
    async with httpx.AsyncClient(
        trust_env=False, headers={"X-Correlation-ID": str(run_id)}
    ) as client:

        async def infer(
            history: list[dict[str, str]], catalog: list[dict[str, Any]], step: int
        ) -> dict[str, Any]:
            key = f"agent-step-{step}"
            with Session(engine) as db:
                run = db.scalar(select(DebugRun).where(DebugRun.id == run_id).with_for_update())
                if run is None or run.lease_token != lease:
                    raise ValueError("run_lease_lost")
                _authorize_run(db, run)
                receipts = list(
                    db.scalars(
                        select(DebugRunEvent).where(
                            DebugRunEvent.run_id == run_id,
                            DebugRunEvent.kind.in_(["agent_turn_started", "agent_turn_completed"]),
                        )
                    )
                )
                completed = next(
                    (
                        r
                        for r in receipts
                        if r.kind == "agent_turn_completed" and r.payload.get("key") == key
                    ),
                    None,
                )
                if completed:
                    saved = completed.payload["action"]
                    if not isinstance(saved, dict):
                        raise ValueError("provider_invalid_response")
                    return cast(dict[str, Any], saved)
                if any(r.payload.get("key") == key for r in receipts):
                    # An unacknowledged paid inference is an uncertain result,
                    # not permission to repeat actions after a worker restart.
                    raise ValueError("interrupted_call_requires_new_run")
                append_event(
                    db,
                    run,
                    "agent_turn_started",
                    {
                        "key": key,
                        "agent": config["agent_name"],
                        "model": config["agent_model_id"],
                        "profile_id": config["agent_profile_id"],
                    },
                )
                db.commit()
            result = await _agent_service_json(
                client,
                settings=settings,
                method="POST",
                path="/v1/debug/turn",
                timeout_seconds=min(config["timeout_seconds"], 420),
                json_body={
                    "agent": config["agent_name"],
                    "model_id": config["agent_model_id"],
                    "profile_id": config["agent_profile_id"],
                    "profile_fingerprint": config.get("agent_profile_fingerprint"),
                    "messages": history,
                    "tools": catalog,
                    "timeout_seconds": min(config["timeout_seconds"], 420),
                },
            )
            if (
                result.get("model_id") != config["agent_model_id"]
                or result.get("agent") != config["agent_name"]
                or result.get("profile_id") != config["agent_profile_id"]
            ):
                raise ValueError("selected_model_not_available")
            raw_action = result["payload"]
            if not isinstance(raw_action, dict):
                raise ValueError("provider_invalid_response")
            if raw_action.get("kind") == "tool_call":
                raw = json.dumps(raw_action, ensure_ascii=False)
                if sanitize_text(raw, limit=100000) != raw:
                    raise ValueError("sensitive_tool_request_rejected")
            action = sanitize_payload(raw_action)
            if not isinstance(action, dict):
                raise ValueError("provider_invalid_response")
            with Session(engine) as db:
                run = db.scalar(select(DebugRun).where(DebugRun.id == run_id).with_for_update())
                if run is None or run.lease_token != lease:
                    raise ValueError("run_lease_lost")
                _authorize_run(db, run)
                if action.get("kind") == "diagnosis" and action.get("facts"):
                    from .findings import proposal_payload

                    for fact in action["facts"]:
                        proposal_payload(
                            db,
                            run,
                            {
                                "classification": "observed_fact",
                                "text": fact,
                                "evidence_ids": action.get("evidence_ids", []),
                            },
                        )
                append_event(
                    db,
                    run,
                    "agent_turn_completed",
                    {
                        "key": key,
                        "action": action,
                        "service_request_id": sanitize_text(
                            str(result.get("request_id", "")), limit=128
                        ),
                    },
                )
                db.commit()
            return cast(dict[str, Any], action)

        async def invoke(name: str, arguments: dict[str, Any], step: int) -> dict[str, Any]:
            return await call_connector(
                engine, run_id, lease, f"agent-tool-{step}", name, arguments
            )

        diagnosis = await tool_loop(messages, tools, infer, invoke)
    # Structured fields persist in the event; no model assertion confirms cause.
    labels = [
        ("happened", "چه اتفاقی افتاد"),
        ("location", "محل مشاهدهٔ خطا"),
        ("facts", "مشاهدات گزارش‌شده؛ برای تأیید شواهد را بررسی کنید"),
        ("hypotheses", "فرضیه‌ها"),
        ("missing_evidence", "شواهد ناموجود"),
        ("next_checks", "بررسی بعدی"),
        ("evidence_ids", "شناسهٔ شواهد"),
        ("files", "فایل‌های مرتبط"),
        ("tests", "آزمون‌های پیشنهادی"),
    ]
    return "\n\n".join(
        label
        + ": "
        + (
            "\n".join(diagnosis[key])
            if isinstance(diagnosis.get(key), list)
            else str(diagnosis.get(key, "نامشخص"))
        )
        for key, label in labels
    )
