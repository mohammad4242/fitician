"""Defense-in-depth filtering for operator text and model/tool output."""

import re


def sanitize_text(value: str) -> str:
    value = value[:32000]
    value = re.sub(r'(?i)\bBearer\s+[^\s"\']+', "Bearer [redacted]", value)
    value = re.sub(
        r"(?i)((?:api[_-]?key|token|password|secret|cookie|authorization)\s*[=:]\s*)[^\s,;]+",
        r"\1[redacted]",
        value,
    )
    value = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[email redacted]", value)
    value = re.sub(r"(?<!\w)(?:\+98|0098|0)9\d{9}(?!\w)", "[phone redacted]", value)
    value = re.sub(r"\b(?:sk-|gh[pousr]_)[A-Za-z0-9_-]{12,}\b", "[credential redacted]", value)
    value = re.sub(r"(https?://[^\s?#]+)\?[^\s#]+", r"\1?[redacted]", value)
    return value
