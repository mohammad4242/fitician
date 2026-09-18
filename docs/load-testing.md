# Local load and failure testing

`ops/load/http_smoke.py` is a standard-library, provider-neutral load smoke.
It reports p50/p95/p99 latency, status counts, error rate, and mean latency.
It sends only HTTP requests to the configured local endpoint; it never calls
OpenRouter, SMS, SMTP, payment, or push providers.

Scenarios:

```bash
bash ops/load/run.sh health
bash ops/load/run.sh catalogue
LOAD_PATH=/api/v1/some-endpoint bash ops/load/run.sh custom
```

The catalogue scenario requires the local app to have the corresponding
authenticated/profile setup. Set `BASE_URL`, `LOAD_REQUESTS`,
`LOAD_CONCURRENCY`, and `LOAD_MAX_P95_MS` to tune a run without code changes.
The default acceptance thresholds are error rate below 1% and p95 below the
scenario threshold. Use deterministic test providers and seeded test data when
exercising authenticated Body Analysis or rate-limit paths; do not point the
runner at paid production providers.

Failure drills use deadline polling rather than fixed success sleeps:

```bash
bash ops/load/failure-drills.sh redis
bash ops/load/failure-drills.sh worker
bash ops/load/failure-drills.sh backend
bash ops/load/failure-drills.sh queue
bash ops/load/failure-drills.sh database
bash ops/load/failure-drills.sh caddy
```

The worker drill seeds one durable fake-provider Body Analysis, kills the worker only after
the claim is visible, expires the abandoned lease through the local fixture, and requires the
replacement worker to finish on attempt two with exactly one result version. The Redis drill
uses an authenticated cached nutrition-catalogue request and proves PostgreSQL cache and
rate-limit fallbacks before Redis recovery. The backlog drill seeds 50 durable fake jobs and
must drain them within 90 seconds by default while reporting queue depth and oldest-job age.
All limits are configurable through the `FAILURE_DRILL_*` environment variables.
