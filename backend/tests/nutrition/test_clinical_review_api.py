from datetime import UTC, date, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.body_analysis.enums import SpecialistRole
from app.body_analysis.models import UserSpecialistRole
from app.notifications.models import NotificationOutboxEvent
from app.nutrition.enums import (
    NutritionLabRequestStatus,
    NutritionPlanLifecycleStatus,
    NutritionPlanReviewStatus,
)
from app.nutrition.models import (
    NutritionLabDocument,
    NutritionLabRequest,
    NutritionPlanPhysicianReview,
    NutritionReviewAuditEvent,
    NutritionWeeklyPlan,
)
from app.profile.models import UserProfile
from tests.nutrition.test_weekly_plan_api import (
    ORIGIN,
    _register_and_estimate,
    _seed_foods_and_prices,
)


def _member_plan(
    client: TestClient,
    db: Session,
    email: str = "clinical-member@example.com",
    *,
    seed_catalogue: bool = True,
) -> dict[str, object]:
    _register_and_estimate(client, db, email)
    if seed_catalogue:
        _seed_foods_and_prices(db)
    response = client.post("/api/v1/nutrition/plans", headers=ORIGIN)
    assert response.status_code == 201
    return response.json()["plan"]


def _login_physician(
    client: TestClient,
    db: Session,
    email: str = "physician@example.com",
) -> User:
    assert client.post("/api/v1/auth/logout", headers=ORIGIN).status_code == 204
    assert (
        client.post(
            "/api/v1/auth/register",
            headers=ORIGIN,
            json={"email": email, "password": "long password"},
        ).status_code
        == 201
    )
    physician = db.scalar(select(User).where(User.email == email))
    assert physician is not None
    db.add(UserSpecialistRole(user_id=physician.id, role=SpecialistRole.PHYSICIAN))
    db.flush()
    return physician


def test_plan_generation_notifies_existing_physicians_of_required_review(
    client: TestClient,
    db: Session,
) -> None:
    assert (
        client.post(
            "/api/v1/auth/register",
            headers=ORIGIN,
            json={
                "email": "existing-physician@example.com",
                "password": "long password",
            },
        ).status_code
        == 201
    )
    physician = db.scalar(select(User).where(User.email == "existing-physician@example.com"))
    assert physician is not None
    db.add(UserSpecialistRole(user_id=physician.id, role=SpecialistRole.PHYSICIAN))
    db.flush()
    assert client.post("/api/v1/auth/logout", headers=ORIGIN).status_code == 204

    plan = _member_plan(client, db)

    event = db.scalar(
        select(NotificationOutboxEvent).where(
            NotificationOutboxEvent.user_id == physician.id,
            NotificationOutboxEvent.event_type == "nutrition_review_required",
        )
    )
    assert event is not None
    assert event.payload["data"]["plan_id"] == plan["id"]


def test_lab_upload_is_private_and_physician_request_has_explicit_state(
    client: TestClient, db: Session
) -> None:
    plan = _member_plan(client, db)
    uploaded = client.post(
        "/api/v1/nutrition/labs",
        headers=ORIGIN,
        files={"file": ("blood.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
        data={"category": "blood_panel", "laboratory_name": "Test Lab"},
    )
    assert uploaded.status_code == 201, uploaded.text
    document_id = uploaded.json()["id"]
    grant = client.post(f"/api/v1/nutrition/labs/{document_id}/access-grant", headers=ORIGIN)
    assert grant.status_code == 200
    assert client.get(grant.json()["access_url"]).status_code == 200

    physician = _login_physician(client, db)
    queue = client.get("/api/v1/nutrition/physician/reviews")
    assert queue.status_code == 200
    review = next(item for item in queue.json() if item["plan_id"] == plan["id"])
    assert (
        client.post(
            f"/api/v1/nutrition/physician/reviews/{review['review_id']}/claim", headers=ORIGIN
        ).status_code
        == 200
    )
    physician_view = client.get(f"/api/v1/nutrition/physician/plans/{plan['id']}")
    assert physician_view.status_code == 200
    assert physician_view.json()["id"] == plan["id"]

    request = client.post(
        f"/api/v1/nutrition/physician/plans/{plan['id']}/request-labs",
        headers=ORIGIN,
        json={
            "expected_plan_revision_id": plan["id"],
            "requested_tests": ["CBC"],
            "user_visible_reason": "برای بررسی ایمن‌تر برنامه",
        },
    )
    assert request.status_code == 200, request.text
    assert request.json()["status"] == "requested"
    persisted = db.scalar(select(NutritionWeeklyPlan).where(NutritionWeeklyPlan.id == plan["id"]))
    assert persisted is not None and persisted.lifecycle_status.value == "awaiting_lab_information"
    lab_request = db.scalar(select(NutritionLabRequest))
    assert lab_request is not None and lab_request.physician_user_id == physician.id
    physician_grant = client.post(
        f"/api/v1/nutrition/labs/{document_id}/access-grant", headers=ORIGIN
    )
    assert physician_grant.status_code == 200
    assert client.get(physician_grant.json()["access_url"]).status_code == 200

    assert client.post("/api/v1/auth/logout", headers=ORIGIN).status_code == 204
    assert (
        client.post(
            "/api/v1/auth/login",
            headers=ORIGIN,
            json={"email": "clinical-member@example.com", "password": "long password"},
        ).status_code
        == 200
    )
    requests = client.get("/api/v1/nutrition/lab-requests")
    assert requests.status_code == 200
    assert requests.json()[0]["requested_tests"] == ["CBC"]
    assert requests.json()[0]["user_visible_reason"] == "برای بررسی ایمن‌تر برنامه"


def test_duplicate_lab_document_can_satisfy_multiple_lab_requests(
    client: TestClient,
    db: Session,
) -> None:
    plan = _member_plan(client, db)
    persisted_plan = db.get(NutritionWeeklyPlan, plan["id"])
    assert persisted_plan is not None
    physician = _login_physician(client, db, "multi-request-lab-physician@example.com")
    assert client.post("/api/v1/auth/logout", headers=ORIGIN).status_code == 204
    assert (
        client.post(
            "/api/v1/auth/login",
            headers=ORIGIN,
            json={"email": "clinical-member@example.com", "password": "long password"},
        ).status_code
        == 200
    )
    requests = [
        NutritionLabRequest(
            user_id=persisted_plan.user_id,
            plan_id=persisted_plan.id,
            physician_user_id=physician.id,
            status=NutritionLabRequestStatus.REQUESTED,
            requested_tests=[test_name],
        )
        for test_name in ("CBC", "Ferritin", "Vitamin D")
    ]
    db.add_all(requests)
    db.flush()
    request_ids = [str(item.id) for item in requests]
    db.commit()

    first_upload = client.post(
        "/api/v1/nutrition/labs",
        headers=ORIGIN,
        files=[
            ("file", ("blood.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")),
            ("request_ids", (None, request_ids[0])),
            ("request_ids", (None, request_ids[1])),
        ],
    )
    reused_upload = client.post(
        "/api/v1/nutrition/labs",
        headers=ORIGIN,
        files=[
            ("file", ("blood-copy.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")),
            ("request_ids", (None, request_ids[2])),
        ],
    )

    assert first_upload.status_code == 201, first_upload.text
    assert reused_upload.status_code == 201, reused_upload.text
    assert reused_upload.json()["id"] == first_upload.json()["id"]
    assert reused_upload.json()["duplicate"] is True
    assert set(reused_upload.json()["request_ids"]) == set(request_ids)
    assert reused_upload.json()["request_id"] == request_ids[0]
    assert {item.status for item in requests} == {NutritionLabRequestStatus.UPLOADED}
    listed = client.get("/api/v1/nutrition/labs")
    assert listed.status_code == 200
    assert set(listed.json()[0]["request_ids"]) == set(request_ids)

    assert client.post("/api/v1/auth/logout", headers=ORIGIN).status_code == 204
    assert (
        client.post(
            "/api/v1/auth/login",
            headers=ORIGIN,
            json={
                "email": "multi-request-lab-physician@example.com",
                "password": "long password",
            },
        ).status_code
        == 200
    )
    review = next(
        item
        for item in client.get("/api/v1/nutrition/physician/reviews").json()
        if item["plan_id"] == plan["id"]
    )
    assert (
        client.post(
            f"/api/v1/nutrition/physician/reviews/{review['review_id']}/claim",
            headers=ORIGIN,
        ).status_code
        == 200
    )
    reviewed = client.put(
        f"/api/v1/nutrition/physician/labs/{first_upload.json()['id']}/review",
        headers=ORIGIN,
        json={"review_status": "reviewed", "notes": "بررسی شد"},
    )
    assert reviewed.status_code == 200, reviewed.text
    assert {item.status for item in requests} == {NutritionLabRequestStatus.REVIEWED}


def test_lab_review_resumes_physician_plan_review(
    client: TestClient,
    db: Session,
) -> None:
    plan = _member_plan(client, db)
    physician_email = "resume-lab-review-physician@example.com"
    _login_physician(client, db, physician_email)
    review = next(
        item
        for item in client.get("/api/v1/nutrition/physician/reviews").json()
        if item["plan_id"] == plan["id"]
    )
    claimed = client.post(
        f"/api/v1/nutrition/physician/reviews/{review['review_id']}/claim",
        headers=ORIGIN,
    )
    assert claimed.status_code == 200, claimed.text
    request = client.post(
        f"/api/v1/nutrition/physician/plans/{plan['id']}/request-labs",
        headers=ORIGIN,
        json={
            "expected_plan_revision_id": plan["id"],
            "requested_tests": ["CBC"],
            "user_visible_reason": "نتیجه برای ادامهٔ بررسی لازم است",
        },
    )
    assert request.status_code == 200, request.text
    assert request.json()["status"] == "requested"

    assert client.post("/api/v1/auth/logout", headers=ORIGIN).status_code == 204
    assert (
        client.post(
            "/api/v1/auth/login",
            headers=ORIGIN,
            json={"email": "clinical-member@example.com", "password": "long password"},
        ).status_code
        == 200
    )
    uploaded = client.post(
        "/api/v1/nutrition/labs",
        headers=ORIGIN,
        files=[
            ("file", ("blood.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")),
            ("request_ids", (None, request.json()["id"])),
        ],
    )
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["request_ids"] == [request.json()["id"]]

    assert client.post("/api/v1/auth/logout", headers=ORIGIN).status_code == 204
    assert (
        client.post(
            "/api/v1/auth/login",
            headers=ORIGIN,
            json={"email": physician_email, "password": "long password"},
        ).status_code
        == 200
    )
    reviewed = client.put(
        f"/api/v1/nutrition/physician/labs/{uploaded.json()['id']}/review",
        headers=ORIGIN,
        json={"review_status": "reviewed", "notes": "بررسی شد"},
    )

    assert reviewed.status_code == 200, reviewed.text
    db.expire_all()
    persisted_plan = db.get(NutritionWeeklyPlan, plan["id"])
    persisted_review = db.scalar(
        select(NutritionPlanPhysicianReview).where(
            NutritionPlanPhysicianReview.plan_id == plan["id"]
        )
    )
    persisted_request = db.get(NutritionLabRequest, request.json()["id"])
    assert persisted_plan is not None
    assert persisted_review is not None
    assert persisted_request is not None
    assert persisted_request.status is NutritionLabRequestStatus.REVIEWED
    assert persisted_review.status is NutritionPlanReviewStatus.IN_REVIEW
    assert (
        persisted_plan.lifecycle_status is NutritionPlanLifecycleStatus.PHYSICIAN_REVIEW_IN_PROGRESS
    )
    claimed_queue = client.get("/api/v1/nutrition/physician/reviews?view=claimed")
    assert claimed_queue.status_code == 200
    resumed = next(item for item in claimed_queue.json() if item["plan_id"] == plan["id"])
    assert resumed["status"] == NutritionPlanReviewStatus.IN_REVIEW.value


def test_resolving_requests_waits_for_last_lab_request_before_resuming(
    client: TestClient,
    db: Session,
) -> None:
    plan = _member_plan(client, db)
    physician_email = "cancel-lab-review-physician@example.com"
    physician = _login_physician(client, db, physician_email)
    review = next(
        item
        for item in client.get("/api/v1/nutrition/physician/reviews").json()
        if item["plan_id"] == plan["id"]
    )
    claimed = client.post(
        f"/api/v1/nutrition/physician/reviews/{review['review_id']}/claim",
        headers=ORIGIN,
    )
    assert claimed.status_code == 200, claimed.text
    request = client.post(
        f"/api/v1/nutrition/physician/plans/{plan['id']}/request-labs",
        headers=ORIGIN,
        json={
            "expected_plan_revision_id": plan["id"],
            "requested_tests": ["CBC"],
            "user_visible_reason": "درخواست لغو شد",
        },
    )
    assert request.status_code == 200, request.text
    persisted_plan = db.get(NutritionWeeklyPlan, plan["id"])
    assert persisted_plan is not None
    additional_request = NutritionLabRequest(
        user_id=persisted_plan.user_id,
        plan_id=persisted_plan.id,
        physician_user_id=physician.id,
        status=NutritionLabRequestStatus.REQUESTED,
        requested_tests=["Ferritin"],
    )
    db.add(additional_request)
    db.commit()

    assert client.post("/api/v1/auth/logout", headers=ORIGIN).status_code == 204
    assert (
        client.post(
            "/api/v1/auth/login",
            headers=ORIGIN,
            json={"email": "clinical-member@example.com", "password": "long password"},
        ).status_code
        == 200
    )
    uploaded = client.post(
        "/api/v1/nutrition/labs",
        headers=ORIGIN,
        files=[
            ("file", ("blood.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")),
            ("request_ids", (None, request.json()["id"])),
        ],
    )
    assert uploaded.status_code == 201, uploaded.text
    assert client.post("/api/v1/auth/logout", headers=ORIGIN).status_code == 204
    assert (
        client.post(
            "/api/v1/auth/login",
            headers=ORIGIN,
            json={"email": physician_email, "password": "long password"},
        ).status_code
        == 200
    )

    resolved_first = client.put(
        f"/api/v1/nutrition/physician/lab-requests/{request.json()['id']}",
        headers=ORIGIN,
        json={"status": "reviewed"},
    )

    assert resolved_first.status_code == 200, resolved_first.text
    db.expire_all()
    persisted_plan = db.get(NutritionWeeklyPlan, plan["id"])
    persisted_review = db.scalar(
        select(NutritionPlanPhysicianReview).where(
            NutritionPlanPhysicianReview.plan_id == plan["id"]
        )
    )
    assert persisted_plan is not None
    assert persisted_review is not None
    assert persisted_review.status is NutritionPlanReviewStatus.AWAITING_LAB_INFORMATION
    assert persisted_plan.lifecycle_status is NutritionPlanLifecycleStatus.AWAITING_LAB_INFORMATION

    cancelled_last = client.put(
        f"/api/v1/nutrition/physician/lab-requests/{additional_request.id}",
        headers=ORIGIN,
        json={"status": "cancelled"},
    )

    assert cancelled_last.status_code == 200, cancelled_last.text
    db.expire_all()
    persisted_plan = db.get(NutritionWeeklyPlan, plan["id"])
    persisted_review = db.scalar(
        select(NutritionPlanPhysicianReview).where(
            NutritionPlanPhysicianReview.plan_id == plan["id"]
        )
    )
    assert persisted_plan is not None
    assert persisted_review is not None
    assert persisted_review.status is NutritionPlanReviewStatus.IN_REVIEW
    assert (
        persisted_plan.lifecycle_status is NutritionPlanLifecycleStatus.PHYSICIAN_REVIEW_IN_PROGRESS
    )


def test_upload_cannot_reopen_cancelled_lab_request(
    client: TestClient,
    db: Session,
) -> None:
    plan = _member_plan(client, db)
    _login_physician(client, db, "cancelled-upload-physician@example.com")
    review = next(
        item
        for item in client.get("/api/v1/nutrition/physician/reviews").json()
        if item["plan_id"] == plan["id"]
    )
    claimed = client.post(
        f"/api/v1/nutrition/physician/reviews/{review['review_id']}/claim",
        headers=ORIGIN,
    )
    assert claimed.status_code == 200, claimed.text
    requested = client.post(
        f"/api/v1/nutrition/physician/plans/{plan['id']}/request-labs",
        headers=ORIGIN,
        json={
            "expected_plan_revision_id": plan["id"],
            "requested_tests": ["CBC"],
            "user_visible_reason": "برای بررسی تکمیلی",
        },
    )
    assert requested.status_code == 200, requested.text

    cancelled = client.put(
        f"/api/v1/nutrition/physician/lab-requests/{requested.json()['id']}",
        headers=ORIGIN,
        json={"status": "cancelled"},
    )
    assert cancelled.status_code == 200, cancelled.text

    assert client.post("/api/v1/auth/logout", headers=ORIGIN).status_code == 204
    logged_in = client.post(
        "/api/v1/auth/login",
        headers=ORIGIN,
        json={"email": "clinical-member@example.com", "password": "long password"},
    )
    assert logged_in.status_code == 200, logged_in.text
    uploaded = client.post(
        "/api/v1/nutrition/labs",
        headers=ORIGIN,
        files=[
            ("file", ("cancelled.pdf", b"%PDF-1.4\ncancelled\n%%EOF", "application/pdf")),
            ("request_ids", (None, requested.json()["id"])),
        ],
    )

    assert uploaded.status_code == 409
    assert uploaded.json()["detail"]["code"] == "LAB_REQUEST_NOT_OPEN"
    persisted_request = db.get(NutritionLabRequest, requested.json()["id"])
    assert persisted_request is not None
    assert persisted_request.status is NutritionLabRequestStatus.CANCELLED


def test_non_physician_cannot_access_review_queue(client: TestClient, db: Session) -> None:
    _member_plan(client, db)
    response = client.get("/api/v1/nutrition/physician/reviews")
    assert response.status_code == 403


def test_admin_status_does_not_grant_physician_role(client: TestClient, db: Session) -> None:
    _member_plan(client, db)
    member = db.scalar(select(User).where(User.email == "clinical-member@example.com"))
    assert member is not None
    member.is_admin = True
    db.flush()

    response = client.get("/api/v1/nutrition/physician/reviews")

    assert response.status_code == 403


def test_physician_cannot_access_ai_price_administration_endpoints(
    client: TestClient,
    db: Session,
) -> None:
    _member_plan(client, db)
    _login_physician(client, db, "price-boundary-physician@example.com")

    monitoring = client.get("/api/v1/nutrition/admin/monitoring")
    price_research = client.post(
        "/api/v1/nutrition/admin/foods/unknown/price-research",
        headers=ORIGIN,
    )

    assert monitoring.status_code == 403
    assert price_research.status_code == 403


def test_mixed_physician_admin_keeps_both_explicit_capabilities(
    client: TestClient,
    db: Session,
) -> None:
    _member_plan(client, db)
    physician = _login_physician(client, db, "mixed-physician-admin@example.com")
    physician.is_admin = True
    db.flush()

    physician_queue = client.get("/api/v1/nutrition/physician/reviews")
    admin_monitoring = client.get("/api/v1/nutrition/admin/monitoring")

    assert physician_queue.status_code == 200
    assert admin_monitoring.status_code == 200


def test_physician_rejection_requires_current_revision_and_cannot_be_replayed(
    client: TestClient,
    db: Session,
) -> None:
    plan = _member_plan(client, db)
    physician = _login_physician(client, db, "rejection-physician@example.com")
    review = next(
        item
        for item in client.get("/api/v1/nutrition/physician/reviews").json()
        if item["plan_id"] == plan["id"]
    )
    assert (
        client.post(
            f"/api/v1/nutrition/physician/reviews/{review['review_id']}/claim",
            headers=ORIGIN,
        ).status_code
        == 200
    )

    stale = client.post(
        f"/api/v1/nutrition/physician/plans/{plan['id']}/action",
        headers=ORIGIN,
        json={
            "expected_plan_revision_id": str(uuid4()),
            "action": "reject",
            "notes": "نسخهٔ قدیمی است",
        },
    )
    missing_notes = client.post(
        f"/api/v1/nutrition/physician/plans/{plan['id']}/action",
        headers=ORIGIN,
        json={
            "expected_plan_revision_id": plan["id"],
            "action": "reject",
            "notes": "  ",
        },
    )
    rejected = client.post(
        f"/api/v1/nutrition/physician/plans/{plan['id']}/action",
        headers=ORIGIN,
        json={
            "expected_plan_revision_id": plan["id"],
            "action": "reject",
            "notes": "به اطلاعات تکمیلی نیاز است",
        },
    )
    replay = client.post(
        f"/api/v1/nutrition/physician/plans/{plan['id']}/action",
        headers=ORIGIN,
        json={
            "expected_plan_revision_id": plan["id"],
            "action": "reject",
            "notes": "تلاش تکراری",
        },
    )

    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "STALE_PLAN_REVISION"
    assert missing_notes.status_code == 409
    assert missing_notes.json()["detail"]["code"] == "REVIEW_NOTES_REQUIRED"
    assert rejected.status_code == 200
    assert rejected.json()["review_status"] == "rejected"
    assert replay.status_code == 409
    assert replay.json()["detail"]["code"] == "REVIEW_NOT_IN_PROGRESS"

    audit_rows = db.scalars(
        select(NutritionReviewAuditEvent).where(
            NutritionReviewAuditEvent.review_id == review["review_id"]
        )
    ).all()
    rejection_events = [row for row in audit_rows if row.action == "reject"]
    assert len(rejection_events) == 1
    assert rejection_events[0].actor_user_id == physician.id
    assert rejection_events[0].metadata_snapshot == {
        "plan_id": plan["id"],
        "revision": plan["revision"],
    }


def test_assigned_review_cannot_be_taken_over_or_approved_by_another_physician(
    client: TestClient,
    db: Session,
) -> None:
    plan = _member_plan(client, db)
    first = _login_physician(client, db, "first-physician@example.com")
    review = next(
        item
        for item in client.get("/api/v1/nutrition/physician/reviews").json()
        if item["plan_id"] == plan["id"]
    )
    assert (
        client.post(
            f"/api/v1/nutrition/physician/reviews/{review['review_id']}/claim",
            headers=ORIGIN,
        ).status_code
        == 200
    )

    second = _login_physician(client, db, "second-physician@example.com")
    response = client.post(
        f"/api/v1/nutrition/physician/plans/{plan['id']}/action",
        headers=ORIGIN,
        json={
            "expected_plan_revision_id": plan["id"],
            "action": "approve",
            "notes": "تأیید",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "REVIEW_ASSIGNED_TO_ANOTHER_PHYSICIAN"
    persisted = db.scalar(
        select(NutritionPlanPhysicianReview).where(
            NutritionPlanPhysicianReview.plan_id == plan["id"]
        )
    )
    assert persisted is not None and persisted.physician_user_id == first.id
    assert persisted.physician_user_id != second.id


def test_assigned_physician_can_read_current_medical_context_only_for_the_assigned_case(
    client: TestClient,
    db: Session,
) -> None:
    plan = _member_plan(client, db)
    safety = client.put(
        "/api/v1/nutrition/safety",
        headers=ORIGIN,
        json={
            "conditions": [{"code": "kidney_disease", "details": "مرحله دوم"}],
            "medications": [{"name": "داروی نمونه", "dosage": "10 mg", "notes": "صبح"}],
            "dangerous_food_reaction_history": False,
            "pregnant": False,
            "breastfeeding": False,
            "eating_disorder_diagnosed": False,
            "eating_disorder_active_symptoms": False,
            "emergency_or_danger_symptoms": False,
            "complex_medication_food_interaction": False,
            "physician_dietary_restrictions": "نمک کم",
            "other_relevant_condition": "فشار خون",
        },
    )
    assert safety.status_code == 200, safety.text

    _login_physician(client, db, "context-physician@example.com")
    review = next(
        item
        for item in client.get("/api/v1/nutrition/physician/reviews").json()
        if item["plan_id"] == plan["id"]
    )
    assert (
        client.post(
            f"/api/v1/nutrition/physician/reviews/{review['review_id']}/claim",
            headers=ORIGIN,
        ).status_code
        == 200
    )

    context = client.get(f"/api/v1/nutrition/physician/plans/{plan['id']}/medical-context")

    assert context.status_code == 200, context.text
    assert context.json()["conditions"] == [{"code": "kidney_disease", "details": "مرحله دوم"}]
    assert context.json()["medications"] == [
        {"name": "داروی نمونه", "dosage": "10 mg", "notes": "صبح"}
    ]
    assert context.json()["physician_dietary_restrictions"] == "نمک کم"
    assert context.json()["other_relevant_condition"] == "فشار خون"
    assert context.json()["safety_reason_codes"]

    _login_physician(client, db, "unassigned-context-physician@example.com")
    denied = client.get(f"/api/v1/nutrition/physician/plans/{plan['id']}/medical-context")
    assert denied.status_code == 409
    assert denied.json()["detail"]["code"] == "REVIEW_ASSIGNED_TO_ANOTHER_PHYSICIAN"


def test_approval_requires_claim_and_activates_exact_due_revision(
    client: TestClient,
    db: Session,
) -> None:
    plan = _member_plan(client, db)
    physician = _login_physician(client, db, "approval-physician@example.com")
    db.add(UserProfile(user_id=physician.id, display_name="دکتر نادری"))
    db.flush()
    payload = {
        "expected_plan_revision_id": plan["id"],
        "action": "approve",
        "notes": "از نظر پزشکی تأیید شد",
        "internal_notes": "یادداشت محرمانه پزشک",
    }
    unclaimed = client.post(
        f"/api/v1/nutrition/physician/plans/{plan['id']}/action",
        headers=ORIGIN,
        json=payload,
    )
    assert unclaimed.status_code == 409
    assert unclaimed.json()["detail"]["code"] == "REVIEW_NOT_CLAIMED"

    review = next(
        item
        for item in client.get("/api/v1/nutrition/physician/reviews").json()
        if item["plan_id"] == plan["id"]
    )
    assert (
        client.post(
            f"/api/v1/nutrition/physician/reviews/{review['review_id']}/claim",
            headers=ORIGIN,
        ).status_code
        == 200
    )
    persisted = db.get(NutritionWeeklyPlan, plan["id"])
    assert persisted is not None
    persisted.start_date = date.today()
    db.commit()

    approved = client.post(
        f"/api/v1/nutrition/physician/plans/{plan['id']}/action",
        headers=ORIGIN,
        json=payload,
    )

    assert approved.status_code == 200, approved.text
    assert approved.json()["lifecycle_status"] == "ready_to_start"
    assert approved.json()["physician_approved"] is True
    assert approved.json()["physician_display_name"] == "دکتر نادری"
    assert "internal_notes" not in approved.json()
    persisted = db.get(NutritionWeeklyPlan, plan["id"])
    assert persisted is not None and persisted.review is not None
    assert persisted.review.internal_notes == "یادداشت محرمانه پزشک"
    member = db.scalar(select(User).where(User.email == "clinical-member@example.com"))
    assert member is not None
    approval_event = db.scalar(
        select(NotificationOutboxEvent).where(
            NotificationOutboxEvent.user_id == member.id,
            NotificationOutboxEvent.event_type == "physician_plan_approved",
        )
    )
    assert approval_event is not None
    assert approval_event.payload["data"] == {
        "event_type": "physician_plan_approved",
        "plan_id": plan["id"],
        "action": "approve",
    }


def test_physician_cannot_approve_plan_after_medical_context_changes(
    client: TestClient,
    db: Session,
) -> None:
    plan = _member_plan(client, db)
    changed_safety = client.put(
        "/api/v1/nutrition/safety",
        headers=ORIGIN,
        json={
            "conditions": [],
            "medications": [{"name": "داروی روزانه", "dosage": "10 mg", "notes": None}],
            "dangerous_food_reaction_history": False,
            "pregnant": False,
            "breastfeeding": False,
            "eating_disorder_diagnosed": False,
            "eating_disorder_active_symptoms": False,
            "emergency_or_danger_symptoms": False,
            "complex_medication_food_interaction": False,
            "physician_dietary_restrictions": None,
            "other_relevant_condition": None,
        },
    )
    assert changed_safety.status_code == 200, changed_safety.text
    physician = _login_physician(client, db, "stale-plan-physician@example.com")
    db.add(UserProfile(user_id=physician.id, display_name="دکتر بازبین"))
    db.flush()
    review = next(
        item
        for item in client.get("/api/v1/nutrition/physician/reviews").json()
        if item["plan_id"] == plan["id"]
    )
    claimed = client.post(
        f"/api/v1/nutrition/physician/reviews/{review['review_id']}/claim",
        headers=ORIGIN,
    )
    assert claimed.status_code == 200, claimed.text

    response = client.post(
        f"/api/v1/nutrition/physician/plans/{plan['id']}/action",
        headers=ORIGIN,
        json={
            "expected_plan_revision_id": plan["id"],
            "action": "approve",
            "notes": "تأیید",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "NUTRITION_PLAN_MEDICAL_CONTEXT_CHANGED"


def test_physician_queue_views_move_a_case_from_pending_to_claimed_to_approved(
    client: TestClient,
    db: Session,
) -> None:
    plan = _member_plan(client, db)
    physician = _login_physician(client, db, "queue-physician@example.com")

    pending = client.get("/api/v1/nutrition/physician/reviews?view=pending")

    assert pending.status_code == 200
    pending_case = next(item for item in pending.json() if item["plan_id"] == plan["id"])
    assert pending_case["member_display_name"] == "کاربر برنامه"
    assert pending_case["status"] == "pending"
    assert "internal_notes" not in pending_case
    assert client.get("/api/v1/nutrition/physician/reviews?view=claimed").json() == []

    claimed = client.post(
        f"/api/v1/nutrition/physician/reviews/{pending_case['review_id']}/claim",
        headers=ORIGIN,
    )

    assert claimed.status_code == 200
    claimed_cases = client.get("/api/v1/nutrition/physician/reviews?view=claimed").json()
    claimed_case = next(item for item in claimed_cases if item["plan_id"] == plan["id"])
    assert claimed_case["physician_user_id"] == str(physician.id)
    assert not any(
        item["plan_id"] == plan["id"]
        for item in client.get("/api/v1/nutrition/physician/reviews?view=pending").json()
    )

    persisted = db.get(NutritionWeeklyPlan, plan["id"])
    assert persisted is not None
    persisted.start_date = date.today()
    db.commit()
    approved = client.post(
        f"/api/v1/nutrition/physician/plans/{plan['id']}/action",
        headers=ORIGIN,
        json={
            "expected_plan_revision_id": plan["id"],
            "action": "approve",
            "notes": "نسخه نهایی تأیید شد",
            "internal_notes": "یادداشت خصوصی",
        },
    )

    assert approved.status_code == 200
    approved_cases = client.get("/api/v1/nutrition/physician/reviews?view=approved").json()
    approved_case = next(item for item in approved_cases if item["plan_id"] == plan["id"])
    assert approved_case["status"] == "approved"
    assert approved_case["reviewed_at"] is not None
    assert "internal_notes" not in approved_case

    _login_physician(client, db, "other-queue-physician@example.com")
    assert not any(
        item["plan_id"] == plan["id"]
        for item in client.get("/api/v1/nutrition/physician/reviews?view=approved").json()
    )


def test_assigned_physician_plan_includes_live_member_profile_summary(
    client: TestClient,
    db: Session,
) -> None:
    plan = _member_plan(client, db, "live-summary-member@example.com")
    _login_physician(client, db, "live-summary-physician@example.com")
    review = next(
        item
        for item in client.get("/api/v1/nutrition/physician/reviews").json()
        if item["plan_id"] == plan["id"]
    )

    claimed = client.post(
        f"/api/v1/nutrition/physician/reviews/{review['review_id']}/claim",
        headers=ORIGIN,
    )
    response = client.get(f"/api/v1/nutrition/physician/plans/{plan['id']}")

    assert claimed.status_code == 200
    assert response.status_code == 200
    summary = response.json()["profile_summary"]
    assert summary["height_cm"] == 165
    assert summary["weight_kg"] == "62.50"
    assert summary["training_location"] is None
    assert summary["nutrition"]["cooking_equipment"] == []
    assert summary["medical"]["safety_outcome"] == "standard_automatic"
    assert summary["medical"]["conditions"] == []
    assert summary["medical"]["medications"] == []


def test_physician_queue_orders_each_view_by_requested_at(
    client: TestClient,
    db: Session,
) -> None:
    older_plan = _member_plan(client, db, "queue-order-older@example.com")
    assert client.post("/api/v1/auth/logout", headers=ORIGIN).status_code == 204
    newer_plan = _member_plan(
        client,
        db,
        "queue-order-newer@example.com",
        seed_catalogue=False,
    )
    older_review = db.scalar(
        select(NutritionPlanPhysicianReview).where(
            NutritionPlanPhysicianReview.plan_id == older_plan["id"]
        )
    )
    newer_review = db.scalar(
        select(NutritionPlanPhysicianReview).where(
            NutritionPlanPhysicianReview.plan_id == newer_plan["id"]
        )
    )
    assert older_review is not None and newer_review is not None
    older_review.requested_at = datetime(2026, 9, 10, 8, tzinfo=UTC)
    newer_review.requested_at = datetime(2026, 9, 14, 8, tzinfo=UTC)

    physician = _login_physician(client, db, "queue-order-physician@example.com")
    for view, status in (
        ("pending", NutritionPlanReviewStatus.PENDING),
        ("claimed", NutritionPlanReviewStatus.IN_REVIEW),
        ("approved", NutritionPlanReviewStatus.APPROVED),
    ):
        older_review.status = status
        newer_review.status = status
        older_review.physician_user_id = physician.id if view != "pending" else None
        newer_review.physician_user_id = physician.id if view != "pending" else None
        db.commit()

        response = client.get(f"/api/v1/nutrition/physician/reviews?view={view}")

        assert response.status_code == 200
        assert [item["plan_id"] for item in response.json()] == [
            newer_plan["id"],
            older_plan["id"],
        ]


def test_assigned_physician_can_list_and_review_member_labs(
    client: TestClient,
    db: Session,
) -> None:
    plan = _member_plan(client, db)
    uploaded = client.post(
        "/api/v1/nutrition/labs",
        headers=ORIGIN,
        files={"file": ("blood.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")},
        data={"category": "blood_panel", "laboratory_name": "آزمایشگاه"},
    )
    assert uploaded.status_code == 201
    document_id = uploaded.json()["id"]
    _login_physician(client, db, "lab-review-physician@example.com")
    review = next(
        item
        for item in client.get("/api/v1/nutrition/physician/reviews").json()
        if item["plan_id"] == plan["id"]
    )
    assert (
        client.post(
            f"/api/v1/nutrition/physician/reviews/{review['review_id']}/claim",
            headers=ORIGIN,
        ).status_code
        == 200
    )

    listed = client.get(f"/api/v1/nutrition/physician/plans/{plan['id']}/labs")
    reviewed = client.put(
        f"/api/v1/nutrition/physician/labs/{document_id}/review",
        headers=ORIGIN,
        json={"review_status": "reviewed", "notes": "بررسی شد"},
    )

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [document_id]
    assert reviewed.status_code == 200, reviewed.text
    row = db.get(NutritionLabDocument, document_id)
    assert row is not None and row.review_status == "reviewed"
    assert row.reviewed_at is not None
