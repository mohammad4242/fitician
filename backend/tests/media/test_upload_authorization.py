from collections.abc import AsyncIterator
from io import BytesIO
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.auth.models import User
from app.config import Settings

ORIGIN = {"Origin": "http://localhost:5173"}
UPLOADS = [
    ("POST", "/api/v1/admin/exercises", True),
    ("PATCH", "/api/v1/admin/exercises/00000000-0000-0000-0000-000000000001", True),
    ("PUT", "/api/v1/profile/photo", False),
    ("POST", "/api/v1/nutrition/admin/foods/test/image", True),
    ("POST", "/api/v1/nutrition/admin/meals/00000000-0000-0000-0000-000000000001/image", True),
    ("POST", "/api/v1/nutrition/tracking/photo-estimates", False),
    ("POST", "/api/v1/nutrition/labs", False),
]


def _watch_body(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    reads: list[int] = []
    original = Request.stream

    async def stream(request: Request) -> AsyncIterator[bytes]:
        async for chunk in original(request):
            reads.append(len(chunk))
            yield chunk

    monkeypatch.setattr(Request, "stream", stream)
    return reads


@pytest.mark.parametrize("method,url,admin_only", UPLOADS)
@pytest.mark.parametrize("credential", ["missing", "invalid_bearer", "invalid_cookie"])
def test_upload_rejects_unauthenticated_request_without_reading_body(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    url: str,
    admin_only: bool,
    credential: str,
) -> None:
    headers = dict(ORIGIN)
    if credential == "invalid_bearer":
        headers["Authorization"] = "Bearer invalid"
    elif credential == "invalid_cookie":
        client.cookies.set("fitician_session", "invalid")
    reads = _watch_body(monkeypatch)
    response = client.request(
        method,
        url,
        headers=headers,
        files=[("unused", ("part.bin", b"x" * 2048)) for _ in range(4)],
    )
    assert response.status_code == 401
    assert reads == []


@pytest.mark.parametrize("method,url,admin_only", UPLOADS)
def test_upload_rejects_untrusted_origin_without_reading_body(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    url: str,
    admin_only: bool,
) -> None:
    registered = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": "origin-upload@example.com", "password": "long password"},
    )
    assert registered.status_code == 201
    if admin_only:
        user = db.get(User, UUID(registered.json()["id"]))
        assert user is not None
        user.is_admin = True
        db.commit()
    reads = _watch_body(monkeypatch)
    response = client.request(
        method,
        url,
        headers={"Origin": "https://untrusted.example"},
        files={"file": ("part.bin", b"x" * 2048)},
    )
    assert response.status_code == 403
    assert reads == []


@pytest.mark.parametrize("method,url,admin_only", [item for item in UPLOADS if item[2]])
def test_admin_upload_rejects_member_without_reading_body(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    url: str,
    admin_only: bool,
) -> None:
    assert (
        client.post(
            "/api/v1/auth/register",
            headers=ORIGIN,
            json={"email": "member-upload@example.com", "password": "long password"},
        ).status_code
        == 201
    )
    reads = _watch_body(monkeypatch)
    response = client.request(
        method,
        url,
        headers=ORIGIN,
        files={"file": ("part.bin", b"x" * 2048)},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "ADMIN_ROLE_REQUIRED"
    assert reads == []


@pytest.mark.parametrize(
    "url", ["/api/v1/nutrition/labs", "/api/v1/nutrition/tracking/photo-estimates"]
)
def test_nutrition_upload_checks_entitlement_before_reading_body(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, url: str
) -> None:
    assert (
        client.post(
            "/api/v1/auth/register",
            headers=ORIGIN,
            json={"email": "unentitled-upload@example.com", "password": "long password"},
        ).status_code
        == 201
    )
    reads = _watch_body(monkeypatch)
    response = client.post(
        url,
        headers={**ORIGIN, "X-Fitician-Food-Photo-Consent": "true"},
        files={"file": ("part.bin", b"x" * 2048)},
    )
    assert response.status_code == 403
    assert reads == []


def test_valid_mobile_bearer_can_upload_but_invalid_bearer_cannot_fall_back_to_cookie(
    client: TestClient, test_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    credentials = {"email": "native-upload@example.com", "password": "long password"}
    assert client.post("/api/v1/auth/register", headers=ORIGIN, json=credentials).status_code == 201
    login = client.post(
        "/api/v1/auth/mobile/password",
        json={**credentials, "device_id": "upload", "platform": "ios", "app_version": "1"},
    )
    assert login.status_code == 200
    reads = _watch_body(monkeypatch)
    rejected = client.put(
        "/api/v1/profile/photo",
        headers={**ORIGIN, "Authorization": "Bearer invalid"},
        files={"file": ("photo.png", b"invalid")},
    )
    assert rejected.status_code == 401
    assert reads == []

    client.cookies.clear()
    image = BytesIO()
    Image.new("RGB", (256, 256)).save(image, format="PNG")
    test_settings.profile_photo_storage_root = test_settings.media_root.parent / "private-profile"
    response = client.put(
        "/api/v1/profile/photo",
        headers={**ORIGIN, "Authorization": f"Bearer {login.json()['access_token']}"},
        files={"file": ("photo.png", image.getvalue(), "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["width"] == 256
    assert sum(reads) > 0


@pytest.mark.parametrize("method,url,admin_only", UPLOADS)
def test_upload_openapi_keeps_the_multipart_contract(
    client: TestClient, method: str, url: str, admin_only: bool
) -> None:
    path = url.replace("00000000-0000-0000-0000-000000000001", "{exercise_id}")
    if "/meals/" in path:
        path = path.replace("{exercise_id}", "{meal_id}")
    path = path.replace("/foods/test/", "/foods/{slug}/")
    operation = client.get("/openapi.json").json()["paths"][path][method.lower()]
    assert "422" in operation["responses"]
    schema = operation["requestBody"]
    form = schema["content"]["multipart/form-data"]["schema"]
    if "/admin/exercises" in path:
        assert form["required"] == ["payload"]
        assert set(form["properties"]) == {
            "payload",
            "media",
            "media_male_video",
            "media_female_video",
            "media_files",
        }
    else:
        assert form["required"] == ["file"]
        assert form["properties"]["file"]["type"] == "string"
        assert form["properties"]["file"]["contentMediaType"] == "application/octet-stream"
        if path.endswith("/labs"):
            assert set(form["properties"]) == {
                "file",
                "test_date",
                "laboratory_name",
                "user_note",
                "category",
                "request_id",
            }
