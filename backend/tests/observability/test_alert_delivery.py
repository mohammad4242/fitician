from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.config import Settings
from app.observability.alert_delivery import claim_alert, complete_alert, enqueue_alerts
from app.observability.alert_sms import SmsReceipt
from app.observability.diagnostics_models import DiagnosticAlertAttempt, DiagnosticAlertDelivery
from app.observability.diagnostics_schemas import EventInput
from app.observability.diagnostics_service import record_event


def settings(now):
    return Settings(
        diagnostics_alert_enabled=True,
        diagnostics_alert_enabled_at=now - timedelta(seconds=1),
        diagnostics_alert_phone="+989123456789",
        frontend_origin="https://fitician.example",
    )


def occurrence(db, operation="workout_generation", category="application_bug"):
    return record_event(
        db,
        EventInput(
            component="acceptance",
            operation=operation,
            stage="failure",
            platform="backend",
            severity="error",
            category=category,
            error_code="UNHANDLED_EXCEPTION",
            outcome="failure",
        ),
    )


def test_repeated_occurrences_aggregate_into_one_sms_then_respect_cooldown(db):
    now = datetime.now(UTC)
    config = settings(now)
    for _ in range(5):
        occurrence(db)
    assert enqueue_alerts(db, config, now=now) == 1
    row = db.scalar(select(DiagnosticAlertDelivery))
    assert row.occurrence_total == 5
    assert claim_alert(db, config, now=now) is None
    job = claim_alert(db, config, now=now + timedelta(seconds=61))
    assert job is not None and "تکرار: 5" in job["text"]
    complete_alert(
        db,
        job["attempt_id"],
        SmsReceipt("accepted", provider_id="12345"),
        now=now + timedelta(seconds=62),
    )
    assert row.state == "accepted" and row.covered_count == 5
    occurrence(db)
    enqueue_alerts(db, config, now=now + timedelta(seconds=90))
    assert row.generation == 2 and row.occurrence_total == 6
    assert claim_alert(db, config, now=now + timedelta(minutes=10)) is None
    job2 = claim_alert(db, config, now=now + timedelta(hours=1, minutes=2))
    assert job2 is not None and "تکرار: 1" in job2["text"]
    assert len(list(db.scalars(select(DiagnosticAlertAttempt)))) == 2


def test_ambiguous_dispatch_and_worker_restart_never_resend_same_batch(db):
    now = datetime.now(UTC)
    config = settings(now)
    occurrence(db)
    enqueue_alerts(db, config, now=now)
    job = claim_alert(db, config, now=now + timedelta(seconds=61))
    assert job is not None
    # An interrupted worker may have sent the SMS before its acknowledgment was persisted.
    assert claim_alert(db, config, now=now + timedelta(minutes=5)) is None
    row = db.scalar(select(DiagnosticAlertDelivery))
    assert row.state == "uncertain"
    assert row.covered_count == 1
    assert enqueue_alerts(db, config, now=now + timedelta(hours=2)) == 0
    assert claim_alert(db, config, now=now + timedelta(hours=2)) is None


def test_expected_rejections_and_historical_issues_do_not_send_sms(db):
    now = datetime.now(UTC)
    occurrence(db, category="business_rejection")
    row = occurrence(db, operation="old_issue")
    from app.observability.diagnostics_models import DiagnosticIssue

    db.get(DiagnosticIssue, row.issue_id).last_seen = now - timedelta(days=2)
    db.flush()
    assert enqueue_alerts(db, settings(now), now=now) == 0
    assert claim_alert(db, settings(now), now=now + timedelta(hours=1)) is None


def test_global_dispatch_spacing_prevents_bursts_across_different_issues(db):
    now = datetime.now(UTC)
    config = settings(now)
    occurrence(db, operation="workout_generation")
    occurrence(db, operation="nutrition_generation")
    assert enqueue_alerts(db, config, now=now) == 2
    first = claim_alert(db, config, now=now + timedelta(seconds=61))
    complete_alert(
        db,
        first["attempt_id"],
        SmsReceipt("accepted", provider_id="1"),
        now=now + timedelta(seconds=62),
    )
    assert claim_alert(db, config, now=now + timedelta(seconds=63)) is None
    assert claim_alert(db, config, now=now + timedelta(seconds=92)) is not None


def test_receipt_recovery_is_read_only_and_updates_the_original_attempt(db):
    from app.observability.alert_delivery import claim_receipt, record_receipt

    now = datetime.now(UTC)
    config = settings(now)
    occurrence(db)
    enqueue_alerts(db, config, now=now)
    job = claim_alert(db, config, now=now + timedelta(seconds=61))
    complete_alert(db, job["attempt_id"], SmsReceipt("uncertain"), now=now + timedelta(seconds=62))
    notice = claim_receipt(db, now=now + timedelta(seconds=95))
    assert notice == job["attempt_id"]
    record_receipt(
        db,
        notice,
        SmsReceipt("provider_delivered", provider_id="12345"),
        now=now + timedelta(seconds=96),
    )
    row = db.scalar(select(DiagnosticAlertDelivery))
    assert row.state == "provider_delivered" and row.provider_message_id == "12345"
    assert claim_receipt(db, now=now + timedelta(hours=1)) is None
    assert claim_alert(db, config, now=now + timedelta(hours=1)) is None
    assert len(list(db.scalars(select(DiagnosticAlertAttempt)))) == 1


def test_notification_status_requires_admin_and_never_exports_destination(client, db, monkeypatch):
    from tests.admin.test_ai_task_settings_api import _admin

    base = "/api/v1/admin/diagnostics/notification-deliveries"
    assert client.get(base).status_code == 401
    _admin(client, db)
    now = datetime.now(UTC)
    occurrence(db)
    enqueue_alerts(db, settings(now), now=now)
    db.commit()
    response = client.get(base)
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["state"] == "queued"
    assert "09123456789" not in response.text and "+989123456789" not in response.text
    monkeypatch.setenv("DIAGNOSTICS_ENVIRONMENT", "different-environment")
    assert client.get(base).json()["items"] == []


def test_retention_keeps_pending_sms_and_expires_closed_completed_delivery_audit(db):
    from app.observability.diagnostics_models import DiagnosticIssue
    from app.observability.diagnostics_service import cleanup_retention

    now = datetime.now(UTC)
    config = settings(now)
    event = occurrence(db)
    enqueue_alerts(db, config, now=now)
    issue = db.get(DiagnosticIssue, event.issue_id)
    issue.status = "resolved"
    db.flush()
    cleanup_retention(db, now=now + timedelta(days=100))
    assert db.get(DiagnosticIssue, event.issue_id) is not None
    row = db.scalar(select(DiagnosticAlertDelivery))
    row.state = "accepted"
    db.flush()
    cleanup_retention(db, now=now + timedelta(days=100))
    assert db.get(DiagnosticAlertDelivery, row.id) is None


def test_regression_can_notify_before_the_regular_per_issue_cooldown(db):
    from app.observability.diagnostics_models import DiagnosticIssue

    now = datetime.now(UTC)
    config = settings(now)
    event = occurrence(db)
    enqueue_alerts(db, config, now=now)
    first = claim_alert(db, config, now=now + timedelta(seconds=61))
    complete_alert(
        db,
        first["attempt_id"],
        SmsReceipt("accepted", provider_id="1"),
        now=now + timedelta(seconds=62),
    )
    issue = db.get(DiagnosticIssue, event.issue_id)
    issue.status = "resolved"
    db.flush()
    occurrence(db)
    enqueue_alerts(db, config, now=now + timedelta(seconds=90))
    assert claim_alert(db, config, now=now + timedelta(seconds=151)) is not None


def test_rate_limit_retries_are_bounded_and_do_not_become_success(db):
    now = datetime.now(UTC)
    config = settings(now)
    occurrence(db)
    enqueue_alerts(db, config, now=now)
    for step in range(5):
        at = now + timedelta(seconds=61 + step * 600)
        job = claim_alert(db, config, now=at)
        assert job is not None
        complete_alert(
            db,
            job["attempt_id"],
            SmsReceipt("retrying", error_code="provider_rate_limited"),
            now=at,
        )
    row = db.scalar(select(DiagnosticAlertDelivery))
    assert row.state == "failed" and row.covered_count == 1
    assert claim_alert(db, config, now=now + timedelta(hours=2)) is None
    assert len(list(db.scalars(select(DiagnosticAlertAttempt)))) == 5


def test_global_hourly_budget_blocks_a_second_issue_without_dropping_its_queue(db):
    now = datetime.now(UTC)
    config = settings(now).model_copy(update={"diagnostics_alert_max_per_hour": 1})
    occurrence(db, operation="workout_generation")
    occurrence(db, operation="nutrition_generation")
    enqueue_alerts(db, config, now=now)
    job = claim_alert(db, config, now=now + timedelta(seconds=61))
    complete_alert(
        db,
        job["attempt_id"],
        SmsReceipt("accepted", provider_id="1"),
        now=now + timedelta(seconds=62),
    )
    assert claim_alert(db, config, now=now + timedelta(minutes=10)) is None
    assert claim_alert(db, config, now=now + timedelta(hours=1, minutes=2)) is not None


def test_worker_restart_persists_dispatch_and_uses_get_receipt_without_resending(db, monkeypatch):
    import httpx
    from sqlalchemy.orm import Session

    from app.observability import alert_worker
    from app.observability.alert_sms import FarazAlertSms

    now = datetime.now(UTC)
    config = settings(now).model_copy(
        update={
            "farazsms_api_key": __import__("pydantic").SecretStr("private-fixture"),
            "farazsms_from_number": "30001234",
        }
    )
    occurrence(db)
    enqueue_alerts(db, config, now=now)
    db.flush()
    clock = {"now": now + timedelta(seconds=61)}

    class Clock:
        @staticmethod
        def now(zone):
            return clock["now"]

    monkeypatch.setattr(alert_worker, "datetime", Clock)
    monkeypatch.setattr(alert_worker, "get_engine", lambda settings: db.bind)
    monkeypatch.setattr(
        alert_worker,
        "Session",
        lambda engine: Session(engine, join_transaction_mode="create_savepoint"),
    )
    calls = []

    def handle(request):
        calls.append(request.method)
        if request.method == "POST":
            return httpx.Response(201, json={"status": "success", "data": 12345})
        notice = request.url.params["search"]
        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": {
                    "data": [
                        {
                            "id": 12345,
                            "metadata": {"text": "notice=" + notice, "recipients": ["09123456789"]},
                            "snapshot": {"total_count": 1, "delivered_count": 1},
                        }
                    ]
                },
            },
        )

    for seconds in [61, 95, 200]:
        clock["now"] = now + timedelta(seconds=seconds)
        with httpx.Client(transport=httpx.MockTransport(handle)) as client:
            alert_worker.run_iteration(config, FarazAlertSms(config, client))
    db.expire_all()
    assert calls == ["POST", "GET"]
    assert db.scalar(select(DiagnosticAlertDelivery)).state == "provider_delivered"
