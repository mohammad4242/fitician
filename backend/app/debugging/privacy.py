"""Defense-in-depth filtering for operator text and model/tool output."""

import json
import re

_PRIVATE_FIELDS = {
    "medicalform",
    "healthform",
    "requestbody",
    "responsebody",
    "rawrequest",
    "rawresponse",
    "prompt",
    "completion",
    "aiprompt",
    "aicompletion",
    "imagebase64",
    "imageurl",
    "photobase64",
    "token",
    "password",
    "secret",
    "cookie",
    "authorization",
    "apikey",
    "credentials",
}


def validate_operator_message(value: str) -> str:
    """Reject identifiable private payloads before creating any conversation records.

    This is a bounded syntax guard, not a claim to detect all personal free text.
    Operators must reference sanitized evidence instead of pasting original payloads.
    """
    if not value.strip() or len(value) > 8000:
        raise ValueError("invalid_message")
    keys = re.findall(r"""(?:^|[\s{,])['"]?([A-Za-z_][A-Za-z_-]*)['"]?\s*[:=]""", value)
    if any(re.sub(r"[_-]", "", key).lower() in _PRIVATE_FIELDS for key in keys) or re.search(
        r"(?i)data:(?:image|application)/[^\s;,]+(?:;[^,]*)?,", value
    ):
        raise ValueError("sensitive_message_rejected")
    try:
        structured = json.loads(value)
    except (ValueError, RecursionError):
        structured = None

    def check(item: object, depth: int = 0) -> None:
        if depth > 16:
            raise ValueError("sensitive_message_rejected")
        if isinstance(item, dict):
            for key, child in item.items():
                if re.sub(r"[_-]", "", str(key)).lower() in _PRIVATE_FIELDS:
                    raise ValueError("sensitive_message_rejected")
                check(child, depth + 1)
        elif isinstance(item, list):
            for child in item:
                check(child, depth + 1)

    check(structured)
    return sanitize_text(value).strip()


def sanitize_text(value: str, *, limit: int = 32000) -> str:
    value = value[:limit]
    value = re.sub(r'(?i)\b(?:Bearer|Basic)\s+[^\s"\']+', "Bearer [redacted]", value)
    value = re.sub(
        r"""(?i)(["']?(?:api[_-]?key|token|password|secret|cookie|authorization)["']?\s*[=:]\s*)(?:"[^"]*"|'[^']*'|[^\s,;}]+)""",
        r"\1[redacted]",
        value,
    )
    value = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[email redacted]", value)
    value = re.sub(r"(?<!\w)(?:\+98|0098|0)9\d{9}(?!\w)", "[phone redacted]", value)
    value = re.sub(
        r"\b(?:sk-|gh[pousr]_|github_pat_|sntry[shup]_|xox[baprs]-)[A-Za-z0-9_-]{12,}\b",
        "[credential redacted]",
        value,
    )
    value = re.sub(r"(https?://[^\s?#]+)\?[^\s#]+", r"\1?[redacted]", value)
    return value


def sanitize_payload(value: object, depth: int = 0) -> object:
    """Scrub strings before JSON serialization, preserving valid structured tool results."""
    if depth > 16:
        return "[truncated]"
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, dict):
        return {
            sanitize_text(str(key)): (
                "[redacted]"
                if re.search(
                    r"(?i)^(?:token|password|secret|cookie|authorization|api_key|email|phone|medical_form|prompt|completion|request_body|response_body)$",
                    str(key),
                )
                else sanitize_payload(item, depth + 1)
            )
            for key, item in list(value.items())[:100]
        }
    if isinstance(value, list):
        return [sanitize_payload(item, depth + 1) for item in value[:100]]
    return value
