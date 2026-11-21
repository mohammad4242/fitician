import asyncio
from uuid import uuid4

from app.auth.models import User
from app.debugging.service import claim_run, submit_message
from app.observability.diagnostics_schemas import EventInput
from app.observability.diagnostics_service import record_event


def make_run(db, backend):
    actor = User(
        id=uuid4(), email=f"{uuid4()}@example.invalid", password_hash="unused", is_admin=True
    )
    db.add(actor)
    db.flush()
    event = record_event(
        db,
        EventInput(
            component="api",
            operation=str(uuid4()),
            stage="test",
            platform="backend",
            category="application_bug",
            severity="error",
            error_code="UNHANDLED_EXCEPTION",
            outcome="failure",
        ),
    )
    run = submit_message(db, event.issue_id, actor.id, "inspect this synthetic issue", str(uuid4()))
    run.config_snapshot = {**run.config_snapshot, "execution_backend": backend}
    db.flush()
    return run


def test_remote_dispatch_does_not_claim_api_model_or_another_environment(db):
    from app.debugging.models import DebugThread
    from app.observability.environment import diagnostics_environment

    api = make_run(db, "api")
    foreign = make_run(db, "agent_service")
    db.get(DebugThread, foreign.thread_id).environment = diagnostics_environment() + "-other"
    remote = make_run(db, "agent_service")
    db.flush()
    assert claim_run(db, execution_backend="agent_service").id == remote.id
    assert api.state == "queued" and foreign.state == "queued"
    assert claim_run(db, execution_backend="agent_service") is None


def test_shared_dispatch_is_serial_and_uses_one_connection(monkeypatch, test_settings, tmp_path):
    from types import SimpleNamespace

    from app.debugging import dispatch

    stop = asyncio.Event()
    seen = []
    claims = []

    class DB:
        def __init__(self, *args):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def commit(self):
            pass

    def engine(settings):
        assert settings.db_pool_size == 1 and settings.db_max_overflow == 0
        assert settings.db_pool_timeout_seconds == 1
        return object()

    def claim(db, *, execution_backend):
        assert execution_backend == "agent_service"
        assert len(seen) == len(claims)
        value = SimpleNamespace(id=uuid4(), lease_token=uuid4())
        claims.append(value.id)
        return value

    async def execute(settings, identifier, lease):
        await asyncio.sleep(0)
        seen.append(identifier)
        if len(seen) == 2:
            stop.set()

    monkeypatch.setattr(dispatch, "Session", DB)
    monkeypatch.setattr(dispatch, "get_engine", engine)
    monkeypatch.setattr(dispatch, "claim_run", claim)
    monkeypatch.setattr(dispatch, "execute_run", execute)
    settings = test_settings.model_copy(update={"job_heartbeat_path": tmp_path / "scheduler.json"})
    asyncio.run(dispatch.remote_dispatch_loop(settings, stop_event=stop))
    assert seen == claims and len(seen) == 2


def test_dispatch_failure_does_not_stop_business_scheduler(
    monkeypatch, test_settings, tmp_path, caplog
):
    from app.debugging import dispatch

    stop = asyncio.Event()

    def broken(*args):
        raise RuntimeError("private-data-do-not-log")

    async def wait(*args, **kwargs):
        stop.set()

    monkeypatch.setattr(dispatch, "get_engine", broken)
    monkeypatch.setattr(dispatch, "wait_for_stop", wait)
    settings = test_settings.model_copy(update={"job_heartbeat_path": tmp_path / "scheduler.json"})
    asyncio.run(dispatch.remote_dispatch_loop(settings, stop_event=stop))
    assert "private-data-do-not-log" not in caplog.text


def test_scheduler_hooks_remote_dispatch_only_when_explicitly_enabled(monkeypatch, tmp_path):
    from sqlalchemy import create_engine

    from app.config import Settings
    from app.scheduler import worker

    assert Settings(_env_file=None).debug_remote_dispatch_enabled is False
    started = []

    async def noop(*args, **kwargs):
        pass

    async def dispatch(*args, **kwargs):
        started.append("remote")

    monkeypatch.setattr(worker, "scheduler_loop", noop)
    monkeypatch.setattr(worker, "retention_scheduler_loop", noop)
    monkeypatch.setattr(worker, "sync_agent_service_proxy", noop)
    monkeypatch.setattr(worker, "remote_dispatch_loop", dispatch)
    monkeypatch.setattr(worker, "get_engine", lambda _: create_engine("sqlite://"))
    settings = Settings(
        app_env="test",
        debug_remote_dispatch_enabled=True,
        job_heartbeat_path=tmp_path / "scheduler.json",
        _env_file=None,
    )
    asyncio.run(worker.run_scheduler(settings, stop_event=asyncio.Event()))
    assert started == ["remote"]
