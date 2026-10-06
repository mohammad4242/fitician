from sqlalchemy import select

from app.exercises.models import Exercise
from app.exercises.service import seed_exercises


def test_anonymous_catalog_is_explicitly_published_and_safe(client, db):
    seed_exercises(db)
    record = db.scalar(select(Exercise).where(Exercise.slug == "dumbbell-bench-press"))
    record.is_public = True
    db.commit()
    response = client.get("/api/v1/public/exercises", params={"search": "Dumbbell Bench"})
    assert response.status_code == 200
    assert response.json()["total"] == 1
    item = response.json()["items"][0]
    assert item["slug"] == record.slug
    assert set(item) == {
        "slug",
        "name_en",
        "name_fa",
        "content_type",
        "body_region",
        "primary_muscle",
        "secondary_muscles",
        "muscle_focus",
        "equipment",
        "difficulty",
        "labels",
        "media_path",
        "media_type",
    }
    assert response.headers["cache-control"] == "no-store"


def test_public_detail_requires_approval_active_and_reviewed(client, db):
    seed_exercises(db)
    record = db.scalar(select(Exercise).where(Exercise.slug == "dumbbell-bench-press"))
    path = f"/api/v1/public/exercises/{record.slug}"
    record.is_public = False
    db.commit()
    assert client.get(path).status_code == 404
    record.is_public = True
    record.is_active = False
    db.commit()
    assert client.get(path).status_code == 404
    record.is_active = True
    record.needs_review = True
    db.commit()
    assert client.get(path).status_code == 404
    record.needs_review = False
    db.commit()
    data = client.get(path).json()
    assert data["instructions_fa"]
    assert data["safety_notes_fa"]
    for field in (
        "id",
        "source",
        "source_id",
        "needs_review",
        "is_active",
        "is_public",
        "is_programmable",
        "substitution_group",
        "aliases_en",
        "media_source_url",
        "media_license",
        "source_metadata_en",
    ):
        assert field not in data
    assert client.get("/api/v1/public/exercises/missing").status_code == 404
    assert client.post(path).status_code == 405
    assert client.get("/api/v1/exercises").status_code == 401


def test_public_media_rejects_unverified_and_private_paths(client, db):
    seed_exercises(db)
    record = db.scalar(select(Exercise).where(Exercise.slug == "dumbbell-bench-press"))
    record.is_public = True
    for path, license in [
        ("/media/private/secret.mp4", "Project owner supplied and authorized"),
        ("/media/exercises/test.mp4?token=secret", "Fitician original"),
        ("/media/exercises/test.mp4", "unknown"),
        ("/home/private/test.mp4", "Fitician original"),
    ]:
        record.media_path = path
        record.media_license = license
        db.commit()
        data = client.get(f"/api/v1/public/exercises/{record.slug}").json()
        assert data["media_type"] == "placeholder"
        assert data["media_path"] == "/exercises/exercise-placeholder.svg"
        assert data["media_assets"] == []


def test_public_categories_filters_and_pagination(client, db):
    seed_exercises(db)
    for record in db.scalars(select(Exercise)):
        record.is_public = True
    db.commit()
    assert client.get("/api/v1/public/exercise-categories").status_code == 200
    response = client.get(
        "/api/v1/public/exercises",
        params={
            "body_region": "upper_body",
            "primary_muscle": "biceps",
            "equipment": "dumbbell",
            "difficulty": "beginner",
            "page_size": 1,
        },
    )
    assert response.status_code == 200
    assert response.json()["total_pages"] >= 2
    item = response.json()["items"][0]
    assert item["primary_muscle"] == "biceps"
    assert "dumbbell" in item["equipment"]
    next_page = client.get(
        "/api/v1/public/exercises",
        params={
            "primary_muscle": "biceps",
            "equipment": "dumbbell",
            "difficulty": "beginner",
            "page_size": 1,
            "page": 2,
        },
    ).json()
    assert next_page["items"][0]["slug"] != item["slug"]
    assert client.get("/api/v1/public/exercises?page_size=10000").status_code == 422
    assert client.get("/api/v1/public/exercises?admin_status=all").status_code == 422


def test_public_rate_limit_fails_closed(client):
    from app.infrastructure.rate_limiter import RateLimitResult, RedisRateLimitUnavailable

    class Limiter:
        async def consume(self, **kwargs):
            return RateLimitResult(allowed=False, count=121, retry_after_seconds=30)

    client.app.state.rate_limiter = Limiter()
    response = client.get("/api/v1/public/exercise-categories")
    assert response.status_code == 429
    assert response.headers["retry-after"] == "30"

    class Unavailable:
        async def consume(self, **kwargs):
            raise RedisRateLimitUnavailable

    client.app.state.rate_limiter = Unavailable()
    assert client.get("/api/v1/public/exercise-categories").status_code == 503
