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
