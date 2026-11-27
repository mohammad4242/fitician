import asyncio
from datetime import UTC, datetime

from app.config import Settings
from app.jobs.heartbeat import heartbeat_is_healthy


def test_shared_roles_reuse_scheduler_and_default_to_disabled(monkeypatch, tmp_path):
    from app.scheduler import worker

    assert Settings(_env_file=None).diagnostics_maintenance_enabled is False
    started = []

    async def maintenance(settings, stop_event):
        started.append("maintenance")

    monkeypatch.setattr(worker, "diagnostics_maintenance_loop", maintenance)

    async def noop(*args, **kwargs):
        pass

    monkeypatch.setattr(worker, "scheduler_loop", noop)
    monkeypatch.setattr(worker, "retention_scheduler_loop", noop)
    monkeypatch.setattr(worker, "sync_agent_service_proxy", noop)
    from sqlalchemy import create_engine

    monkeypatch.setattr(worker, "get_engine", lambda _: create_engine("sqlite://"))
    settings = Settings(
        app_env="test",
        diagnostics_maintenance_enabled=True,
        job_heartbeat_path=tmp_path / "scheduler.json",
        _env_file=None,
    )
    asyncio.run(worker.run_scheduler(settings, stop_event=asyncio.Event()))
    assert started == ["maintenance"]


def test_missing_sync_configuration_does_not_activate_sms_or_fake_heartbeat(tmp_path):
    from app.observability.maintenance import Maintenance

    settings = Settings(
        app_env="test", job_heartbeat_path=tmp_path / "scheduler.json", _env_file=None
    )
    with Maintenance(settings, environ={}) as maintenance:
        maintenance.tick()
        assert maintenance.states == {
            "diagnostics-sync-worker": "unconfigured",
            "diagnostics-alert-worker": "disabled",
        }
    assert not list(tmp_path.glob("diagnostics-*.json"))


def test_sync_failure_does_not_starve_alerts_or_report_sync_healthy(monkeypatch, tmp_path):
    from app.observability.maintenance import Maintenance

    settings = Settings(
        app_env="test",
        diagnostics_alert_enabled=True,
        diagnostics_alert_enabled_at=datetime.now(UTC),
        job_heartbeat_path=tmp_path / "scheduler.json",
        _env_file=None,
    )
    seen = []

    def broken(*args):
        raise RuntimeError("private-data-must-not-be-logged")

    monkeypatch.setattr(Maintenance, "sync_once", broken)
    monkeypatch.setattr(Maintenance, "alert_once", lambda *_: seen.append("alert"))
    with Maintenance(
        settings,
        environ={
            "SENTRY_ORG": "test",
            "SENTRY_PROJECT": "backend",
            "SENTRY_API_TOKEN": "synthetic",
        },
    ) as maintenance:
        maintenance.tick()
        assert seen == ["alert"]
        assert maintenance.states["diagnostics-sync-worker"] == "unavailable"
        assert heartbeat_is_healthy(
            tmp_path / "diagnostics-alert-worker.json",
            max_age_seconds=30,
            expected_service="diagnostics-alert-worker",
        )
        assert not (tmp_path / "diagnostics-sync-worker.json").exists()


def test_sentry_authorization_never_reaches_sms_client(tmp_path):
    from app.observability.maintenance import Maintenance

    settings = Settings(
        app_env="test", job_heartbeat_path=tmp_path / "scheduler.json", _env_file=None
    )
    with Maintenance(settings, environ={"SENTRY_API_TOKEN": "synthetic"}) as maintenance:
        assert maintenance.sync_client.headers["Authorization"] == "Bearer synthetic"
        assert "Authorization" not in maintenance.sms_client.headers


def test_heartbeat_write_failure_does_not_stop_business_scheduler(monkeypatch, tmp_path):
    from app.observability import maintenance as module

    settings = Settings(
        app_env="test", job_heartbeat_path=tmp_path / "scheduler.json", _env_file=None
    )

    def broken(*args, **kwargs):
        raise OSError("synthetic disk error")

    monkeypatch.setattr(module.Maintenance, "sync_once", lambda *_: None)
    monkeypatch.setattr(module, "write_heartbeat", broken)
    with module.Maintenance(
        settings,
        environ={
            "SENTRY_ORG": "test",
            "SENTRY_PROJECT": "backend",
            "SENTRY_API_TOKEN": "synthetic",
        },
    ) as maintenance:
        maintenance.tick()
        assert maintenance.states["diagnostics-sync-worker"] == "unavailable"


def test_bad_maintenance_configuration_does_not_terminate_scheduler(monkeypatch):
    from app.observability import maintenance as module

    class Broken:
        def __init__(self, *_args):
            raise ValueError("private proxy configuration")

    monkeypatch.setattr(module, "Maintenance", Broken)

    async def run():
        stop = asyncio.Event()
        asyncio.get_running_loop().call_later(0.01, stop.set)
        await asyncio.wait_for(
            module.diagnostics_maintenance_loop(Settings(_env_file=None), stop_event=stop), 1
        )

    asyncio.run(run())
