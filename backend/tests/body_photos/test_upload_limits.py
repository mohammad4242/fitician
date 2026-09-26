from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import FormData
from starlette.requests import Request

from app.config import Settings

ORIGIN = {"Origin": "http://localhost:5173"}


@pytest.mark.parametrize("authorization", [None, "Bearer invalid-token"])
def test_unauthenticated_upload_is_rejected_before_multipart_parsing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, authorization: str | None
) -> None:
    parser = AsyncMock(return_value=FormData())
    monkeypatch.setattr(Request, "_get_form", parser)
    headers = dict(ORIGIN)
    if authorization:
        headers["Authorization"] = authorization
    response = client.put(
        f"/api/v1/body-photo-sessions/{uuid4()}/photos/front",
        headers=headers,
        files={"file": ("photo.jpg", b"x" * 2048, "image/jpeg")},
    )
    assert response.status_code == 401
    parser.assert_not_called()


@pytest.mark.parametrize("length", ["actual", "missing", "understated"])
def test_oversized_upload_is_rejected_before_parsing(
    client: TestClient, test_settings: Settings, monkeypatch: pytest.MonkeyPatch, length: str
) -> None:
    assert (
        client.post(
            "/api/v1/auth/register",
            headers=ORIGIN,
            json={"email": "upload-limit@example.com", "password": "long password"},
        ).status_code
        == 201
    )
    test_settings.body_photo_max_bytes = 1024
    parser = AsyncMock(return_value=FormData())
    monkeypatch.setattr(Request, "_get_form", parser)
    body = b"x" * (1024 + 64 * 1024 + 1)
    headers = {**ORIGIN, "Content-Type": "multipart/form-data; boundary=test"}
    if length != "missing":
        headers["Content-Length"] = str(len(body)) if length == "actual" else "1"
    response = client.put(
        f"/api/v1/body-photo-sessions/{uuid4()}/photos/front",
        headers=headers,
        content=iter([body[:1024], body[1024:]]),
    )
    assert response.status_code == 413
    parser.assert_not_called()


def test_mobile_bearer_upload_still_reaches_the_authenticated_session_check(
    client: TestClient,
) -> None:
    credentials = {"email": "mobile-upload@example.com", "password": "long password"}
    assert client.post("/api/v1/auth/register", headers=ORIGIN, json=credentials).status_code == 201
    login = client.post(
        "/api/v1/auth/mobile/password",
        json={**credentials, "device_id": "upload", "platform": "ios", "app_version": "1"},
    )
    assert login.status_code == 200
    client.cookies.clear()
    response = client.put(
        f"/api/v1/body-photo-sessions/{uuid4()}/photos/front",
        headers={**ORIGIN, "Authorization": f"Bearer {login.json()['access_token']}"},
        files={"file": ("photo.jpg", b"small-file", "image/jpeg")},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "BODY_PHOTO_SESSION_NOT_FOUND"
