from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
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
from app.workout_reviews.enums import WorkoutReviewErrorCode, WorkoutReviewStatus
from app.workout_reviews.models import WorkoutPlanReview
from app.workout_reviews.repository import ensure_pending_review
from app.workout_reviews.schemas import WorkoutReviewDraftUpdate
from app.workout_reviews.service import ReviewConflict, WorkoutReviewService
from app.workouts.enums import WorkoutPlanStatus
from app.workouts.models import WorkoutDay, WorkoutPlan, WorkoutPlanExercise


def _user(db: Session, prefix: str) -> User:
    user = User(email=f"{prefix}-{uuid4()}@example.com", password_hash="hash")
    db.add(user)
    db.flush()
    return user


def _exercise(db: Session, slug: str) -> Exercise:
    exercise = Exercise(
        slug=f"{slug}-{uuid4().hex}",
        name_en=slug.replace("-", " ").title(),
        name_fa=f"حرکت {slug}",
        body_region=BodyRegion.UPPER_BODY,
        primary_muscle=MuscleGroup.CHEST,
        muscle_focus=MuscleFocus.MID_CHEST,
        difficulty=Difficulty.BEGINNER,
        movement_pattern=MovementPattern.HORIZONTAL_PUSH,
        exercise_type=ExerciseType.COMPOUND,
        instructions_en=["Set up.", "Move safely.", "Finish."],
        instructions_fa=["آماده شو.", "ایمن حرکت کن.", "تمام کن."],
        safety_notes_en=["Move with control."],
        safety_notes_fa=["کنترل‌شده حرکت کن."],
        media_path="/exercises/exercise-placeholder.svg",
        media_type=MediaType.PLACEHOLDER,
        is_active=True,
        is_programmable=True,
        needs_review=False,
    )
    db.add(exercise)
    db.flush()
    return exercise


def _snapshot(exercise: Exercise) -> dict[str, object]:
    return {
        "id": str(exercise.id),
        "primary_muscle": exercise.primary_muscle.value,
        "secondary_muscles": [],
        "movement_pattern": exercise.movement_pattern.value,
        "exercise_type": exercise.exercise_type.value,
        "equipment": [],
        "difficulty": exercise.difficulty.value,
        "caution_tags": [],
        "labels": [],
    }


def _plan(db: Session, member: User, exercises: list[Exercise]) -> WorkoutPlan:
    plan = WorkoutPlan(
        user_id=member.id,
        status=WorkoutPlanStatus.ACTIVE,
        generation_signature="a" * 64,
        profile_snapshot={"plan_duration_weeks": 4, "session_duration_minutes": 45},
        provider="fake",
        model_id="fake-model",
        prompt_version="v1",
        generation_policy_version="v1",
        candidate_set_hash="b" * 64,
        generation_method="ai",
        exercise_catalog_snapshot={
            "exercises": {str(item.id): _snapshot(item) for item in exercises}
        },
    )
    day = WorkoutDay(
        day_number=1,
        title_en="Upper body",
        title_fa="بالاتنه",
        estimated_duration_minutes=20,
    )
    day.exercises.append(
        WorkoutPlanExercise(
            exercise_id=exercises[0].id,
            order_index=1,
            sets=3,
            reps_min=8,
            reps_max=12,
            rest_seconds=90,
            rir=2,
            estimated_minutes=5,
            exercise_snapshot=_snapshot(exercises[0]),
        )
    )
    plan.days.append(day)
    db.add(plan)
    db.flush()
    return plan


def _draft_with_structure(review: WorkoutPlanReview, added: Exercise) -> WorkoutReviewDraftUpdate:
    assert review.draft_payload is not None
    payload = deepcopy(review.draft_payload)
    payload["expected_revision"] = review.draft_revision
    payload["days"][0]["exercises"].append(
        {
            "order_index": 2,
            "exercise_id": str(added.id),
            "sets": 2,
            "prescription_mode": "reps",
            "reps_min": 10,
            "reps_max": 15,
            "duration_min_seconds": None,
            "duration_max_seconds": None,
            "rir": 2,
            "rest_seconds": 60,
            "notes_en": None,
            "notes_fa": None,
        }
    )
    payload["days"].append(
        {
            "day_number": 2,
            "exercises": [
                {
                    "order_index": 1,
                    "exercise_id": str(added.id),
                    "sets": 2,
                    "prescription_mode": "reps",
                    "reps_min": 8,
                    "reps_max": 12,
                    "duration_min_seconds": None,
                    "duration_max_seconds": None,
                    "rir": 2,
                    "rest_seconds": 60,
                    "notes_en": None,
                    "notes_fa": None,
                }
            ],
        }
    )
    return WorkoutReviewDraftUpdate.model_validate(payload)


def test_coach_draft_accepts_added_day_and_exercise(db: Session) -> None:
    member = _user(db, "structure-member")
    coach = _user(db, "structure-coach")
    original = _exercise(db, "original-press")
    added = _exercise(db, "added-row")
    source = _plan(db, member, [original, added])
    review = ensure_pending_review(db, source)
    service = WorkoutReviewService(db)

    claimed = service.claim(review.id, coach.id)
    saved = service.save_draft(review.id, coach.id, _draft_with_structure(claimed, added))

    assert saved.draft_payload is not None
    assert len(saved.draft_payload["days"]) == 2
    assert len(saved.draft_payload["days"][0]["exercises"]) == 2


def test_coach_submission_waits_for_member_acceptance(db: Session) -> None:
    member = _user(db, "submit-member")
    coach = _user(db, "submit-coach")
    original = _exercise(db, "submit-original")
    added = _exercise(db, "submit-added")
    source = _plan(db, member, [original, added])
    review = ensure_pending_review(db, source)
    service = WorkoutReviewService(db)
    claimed = service.claim(review.id, coach.id)
    saved = service.save_draft(review.id, coach.id, _draft_with_structure(claimed, added))

    submitted = service.submit_for_member(
        review.id, coach.id, expected_revision=saved.draft_revision
    )

    assert submitted.status is WorkoutReviewStatus.AWAITING_MEMBER_ACCEPTANCE
    assert submitted.proposed_plan is not None
    assert submitted.proposed_plan.status is WorkoutPlanStatus.PENDING_REVIEW
    assert source.status is WorkoutPlanStatus.ACTIVE
    assert submitted.approved_plan_id is None


def test_member_rejection_returns_case_to_same_coach(db: Session) -> None:
    member = _user(db, "reject-member")
    coach = _user(db, "reject-coach")
    original = _exercise(db, "reject-original")
    added = _exercise(db, "reject-added")
    source = _plan(db, member, [original, added])
    review = ensure_pending_review(db, source)
    service = WorkoutReviewService(db)
    claimed = service.claim(review.id, coach.id)
    saved = service.save_draft(review.id, coach.id, _draft_with_structure(claimed, added))
    submitted = service.submit_for_member(
        review.id, coach.id, expected_revision=saved.draft_revision
    )

    rejected = service.reject_by_member(review.id, member.id, "روز دوم را ساده‌تر کن")

    assert rejected.status is WorkoutReviewStatus.MEMBER_CHANGES_REQUESTED
    assert rejected.member_rejection_note == "روز دوم را ساده‌تر کن"
    assert rejected.claimed_by_user_id == coach.id
    assert source.status is WorkoutPlanStatus.ACTIVE

    reopened = service.claim(review.id, coach.id)
    assert reopened.status is WorkoutReviewStatus.CLAIMED
    assert reopened.proposed_plan_id == submitted.proposed_plan_id


def test_member_acceptance_activates_proposal_atomically_and_is_idempotent(db: Session) -> None:
    member = _user(db, "accept-member")
    coach = _user(db, "accept-coach")
    original = _exercise(db, "accept-original")
    added = _exercise(db, "accept-added")
    source = _plan(db, member, [original, added])
    review = ensure_pending_review(db, source)
    service = WorkoutReviewService(db)
    claimed = service.claim(review.id, coach.id)
    saved = service.save_draft(review.id, coach.id, _draft_with_structure(claimed, added))
    submitted = service.submit_for_member(
        review.id, coach.id, expected_revision=saved.draft_revision
    )

    approved = service.accept_by_member(review.id, member.id)
    repeated = service.accept_by_member(review.id, member.id)

    assert approved.id == submitted.proposed_plan_id
    assert repeated.id == approved.id
    assert approved.status is WorkoutPlanStatus.ACTIVE
    assert source.status is WorkoutPlanStatus.SUPERSEDED
    assert review.status is WorkoutReviewStatus.APPROVED
    assert db.scalar(
        select(WorkoutPlan).where(
            WorkoutPlan.user_id == member.id,
            WorkoutPlan.status == WorkoutPlanStatus.ACTIVE,
        )
    ).id == approved.id


def test_member_cannot_accept_another_members_review(db: Session) -> None:
    member = _user(db, "owner-member")
    other = _user(db, "other-member")
    coach = _user(db, "owner-coach")
    original = _exercise(db, "owner-original")
    added = _exercise(db, "owner-added")
    source = _plan(db, member, [original, added])
    review = ensure_pending_review(db, source)
    service = WorkoutReviewService(db)
    claimed = service.claim(review.id, coach.id)
    saved = service.save_draft(review.id, coach.id, _draft_with_structure(claimed, added))
    service.submit_for_member(review.id, coach.id, expected_revision=saved.draft_revision)

    with pytest.raises(ReviewConflict) as error:
        service.accept_by_member(review.id, other.id)

    assert error.value.code is WorkoutReviewErrorCode.MEMBER_NOT_ALLOWED
