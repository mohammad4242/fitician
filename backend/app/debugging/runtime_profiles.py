"""Explicit local connector profiles, isolated from generation runner capabilities."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.body_analysis.admin_config.enums import AIAgentName, AITaskType
from app.body_analysis.admin_config.schemas import (
    AgentServiceCapabilitiesResponse,
    AgentServiceModelProfile,
    AgentServiceRunnerCapability,
)
from app.observability.environment import diagnostics_environment

from .appserver import SUPPORTED_VERSIONS
from .models import DebugConnector


def connected_connectors(db: Session) -> list[DebugConnector]:
    return list(
        db.scalars(
            select(DebugConnector)
            .join(User, User.id == DebugConnector.actor_id)
            .where(
                DebugConnector.environment == diagnostics_environment(),
                DebugConnector.revoked.is_(False),
                DebugConnector.last_seen >= datetime.now(UTC) - timedelta(seconds=30),
                User.is_admin.is_(True),
            )
        )
    )


def profile_id(connector: DebugConnector, model: str) -> str:
    return f"connector:{connector.id}:{hashlib.sha256(model.encode()).hexdigest()[:16]}"


def connector_for_profile(
    db: Session, profile: str | None, model: str | None, *, include_offline: bool = False
) -> DebugConnector | None:
    if include_offline:
        parts = (profile or "").split(":")
        if len(parts) != 3 or parts[0] != "connector":
            return None
        candidates = [authorized_target(db, parts[1])]
    else:
        candidates = connected_connectors(db)
    for connector in candidates:
        if connector.capabilities.get(
            "cli_version"
        ) not in SUPPORTED_VERSIONS or not connector.capabilities.get("supports_codex"):
            continue
        if (
            model in connector.capabilities.get("models", [])
            and profile_id(connector, model or "") == profile
        ):
            return connector
    return None


def capabilities(db: Session) -> AgentServiceCapabilitiesResponse:
    profiles = []
    for connector in connected_connectors(db):
        if connector.capabilities.get(
            "cli_version"
        ) not in SUPPORTED_VERSIONS or not connector.capabilities.get("supports_codex"):
            continue
        for model in connector.capabilities.get("models", []):
            profiles.append(
                AgentServiceModelProfile(
                    profile_id=profile_id(connector, model),
                    agent=AIAgentName.CODEX,
                    model_id=model,
                    display_name=f"{connector.name} · {model}",
                    task_kinds=[AITaskType.DEBUG_AGENT],
                    fingerprint=hashlib.sha256(
                        json.dumps(
                            {
                                "connector_id": str(connector.id),
                                "model": model,
                                **execution_capabilities(connector),
                            },
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode()
                    ).hexdigest(),
                    supports_text_input=True,
                    supports_image_input=False,
                    supports_structured_output=False,
                )
            )
    return AgentServiceCapabilitiesResponse(
        runners=[
            AgentServiceRunnerCapability(
                agent=AIAgentName.CODEX,
                installed=bool(profiles),
                auth_state="authenticated" if profiles else "unknown",
                profiles=profiles,
            )
        ]
    )


def snapshot_connector(db: Session, config: dict[str, Any]) -> str | None:
    if config.get("execution_backend") == "agent_service":
        connector = connector_for_profile(
            db, config.get("agent_profile_id"), config.get("agent_model_id"), include_offline=True
        )
        return str(connector.id) if connector else None
    identifier = config.get("debug_connector_id")
    return str(authorized_target(db, identifier).id) if identifier else None


def authorized_target(db: Session, identifier: UUID | str) -> DebugConnector:
    target = db.scalar(
        select(DebugConnector)
        .join(User, User.id == DebugConnector.actor_id)
        .where(
            DebugConnector.id == UUID(str(identifier)),
            DebugConnector.environment == diagnostics_environment(),
            DebugConnector.repository == "mohammad4242/fitician",
            DebugConnector.revoked.is_(False),
            User.is_admin.is_(True),
        )
    )
    if target is None:
        raise ValueError("execution_target_not_authorized")
    # Offline is a visible blocked step, never permission to select another machine.
    return target


def execution_capabilities(connector: DebugConnector) -> dict[str, Any]:
    return {
        "cli_version": connector.capabilities.get("cli_version"),
        "runtime_revision": connector.capabilities.get("runtime_revision"),
        "supports_tests": bool(connector.capabilities.get("supports_tests")),
        "supports_github": bool(connector.capabilities.get("supports_github")),
    }
