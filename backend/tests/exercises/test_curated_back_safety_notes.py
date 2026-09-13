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

CURRENT_ACTIVE_BACK_TRAINING_SLUGS = frozenset(
    {
        "barbell-bent-over-row",
        "fedb-0027-barbell-underhand-bent-over-row",
        "fedb-0198-cable-pulldown",
        "fedb-0207-reverse-grip-cable-lat-pulldown",
        "fedb-0208-seated-cable-row-v-grip",
        "fedb-0213-cable-seated-high-row-v-bar",
        "fedb-0218-seated-cable-row-wide-grip",
        "fedb-0238-cable-straight-arm-pulldown",
        "fedb-0248-cambered-bar-lying-row",
        "fedb-0253-chin-ups-narrow-parallel-grip",
        "fedb-0293-dumbbell-bent-over-row",
        "fedb-0327-dumbbell-incline-row",
        "fedb-0489-45-degree-hyperextension",
        "fedb-0498-inverted-row-with-straps",
        "fedb-0499-inverted-row-between-chairs",
        "fedb-0570-bench-pull-up",
        "fedb-0573-lever-back-extension",
        "fedb-0581-lever-high-row",
        "fedb-0651-shoulder-width-pull-up",
        "fedb-0673-reverse-grip-machine-lat-pulldown",
        "fedb-0752-smith-machine-deadlift",
        "fedb-0861-cable-one-arm-twisting-seated-row",
        "fedb-0970-band-assisted-pull-up",
        "fedb-0974-cable-close-grip-lat-pulldown",
        "fedb-0983-band-kneeling-one-arm-pulldown",
        "fedb-0990-band-seated-row",
        "fedb-1328-dumbbell-lying-rear-delt-row",
        "fedb-1329-dumbbell-palm-rotational-bent-over-row",
        "fedb-1330-dumbbell-hammer-grip-incline-bench-row",
        "fedb-1349-lever-reverse-t-bar-row",
        "fedb-1429-pull-up-wide-grip",
        "fedb-2327-reverse-grip-pull-up",
        "fedb-2616-cable-one-arm-lateral-pulldown",
        "fedb-2987-close-grip-chin-up",
        "fedb-3144-band-straight-back-seated-row",
        "fedb-drv-cable-bar-lateral-pulldown-wide-shoulder-grip-wide-grip-cable-lat-pulldown",
        "fedb-drv-chin-ups-pull-ups-pull-up-chin-up",
        "fedb-drv-commando-pull-up-commando-pull-up",
        "fedb-drv-lever-t-bar-row-lever-t-bar-row",
        "fedb-drv-ring-high-row-ring-high-row",
        "owner-0a8f98e8fb45-lat-pulldown",
        "owner-1228b1ee2349-seated-cable-row-close-neutral-grip",
        "owner-1762510e543b-seated-cable-rope-pulldown",
        "owner-196c37935776-dumbbell-chest-supported-row",
        "owner-2a5de4dc7ba3-seated-cable-row",
        "owner-2be5b59c8936-underhand-lat-pulldown-entire-lats",
        "owner-3838601de93e-seated-cable-lat-pulldown",
        "owner-3a346817b851-back-workout-compilation",
        "owner-435983d4e255-close-neutral-lat-pulldown-lower-lats",
        "owner-6870f0f21141-seated-rope-cable-lat-pulldown",
        "owner-68e61505aafd-wide-overhand-lat-pulldown-upper-lats",
        "owner-69f576423434-close-grip-lat-pulldown",
        "owner-7229b1ea15b7-dumbbell-pullover",
        "owner-7a5d1aac09bf-lat-pulldown-variations",
        "owner-802adbd216bf-incline-dumbbell-row",
        "owner-91d806ba40f4-seated-high-row",
        "owner-985a6b89a33a-seated-close-grip-cable-lat-pulldown",
        "owner-a0d34387c231-bent-over-dumbbell-high-row",
        "owner-a4a25c322a76-wide-neutral-grip-lat-pulldown-entire-lats",
        "owner-b7ab76b15fd4-standing-cable-row-with-straight-bar",
        "owner-baf4e3c97566-seated-high-cable-rope-row",
        "owner-d111c927f0e6-cable-upright-row",
        "owner-d11b62b4dd71-shoulder-width-pull-up-dumbbell-front-raise-conflicting-frames",
        "owner-da3c8c259901-close-overhand-lat-pulldown-lower-lats",
        "owner-e0c26a271aac-barbell-bent-over-row",
        "owner-e94b2c4b4eaa-cable-bent-over-straight-arm-pulldown",
    }
)

MOBILITY_BACK_SLUGS = (
    "fedb-0690-seated-lower-back-stretch",
    "fedb-1339-exercise-ball-spinal-stretch",
    "fedb-1346-kneeling-lat-stretch",
    "fedb-1363-spine-stretch",
    "fedb-1405-middle-back-stretch",
    "fedb-drv-stretching-kneeling-back-rotation-stretch-kneeling-back-rotation-stretch",
    "fedb-drv-stretching-sitting-bent-over-back-stretch-seated-bent-over-back-stretch",
)

API_DETAIL_SPOT_CHECK_SLUGS = (
    "fedb-0581-lever-high-row",
    "barbell-bent-over-row",
    "owner-2a5de4dc7ba3-seated-cable-row",
    "fedb-0974-cable-close-grip-lat-pulldown",
    "fedb-0238-cable-straight-arm-pulldown",
    "fedb-0218-seated-cable-row-wide-grip",
    "fedb-1429-pull-up-wide-grip",
    "fedb-0489-45-degree-hyperextension",
)


def _seed_active_back_training_catalog(db: Session) -> None:
    from app.exercises.curated_safety_notes import get_curated_safety_notes

    seed_exercises(db)
    for slug in sorted(CURRENT_ACTIVE_BACK_TRAINING_SLUGS):
        if slug == "barbell-bent-over-row":
            continue
        curated = get_curated_safety_notes(slug)
        assert curated is not None, slug
        source = "owner-video" if slug.startswith("owner-") else "free-exercise-db"
        db.add(
            Exercise(
                id=uuid5(NAMESPACE_URL, f"https://fitsho.test/back-safety/{slug}"),
                slug=slug,
                name_en=slug.replace("-", " ").title(),
                name_fa="حرکت تمرینی پشت",
                body_region=BodyRegion.UPPER_BODY,
                primary_muscle=MuscleGroup.BACK,
                muscle_focus=MuscleFocus.GENERAL_BACK,
                difficulty=Difficulty.INTERMEDIATE,
                movement_pattern=MovementPattern.HORIZONTAL_PULL,
                exercise_type=ExerciseType.COMPOUND,
                instructions_en=[
                    "Set up safely.",
                    "Move through the exercise.",
                    "Return with control.",
                ],
                instructions_fa=["ایمن آماده شو.", "حرکت را انجام بده.", "کنترل‌شده برگرد."],
                safety_notes_en=list(curated.en),
                safety_notes_fa=list(curated.fa),
                media_path="/exercises/exercise-placeholder.svg",
                media_type=MediaType.PLACEHOLDER,
                source=source,
                source_id=f"test-{slug}",
                is_active=True,
                is_programmable=True,
            )
        )
    for slug in MOBILITY_BACK_SLUGS:
        db.add(
            Exercise(
                id=uuid5(NAMESPACE_URL, f"https://fitsho.test/back-mobility/{slug}"),
                slug=slug,
                name_en=slug.replace("-", " ").title(),
                name_fa="کشش پشت",
                body_region=BodyRegion.UPPER_BODY,
                primary_muscle=MuscleGroup.BACK,
                muscle_focus=MuscleFocus.GENERAL_BACK,
                difficulty=Difficulty.BEGINNER,
                movement_pattern=MovementPattern.OTHER,
                exercise_type=ExerciseType.MOBILITY,
                instructions_en=["Set up safely.", "Move gently.", "Return with control."],
                instructions_fa=["ایمن آماده شو.", "آرام حرکت کن.", "کنترل‌شده برگرد."],
                safety_notes_en=[],
                safety_notes_fa=[],
                media_path="/exercises/exercise-placeholder.svg",
                media_type=MediaType.PLACEHOLDER,
                source="free-exercise-db",
                source_id=f"test-{slug}",
                is_active=True,
                is_programmable=False,
            )
        )
    db.flush()


def test_every_active_back_training_exercise_has_ordered_curated_notes(db: Session) -> None:
    from app.exercises.curated_safety_notes import get_curated_safety_notes

    _seed_active_back_training_catalog(db)
    exercises = list(
        db.scalars(
            select(Exercise)
            .where(
                Exercise.is_active.is_(True),
                Exercise.primary_muscle == MuscleGroup.BACK,
                Exercise.exercise_type != ExerciseType.MOBILITY,
            )
            .order_by(Exercise.slug)
        )
    )

    assert {exercise.slug for exercise in exercises} == CURRENT_ACTIVE_BACK_TRAINING_SLUGS
    for exercise in exercises:
        curated = get_curated_safety_notes(exercise.slug)
        assert curated is not None, exercise.slug
        assert 2 <= len(curated.fa) <= 5
        assert 2 <= len(curated.en) <= 5
        assert len(curated.fa) == len(curated.en)
        assert all(note.strip() for note in (*curated.fa, *curated.en))
        assert exercise.safety_notes_fa == list(curated.fa)
        assert exercise.safety_notes_en == list(curated.en)


def test_back_aliases_reuse_the_same_canonical_note_objects() -> None:
    from app.exercises.curated_safety_notes import get_curated_safety_notes

    assert get_curated_safety_notes("barbell-bent-over-row") is get_curated_safety_notes(
        "owner-e0c26a271aac-barbell-bent-over-row"
    )
    assert get_curated_safety_notes(
        "fedb-0208-seated-cable-row-v-grip"
    ) is get_curated_safety_notes("owner-2a5de4dc7ba3-seated-cable-row")
    assert get_curated_safety_notes("fedb-0327-dumbbell-incline-row") is get_curated_safety_notes(
        "owner-196c37935776-dumbbell-chest-supported-row"
    )
    assert get_curated_safety_notes("fedb-0327-dumbbell-incline-row") is get_curated_safety_notes(
        "owner-802adbd216bf-incline-dumbbell-row"
    )


def test_back_mobility_exercises_are_not_curated_as_training_notes(db: Session) -> None:
    _seed_active_back_training_catalog(db)

    mobility_rows = list(
        db.scalars(
            select(Exercise).where(
                Exercise.is_active.is_(True),
                Exercise.primary_muscle == MuscleGroup.BACK,
                Exercise.exercise_type == ExerciseType.MOBILITY,
            )
        )
    )

    assert {exercise.slug for exercise in mobility_rows} == set(MOBILITY_BACK_SLUGS)
    assert all(
        not exercise.safety_notes_fa and not exercise.safety_notes_en for exercise in mobility_rows
    )


def test_api_detail_preserves_curated_back_note_order(
    client: TestClient,
    db: Session,
) -> None:
    from tests.exercises.test_exercise_api import complete_profile, register

    register(client, "back-safety-api@example.com")
    complete_profile(client)
    _seed_active_back_training_catalog(db)

    from app.exercises.curated_safety_notes import get_curated_safety_notes

    for slug in API_DETAIL_SPOT_CHECK_SLUGS:
        response = client.get(f"/api/v1/exercises/{slug}")
        curated = get_curated_safety_notes(slug)

        assert response.status_code == 200
        assert curated is not None
        assert response.json()["safety_notes_fa"] == list(curated.fa)
        assert response.json()["safety_notes_en"] == list(curated.en)
