"""Defense-in-depth filtering for operator text and model/tool output."""

import re


def sanitize_text(value: str) -> str:
    value = value[:32000]
    value = re.sub(r'(?i)\b(?:Bearer|Basic)\s+[^\s"\']+', "Bearer [redacted]", value)
    value = re.sub(
        r"(?i)((?:api[_-]?key|token|password|secret|cookie|authorization)\s*[=:]\s*)[^\s,;]+",
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
