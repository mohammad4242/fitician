from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.account_deletion.models import AccountDeletionRequest, AccountDeletionStatus
from app.account_deletion.service import execute_due_account_deletions
from app.auth.models import AuthSession, MobileTokenFamily, User
from app.auth.security import hash_session_token, make_session_token
from app.auth.service import issue_mobile_tokens
from app.body_analysis.admin_config.enums import AIAuditAction
from app.body_analysis.admin_config.models import AIAuditEvent
from app.body_photos.enums import BodyPhotoCleanupReason, BodyPhotoPurpose, BodyPhotoView
from app.body_photos.models import BodyPhoto, BodyPhotoSession, BodyPhotoStorageCleanup
from app.config import Settings
from app.nutrition.models import (
    NutritionFoodPhotoEstimate,
    NutritionLabDocument,
    NutritionSecurityAuditEvent,
)
from app.profile.models import UserProfilePhoto
from app.workout_reviews.enums import WorkoutReviewStatus
from app.workout_reviews.models import WorkoutPlanReview
from app.workouts.enums import WorkoutPlanStatus
from app.workouts.models import WorkoutPlan

ORIGIN = {"Origin": "http://localhost:5173"}
PASSWORD = "long password"


def _register(client: TestClient, email: str = "delete@example.com") -> None:
    response = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 201


def _enable_deletion(test_settings: Settings) -> None:
    test_settings.account_deletion_enabled = True


def _account_deletion_request(
    db: Session,
    user: User,
    *,
    due_at: datetime,
) -> AccountDeletionRequest:
    deletion = AccountDeletionRequest(
        user_id=user.id,
        status=AccountDeletionStatus.PENDING,
        requested_at=due_at - timedelta(days=1),
        reauthenticated_at=due_at - timedelta(days=1),
        grace_period_ends_at=due_at,
    )
    db.add(deletion)
    db.flush()
    return deletion


def _coach_review(
    db: Session,
    *,
    member: User,
    coach: User,
    status: WorkoutReviewStatus,
    plan_status: WorkoutPlanStatus = WorkoutPlanStatus.ACTIVE,
) -> WorkoutPlanReview:
    plan = WorkoutPlan(
        user_id=member.id,
        status=plan_status,
        generation_signature="a" * 64,
        profile_snapshot={"plan_duration_weeks": 4},
        provider="fake",
        model_id="fake-model",
        prompt_version="v1",
        generation_policy_version="v1",
        candidate_set_hash="b" * 64,
        generation_method="ai",
    )
    db.add(plan)
    db.flush()
    review = WorkoutPlanReview(
        source_plan_id=plan.id,
        user_id=member.id,
        status=status,
        claimed_by_user_id=coach.id,
        lease_acquired_at=datetime.now(UTC),
        lease_expires_at=None,
    )
    db.add(review)
    db.flush()
    return review


def test_deletion_requires_explicit_confirmation_and_current_password(
    client: TestClient,
    test_settings: Settings,
) -> None:
    _enable_deletion(test_settings)
    _register(client)

    wrong_confirmation = client.post(
        "/api/v1/account-deletion",
        headers=ORIGIN,
        json={"confirmation": "delete", "password": PASSWORD},
    )
    wrong_password = client.post(
        "/api/v1/account-deletion",
        headers=ORIGIN,
        json={"confirmation": "DELETE", "password": "wrong password"},
    )
    accepted = client.post(
        "/api/v1/account-deletion",
        headers=ORIGIN,
        json={"confirmation": "DELETE", "password": PASSWORD},
    )

    assert wrong_confirmation.status_code == 422
    assert wrong_password.status_code == 403
    assert accepted.status_code == 202
    body = accepted.json()
    assert body["status"] == "pending"
    assert body["request_id"]
    assert body["grace_period_ends_at"]

    current = client.get("/api/v1/account-deletion")
    assert current.status_code == 200
    assert current.json() == body


def test_deletion_can_be_cancelled_and_requested_again(
    client: TestClient,
    test_settings: Settings,
) -> None:
    _enable_deletion(test_settings)
    _register(client, "repeat-delete@example.com")

    first = client.post(
        "/api/v1/account-deletion",
        headers=ORIGIN,
        json={"confirmation": "DELETE", "password": PASSWORD},
    )
    assert first.status_code == 202

    cancelled = client.post(
        "/api/v1/account-deletion/cancel",
        headers=ORIGIN,
        json={"confirmation": "CANCEL"},
    )
    second = client.post(
        "/api/v1/account-deletion",
        headers=ORIGIN,
        json={"confirmation": "DELETE", "password": PASSWORD},
    )

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert second.status_code == 202
    assert second.json()["status"] == "pending"
    assert second.json()["request_id"] != first.json()["request_id"]


def test_cookie_mutation_requires_trusted_origin(
    client: TestClient,
    test_settings: Settings,
) -> None:
    _enable_deletion(test_settings)
    _register(client, "origin-delete@example.com")

    response = client.post(
        "/api/v1/account-deletion",
        json={"confirmation": "DELETE", "password": PASSWORD},
    )

    assert response.status_code == 403


def test_mobile_bearer_reauthentication_does_not_require_cookie_origin(
    client: TestClient,
    test_settings: Settings,
) -> None:
    _enable_deletion(test_settings)
    _register(client, "mobile-delete@example.com")
    client.post("/api/v1/auth/logout", headers=ORIGIN)
    login = client.post(
        "/api/v1/auth/mobile/password",
        json={
            "email": "mobile-delete@example.com",
            "password": PASSWORD,
            "device_id": "delete-device",
            "platform": "android",
            "app_version": "1.0.0",
            "device_name": "Pixel",
        },
    )
    assert login.status_code == 200

    response = client.post(
        "/api/v1/account-deletion",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        json={"confirmation": "DELETE", "password": PASSWORD},
    )

    assert response.status_code == 202


def test_due_deletion_removes_user_and_revokes_all_auth_sessions(
    client: TestClient,
    db: Session,
    test_settings: Settings,
) -> None:
    _enable_deletion(test_settings)
    _register(client, "execute-delete@example.com")
    user = db.scalar(select(User).where(User.email == "execute-delete@example.com"))
    assert user is not None
    user_id = user.id
    ai_audit = AIAuditEvent(
        actor_user_id=user_id,
        action=AIAuditAction.CONNECTION_TESTED,
    )
    security_audit = NutritionSecurityAuditEvent(
        actor_user_id=user_id,
        owner_user_id=user_id,
        event_type="account_deletion_test",
        resource_type="test",
        outcome="success",
        metadata_snapshot={"safe": True},
    )
    db.add_all([ai_audit, security_audit])
    db.flush()
    mobile = issue_mobile_tokens(
        db,
        user,
        device_id="execute-device",
        platform="android",
        app_version="1.0.0",
        device_name="Pixel",
        access_ttl_seconds=10 * 60 * 60,
        refresh_ttl_seconds=3600,
    )
    request = client.post(
        "/api/v1/account-deletion",
        headers=ORIGIN,
        json={"confirmation": "DELETE", "password": PASSWORD},
    )
    assert request.status_code == 202
    deletion = db.get(AccountDeletionRequest, request.json()["request_id"])
    assert deletion is not None

    processed = execute_due_account_deletions(
        db,
        test_settings,
        now=deletion.grace_period_ends_at + timedelta(seconds=1),
    )

    assert processed == 1
    assert db.get(User, user_id) is None
    assert db.scalar(select(AuthSession).where(AuthSession.user_id == user_id)) is None
    assert db.scalar(select(MobileTokenFamily).where(MobileTokenFamily.user_id == user_id)) is None
    completed = db.get(AccountDeletionRequest, deletion.id)
    assert completed is not None
    assert completed.status == "completed"
    assert completed.user_id is None
    assert completed.completed_at is not None
    assert db.get(AIAuditEvent, ai_audit.id).actor_user_id is None
    retained_security_audit = db.get(NutritionSecurityAuditEvent, security_audit.id)
    assert retained_security_audit is not None
    assert retained_security_audit.actor_user_id is None
    assert retained_security_audit.owner_user_id is None
    assert client.get("/api/v1/auth/me").status_code == 401
    assert mobile.raw_access_token


def test_due_deletion_releases_claimed_coach_review(
    db: Session,
    test_settings: Settings,
) -> None:
    _enable_deletion(test_settings)
    member = User(email="claimed-review-member@example.com", password_hash="hash")
    coach = User(email="claimed-review-coach@example.com", password_hash="hash")
    db.add_all([member, coach])
    db.flush()
    review = _coach_review(
        db,
        member=member,
        coach=coach,
        status=WorkoutReviewStatus.CLAIMED,
    )
    coach_id = coach.id
    member_id = member.id
    review_id = review.id
    now = datetime.now(UTC)
    deletion = _account_deletion_request(db, coach, due_at=now - timedelta(seconds=1))

    processed = execute_due_account_deletions(db, test_settings, now=now)

    assert processed == 1
    assert db.get(User, coach_id) is None
    assert db.get(User, member_id) is not None
    completed = db.get(AccountDeletionRequest, deletion.id)
    assert completed is not None
    assert completed.status is AccountDeletionStatus.COMPLETED
    retained_review = db.get(WorkoutPlanReview, review_id)
    assert retained_review is not None
    assert retained_review.status is WorkoutReviewStatus.PENDING
    assert retained_review.claimed_by_user_id is None
    assert retained_review.lease_acquired_at is None
    assert retained_review.lease_expires_at is None


def test_due_deletion_detaches_coach_from_historical_approved_review(
    db: Session,
    test_settings: Settings,
) -> None:
    _enable_deletion(test_settings)
    member = User(email="approved-review-member@example.com", password_hash="hash")
    coach = User(email="approved-review-coach@example.com", password_hash="hash")
    db.add_all([member, coach])
    db.flush()
    historical_reviews: list[tuple[WorkoutReviewStatus, WorkoutPlanReview, WorkoutPlan]] = []
    for index, status in enumerate(
        (
            WorkoutReviewStatus.APPROVED,
            WorkoutReviewStatus.REJECTED,
            WorkoutReviewStatus.SUPERSEDED,
        )
    ):
        review = _coach_review(
            db,
            member=member,
            coach=coach,
            status=status,
            plan_status=(WorkoutPlanStatus.ACTIVE if index == 0 else WorkoutPlanStatus.SUPERSEDED),
        )
        review.coach_note = f"Historical {status.value} note"
        review.draft_payload = {"history": status.value}
        review.member_rejection_note = "Retain member feedback"
        plan = db.get(WorkoutPlan, review.source_plan_id)
        assert plan is not None
        historical_reviews.append((status, review, plan))
    coach_id = coach.id
    member_id = member.id
    now = datetime.now(UTC)
    deletion = _account_deletion_request(db, coach, due_at=now - timedelta(seconds=1))

    processed = execute_due_account_deletions(db, test_settings, now=now)

    assert processed == 1
    assert db.get(User, coach_id) is None
    assert db.get(User, member_id) is not None
    completed = db.get(AccountDeletionRequest, deletion.id)
    assert completed is not None
    assert completed.status is AccountDeletionStatus.COMPLETED
    for expected_status, original_review, plan in historical_reviews:
        assert db.get(WorkoutPlan, plan.id) is not None
        retained_review = db.get(WorkoutPlanReview, original_review.id)
        assert retained_review is not None
        assert retained_review.status is expected_status
        assert retained_review.claimed_by_user_id is None
        assert retained_review.lease_acquired_at is None
        assert retained_review.lease_expires_at is None
        assert retained_review.coach_note == f"Historical {expected_status.value} note"
        assert retained_review.draft_payload == {"history": expected_status.value}
        assert retained_review.member_rejection_note == "Retain member feedback"


def test_claimed_coach_deletion_does_not_block_next_due_account(
    db: Session,
    test_settings: Settings,
) -> None:
    _enable_deletion(test_settings)
    member = User(email="batch-review-member@example.com", password_hash="hash")
    coach = User(email="batch-review-coach@example.com", password_hash="hash")
    next_user = User(email="batch-next-delete@example.com", password_hash="hash")
    db.add_all([member, coach, next_user])
    db.flush()
    review = _coach_review(
        db,
        member=member,
        coach=coach,
        status=WorkoutReviewStatus.CLAIMED,
    )
    coach_id = coach.id
    next_user_id = next_user.id
    review_id = review.id
    now = datetime.now(UTC)
    coach_deletion = _account_deletion_request(
        db,
        coach,
        due_at=now - timedelta(seconds=2),
    )
    next_deletion = _account_deletion_request(
        db,
        next_user,
        due_at=now - timedelta(seconds=1),
    )

    processed = execute_due_account_deletions(db, test_settings, now=now, batch_size=2)

    assert processed == 2
    assert db.get(User, coach_id) is None
    assert db.get(User, next_user_id) is None
    for deletion_id in (coach_deletion.id, next_deletion.id):
        completed = db.get(AccountDeletionRequest, deletion_id)
        assert completed is not None
        assert completed.status is AccountDeletionStatus.COMPLETED
    returned_review = db.get(WorkoutPlanReview, review_id)
    assert returned_review is not None
    assert returned_review.status is WorkoutReviewStatus.PENDING
    assert returned_review.claimed_by_user_id is None
    assert returned_review.lease_acquired_at is None
    assert returned_review.lease_expires_at is None


def test_due_deletion_removes_every_private_media_object(
    client: TestClient,
    db: Session,
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    _enable_deletion(test_settings)
    test_settings.body_photo_storage_root = tmp_path / "body-photos"
    test_settings.profile_photo_storage_root = tmp_path / "profile-photos"
    test_settings.food_photo_storage_root = tmp_path / "food-photos"
    test_settings.nutrition_lab_storage_root = tmp_path / "nutrition-labs"
    _register(client, "media-delete@example.com")
    user = db.scalar(select(User).where(User.email == "media-delete@example.com"))
    assert user is not None
    now = datetime.now(UTC)

    body_key = "aa/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.jpg"
    failed_upload_key = "ab/abababababababababababababababab.jpg"
    profile_key = "bb/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.jpg"
    food_key = "cc/food-photo.jpg"
    lab_key = "dd/lab-report.pdf"
    for root, key in (
        (test_settings.body_photo_storage_root, body_key),
        (test_settings.body_photo_storage_root, failed_upload_key),
        (test_settings.profile_photo_storage_root, profile_key),
        (test_settings.food_photo_storage_root, food_key),
        (test_settings.nutrition_lab_storage_root, lab_key),
    ):
        path = root / key
        path.parent.mkdir(parents=True)
        path.write_bytes(b"private")

    body_session = BodyPhotoSession(
        user_id=user.id,
        purpose=BodyPhotoPurpose.PROGRESS_CHECK,
    )
    db.add(body_session)
    db.flush()
    db.add(
        BodyPhoto(
            session_id=body_session.id,
            view=BodyPhotoView.FRONT,
            storage_key=body_key,
            mime_type="image/jpeg",
            byte_size=7,
            width=256,
            height=512,
        )
    )
    db.add(
        BodyPhotoStorageCleanup(
            session_id=body_session.id,
            storage_key=failed_upload_key,
            reason=BodyPhotoCleanupReason.FAILED_UPLOAD_ROLLBACK,
        )
    )
    db.add(
        UserProfilePhoto(
            user_id=user.id,
            storage_key=profile_key,
            mime_type="image/jpeg",
            byte_size=7,
            width=256,
            height=256,
        )
    )
    db.add(
        NutritionFoodPhotoEstimate(
            user_id=user.id,
            storage_key=food_key,
            sha256="a" * 64,
            content_type="image/jpeg",
            byte_size=7,
            status="estimated",
            provider="test",
            raw_estimate={},
            mapped_items=[],
            consented_at=now,
            expires_at=now + timedelta(days=1),
        )
    )
    db.add(
        NutritionLabDocument(
            user_id=user.id,
            storage_key=lab_key,
            original_filename="lab-report.pdf",
            content_type="application/pdf",
            byte_size=7,
            sha256="b" * 64,
        )
    )
    db.commit()

    request = client.post(
        "/api/v1/account-deletion",
        headers=ORIGIN,
        json={"confirmation": "DELETE", "password": PASSWORD},
    )
    assert request.status_code == 202
    deletion = db.get(AccountDeletionRequest, request.json()["request_id"])
    assert deletion is not None
    assert (
        execute_due_account_deletions(
            db,
            test_settings,
            now=deletion.grace_period_ends_at + timedelta(seconds=1),
        )
        == 1
    )

    assert not (test_settings.body_photo_storage_root / body_key).exists()
    assert not (test_settings.body_photo_storage_root / failed_upload_key).exists()
    assert not (test_settings.profile_photo_storage_root / profile_key).exists()
    assert not (test_settings.food_photo_storage_root / food_key).exists()
    assert not (test_settings.nutrition_lab_storage_root / lab_key).exists()


def test_all_user_references_are_safe_for_account_deletion(db: Session) -> None:
    inspector = inspect(db.get_bind())
    for table in inspector.get_table_names():
        for foreign_key in inspector.get_foreign_keys(table):
            if foreign_key["referred_table"] == "users":
                assert foreign_key["options"].get("ondelete") in {"CASCADE", "SET NULL"}

    nullable_retained_references = {
        "body_analysis_reviews": "reviewer_id",
        "nutrition_food_price_overrides": "created_by_user_id",
        "nutrition_lab_requests": "physician_user_id",
        "nutrition_supplement_orders": "physician_user_id",
        "nutrition_supplement_order_audits": "actor_user_id",
        "nutrition_review_audit_events": "actor_user_id",
    }
    for table, column in nullable_retained_references.items():
        details = next(item for item in inspector.get_columns(table) if item["name"] == column)
        assert details["nullable"] is True


def test_status_is_none_for_an_authenticated_user_without_a_request(
    client: TestClient,
    test_settings: Settings,
) -> None:
    _enable_deletion(test_settings)
    _register(client, "no-delete@example.com")

    response = client.get("/api/v1/account-deletion")

    assert response.status_code == 200
    assert response.json() == {
        "status": "none",
        "request_id": None,
        "requested_at": None,
        "reauthenticated_at": None,
        "grace_period_ends_at": None,
        "cancelled_at": None,
        "completed_at": None,
    }


def test_fresh_mobile_session_is_required_for_passwordless_accounts(
    client: TestClient,
    db: Session,
    test_settings: Settings,
) -> None:
    _enable_deletion(test_settings)
    user = User(google_sub="google-delete-sub")
    db.add(user)
    db.flush()
    mobile = issue_mobile_tokens(
        db,
        user,
        device_id="google-delete-device",
        platform="android",
        app_version="1.0.0",
        device_name=None,
        access_ttl_seconds=900,
        refresh_ttl_seconds=3600,
    )

    response = client.post(
        "/api/v1/account-deletion",
        headers={"Authorization": f"Bearer {mobile.raw_access_token}"},
        json={"confirmation": "DELETE"},
    )

    assert response.status_code == 202


def test_passwordless_accounts_cannot_delete_from_an_old_mobile_session(
    client: TestClient,
    db: Session,
    test_settings: Settings,
) -> None:
    _enable_deletion(test_settings)
    user = User(google_sub="old-google-delete-sub")
    db.add(user)
    db.flush()
    mobile = issue_mobile_tokens(
        db,
        user,
        device_id="old-google-delete-device",
        platform="android",
        app_version="1.0.0",
        device_name=None,
        access_ttl_seconds=10 * 60 * 60,
        refresh_ttl_seconds=3600,
        now=datetime.now(UTC) - timedelta(hours=2),
    )

    response = client.post(
        "/api/v1/account-deletion",
        headers={"Authorization": f"Bearer {mobile.raw_access_token}"},
        json={"confirmation": "DELETE"},
    )

    assert response.status_code == 403


def test_fresh_passwordless_web_session_allows_external_deletion(
    client: TestClient,
    db: Session,
    test_settings: Settings,
) -> None:
    _enable_deletion(test_settings)
    now = datetime.now(UTC)
    user = User(google_sub="fresh-web-delete-sub")
    db.add(user)
    db.flush()
    raw_token, token_hash = make_session_token()
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=token_hash,
            created_at=now - timedelta(seconds=30),
            expires_at=now + timedelta(hours=1),
        )
    )
    db.commit()
    client.cookies.set(test_settings.session_cookie_name, raw_token)

    response = client.post(
        "/api/v1/account-deletion",
        headers=ORIGIN,
        json={"confirmation": "DELETE"},
    )

    assert response.status_code == 202


def test_old_passwordless_web_session_requires_reauthentication(
    client: TestClient,
    db: Session,
    test_settings: Settings,
) -> None:
    _enable_deletion(test_settings)
    now = datetime.now(UTC)
    user = User(google_sub="old-web-delete-sub")
    db.add(user)
    db.flush()
    raw_token, token_hash = make_session_token()
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_session_token(raw_token),
            created_at=now
            - timedelta(seconds=test_settings.account_deletion_reauth_window_seconds + 1),
            expires_at=now + timedelta(hours=1),
        )
    )
    db.commit()
    client.cookies.set(test_settings.session_cookie_name, raw_token)

    response = client.post(
        "/api/v1/account-deletion",
        headers=ORIGIN,
        json={"confirmation": "DELETE"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "RECENT_AUTHENTICATION_REQUIRED"
