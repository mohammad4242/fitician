from uuid import NAMESPACE_URL, uuid5

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

CURRENT_ACTIVE_CHEST_TRAINING_SLUGS = frozenset(
    {
        "dumbbell-bench-press",
        "fedb-0025-barbell-bench-press",
        "fedb-0033-barbell-decline-bench-press",
        "fedb-0047-barbell-incline-bench-press",
        "fedb-0301-decline-dumbbell-bench-press",
        "fedb-0302-decline-dumbbell-fly",
        "fedb-0308-dumbbell-fly",
        "fedb-0314-dumbbell-incline-bench-press",
        "fedb-0319-dumbbell-incline-fly",
        "fedb-0321-dumbbell-incline-hammer-press",
        "fedb-0340-dumbbell-lying-hammer-press",
        "fedb-0493-incline-push-up",
        "fedb-0577-lever-lying-chest-press",
        "fedb-0620-flat-bench-cable-fly",
        "fedb-1269-cable-standing-fly",
        "fedb-1274-deep-push-up",
        "fedb-1277-dumbbell-fly-on-exercise-ball",
        "fedb-1278-dumbbell-incline-fly-on-exercise-ball",
        "fedb-1299-lever-incline-hammer-chest-press",
        "fedb-drv-band-high-fly-resistance-band-high-fly",
        "fedb-drv-chest-dips-chest-dips",
        "fedb-drv-lever-pec-deck-fly-pec-deck-fly",
        "fedb-drv-push-ups-push-up",
        "fedb-drv-rotate-push-up-female-rotational-push-up",
        "owner-10b53230907d-incline-dumbbell-bench-press",
        "owner-1f8e38bb4987-v-bar-close-grip-bench-press",
        "owner-58fc33e9ee2f-barbell-bench-press",
        "owner-70511e2a29d7-barbell-bench-press",
        "owner-8f222e61e93c-pec-deck-fly",
        "owner-94176702df28-barbell-bench-press",
        "owner-9cfaf45c29f4-push-up-variations-decline-and-deep",
        "owner-a7f5c2f31bca-pec-deck-fly",
        "owner-cb58d2dbac7f-dumbbell-bench-press",
        "owner-db0d7c3471db-pec-deck-fly",
        "owner-ed7a7bc1b137-barbell-bench-press-variations",
    }
)


def _seed_active_chest_training_catalog(db: Session) -> None:
    from app.exercises.curated_safety_notes import get_curated_safety_notes

    seed_exercises(db)
    for slug in sorted(CURRENT_ACTIVE_CHEST_TRAINING_SLUGS):
        if slug == "dumbbell-bench-press":
            continue
        curated = get_curated_safety_notes(slug)
        assert curated is not None, slug
        exercise_type = (
            ExerciseType.ISOLATION
            if "fly" in slug or "pec-deck" in slug
            else ExerciseType.COMPOUND
        )
        db.add(
            Exercise(
                id=uuid5(NAMESPACE_URL, f"https://fitsho.test/chest-safety/{slug}"),
                slug=slug,
                name_en=slug.replace("-", " ").title(),
                name_fa="حرکت تمرینی سینه",
                body_region=BodyRegion.UPPER_BODY,
                primary_muscle=MuscleGroup.CHEST,
                muscle_focus=MuscleFocus.GENERAL_CHEST,
                difficulty=Difficulty.INTERMEDIATE,
                movement_pattern=MovementPattern.HORIZONTAL_PUSH,
                exercise_type=exercise_type,
                instructions_en=["Set up.", "Move with control.", "Return safely."],
                instructions_fa=["آماده شو.", "حرکت را کنترل کن.", "ایمن برگرد."],
                safety_notes_en=list(curated.en),
                safety_notes_fa=list(curated.fa),
                media_path="/exercises/exercise-placeholder.svg",
                media_type=MediaType.PLACEHOLDER,
                source="curated-chest-test",
                source_id=slug,
                is_active=True,
                is_programmable=True,
            )
        )
    db.flush()


def test_every_active_chest_training_exercise_has_ordered_curated_notes(db: Session) -> None:
    from app.exercises.curated_safety_notes import get_curated_safety_notes

    _seed_active_chest_training_catalog(db)
    exercises = list(
        db.scalars(
            select(Exercise)
            .where(
                Exercise.is_active.is_(True),
                Exercise.primary_muscle == MuscleGroup.CHEST,
                Exercise.exercise_type != ExerciseType.MOBILITY,
            )
            .order_by(Exercise.slug)
        )
    )

    assert {exercise.slug for exercise in exercises} == CURRENT_ACTIVE_CHEST_TRAINING_SLUGS
    for exercise in exercises:
        curated = get_curated_safety_notes(exercise.slug)
        assert curated is not None, exercise.slug
        assert 2 <= len(curated.fa) <= 5
        assert len(curated.fa) == len(curated.en)
        assert all(note.strip() for note in (*curated.fa, *curated.en))
        assert exercise.safety_notes_fa == list(curated.fa)
        assert exercise.safety_notes_en == list(curated.en)


def test_canonical_template_placeholders_reuse_curated_alias_notes() -> None:
    from app.exercises.curated_safety_notes import get_curated_safety_notes
    from app.training_templates.catalog_placeholders import _placeholder_exercise
    from app.training_templates.seed_data import TemplateSlotSeed

    for slug in ("machine-chest-press", "pec-deck-fly"):
        exercise = _placeholder_exercise(
            TemplateSlotSeed(
                exercise_slug_hint=slug,
                catalog_slug_hints=(slug,),
                target_muscles=(MuscleGroup.CHEST,),
                movement_pattern=MovementPattern.HORIZONTAL_PUSH,
            )
        )
        curated = get_curated_safety_notes(slug)
        assert curated is not None
        assert exercise.safety_notes_fa == list(curated.fa)
        assert exercise.safety_notes_en == list(curated.en)
