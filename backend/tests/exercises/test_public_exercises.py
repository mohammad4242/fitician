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
    unfiltered = client.get("/api/v1/public/exercises").json()
    assert unfiltered["total"] == 1
    assert [item["slug"] for item in unfiltered["items"]] == [record.slug]
    for attribute, value in [("is_active", False), ("needs_review", True)]:
        original = getattr(record, attribute)
        setattr(record, attribute, value)
        db.commit()
        assert client.get("/api/v1/public/exercises").json()["total"] == 0
        setattr(record, attribute, original)
        db.commit()


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


def test_approval_requires_a_published_page_before_catalog_discovery(client, db):
    seed_exercises(db)
    record = db.scalar(select(Exercise).where(Exercise.slug == "dumbbell-bench-press"))
    record.slug = "new-approved-page-awaiting-web-publication"
    record.is_public = True
    db.commit()
    response = client.get("/api/v1/public/exercises", params={"search": record.name_en})
    assert response.json()["total"] == 0
    assert client.get(f"/api/v1/public/exercises/{record.slug}").status_code == 404


def test_public_media_allows_owner_authorized_stable_delivery(client, db):
    from app.exercises.media_metadata import OWNER_LICENSE

    seed_exercises(db)
    record = db.scalar(select(Exercise).where(Exercise.slug == "dumbbell-bench-press"))
    record.is_public = True
    record.media_license = OWNER_LICENSE
    record.media_source_url = "https://private.example/source?secret=hidden"
    db.commit()
    data = client.get(f"/api/v1/public/exercises/{record.slug}").json()
    assert data["media_path"] == "/media/exercises/seed/dumbbell-bench-press.gif"
    assert data["media_type"] == "gif"
    assert "private.example" not in str(data)
    assert "secret" not in str(data)


def test_export_projects_only_reviewed_active_approved_records(db, tmp_path):
    import json

    from app.exercises.public_export import export_public_exercises

    seed_exercises(db)
    records = list(db.scalars(select(Exercise).order_by(Exercise.slug)))
    approved, inactive, review = records[:3]
    for record in [approved, inactive, review]:
        record.is_public = True
    inactive.is_active = False
    review.needs_review = True
    db.commit()
    output, manifest = tmp_path / "public.json", tmp_path / "slugs.json"
    export_public_exercises(db, output, manifest)
    data = json.loads(output.read_text())
    assert [item["slug"] for item in data] == [approved.slug]
    assert json.loads(manifest.read_text()) == [approved.slug]
    for forbidden in [
        "source_id",
        "needs_review",
        "is_public",
        "is_programmable",
        "source_metadata",
    ]:
        assert forbidden not in output.read_text()


def test_approval_backfill_matches_previously_published_seed_pages():
    import importlib.util
    import json
    from pathlib import Path

    from app.exercises.seed_data import EXERCISE_SEEDS

    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "public_approval_migration",
        root / "alembic/versions/20261006_170_public_exercise_approval.py",
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    manifest = json.loads((root / "app/exercises/publication_slugs.json").read_text())
    snapshot = json.loads((root.parent / "frontend/src/seo/exercise-publications.json").read_text())
    if snapshot is None:
        assert set(migration.PUBLISHED_SLUGS) == set(manifest)
    assert set(migration.PUBLISHED_SLUGS) == {seed.slug for seed in EXERCISE_SEEDS}


def test_public_detail_labels_missing_specific_safety_instead_of_omitting_it(client, db):
    seed_exercises(db)
    record = db.scalar(select(Exercise).where(Exercise.slug == "dumbbell-bench-press"))
    record.is_public = True
    record.safety_notes_fa = []
    record.safety_notes_en = []
    db.commit()
    data = client.get(f"/api/v1/public/exercises/{record.slug}").json()
    assert data["safety_notes_fa"]
    assert data["safety_notes_en"]
    assert "اختصاصی ثبت نشده" in data["safety_notes_fa"][0]
    assert record.safety_notes_fa == []


def test_approved_imported_exercise_uses_publication_and_safe_projection(client, db):
    from app.exercises.enums import MediaPresentation, MediaRole, MediaType
    from app.exercises.media_metadata import OWNER_LICENSE
    from app.exercises.models import ExerciseMediaAsset

    seed_exercises(db)
    record = db.scalar(select(Exercise).where(Exercise.slug == "dumbbell-bench-press"))
    record.slug = "fedb-0033-barbell-decline-bench-press"
    record.is_public = True
    record.source = "free-exercise-db"
    record.source_id = "internal-source-do-not-publish"
    record.media_assets.append(
        ExerciseMediaAsset(
            presentation=MediaPresentation.MALE,
            role=MediaRole.VIDEO,
            sort_order=0,
            media_path="/media/exercises/imported/demo.mp4",
            media_type=MediaType.VIDEO,
            media_license=OWNER_LICENSE,
            media_source_url="private-source-do-not-publish",
            source="free-exercise-db",
            source_id="internal-video-do-not-publish",
        )
    )
    db.commit()
    response = client.get(f"/api/v1/public/exercises/{record.slug}")
    assert response.status_code == 200
    data = response.json()
    assert data["media_assets"][0]["media_path"] == "/media/exercises/imported/demo.mp4"
    assert "do-not-publish" not in response.text
    assert (
        client.get("/api/v1/public/exercises", params={"primary_muscle": "chest"}).json()["total"]
        == 1
    )


def test_full_library_approval_migration_preserves_review_and_inactive_gates(db):
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    seed_exercises(db)
    records = list(db.scalars(select(Exercise).order_by(Exercise.slug)))
    active, inactive, review, unrelated = records[:4]
    active.slug = "fedb-0033-barbell-decline-bench-press"
    inactive.slug = "fedb-0047-barbell-incline-bench-press"
    review.slug = "fedb-0301-decline-dumbbell-bench-press"
    unrelated.slug = "not-in-reviewed-publication"
    inactive.is_active = False
    review.needs_review = True
    for record in [active, inactive, review, unrelated]:
        record.is_public = False
    db.flush()
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic/versions/20261007_171_publish_reviewed_exercise_library.py"
    )
    spec = importlib.util.spec_from_file_location("full_public_approval", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with Operations.context(MigrationContext.configure(db.connection())):
        migration.upgrade()
        migration.upgrade()
    db.expire_all()
    assert active.is_public is True
    assert inactive.is_public is False
    assert review.is_public is False
    assert unrelated.is_public is False
    with Operations.context(MigrationContext.configure(db.connection())):
        migration.downgrade()
    db.expire_all()
    assert active.is_public is False


def test_public_export_rejects_unfinished_importer_review_instructions(db, tmp_path):
    import pytest

    from app.exercises.public_export import export_public_exercises

    seed_exercises(db)
    record = db.scalar(select(Exercise).where(Exercise.slug == "dumbbell-bench-press"))
    record.is_public = True
    record.instructions_en = [
        "Review the attached owner video before programming this exercise.",
        "Confirm the movement identity and equipment.",
        "Replace this placeholder metadata after review.",
    ]
    db.commit()
    with pytest.raises(ValueError, match="instructional review"):
        export_public_exercises(db, tmp_path / "public.json", tmp_path / "slugs.json")
    assert not (tmp_path / "public.json").exists()
    assert not (tmp_path / "slugs.json").exists()
