from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.entitlements.enums import AccessPackageCode, EntitlementCode, GrantSource
from app.entitlements.exceptions import EntitlementQuotaExceededError, EntitlementRequiredError
from app.entitlements.service import grant_package

ORIGIN = {"Origin": "http://localhost:5173"}


def register(client: TestClient, email: str) -> None:
    response = client.post(
        "/api/v1/auth/register",
        headers=ORIGIN,
        json={"email": email, "password": "long password"},
    )
    assert response.status_code == 201


def test_products_returns_catalog_without_prices(client: TestClient) -> None:
    response = client.get("/api/v1/products")

    assert response.status_code == 200
    products = response.json()
    assert len(products) == 8
    assert {item["code"] for item in products} == {code.value for code in AccessPackageCode}
    assert all("price" not in item and "currency" not in item for item in products)
    trial = next(item for item in products if item["code"] == "launch_trial")
    assert trial["kind"] == "trial"
    assert trial["is_purchasable"] is False
    assert {
        policy["entitlement"]
        for policy in trial["quota_policies"]
    } == {
        EntitlementCode.BODY_ANALYSIS_RUN.value,
        EntitlementCode.TRAINING_COACH_REVIEW.value,
        EntitlementCode.NUTRITION_PHYSICIAN_REVIEW.value,
    }


def test_my_entitlements_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/entitlements/me")

    assert response.status_code == 401


def test_my_entitlements_does_not_require_completed_profile(
    client: TestClient,
) -> None:
    register(client, "incomplete-profile@example.com")

    response = client.get("/api/v1/entitlements/me")

    assert response.status_code == 200
    body = response.json()
    assert body["primary_package"] == "launch_trial"
    assert body["active_packages"] == ["launch_trial", "free"]
    assert "training.plan.generate" in body["entitlements"]["granted"]


def test_my_entitlements_serializes_trial_and_quota_status(
    client: TestClient,
    db: Session,
) -> None:
    register(client, "trial-api@example.com")
    user = db.scalar(select(User).where(User.email == "trial-api@example.com"))
    assert user is not None
    now = datetime.now(UTC)
    grant_package(
        db,
        user.id,
        AccessPackageCode.LAUNCH_TRIAL,
        source=GrantSource.LAUNCH_TRIAL,
        starts_at=now,
        ends_at=now + timedelta(days=30),
        idempotency_key="launch_trial:v1",
    )

    response = client.get("/api/v1/entitlements/me")

    assert response.status_code == 200
    body = response.json()
    assert body["primary_package"] == "launch_trial"
    assert body["trial"]["active"] is True
    assert body["trial"]["ends_at"]
    assert "training.coach_review" in body["entitlements"]["granted"]
    quotas = {item["entitlement"]: item for item in body["entitlements"]["quotas"]}
    assert quotas["body_analysis.run"]["limit"] == 1
    assert quotas["body_analysis.run"]["remaining"] == 1
    assert quotas["body_analysis.run"]["window_days"] == 7


def test_standardized_entitlement_errors_are_structured(client: TestClient) -> None:
    app = client.app

    def missing() -> None:
        raise EntitlementRequiredError(EntitlementCode.TRAINING_PLAN_GENERATE)

    def exhausted() -> None:
        raise EntitlementQuotaExceededError(
            EntitlementCode.BODY_ANALYSIS_RUN,
            datetime(2026, 9, 19, tzinfo=UTC),
            retry_after_seconds=123,
        )

    app.add_api_route("/test-entitlement-required", missing, methods=["GET"])
    app.add_api_route("/test-entitlement-quota", exhausted, methods=["GET"])

    missing_response = client.get("/test-entitlement-required")
    quota_response = client.get("/test-entitlement-quota")

    assert missing_response.status_code == 403
    missing_detail = missing_response.json()["detail"]
    assert missing_detail["code"] == "ENTITLEMENT_REQUIRED"
    assert missing_detail["message"]
    assert missing_detail["retryable"] is False
    assert missing_detail["meta"] == {
        "entitlement": "training.plan.generate",
        "eligible_packages": ["training", "training_coach", "complete", "complete_care"],
    }
    assert missing_detail["request_id"]
    assert quota_response.status_code == 429
    assert quota_response.headers["retry-after"] == "123"
    quota_detail = quota_response.json()["detail"]
    assert quota_detail["code"] == "ENTITLEMENT_QUOTA_EXCEEDED"
    assert quota_detail["message"]
    assert quota_detail["retryable"] is True
    assert quota_detail["meta"] == {
        "entitlement": "body_analysis.run",
        "reset_at": "2026-09-19T00:00:00+00:00",
        "retry_after_seconds": 123,
    }
    assert quota_detail["request_id"]
