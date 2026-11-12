from uuid import uuid4

import pytest

from app.auth.models import User
from app.debugging.connectors import enroll_connector
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
