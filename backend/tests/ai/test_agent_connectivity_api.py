import httpx
from fastapi.testclient import TestClient


def test_connectivity_is_authenticated_and_recovers_without_running_a_model(
    client: TestClient,
) -> None:
    assert client.get("/api/v1/ai/connectivity").status_code == 401
    registered = client.post(
        "/api/v1/auth/register",
        headers={"Origin": "http://localhost:5173"},
        json={"email": "connectivity-test@example.com", "password": "long password"},
    )
    assert registered.status_code == 201
    online = False
    seen = []

    def respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if not online:
            raise httpx.ConnectError("no route", request=request)
        return httpx.Response(200, json={"status": "ok"})

    client.app.state.agent_http_client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    offline = client.get("/api/v1/ai/connectivity")
    assert offline.json() == {
        "network_unavailable": True,
        "error_code": "agent_network_unavailable",
    }
    online = True
    assert client.get("/api/v1/ai/connectivity").json() == {
        "network_unavailable": False,
        "error_code": None,
    }
    assert len(seen) == 3
    assert all(request.method == "GET" and request.url.path == "/healthz" for request in seen)


def test_agent_http_failure_does_not_report_an_internet_outage(client: TestClient) -> None:
    assert (
        client.post(
            "/api/v1/auth/register",
            headers={"Origin": "http://localhost:5173"},
            json={"email": "connectivity-status@example.com", "password": "long password"},
        ).status_code
        == 201
    )
    client.app.state.agent_http_client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(503)),
    )
    result = client.get("/api/v1/ai/connectivity")
    assert result.json() == {"network_unavailable": False, "error_code": "provider_unavailable"}
