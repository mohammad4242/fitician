from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Iterator[None]:
    """Keep this process-isolated mapper test independent from the database."""
    yield


@pytest.mark.parametrize(
    "module_name",
    (
        "app.body_analysis.worker",
        "app.nutrition.food_photo_worker",
        "app.notifications.worker",
        "app.scheduler.worker",
    ),
)
def test_worker_registers_models_before_starting_diagnostics(module_name: str) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    script = f'''
import asyncio
import contextlib
import importlib
import threading
from sqlalchemy.orm import configure_mappers
from app.config import Settings

worker = importlib.import_module("{module_name}")
worker.install_diagnostic_log_bridge = lambda _settings: configure_mappers()
worker.get_engine = lambda _settings: None

@contextlib.asynccontextmanager
async def async_heartbeat(*_args, **_kwargs):
    yield

@contextlib.contextmanager
def threaded_heartbeat(*_args, **_kwargs):
    yield

if hasattr(worker, "async_heartbeat"):
    worker.async_heartbeat = async_heartbeat
if hasattr(worker, "threaded_heartbeat"):
    worker.threaded_heartbeat = threaded_heartbeat

settings = Settings(
    app_env="test",
    database_url="sqlite://",
    job_heartbeat_path="unused-heartbeat.json",
    notification_fcm_enabled=False,
    notification_apns_enabled=False,
    _env_file=None,
)

if "scheduler" in "{module_name}":
    class EmptySession:
        def __init__(self, _engine): pass
        def __enter__(self): return self
        def __exit__(self, *_args): pass
    worker.Session = EmptySession
    async def noop(*_args, **_kwargs): pass
    worker.sync_agent_service_proxy = noop
    worker.scheduler_loop = noop
    worker.retention_scheduler_loop = noop
    worker.account_deletion_scheduler_loop = noop
    stop = asyncio.Event()
    stop.set()
    asyncio.run(worker.run_scheduler(settings, stop_event=stop))
elif "notifications" in "{module_name}":
    stop = threading.Event()
    stop.set()
    worker.run_worker(settings, stop_event=stop)
else:
    stop = asyncio.Event()
    stop.set()
    asyncio.run(worker.run_worker(settings, stop_event=stop))
'''
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(backend_root)
    environment["APP_ENV"] = "test"
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=backend_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
