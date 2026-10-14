import asyncio
import json
import socket
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

from app.body_analysis.providers.agent_service import AgentServiceProvider
from app.body_analysis.providers.models import AIProviderError
from tests.ai.test_agent_service_provider import _request


def test_agent_connect_failures_have_distinct_safe_contract() -> None:
    provider = AgentServiceProvider(
        httpx.AsyncClient(), base_url="http://agent:9001", token="test", agent_name="codex"
    )
    for error in (httpx.ConnectError("DNS failed"), httpx.ConnectTimeout("connect failed")):
        normalized = provider.normalize_error(error)
        assert normalized.code.value == "agent_network_unavailable"
        assert normalized.safe_message == "اینترنت بین‌الملل در دسترس نیست"
    for error in (httpx.ReadTimeout("generation slow"), httpx.PoolTimeout("pool busy")):
        assert provider.normalize_error(error).code.value == "timeout"
    certificate_error = httpx.ConnectError("invalid certificate")
    certificate_error.__cause__ = ssl.SSLCertVerificationError("invalid certificate")
    assert provider.normalize_error(certificate_error).code.value != "agent_network_unavailable"


def test_short_agent_probe_recovers_on_same_provider_without_restart() -> None:
    async def scenario() -> None:
        online = False
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            if not online:
                raise httpx.ConnectError("no route", request=request)
            return httpx.Response(200, json={"status": "ok"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = AgentServiceProvider(
                client, base_url="http://agent:9001", token="test", agent_name="codex"
            )
            with pytest.raises(AIProviderError) as failure:
                await provider.ensure_connection()
            assert failure.value.code.value == "agent_network_unavailable"
            assert len(calls) == 2
            assert all(request.method == "GET" for request in calls)
            assert all(request.extensions["timeout"]["connect"] <= 3 for request in calls)
            assert all(request.extensions["timeout"]["read"] <= 3 for request in calls)
            online = True
            await provider.ensure_connection()
            assert len(calls) == 3

    asyncio.run(scenario())


@pytest.mark.parametrize("status", [401, 403, 429, 500, 503])
def test_reachable_agent_http_errors_are_never_internet_errors(status: int) -> None:
    async def scenario() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(status))
        ) as client:
            provider = AgentServiceProvider(
                client, base_url="http://agent:9001", token="test", agent_name="codex"
            )
            with pytest.raises(AIProviderError) as failure:
                await provider.ensure_connection()
            assert failure.value.code.value != "agent_network_unavailable"

    asyncio.run(scenario())


def test_real_http_transport_recovers_and_generates_without_reconfiguration() -> None:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

        def do_GET(self) -> None:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')

        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            output = {
                "payload": {"score": 0.82},
                "agent": "codex",
                "model_id": body["model_id"],
                "request_id": "isolated-recovery",
                "duration_seconds": 0.01,
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(output).encode())

    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]

    async def scenario() -> None:
        async with httpx.AsyncClient(trust_env=False) as client:
            provider = AgentServiceProvider(
                client,
                base_url=f"http://127.0.0.1:{port}",
                token="test",
                agent_name="codex",
            )
            with pytest.raises(AIProviderError) as failure:
                await provider.generate_structured_text(_request())
            assert failure.value.code.value == "agent_network_unavailable"
            server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                result = await provider.generate_structured_text(_request())
                assert result.payload == {"score": 0.82}
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    asyncio.run(scenario())


def test_agent_network_race_does_not_retry_other_models() -> None:
    posts = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200)
        posts.append(request)
        raise httpx.ConnectError("route disappeared", request=request)

    request = _request()
    request = request.model_copy(
        update={
            "route": request.route.model_copy(update={"fallback_models": ("fallback",)}),
        }
    )
    provider = AgentServiceProvider(
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        base_url="http://agent:9001",
        token="test",
        agent_name="codex",
    )
    with pytest.raises(AIProviderError):
        asyncio.run(provider.generate_structured_text(request))
    assert len(posts) == 1
