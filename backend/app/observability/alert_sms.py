"""Narrow FarazSMS operational alerts. Never use the login OTP template for alerts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import urlsplit
from uuid import UUID

import httpx

from app.config import Settings


@dataclass(frozen=True)
class SmsReceipt:
    state: str
    provider_id: str | None = None
    error_code: str | None = None
    retry_after: int = 60


def compose_alert_message(
    issue_id: UUID,
    category: str,
    operation: str,
    count: int,
    origin: str,
    *,
    notice_id: UUID | None = None,
) -> str:
    parsed = urlsplit(origin)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("public_https_panel_origin_required")
    feature = {
        "body_analysis": "تحلیل بدن",
        "food_photo_estimation": "بررسی عکس غذا",
        "food_photo_analysis": "بررسی عکس غذا",
        "workout_generation": "ساخت برنامه تمرین",
        "nutrition_generation": "ساخت برنامه تغذیه",
    }.get(operation, "یکی از بخش‌های برنامه")
    fact = {
        "provider_failure": "سرویس پردازش پاسخ موفق نداد",
        "database_failure": "عملیات پایگاه داده انجام نشد",
        "infrastructure_failure": "یک سرویس در دسترس نبود",
        "job_failure": "پردازش پس‌زمینه انجام نشد",
    }.get(category, "اجرای عملیات با خطا متوقف شد")
    return (
        f"هشدار فیتیشن\n{feature}: {fact}.\nتکرار: {min(max(count, 1), 999999999)}\n"
        f"{origin.rstrip('/')}/admin/diagnostics?tab=issues&issue={UUID(str(issue_id))}"
        + (f"&notice={notice_id}" if notice_id else "")
    )


class FarazAlertSms:
    def __init__(self, settings: Settings, client: httpx.Client) -> None:
        self.client = client
        self.base = settings.farazsms_base_url.rstrip("/")
        if self.base != "https://api.iranpayamak.com/ws/v1":
            raise ValueError("faraz_alert_api_target_not_authorized")
        self.key = settings.farazsms_api_key.get_secret_value() if settings.farazsms_api_key else ""
        self.line = settings.farazsms_from_number or ""
        phone = (
            settings.diagnostics_alert_phone.get_secret_value()
            if settings.diagnostics_alert_phone
            else ""
        )
        if (
            not self.key
            or not re.fullmatch(r"[0-9]{5,20}", self.line)
            or not re.fullmatch(r"\+989[0-9]{9}", phone)
        ):
            raise ValueError("faraz_alert_configuration_incomplete")
        self.recipient = "0" + phone[3:]

    def send(self, text: str) -> SmsReceipt:
        if not text or len(text) > 400:
            raise ValueError("bounded_alert_message_required")
        try:
            with self.client.stream(
                "POST",
                self.base + "/sms/simple",
                headers={"Api-Key": self.key, "Accept": "application/json"},
                json={
                    "text": text,
                    "line_number": self.line,
                    "recipients": [self.recipient],
                    "number_format": "english",
                },
                timeout=10,
                follow_redirects=False,
            ) as response:
                if response.status_code == 429:
                    retry = response.headers.get("Retry-After", "60")
                    return SmsReceipt(
                        "retrying",
                        error_code="provider_rate_limited",
                        retry_after=min(max(int(retry), 30), 3600) if retry.isdigit() else 60,
                    )
                if response.status_code >= 500:
                    return SmsReceipt("uncertain", error_code="delivery_acknowledgment_unknown")
                if response.status_code not in {200, 201}:
                    return SmsReceipt("failed", error_code="provider_rejected")
                content = bytearray()
                for chunk in response.iter_bytes():
                    content.extend(chunk)
                    if len(content) > 32768:
                        return SmsReceipt("uncertain", error_code="invalid_provider_acknowledgment")
                body = json.loads(content)
            if not isinstance(body, dict) or str(body.get("status")).lower() != "success":
                return SmsReceipt("failed", error_code="provider_rejected")
            identifier = str(body.get("data", ""))
            if not re.fullmatch(r"[1-9][0-9]{0,29}", identifier):
                return SmsReceipt("uncertain", error_code="provider_reference_unknown")
            return SmsReceipt("accepted", provider_id=identifier)
        except (httpx.ConnectError, httpx.ConnectTimeout):
            return SmsReceipt("retrying", error_code="provider_connect_failed")
        except (httpx.HTTPError, ValueError):
            # A timeout after dispatch may follow a successful enqueue; never send it again.
            return SmsReceipt("uncertain", error_code="delivery_acknowledgment_unknown")

    def reconcile(self, notice_id: UUID) -> SmsReceipt:
        """Read only the bounded matching dispatch. No resend and no untrusted pagination URL."""
        matches: dict[str, dict[str, object]] = {}
        try:
            for page in range(1, 4):
                with self.client.stream(
                    "GET",
                    self.base + "/send_request",
                    params={"search": str(notice_id), "page": page, "limit": 5},
                    headers={"Api-Key": self.key, "Accept": "application/json"},
                    timeout=10,
                    follow_redirects=False,
                ) as response:
                    if response.status_code != 200:
                        return SmsReceipt("uncertain", error_code="receipt_lookup_unavailable")
                    raw = bytearray()
                    for chunk in response.iter_bytes():
                        raw.extend(chunk)
                        if len(raw) > 131072:
                            return SmsReceipt("uncertain", error_code="receipt_response_too_large")
                    body = json.loads(raw)
                data = body.get("data", {})
                records = data.get("data", [])
                if body.get("status") != "success" or not isinstance(records, list):
                    return SmsReceipt("uncertain", error_code="receipt_lookup_unavailable")
                for record in records[:5]:
                    if not isinstance(record, dict):
                        continue
                    metadata = record.get("metadata") or {}
                    identifier = str(record.get("id", ""))
                    recipients = metadata.get("recipients")
                    if (
                        f"notice={notice_id}" not in str(metadata.get("text", ""))
                        or not re.fullmatch(r"[1-9][0-9]{0,29}", identifier)
                        or recipients
                        not in (
                            [self.recipient],
                            ["+98" + self.recipient[1:]],
                            ["98" + self.recipient[1:]],
                        )
                    ):
                        continue
                    matches[identifier] = record.get("snapshot") or {}
                if not data.get("next_page_url"):
                    break
            else:
                return SmsReceipt("uncertain", error_code="receipt_scope_ambiguous")
            if len(matches) != 1:
                return SmsReceipt("uncertain", error_code="receipt_not_observed")
            identifier, snapshot = next(iter(matches.items()))
            if snapshot.get("total_count") != 1:
                return SmsReceipt("uncertain", error_code="receipt_scope_ambiguous")
            if snapshot.get("delivered_count") == 1:
                return SmsReceipt("provider_delivered", provider_id=identifier)
            if snapshot.get("delivery_failure_count") == 1 or snapshot.get("blacklist_count") == 1:
                return SmsReceipt(
                    "delivery_failed", provider_id=identifier, error_code="provider_delivery_failed"
                )
            return SmsReceipt("accepted", provider_id=identifier)
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            return SmsReceipt("uncertain", error_code="receipt_lookup_unavailable")
