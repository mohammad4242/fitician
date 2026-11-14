from uuid import uuid4

import pytest
from sqlalchemy import delete

from app.auth.models import User
from app.debugging.connectors import enroll_connector
from app.debugging.models import DebugConnectorProbe
from app.debugging.probes import claim_probe, finish_probe, queue_probe


def test_probe_is_scoped_read_only_model_bound_and_revocable(db):
    actor = User(
        id=uuid4(), email="runtime-probe@example.com", password_hash="unused", is_admin=True
    )
    db.add(actor)
    db.flush()
    connector, _ = enroll_connector(db, actor.id, "Laptop")
    connector.capabilities = {
        "repository_head": "a" * 40,
        "models": ["selected-model"],
        "cli_version": "0.167.2",
        "supports_codex": True,
    }
    probe = queue_probe(db, connector, actor.id, "selected-model")
    job = claim_probe(db, connector)
    assert job["model"] == "selected-model"
    assert job["release_commit"] == "a" * 40
    assert claim_probe(db, connector) is None
    with pytest.raises(ValueError, match="probe_model_mismatch"):
        finish_probe(db, connector, probe.id, probe.lease_token, {"model": "substituted-model"})
    actor.is_admin = False
    with pytest.raises(ValueError, match="probe_not_authorized"):
        finish_probe(db, connector, probe.id, probe.lease_token, {"model": "selected-model"})


@pytest.mark.parametrize("running", [False, True])
def test_account_deletion_keeps_probe_audit_but_removes_execution_authority(db, running):
    actor = User(
        email=f"deleted-probe-{uuid4()}@example.com", password_hash="unused", is_admin=True
    )
    db.add(actor)
    db.flush()
    connector, _ = enroll_connector(db, actor.id, "Deletion fixture")
    connector.capabilities = {"repository_head": "b" * 40, "models": ["selected-model"]}
    probe = queue_probe(db, connector, actor.id, "selected-model")
    if running:
        claim_probe(db, connector)
    probe_id, lease = probe.id, probe.lease_token
    db.execute(delete(User).where(User.id == actor.id))
    db.flush()
    db.expire_all()
    retained = db.get(DebugConnectorProbe, probe_id)
    assert retained is not None and retained.actor_id is None
    assert retained.model == "selected-model"
    assert connector.actor_id is None
    if running:
        with pytest.raises(ValueError, match="probe_not_authorized"):
            finish_probe(db, connector, probe_id, lease, {"model": "selected-model"})
    else:
        assert claim_probe(db, connector) is None
        assert retained.state == "failed"


def test_probe_migration_downgrade_preserves_actorless_audit(db):
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect

    actor = User(
        email=f"audit-rollback-{uuid4()}@example.com", password_hash="unused", is_admin=True
    )
    db.add(actor)
    db.flush()
    connector, _ = enroll_connector(db, actor.id, "Rollback fixture")
    connector.capabilities = {"repository_head": "c" * 40, "models": ["selected-model"]}
    probe = queue_probe(db, connector, actor.id, "selected-model")
    db.execute(delete(User).where(User.id == actor.id))
    db.flush()
    source = (
        Path(__file__).parents[1] / "alembic/versions/20261113_182_debug_probe_actor_retention.py"
    )
    spec = importlib.util.spec_from_file_location("probe_retention_migration", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with Operations.context(MigrationContext.configure(db.connection())):
        with pytest.raises(RuntimeError, match="require roll-forward"):
            module.downgrade()
    db.expire_all()
    assert db.get(DebugConnectorProbe, probe.id).actor_id is None
    foreign_key = next(
        key
        for key in inspect(db.connection()).get_foreign_keys("debug_connector_probes")
        if key["referred_table"] == "users"
    )
    assert foreign_key["options"]["ondelete"] == "SET NULL"
