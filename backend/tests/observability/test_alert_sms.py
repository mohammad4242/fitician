import json
from uuid import uuid4

import httpx
import pytest

from app.config import Settings
from app.observability.alert_sms import FarazAlertSms, compose_alert_message


def configured():
    return Settings(
        farazsms_api_key="private-fixture",
        farazsms_from_number="30001234",
        diagnostics_alert_phone="+989123456789",
        frontend_origin="https://fitician.example",
    )


def test_sms_contains_only_deterministic_persian_summary_count_and_authenticated_link():
    identifier = uuid4()
    message = compose_alert_message(
        identifier, "provider_failure", "body_analysis", 12, "https://fitician.example"
    )
    assert "۱۲" in message or "12" in message
    assert "تحلیل بدن" in message
    assert message.endswith(
        f"https://fitician.example/admin/diagnostics?tab=issues&issue={identifier}"
    )
    assert len(message) < 400
    assert "provider_failure" not in message


def test_faraz_uses_existing_credentials_without_reusing_the_otp_pattern():
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(201, json={"status": "success", "data": 12345})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        receipt = FarazAlertSms(configured(), client).send("خلاصهٔ آزمایشی")
    assert receipt.state == "accepted"
    assert receipt.provider_id == "12345"
    request = requests[0]
    assert str(request.url) == "https://api.iranpayamak.com/ws/v1/sms/simple"
    assert request.headers["Api-Key"] == "private-fixture"
    payload = json.loads(request.content)
    assert payload == {
        "text": "خلاصهٔ آزمایشی",
        "line_number": "30001234",
        "recipients": ["09123456789"],
        "number_format": "english",
    }
    assert "pattern" not in str(request.url)


@pytest.mark.parametrize(
    "response,expected", [(429, "retrying"), (401, "failed"), (403, "failed"), (500, "uncertain")]
)
def test_rejections_do_not_become_delivered_or_leak_provider_response(response, expected):
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                response, json={"status": "error", "messages": "private medical fixture"}
            )
        )
    ) as client:
        receipt = FarazAlertSms(configured(), client).send("خلاصه")
    assert receipt.state == expected
    assert "private" not in repr(receipt)


def test_send_timeout_is_uncertain_and_cannot_be_automatically_repeated():
    def handle(request):
        raise httpx.ReadTimeout("private-fixture", request=request)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        receipt = FarazAlertSms(configured(), client).send("خلاصه")
    assert receipt.state == "uncertain"
    assert receipt.error_code == "delivery_acknowledgment_unknown"


def test_generated_provider_id_is_not_phone_delivery_confirmation():
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(201, json={"status": "success", "data": 0})
        )
    ) as client:
        receipt = FarazAlertSms(configured(), client).send("خلاصه")
    assert receipt.state == "uncertain"
    assert receipt.provider_id is None


@pytest.mark.parametrize(
    "delivered,failed,state",
    [(1, 0, "provider_delivered"), (0, 1, "delivery_failed"), (0, 0, "accepted")],
)
def test_receipt_lookup_matches_one_opaque_notice_and_private_recipient(delivered, failed, state):
    notice = uuid4()
    calls = []

    def handle(request):
        calls.append(request)
        assert request.method == "GET"
        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": {
                    "data": [
                        {
                            "id": 12345,
                            "metadata": {
                                "text": f"https://fitician.example/admin/diagnostics?notice={notice}",
                                "recipients": ["09123456789"],
                            },
                            "snapshot": {
                                "total_count": 1,
                                "delivered_count": delivered,
                                "delivery_failure_count": failed,
                            },
                        }
                    ],
                    "next_page_url": None,
                },
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        receipt = FarazAlertSms(configured(), client).reconcile(notice)
    assert receipt.state == state and receipt.provider_id == "12345"
    assert calls[0].url.params["search"] == str(notice)
    assert "09123456789" not in str(calls[0].url)


def test_other_recipient_or_notice_cannot_establish_delivery():
    notice = uuid4()
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {
                        "data": [
                            {
                                "id": 12345,
                                "metadata": {
                                    "text": f"notice={notice}",
                                    "recipients": ["09999999999"],
                                },
                                "snapshot": {"total_count": 1, "delivered_count": 1},
                            }
                        ]
                    },
                },
            )
        )
    ) as client:
        receipt = FarazAlertSms(configured(), client).reconcile(notice)
    assert receipt.state == "uncertain" and receipt.provider_id is None


def test_blank_optional_alert_configuration_does_not_break_default_environment():
    value = Settings(diagnostics_alert_phone="", diagnostics_alert_enabled_at="")
    assert value.diagnostics_alert_phone is None
    assert value.diagnostics_alert_enabled_at is None
