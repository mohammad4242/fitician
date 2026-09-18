# Provider resilience policy

All provider calls must have a finite timeout. Existing task-specific settings
remain the source of truth for AI and queue execution; the shared policy in
`backend/app/resilience/policy.py` supplies bounded backoff and idempotency
checks for new integrations.

Retry only when the operation is idempotent or carries a durable idempotency
key. Retryable HTTP responses are 408, 425, 429, 500, 502, 503, and 504. Do not
retry payment writes, account mutations, or delivery writes without the
existing durable deduplication/lease contract.

Body Analysis keeps provider accounting and durable job state in PostgreSQL.
Transient provider errors are requeued with bounded, stable per-job jitter;
terminal errors persist a safe message and enqueue one deduplicated failure
notification. Food Photo and Notification workers retain their existing
attempt/dead-letter contracts while adopting the same policy for future
provider adapters.
