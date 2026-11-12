from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.auth.models import User
from app.body_analysis.admin_config.enums import AITaskType
from app.body_analysis.admin_config.models import AIAgentProfileVerification
from app.body_analysis.admin_config.schemas import AITaskConfigUpdate
from app.body_analysis.admin_config.service import AIConfigError, save_task_config
from app.debugging.connectors import enroll_connector
from app.debugging.runtime_profiles import capabilities


def test_debug_settings_require_current_online_verified_profile_without_touching_generation(
    db, test_settings
):
    actor = User(
        id=uuid4(), email="profile-verification@example.com", password_hash="unused", is_admin=True
    )
    db.add(actor)
    db.flush()
    connector, _ = enroll_connector(db, actor.id, "Laptop")
    connector.last_seen = datetime.now(UTC)
    connector.capabilities = {
        "cli_version": "0.167.2",
        "supports_codex": True,
        "models": ["selected-model"],
    }
    profile = capabilities(db).runners[0].profiles[0]
    assert profile.task_kinds == [AITaskType.DEBUG_AGENT]
    payload = AITaskConfigUpdate(
        execution_backend="agent_service",
        agent_name="codex",
        agent_model_id=profile.model_id,
        agent_profile_id=profile.profile_id,
        enabled=True,
    )
    with pytest.raises(AIConfigError, match="must pass"):
        save_task_config(
            db,
            task_type=AITaskType.DEBUG_AGENT,
            payload=payload,
            actor=actor,
            settings=test_settings,
        )
    db.add(
        AIAgentProfileVerification(
            profile_id=profile.profile_id,
            task_type=AITaskType.DEBUG_AGENT,
            profile_fingerprint=profile.fingerprint,
            status="passed",
            checked_at=datetime.now(UTC),
        )
    )
    db.flush()
    saved = save_task_config(
        db, task_type=AITaskType.DEBUG_AGENT, payload=payload, actor=actor, settings=test_settings
    )
    assert saved.agent_model_id == "selected-model"
    connector.revoked = True
    db.flush()
    with pytest.raises(AIConfigError, match="must be online"):
        save_task_config(
            db,
            task_type=AITaskType.DEBUG_AGENT,
            payload=payload,
            actor=actor,
            settings=test_settings,
        )
