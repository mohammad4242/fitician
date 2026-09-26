from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.notifications.content import build_notification_payload
from app.notifications.outbox import enqueue_notification_event
from app.workout_reviews.diff import build_coach_difference_summary
from app.workout_reviews.enums import (
    EXCLUSIVE_ASSIGNMENT_STATUSES,
    WorkoutReviewErrorCode,
    WorkoutReviewQueueView,
    WorkoutReviewStatus,
)
from app.workout_reviews.models import WorkoutPlanReview
from app.workout_reviews.repository import (
    get_active_plan_for_update,
    get_review,
    get_review_for_update,
    list_reviews,
    supersede_open_review,
)
from app.workout_reviews.schemas import WorkoutReviewDraftUpdate
from app.workout_reviews.validation import ValidatedDraft, WorkoutReviewDraftValidator
from app.workouts.enums import WorkoutPlanStatus
from app.workouts.models import WorkoutDay, WorkoutPlan, WorkoutPlanExercise

LEASE_DURATION = timedelta(minutes=30)


class ReviewConflict(Exception):
    def __init__(self, code: WorkoutReviewErrorCode) -> None:
        super().__init__(code.value)
        self.code = code


class WorkoutReviewService:
    def __init__(
        self,
        db: Session,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._db = db
        self._clock = clock or (lambda: datetime.now(UTC))
        self._validator = WorkoutReviewDraftValidator(db)

    def detail(self, review_id: UUID, viewer_id: UUID | None = None) -> WorkoutPlanReview:
        review = get_review(self._db, review_id)
        if review is None:
            raise ReviewConflict(WorkoutReviewErrorCode.REVIEW_NOT_FOUND)
        if (
            viewer_id is not None
            and review.status in EXCLUSIVE_ASSIGNMENT_STATUSES
            and review.claimed_by_user_id != viewer_id
        ):
            raise ReviewConflict(WorkoutReviewErrorCode.REVIEW_ALREADY_CLAIMED)
        return review

    def queue(
        self,
        view: WorkoutReviewQueueView,
        coach_id: UUID,
    ) -> list[WorkoutPlanReview]:
        return list_reviews(self._db, view=view, coach_id=coach_id, now=self._clock())

    def claim(self, review_id: UUID, coach_id: UUID) -> WorkoutPlanReview:
        review = self._required_review(review_id)
        now = self._clock()
        self._require_open(review)
        if review.status is WorkoutReviewStatus.AWAITING_MEMBER_ACCEPTANCE:
            raise ReviewConflict(WorkoutReviewErrorCode.REVIEW_NOT_CLAIMED)
        if review.claimed_by_user_id is not None and review.claimed_by_user_id != coach_id:
            raise ReviewConflict(WorkoutReviewErrorCode.REVIEW_ALREADY_CLAIMED)
        review.status = WorkoutReviewStatus.CLAIMED
        review.claimed_by_user_id = coach_id
        review.lease_acquired_at = now
        review.lease_expires_at = None
        if review.draft_payload is None:
            review.draft_payload = self._initial_draft(review.source_plan)
        self._db.commit()
        return review

    def renew(self, review_id: UUID, coach_id: UUID) -> WorkoutPlanReview:
        review = self._required_review(review_id)
        self._require_claim(review, coach_id)
        return review

    def release(self, review_id: UUID, coach_id: UUID) -> WorkoutPlanReview:
        review = self._required_review(review_id)
        self._require_claim(review, coach_id)
        review.status = WorkoutReviewStatus.PENDING
        review.claimed_by_user_id = None
        review.lease_acquired_at = None
        review.lease_expires_at = None
        self._db.commit()
        return review

    def save_draft(
        self,
        review_id: UUID,
        coach_id: UUID,
        payload: WorkoutReviewDraftUpdate,
    ) -> WorkoutPlanReview:
        review = self._required_review(review_id)
        self._require_claim(review, coach_id)
        self._require_revision(review, payload.expected_revision)
        self._validator.validate(review.source_plan, payload)
        review.draft_payload = payload.model_dump(
            mode="json", exclude={"expected_revision", "coach_note"}
        )
        review.coach_note = payload.coach_note.strip() if payload.coach_note else None
        review.draft_revision += 1
        now = self._clock()
        review.lease_acquired_at = now
        review.lease_expires_at = now + LEASE_DURATION
        self._db.commit()
        return review

    def submit_for_member(
        self,
        review_id: UUID,
        coach_id: UUID,
        *,
        expected_revision: int,
    ) -> WorkoutPlanReview:
        review = self._required_review(review_id)
        if review.status is WorkoutReviewStatus.AWAITING_MEMBER_ACCEPTANCE:
            if review.claimed_by_user_id != coach_id:
                raise ReviewConflict(WorkoutReviewErrorCode.REVIEW_ALREADY_CLAIMED)
            self._require_revision(review, expected_revision)
            if review.proposed_plan is None:
                raise ReviewConflict(WorkoutReviewErrorCode.REVIEW_PROPOSAL_NOT_FOUND)
            return review
        self._require_claim(review, coach_id)
        self._require_revision(review, expected_revision)
        active = get_active_plan_for_update(self._db, review.user_id)
        self._require_current_source(review, active)
        payload = self._stored_payload(review, expected_revision)
        validated = self._validator.validate(review.source_plan, payload)
        proposal = self._clone_plan(
            review.source_plan,
            validated,
            regeneration_reason="coach_review_proposed",
        )
        now = self._clock()
        if review.proposed_plan is not None:
            review.proposed_plan.status = WorkoutPlanStatus.SUPERSEDED
            review.proposed_plan.superseded_at = now
        proposal.status = WorkoutPlanStatus.PENDING_REVIEW
        proposal.activated_at = None
        self._db.add(proposal)
        self._db.flush()
        review.proposed_plan_id = proposal.id
        review.approved_plan_id = None
        review.approved_at = None
        review.member_rejection_note = None
        review.status = WorkoutReviewStatus.AWAITING_MEMBER_ACCEPTANCE
        review.lease_expires_at = None
        enqueue_notification_event(
            self._db,
            user_id=review.user_id,
            event_type="workout_plan_acceptance_required",
            category="required_reviews",
            deduplication_key=f"workout-review:{review.id}:acceptance:{proposal.id}",
            payload=build_notification_payload(
                "workout_plan_acceptance_required",
                data={"review_id": review.id, "plan_id": proposal.id},
            ),
        )
        self._db.commit()
        return review

    def accept_by_member(
        self,
        review_id: UUID,
        member_id: UUID,
        *,
        expected_revision: int | None = None,
    ) -> WorkoutPlan:
        review = self._required_review(review_id)
        self._require_member(review, member_id)
        if review.status is WorkoutReviewStatus.APPROVED:
            if review.approved_plan is None:
                raise ReviewConflict(WorkoutReviewErrorCode.REVIEW_PROPOSAL_NOT_FOUND)
            return review.approved_plan
        if review.status is not WorkoutReviewStatus.AWAITING_MEMBER_ACCEPTANCE:
            raise ReviewConflict(
                WorkoutReviewErrorCode.REVIEW_NOT_AWAITING_MEMBER_ACCEPTANCE
            )
        if expected_revision is not None:
            self._require_revision(review, expected_revision)
        proposal = review.proposed_plan
        if proposal is None:
            raise ReviewConflict(WorkoutReviewErrorCode.REVIEW_PROPOSAL_NOT_FOUND)
        coach_id = review.claimed_by_user_id
        if coach_id is None:
            raise ReviewConflict(WorkoutReviewErrorCode.REVIEW_PROPOSAL_NOT_FOUND)
        active = get_active_plan_for_update(self._db, review.user_id)
        self._require_current_source(review, active)
        now = self._clock()
        if active is not None and active.id != review.source_plan_id:
            active.status = WorkoutPlanStatus.SUPERSEDED
            active.superseded_at = now
            supersede_open_review(self._db, active.id)
        review.source_plan.status = WorkoutPlanStatus.SUPERSEDED
        review.source_plan.superseded_at = now
        self._db.flush()
        proposal.status = WorkoutPlanStatus.ACTIVE
        proposal.activated_at = now
        proposal.difference_summary = build_coach_difference_summary(
            review.source_plan,
            proposal,
            review_id=review.id,
            coach_id=coach_id,
            previous_active_plan_id=(
                active.id if active is not None and active.id != review.source_plan_id else None
            ),
        )
        review.status = WorkoutReviewStatus.APPROVED
        review.approved_plan_id = proposal.id
        review.approved_at = now
        enqueue_notification_event(
            self._db,
            user_id=review.user_id,
            event_type="workout_plan_approved",
            category="approved_plans",
            deduplication_key=f"workout-plan:{proposal.id}:approved",
            payload=build_notification_payload(
                "workout_plan_approved",
                data={"plan_id": proposal.id},
            ),
        )
        self._db.commit()
        return proposal

    def reject_by_member(
        self,
        review_id: UUID,
        member_id: UUID,
        explanation: str,
        *,
        expected_revision: int | None = None,
    ) -> WorkoutPlanReview:
        review = self._required_review(review_id)
        self._require_member(review, member_id)
        if review.status is not WorkoutReviewStatus.AWAITING_MEMBER_ACCEPTANCE:
            raise ReviewConflict(
                WorkoutReviewErrorCode.REVIEW_NOT_AWAITING_MEMBER_ACCEPTANCE
            )
        if expected_revision is not None:
            self._require_revision(review, expected_revision)
        normalized_explanation = explanation.strip()
        if not normalized_explanation:
            raise ReviewConflict(WorkoutReviewErrorCode.REVIEW_EXPLANATION_REQUIRED)
        review.member_rejection_note = normalized_explanation
        review.status = WorkoutReviewStatus.MEMBER_CHANGES_REQUESTED
        if review.claimed_by_user_id is not None:
            enqueue_notification_event(
                self._db,
                user_id=review.claimed_by_user_id,
                event_type="workout_plan_changes_requested",
                category="required_reviews",
                deduplication_key=f"workout-review:{review.id}:changes:{review.draft_revision}",
                payload=build_notification_payload(
                    "workout_plan_changes_requested",
                    data={"review_id": review.id, "plan_id": review.source_plan_id},
                ),
            )
        self._db.commit()
        return review

    def approve(
        self,
        review_id: UUID,
        coach_id: UUID,
        *,
        expected_revision: int,
    ) -> WorkoutPlan:
        review = self._required_review(review_id)
        if review.status is WorkoutReviewStatus.APPROVED:
            if review.approved_plan is None:
                raise ReviewConflict(WorkoutReviewErrorCode.INVALID_DRAFT)
            return review.approved_plan
        self._require_claim(review, coach_id)
        self._require_revision(review, expected_revision)
        active = get_active_plan_for_update(self._db, review.user_id)
        if review.source_plan.status not in {
            WorkoutPlanStatus.PENDING_REVIEW,
            WorkoutPlanStatus.ACTIVE,
        } or (
            review.source_plan.status is WorkoutPlanStatus.ACTIVE
            and (active is None or active.id != review.source_plan_id)
        ):
            review.status = WorkoutReviewStatus.SUPERSEDED
            self._db.commit()
            raise ReviewConflict(WorkoutReviewErrorCode.REVIEW_SUPERSEDED)
        if review.draft_payload is None:
            raise ReviewConflict(WorkoutReviewErrorCode.INVALID_DRAFT)
        payload = WorkoutReviewDraftUpdate.model_validate(
            {
                **review.draft_payload,
                "expected_revision": expected_revision,
                "coach_note": review.coach_note,
            }
        )
        validated = self._validator.validate(review.source_plan, payload)
        approved = self._clone_approved_plan(
            review.source_plan,
            validated,
        )
        now = self._clock()
        if active is not None:
            active.status = WorkoutPlanStatus.SUPERSEDED
            active.superseded_at = now
            supersede_open_review(self._db, active.id)
        review.source_plan.status = WorkoutPlanStatus.SUPERSEDED
        review.source_plan.superseded_at = now
        approved.status = WorkoutPlanStatus.ACTIVE
        approved.activated_at = now
        self._db.add(approved)
        self._db.flush()
        approved.difference_summary = build_coach_difference_summary(
            review.source_plan,
            approved,
            review_id=review.id,
            coach_id=coach_id,
            previous_active_plan_id=active.id if active is not None else None,
        )
        self._db.flush()
        review.status = WorkoutReviewStatus.APPROVED
        review.approved_plan_id = approved.id
        review.approved_at = now
        enqueue_notification_event(
            self._db,
            user_id=approved.user_id,
            event_type="workout_plan_approved",
            category="approved_plans",
            deduplication_key=f"workout-plan:{approved.id}:approved",
            payload=build_notification_payload(
                "workout_plan_approved",
                data={"plan_id": approved.id},
            ),
        )
        self._db.commit()
        return approved

    def reject(
        self,
        review_id: UUID,
        coach_id: UUID,
        *,
        expected_revision: int,
        explanation: str,
    ) -> WorkoutPlanReview:
        review = self._required_review(review_id)
        self._require_claim(review, coach_id)
        self._require_revision(review, expected_revision)
        normalized_explanation = explanation.strip()
        if not normalized_explanation:
            raise ReviewConflict(WorkoutReviewErrorCode.REVIEW_EXPLANATION_REQUIRED)
        review.coach_note = normalized_explanation
        review.status = WorkoutReviewStatus.REJECTED
        self._db.commit()
        return review

    def _required_review(self, review_id: UUID) -> WorkoutPlanReview:
        review = get_review_for_update(self._db, review_id)
        if review is None:
            raise ReviewConflict(WorkoutReviewErrorCode.REVIEW_NOT_FOUND)
        return review

    @staticmethod
    def _require_open(review: WorkoutPlanReview) -> None:
        if review.status is WorkoutReviewStatus.APPROVED:
            raise ReviewConflict(WorkoutReviewErrorCode.REVIEW_ALREADY_APPROVED)
        if review.status is WorkoutReviewStatus.REJECTED:
            raise ReviewConflict(WorkoutReviewErrorCode.REVIEW_ALREADY_REJECTED)
        if review.status is WorkoutReviewStatus.SUPERSEDED:
            raise ReviewConflict(WorkoutReviewErrorCode.REVIEW_SUPERSEDED)

    def _require_claim(self, review: WorkoutPlanReview, coach_id: UUID) -> None:
        self._require_open(review)
        if review.status not in {
            WorkoutReviewStatus.CLAIMED,
            WorkoutReviewStatus.MEMBER_CHANGES_REQUESTED,
        }:
            raise ReviewConflict(WorkoutReviewErrorCode.REVIEW_NOT_CLAIMED)
        if review.claimed_by_user_id is None:
            raise ReviewConflict(WorkoutReviewErrorCode.REVIEW_NOT_CLAIMED)
        if review.claimed_by_user_id != coach_id:
            raise ReviewConflict(WorkoutReviewErrorCode.REVIEW_ALREADY_CLAIMED)

    def _require_current_source(
        self,
        review: WorkoutPlanReview,
        active: WorkoutPlan | None,
    ) -> None:
        if review.source_plan.status not in {
            WorkoutPlanStatus.PENDING_REVIEW,
            WorkoutPlanStatus.ACTIVE,
        } or (
            review.source_plan.status is WorkoutPlanStatus.ACTIVE
            and (active is None or active.id != review.source_plan_id)
        ):
            review.status = WorkoutReviewStatus.SUPERSEDED
            self._db.commit()
            raise ReviewConflict(WorkoutReviewErrorCode.REVIEW_SUPERSEDED)

    @staticmethod
    def _require_member(review: WorkoutPlanReview, member_id: UUID) -> None:
        if review.user_id != member_id:
            raise ReviewConflict(WorkoutReviewErrorCode.MEMBER_NOT_ALLOWED)

    @staticmethod
    def _require_revision(review: WorkoutPlanReview, expected_revision: int) -> None:
        if review.draft_revision != expected_revision:
            raise ReviewConflict(WorkoutReviewErrorCode.STALE_DRAFT_REVISION)

    @staticmethod
    def _stored_payload(
        review: WorkoutPlanReview,
        expected_revision: int,
    ) -> WorkoutReviewDraftUpdate:
        if review.draft_payload is None:
            raise ReviewConflict(WorkoutReviewErrorCode.INVALID_DRAFT)
        return WorkoutReviewDraftUpdate.model_validate(
            {
                **review.draft_payload,
                "expected_revision": expected_revision,
                "coach_note": review.coach_note,
            }
        )

    @staticmethod
    def _initial_draft(plan: WorkoutPlan) -> dict[str, object]:
        return {
            "days": [
                {
                    "day_number": day.day_number,
                    "title_en": day.title_en,
                    "title_fa": day.title_fa,
                    "exercises": [
                        {
                            "order_index": item.order_index,
                            "exercise_id": str(item.exercise_id),
                            "sets": item.sets,
                            "prescription_mode": item.prescription_mode.value,
                            "reps_min": item.reps_min,
                            "reps_max": item.reps_max,
                            "duration_min_seconds": item.duration_min_seconds,
                            "duration_max_seconds": item.duration_max_seconds,
                            "rir": item.rir,
                            "rest_seconds": item.rest_seconds,
                            "notes_en": item.notes_en,
                            "notes_fa": item.notes_fa,
                        }
                        for item in day.exercises
                    ],
                }
                for day in plan.days
            ]
        }

    @staticmethod
    def _clone_approved_plan(source: WorkoutPlan, validated: ValidatedDraft) -> WorkoutPlan:
        return WorkoutReviewService._clone_plan(
            source,
            validated,
            regeneration_reason="coach_review_approved",
        )

    @staticmethod
    def _clone_plan(
        source: WorkoutPlan,
        validated: ValidatedDraft,
        *,
        regeneration_reason: str,
    ) -> WorkoutPlan:
        plan = WorkoutPlan(
            user_id=source.user_id,
            status=WorkoutPlanStatus.GENERATING,
            generation_signature=source.generation_signature,
            profile_snapshot=deepcopy(source.profile_snapshot),
            provider=source.provider,
            model_id=source.model_id,
            prompt_version=source.prompt_version,
            generation_policy_version=source.generation_policy_version,
            candidate_set_hash=source.candidate_set_hash,
            generation_method="coach_review",
            engine_version=source.engine_version,
            ruleset_version=source.ruleset_version,
            primary_goal=source.primary_goal,
            secondary_goal=source.secondary_goal,
            training_status=source.training_status,
            safety_status=source.safety_status,
            seed=source.seed,
            exercise_catalog_snapshot=deepcopy(source.exercise_catalog_snapshot),
            assumptions=deepcopy(source.assumptions),
            warnings=deepcopy(source.warnings),
            validation_report=deepcopy(source.validation_report),
            aggregate_metrics=deepcopy(source.aggregate_metrics),
            decision_trace=deepcopy(source.decision_trace),
            body_analysis_provenance=deepcopy(source.body_analysis_provenance),
            ai_coach_template_slug=source.ai_coach_template_slug,
            ai_coach_program_explanation_fa=source.ai_coach_program_explanation_fa,
            progression_policy=deepcopy(source.progression_policy),
            previous_program_id=source.id,
            regeneration_reason=regeneration_reason,
        )
        source_days = {day.day_number: day for day in source.days}
        source_slots = {
            (day.day_number, item.order_index): item
            for day in source.days
            for item in day.exercises
        }
        catalog = source.exercise_catalog_snapshot.get("exercises", {})
        draft_days = {day.day_number: day for day in validated.payload.days}
        for output_day in validated.plan.days:
            draft_day = draft_days[output_day.day_number]
            source_day = source_days.get(output_day.day_number)
            day = WorkoutDay(
                day_number=output_day.day_number,
                title_en=output_day.title_en,
                title_fa=output_day.title_fa,
                estimated_duration_minutes=output_day.estimated_duration_minutes,
                weekday=source_day.weekday if source_day is not None else None,
                focus=source_day.focus if source_day is not None else "legacy",
                cardio=deepcopy(source_day.cardio) if source_day is not None else None,
                ai_coach_explanation_fa=(
                    source_day.ai_coach_explanation_fa if source_day is not None else None
                ),
            )
            source_items_by_exercise = {
                item.exercise_id: item for item in (source_day.exercises if source_day else [])
            }
            for output_item, draft_item in zip(
                output_day.exercises, draft_day.exercises, strict=True
            ):
                source_slot = source_slots.get((output_day.day_number, draft_item.order_index))
                source_item = source_slot
                matching_source_item = source_items_by_exercise.get(output_item.exercise_id)
                metadata_item = matching_source_item or source_item
                changed_exercise = (
                    source_item is None or output_item.exercise_id != source_item.exercise_id
                )
                snapshot = (
                    deepcopy(catalog.get(str(output_item.exercise_id), {}))
                    if isinstance(catalog, dict)
                    else {}
                )
                if not snapshot and metadata_item is not None:
                    snapshot = deepcopy(metadata_item.exercise_snapshot)
                day.exercises.append(
                    WorkoutPlanExercise(
                        exercise_id=output_item.exercise_id,
                        order_index=draft_item.order_index,
                        sets=output_item.sets,
                        prescription_mode=output_item.prescription_mode,
                        reps_min=output_item.reps_min,
                        reps_max=output_item.reps_max,
                        duration_min_seconds=output_item.duration_min_seconds,
                        duration_max_seconds=output_item.duration_max_seconds,
                        rest_seconds=output_item.rest_seconds,
                        rir=output_item.rir,
                        estimated_minutes=output_item.estimated_minutes,
                        notes_en=output_item.notes_en,
                        notes_fa=output_item.notes_fa,
                        exercise_snapshot=snapshot,
                        reason_codes=(
                            ["coach_added_exercise"]
                            if source_item is None
                            else ["coach_replaced_exercise"]
                            if changed_exercise
                            else deepcopy(metadata_item.reason_codes if metadata_item else [])
                        ),
                        substitution_exercise_ids=(
                            []
                            if changed_exercise
                            else deepcopy(
                                metadata_item.substitution_exercise_ids
                                if metadata_item
                                else []
                            )
                        ),
                        warmup_sets=metadata_item.warmup_sets if metadata_item else 0,
                        load_guidance=metadata_item.load_guidance if metadata_item else "",
                        progression_rule=(
                            metadata_item.progression_rule if metadata_item else "legacy"
                        ),
                    )
                )
            plan.days.append(day)
        return plan
