import asyncio
import threading
from types import SimpleNamespace

import httpx

from app import main


def test_readiness_db_wait_does_not_block_requests_on_the_event_loop(monkeypatch, test_settings):
    release = threading.Event()
    entered = threading.Event()
    released = []

    class Database:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, *args):
            entered.set()
            released.append(release.wait(1))

    class Redis:
        client = None

        async def ping(self):
            return SimpleNamespace(available=True)

    monkeypatch.setattr(main, "Session", lambda *_: Database())
    monkeypatch.setattr(main, "get_engine", lambda *_: None)
    monkeypatch.setattr(main, "create_redis_service", lambda *_: Redis())
    app = main.create_app(test_settings)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test"
        ) as client:
            request = asyncio.create_task(client.get("/readyz"))
            for _ in range(100):
                if entered.is_set():
                    break
                await asyncio.sleep(0.001)
            release.set()
            response = await request
            assert response.status_code == 200

    asyncio.run(run())
    assert released == [True], "A readiness pool wait blocked the event loop that releases requests"
