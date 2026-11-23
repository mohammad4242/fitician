import asyncio
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from app.debugging.connector import LaptopConnector


def connector(tmp_path, client):
    return LaptopConnector(
        {
            "server": "https://fitician.example",
            "id": str(uuid4()),
            "token": "synthetic-only",
            "repository": str(tmp_path),
            "workspace_root": str(tmp_path / "state"),
            "codex_home": str(tmp_path / "auth"),
            "codex_executable": "/operator/pinned-codex",
            "persistent_codex": True,
        },
        client,
    )


class Runtime:
    instances = []

    def __init__(self, **kwargs):
        self.process = SimpleNamespace(returncode=None)
        self.failure = None
        self.thread_id = None
        self.closed = False
        self.released = 0
        Runtime.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.closed = True

    async def close(self):
        self.closed = True

    async def release_thread(self):
        self.released += 1


def test_persistent_runtime_reuses_one_process_and_closes_on_service_stop(tmp_path, monkeypatch):
    Runtime.instances = []
    monkeypatch.setattr("app.debugging.connector.AppServer", Runtime)

    async def run():
        async with httpx.AsyncClient() as client:
            c = connector(tmp_path, client)
            async with c.codex_server() as first:
                pass
            async with c.codex_server() as second:
                assert second is first
            assert len(Runtime.instances) == 1
            assert not first.closed
            await c.close_runtime()
            assert first.closed

    asyncio.run(run())


def test_failed_turn_closes_process_and_next_explicit_call_starts_fresh(tmp_path, monkeypatch):
    Runtime.instances = []
    monkeypatch.setattr("app.debugging.connector.AppServer", Runtime)

    async def run():
        async with httpx.AsyncClient() as client:
            c = connector(tmp_path, client)
            with pytest.raises(ValueError, match="cancelled"):
                async with c.codex_server():
                    raise ValueError("cancelled")
            assert Runtime.instances[0].closed
            async with c.codex_server():
                assert len(Runtime.instances) == 2
            await c.close_runtime()

    asyncio.run(run())


def test_persistent_runtime_serializes_callers(tmp_path, monkeypatch):
    Runtime.instances = []
    monkeypatch.setattr("app.debugging.connector.AppServer", Runtime)

    async def run():
        async with httpx.AsyncClient() as client:
            c = connector(tmp_path, client)
            active = 0
            maximum = 0

            async def turn():
                nonlocal active, maximum
                async with c.codex_server():
                    active += 1
                    maximum = max(maximum, active)
                    await asyncio.sleep(0.01)
                    active -= 1

            await asyncio.gather(turn(), turn())
            assert maximum == 1
            assert len(Runtime.instances) == 1
            await c.close_runtime()

    asyncio.run(run())


def test_release_unsubscribes_without_deleting_thread_history():
    from app.debugging.appserver import AppServer

    server = AppServer()
    server.thread_id = "issue-thread"
    server.turn_id = "completed-turn"
    calls = []

    async def call(method, params):
        calls.append((method, params))
        return {"status": "unsubscribed"}

    server.call = call
    asyncio.run(server.release_thread())
    assert calls == [("thread/unsubscribe", {"threadId": "issue-thread"})]
    assert server.thread_id is None and server.turn_id is None


def test_idle_thread_memory_is_released_immediately_in_pinned_protocol(tmp_path):
    from app.debugging.appserver import thread_parameters

    assert (
        thread_parameters("selected-model", tmp_path, [])["config"]["thread_unload_delay_secs"] == 0
    )


@pytest.mark.parametrize("scope", [{}, {"threadId": "another-issue", "turnId": "old-turn"}])
def test_persistent_wire_rejects_unscoped_or_stale_tool_requests(scope):
    from app.debugging.appserver import AppServer

    server = AppServer()
    server.thread_id = "selected-issue"
    sent = []
    invoked = []

    async def call(method, params):
        return {"turn": {"id": "current-turn"}}

    async def send(message):
        sent.append(message)

    async def tool(name, args):
        invoked.append(name)
        return "must not execute"

    async def progress(*args):
        pass

    server.call = call
    server._send = send

    async def run():
        await server.notifications.put(
            {
                "id": 77,
                "method": "item/tool/call",
                "params": {
                    **scope,
                    "tool": "fitician_read_file",
                    "arguments": {"path": "README.md"},
                },
            }
        )
        await server.notifications.put(
            {
                "method": "turn/completed",
                "params": {
                    "threadId": "selected-issue",
                    "turnId": "current-turn",
                    "turn": {"status": "completed"},
                },
            }
        )
        await server.run_turn("selected-model", "synthetic", tool, progress)

    asyncio.run(run())
    assert invoked == []
    assert sent[0]["id"] == 77 and "error" in sent[0]
