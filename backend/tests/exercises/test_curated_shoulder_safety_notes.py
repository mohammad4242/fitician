from uuid import NAMESPACE_URL, uuid5

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exercises.enums import (
    BodyRegion,
    Difficulty,
    ExerciseType,
    MediaType,
    MovementPattern,
    MuscleFocus,
    MuscleGroup,
)
from app.exercises.models import Exercise
from app.exercises.service import seed_exercises

CURRENT_ACTIVE_SHOULDER_TRAINING_SLUGS = frozenset(
    {
        "dumbbell-lateral-raise",
        "fedb-0028-barbell-clean-and-press",
        "fedb-0041-barbell-front-raise",
        "fedb-0075-barbell-rear-delt-raise",
        "fedb-0123-barbell-wide-grip-upright-row",
        "fedb-0128-battling-ropes",
        "fedb-0154-cable-crossover-reverse-fly",
        "fedb-0162-cable-one-arm-front-raise",
        "fedb-0178-cable-lateral-raise",
        "fedb-0192-cable-one-arm-lateral-raise",
        "fedb-0203-cable-rear-delt-row-with-rope",
        "fedb-0289-seated-dumbbell-shoulder-press",
        "fedb-0310-dumbbell-front-raise",
        "fedb-0326-dumbbell-incline-rear-lateral-raise",
        "fedb-0332-dumbbell-iron-cross",
        "fedb-0334-dumbbell-lateral-raise",
        "fedb-0355-dumbbell-one-arm-lateral-raise",
        "fedb-0361-dumbbell-alternating-shoulder-press",
        "fedb-0377-dumbbell-rear-delt-row",
        "fedb-0392-dumbbell-seated-front-raise",
        "fedb-0396-dumbbell-seated-lateral-raise",
        "fedb-0437-dumbbell-upright-row",
        "fedb-0445-ez-barbell-anti-gravity-press",
        "fedb-0553-military-press",
        "fedb-0584-lever-lateral-raise",
        "fedb-0602-lever-seated-reverse-fly",
        "fedb-0765-smith-seated-shoulder-press",
        "fedb-1017-band-one-arm-front-raise",
        "fedb-1022-band-standing-rear-delt-row",
        "fedb-2137-dumbbell-arnold-press",
        "fedb-drv-band-bent-over-rear-lateral-raise-band-bent-over-rear-lateral-raise",
        "fedb-drv-barbell-seated-behind-head-military-press-barbell-seated-behind-the-neck-press",
        "owner-2f6026f53abb-seated-cable-rope-lat-pulldown",
        "owner-3a30c79d77aa-kneeling-face-pull",
        "owner-43ec8f18aa72-seated-barbell-overhead-press",
        "owner-6ade15ad4ded-shoulder-workout-compilation",
        "owner-6b7757e85637-seated-cable-rope-face-pull",
        "owner-7918dc7f8d77-standing-dumbbell-shoulder-press",
        "owner-bf2134aafcda-neutral-grip-dumbbell-front-raise",
        "owner-dc4ac8c89e95-dumbbell-bent-over-rear-delt-fly",
        "owner-e40dc9bd636b-dumbbell-incline-rear-lateral-raise",
        "owner-f9d1558c4263-bench-supported-dumbbell-lateral-raise",
        "rear-delt-fly",
        "smith-machine-shoulder-press",
    }
)

MOBILITY_SHOULDER_SLUGS = (
    "fedb-0669-rear-deltoid-stretch",
    "fedb-2203-seated-shoulder-flexor-depressor-retractor-stretch",
    "fedb-drv-stretching-band-warm-up-shoulder-stretch-band-shoulder-warm-up-stretch",
)

API_DETAIL_SPOT_CHECK_SLUGS = (
    "fedb-0334-dumbbell-lateral-raise",
    "fedb-0178-cable-lateral-raise",
    "fedb-0584-lever-lateral-raise",
    "fedb-0289-seated-dumbbell-shoulder-press",
    "fedb-0553-military-press",
    "fedb-0765-smith-seated-shoulder-press",
    "fedb-2137-dumbbell-arnold-press",
    "fedb-0602-lever-seated-reverse-fly",
    "fedb-0154-cable-crossover-reverse-fly",
    "fedb-0203-cable-rear-delt-row-with-rope",
    "fedb-drv-barbell-seated-behind-head-military-press-barbell-seated-behind-the-neck-press",
    "owner-3a30c79d77aa-kneeling-face-pull",
)


def _seed_active_shoulder_training_catalog(db: Session) -> None:
    from app.exercises.curated_safety_notes import get_curated_safety_notes

    seed_exercises(db)
    seed_slugs = {"dumbbell-lateral-raise", "rear-delt-fly", "smith-machine-shoulder-press"}
    for slug in sorted(CURRENT_ACTIVE_SHOULDER_TRAINING_SLUGS - seed_slugs):
        curated = get_curated_safety_notes(slug)
        assert curated is not None, slug
        db.add(
            Exercise(
                id=uuid5(NAMESPACE_URL, f"https://fitsho.test/shoulder-safety/{slug}"),
                slug=slug,
                name_en=slug.replace("-", " ").title(),
                name_fa="حرکت تمرینی سرشانه",
                body_region=BodyRegion.UPPER_BODY,
                primary_muscle=MuscleGroup.SHOULDERS,
                muscle_focus=MuscleFocus.GENERAL_SHOULDERS,
                difficulty=Difficulty.INTERMEDIATE,
                movement_pattern=MovementPattern.OTHER,
                exercise_type=ExerciseType.COMPOUND,
                instructions_en=["Set up safely.", "Move with control.", "Return safely."],
                instructions_fa=["ایمن آماده شو.", "حرکت را کنترل کن.", "ایمن برگرد."],
                safety_notes_en=list(curated.en),
                safety_notes_fa=list(curated.fa),
                media_path="/exercises/exercise-placeholder.svg",
                media_type=MediaType.PLACEHOLDER,
                source="curated-shoulder-test",
                source_id=slug,
                is_active=True,
                is_programmable=True,
            )
        )
    for slug in MOBILITY_SHOULDER_SLUGS:
        db.add(
            Exercise(
                id=uuid5(NAMESPACE_URL, f"https://fitsho.test/shoulder-mobility/{slug}"),
                slug=slug,
                name_en=slug.replace("-", " ").title(),
                name_fa="کشش سرشانه",
                body_region=BodyRegion.UPPER_BODY,
                primary_muscle=MuscleGroup.SHOULDERS,
                muscle_focus=MuscleFocus.GENERAL_SHOULDERS,
                difficulty=Difficulty.BEGINNER,
                movement_pattern=MovementPattern.OTHER,
                exercise_type=ExerciseType.MOBILITY,
                instructions_en=["Set up safely.", "Move gently.", "Return safely."],
                instructions_fa=["ایمن آماده شو.", "آرام حرکت کن.", "ایمن برگرد."],
                safety_notes_en=[],
                safety_notes_fa=[],
                media_path="/exercises/exercise-placeholder.svg",
                media_type=MediaType.PLACEHOLDER,
                source="curated-shoulder-test",
                source_id=slug,
                is_active=True,
                is_programmable=False,
            )
        )
    db.flush()


def test_every_active_shoulder_training_exercise_has_ordered_curated_notes(db: Session) -> None:
    from app.exercises.curated_safety_notes import get_curated_safety_notes

    _seed_active_shoulder_training_catalog(db)
    exercises = list(
        db.scalars(
            select(Exercise)
            .where(
                Exercise.is_active.is_(True),
                Exercise.primary_muscle == MuscleGroup.SHOULDERS,
                Exercise.exercise_type != ExerciseType.MOBILITY,
            )
            .order_by(Exercise.slug)
        )
    )

    assert {exercise.slug for exercise in exercises} == CURRENT_ACTIVE_SHOULDER_TRAINING_SLUGS
    for exercise in exercises:
        curated = get_curated_safety_notes(exercise.slug)
        assert curated is not None, exercise.slug
        assert 2 <= len(curated.fa) <= 5
        assert 2 <= len(curated.en) <= 5
        assert len(curated.fa) == len(curated.en)
        assert all(note.strip() for note in (*curated.fa, *curated.en))
        assert exercise.safety_notes_fa == list(curated.fa)
        assert exercise.safety_notes_en == list(curated.en)


def test_shoulder_mobility_exercises_are_excluded_from_curated_training_notes(
    db: Session,
) -> None:
    from app.exercises.curated_safety_notes import get_curated_safety_notes

    _seed_active_shoulder_training_catalog(db)
    mobility_rows = list(
        db.scalars(
            select(Exercise).where(
                Exercise.is_active.is_(True),
                Exercise.primary_muscle == MuscleGroup.SHOULDERS,
                Exercise.exercise_type == ExerciseType.MOBILITY,
            )
        )
    )

    assert {exercise.slug for exercise in mobility_rows} == set(MOBILITY_SHOULDER_SLUGS)
    assert all(get_curated_safety_notes(exercise.slug) is None for exercise in mobility_rows)
    assert all(
        not exercise.safety_notes_fa and not exercise.safety_notes_en for exercise in mobility_rows
    )


def test_shoulder_aliases_reuse_the_same_canonical_note_objects() -> None:
    from app.exercises.curated_safety_notes import get_curated_safety_notes

    aliases = (
        ("dumbbell-lateral-raise", "fedb-0334-dumbbell-lateral-raise"),
        ("smith-machine-shoulder-press", "fedb-0765-smith-seated-shoulder-press"),
        ("rear-delt-fly", "owner-dc4ac8c89e95-dumbbell-bent-over-rear-delt-fly"),
        ("face-pull", "owner-3a30c79d77aa-kneeling-face-pull"),
        ("face-pull", "owner-6b7757e85637-seated-cable-rope-face-pull"),
    )
    for canonical_slug, alias_slug in aliases:
        canonical = get_curated_safety_notes(canonical_slug)
        alias = get_curated_safety_notes(alias_slug)
        assert canonical is not None, canonical_slug
        assert alias is canonical, alias_slug


def test_api_detail_preserves_curated_shoulder_note_order(
    client: TestClient,
    db: Session,
) -> None:
    from tests.exercises.test_exercise_api import complete_profile, register

    register(client, "shoulder-safety-api@example.com")
    complete_profile(client)
    _seed_active_shoulder_training_catalog(db)

    from app.exercises.curated_safety_notes import get_curated_safety_notes

    for slug in API_DETAIL_SPOT_CHECK_SLUGS:
        response = client.get(f"/api/v1/exercises/{slug}")
        curated = get_curated_safety_notes(slug)

        assert response.status_code == 200
        assert curated is not None
        assert response.json()["safety_notes_fa"] == list(curated.fa)
        assert response.json()["safety_notes_en"] == list(curated.en)

    assert get_curated_safety_notes("face-pull") is not None
