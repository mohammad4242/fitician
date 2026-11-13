from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.auth.models import User
from app.body_analysis.admin_config.enums import AITaskType
from app.body_analysis.admin_config.models import AIAgentProfileVerification
from app.body_analysis.admin_config.schemas import AITaskConfigUpdate
from app.body_analysis.admin_config.service import AIConfigError, save_task_config
from app.debugging.connectors import enroll_connector
from app.debugging.runtime_profiles import capabilities, snapshot_connector


def target_fixture(db, name="Germany"):
    actor = User(
        id=uuid4(), email=f"target-{uuid4()}@example.invalid", password_hash="unused", is_admin=True
    )
    db.add(actor)
    db.flush()
    target, _ = enroll_connector(db, actor.id, name)
    target.last_seen = datetime.now(UTC)
    db.flush()
    return actor, target


def test_profile_verification_is_invalidated_when_execution_authority_changes(db):
    _, target = target_fixture(db)
    target.capabilities = {
        "cli_version": "0.167.2",
        "supports_codex": True,
        "models": ["chosen"],
        "supports_tests": False,
    }
    first = capabilities(db).runners[0].profiles[0].fingerprint
    target.capabilities = {**target.capabilities, "supports_tests": True}
    assert capabilities(db).runners[0].profiles[0].fingerprint != first


def test_api_execution_target_is_never_implicitly_chosen(db):
    target_fixture(db)
    assert snapshot_connector(db, {"execution_backend": "api"}) is None


def test_selected_api_target_is_retained_when_offline_without_laptop_substitution(db):
    _, server = target_fixture(db)
    target_fixture(db, "Laptop")
    server.last_seen = None
    db.flush()
    assert snapshot_connector(
        db, {"execution_backend": "api", "debug_connector_id": str(server.id)}
    ) == str(server.id)


def test_execution_target_cannot_cross_environment_or_revocation_boundary(db):
    _, target = target_fixture(db)
    environment = target.environment
    target.environment = "another-environment"
    db.flush()
    with pytest.raises(ValueError, match="execution_target_not_authorized"):
        snapshot_connector(db, {"execution_backend": "api", "debug_connector_id": str(target.id)})
    target.environment = environment
    target.revoked = True
    with pytest.raises(ValueError, match="execution_target_not_authorized"):
        snapshot_connector(db, {"execution_backend": "api", "debug_connector_id": str(target.id)})


def test_api_execution_target_persists_only_in_debug_agent_settings(db, test_settings):
    actor, target = target_fixture(db)
    payload = AITaskConfigUpdate(enabled=False, debug_connector_id=target.id)
    saved = save_task_config(
        db, task_type=AITaskType.DEBUG_AGENT, payload=payload, actor=actor, settings=test_settings
    )
    assert saved.debug_connector_id == target.id
    with pytest.raises(AIConfigError, match="only supported for debug_agent"):
        save_task_config(
            db,
            task_type=AITaskType.WORKOUT_PLAN_GENERATION,
            payload=payload,
            actor=actor,
            settings=test_settings,
        )


def test_selected_codex_profile_keeps_its_offline_target_in_run_provenance(db):
    from app.debugging.runtime_profiles import profile_id

    _, target = target_fixture(db)
    target.last_seen = None
    target.capabilities = {"cli_version": "0.167.2", "supports_codex": True, "models": ["chosen"]}
    db.flush()
    assert snapshot_connector(
        db,
        {
            "execution_backend": "agent_service",
            "agent_model_id": "chosen",
            "agent_profile_id": profile_id(target, "chosen"),
        },
    ) == str(target.id)


def test_saved_execution_target_has_database_scope_and_downgrade_guards(db, test_settings):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    actor, target = target_fixture(db)
    save_task_config(
        db,
        task_type=AITaskType.DEBUG_AGENT,
        payload=AITaskConfigUpdate(enabled=False, debug_connector_id=target.id),
        actor=actor,
        settings=test_settings,
    )
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(
            text(
                "UPDATE ai_task_configs SET task_type='workout_plan_generation' "
                "WHERE task_type='debug_agent'"
            )
        )
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path

    spec = spec_from_file_location(
        "debug_target_migration",
        Path(__file__).parents[1] / "alembic/versions/20261113_183_debug_execution_target.py",
    )
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    with (
        Operations.context(MigrationContext.configure(db.connection())),
        pytest.raises(RuntimeError, match="Clear the selected debug target"),
    ):
        migration.downgrade()
    assert (
        db.scalar(
            text("SELECT debug_connector_id FROM ai_task_configs WHERE task_type='debug_agent'")
        )
        == target.id
    )


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
