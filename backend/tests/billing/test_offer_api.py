from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.billing.enums import BillingOfferCode
from app.billing.models import BillingOfferConfig

ORIGIN = {"Origin": "http://localhost:5173"}


def add_config(
    db: Session,
    code: BillingOfferCode = BillingOfferCode.TRAINING_4W,
    *,
    price: int = 1_250_000,
    active: bool = True,
    available_from: datetime | None = None,
    available_until: datetime | None = None,
) -> None:
    db.add(
        BillingOfferConfig(
            offer_code=code,
            price_irr=price,
            currency="IRR",
            is_active=active,
            available_from=available_from,
            available_until=available_until,
        )
    )
    db.flush()


def test_public_billing_offers_expose_immutable_catalog_and_db_price(
    client,
    db: Session,
) -> None:
    add_config(db)

    response = client.get("/api/v1/billing/offers")

    assert response.status_code == 200
    offers = response.json()
    assert len(offers) == 18
    training_4w = next(item for item in offers if item["offer_code"] == "training_4w")
    assert training_4w["package_code"] == "training"
    assert training_4w["duration_weeks"] == 4
    assert training_4w["price_irr"] == 1_250_000
    assert training_4w["currency"] == "IRR"
    assert training_4w["is_available"] is True
    assert "training.plan.generate" in training_4w["entitlements"]
    assert all(item["offer_code"] not in {"free", "launch_trial"} for item in offers)


def test_missing_or_out_of_window_price_config_is_unavailable(client, db: Session) -> None:
    now = datetime.now(UTC)
    add_config(
        db,
        BillingOfferCode.TRAINING_6W,
        available_from=now + timedelta(days=1),
    )

    response = client.get("/api/v1/billing/offers")

    assert response.status_code == 200
    offers = {item["offer_code"]: item for item in response.json()}
    assert offers["training_4w"]["price_irr"] is None
    assert offers["training_4w"]["is_available"] is False
    assert offers["training_6w"]["price_irr"] == 1_250_000
    assert offers["training_6w"]["is_available"] is False


def test_inactive_offer_is_not_available(client, db: Session) -> None:
    add_config(db, active=False)

    response = client.get("/api/v1/billing/offers")

    assert response.status_code == 200
    offer = next(item for item in response.json() if item["offer_code"] == "training_4w")
    assert offer["is_available"] is False
