from __future__ import annotations

from uuid import uuid4

from app.auth.models import User
from app.body_analysis.models import BodyAnalysis
from app.notifications.models import NotificationOutboxEvent
from app.notifications.outbox import enqueue_notification_event
from app.nutrition.models import NutritionFoodPhotoAnalysisJob


def test_durable_queue_models_have_optional_correlation_ids() -> None:
    assert BodyAnalysis.correlation_id.property.columns[0].nullable is True
    assert NutritionFoodPhotoAnalysisJob.correlation_id.property.columns[0].nullable is True
    assert NotificationOutboxEvent.correlation_id.property.columns[0].nullable is True


def test_notification_enqueue_persists_correlation_id(db) -> None:
    user_id = uuid4()
    db.add(User(id=user_id, email=f"correlation-{user_id}@example.com", password_hash="x"))
    db.flush()
    event = enqueue_notification_event(
        db,
        user_id=user_id,
        event_type="test",
        category="test",
        deduplication_key="test:correlation",
        payload={"data": {"id": "safe"}},
        correlation_id="request-123",
    )

    assert event.correlation_id == "request-123"
