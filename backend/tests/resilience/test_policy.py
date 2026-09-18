from __future__ import annotations

import httpx

from app.resilience.policy import (
    RetryPolicy,
    TimeoutPolicy,
    bounded_backoff_seconds,
    retry_eligible,
)


def test_bounded_backoff_is_exponential_and_stable_per_job() -> None:
    first = bounded_backoff_seconds(10, 60, 1, jitter_key="job-a")
    second = bounded_backoff_seconds(10, 60, 2, jitter_key="job-a")
    repeated = bounded_backoff_seconds(10, 60, 1, jitter_key="job-a")

    assert 1 <= first <= 10
    assert 1 <= second <= 20
    assert first == repeated


def test_retry_policy_rejects_unsafe_non_idempotent_writes() -> None:
    policy = RetryPolicy(name="payment", max_attempts=3, base_seconds=1, max_seconds=10)

    assert retry_eligible(policy, status_code=503, idempotent=False) is False
    assert retry_eligible(policy, status_code=503, idempotent=True) is True
    assert retry_eligible(policy, status_code=404, idempotent=True) is False


def test_timeout_policy_builds_finite_httpx_timeout() -> None:
    policy = TimeoutPolicy(connect=1.0, read=2.0, write=3.0, pool=4.0)
    timeout = policy.as_httpx()

    assert isinstance(timeout, httpx.Timeout)
    assert timeout.connect == 1.0
    assert timeout.read == 2.0
    assert timeout.write == 3.0
    assert timeout.pool == 4.0
