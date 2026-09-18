from __future__ import annotations

import hashlib
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class TimeoutPolicy:
    connect: float
    read: float
    write: float
    pool: float

    def as_httpx(self) -> httpx.Timeout:
        return httpx.Timeout(
            timeout=None,
            connect=self.connect,
            read=self.read,
            write=self.write,
            pool=self.pool,
        )


@dataclass(frozen=True)
class RetryPolicy:
    name: str
    max_attempts: int
    base_seconds: int
    max_seconds: int
    retryable_statuses: frozenset[int] = frozenset({408, 425, 429, 500, 502, 503, 504})


def bounded_backoff_seconds(
    base_seconds: int,
    max_seconds: int,
    attempt: int,
    *,
    jitter_key: str | None = None,
) -> int:
    """Return bounded exponential backoff with stable per-job jitter."""

    safe_base = max(1, int(base_seconds))
    safe_max = max(safe_base, int(max_seconds))
    exponent = max(0, int(attempt) - 1)
    cap: int = int(min(safe_max, safe_base * (2**exponent)))
    if jitter_key is None:
        return cap
    digest = hashlib.sha256(jitter_key.encode("utf-8")).digest()
    fraction = int.from_bytes(digest[:8], "big") / float(2**64 - 1)
    jittered: int = int(round(cap * fraction))
    return max(1, min(cap, jittered))


def retry_eligible(
    policy: RetryPolicy,
    *,
    status_code: int | None = None,
    error: BaseException | None = None,
    idempotent: bool,
    attempt: int = 1,
) -> bool:
    """Allow retries only for bounded, idempotent transient operations."""

    if not idempotent or attempt >= max(1, policy.max_attempts):
        return False
    if status_code is not None:
        return status_code in policy.retryable_statuses
    return isinstance(error, (TimeoutError, OSError, httpx.TimeoutException, httpx.NetworkError))
