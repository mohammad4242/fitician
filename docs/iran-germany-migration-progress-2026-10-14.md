# Regional migration execution — 2026-10-14

Netherlands remains authoritative. No final source freeze, production adoption,
DNS write or automatic CD enablement has occurred. The current owner instruction
authorizes migration execution subject to data, security and release gates; it
supersedes the older preparation-only instruction.

## Fresh audit and executed work

- Repository `main` matched origin at `b2fbc6ef` before changes. Source application
  images remain `bf182dd42d97304aa55d39e7f51a92a073f9e021`.
- SSH to Iran, Germany and Netherlands works locally. Iran has 3,916 MiB RAM,
  two CPUs and approximately 19 GiB available disk; Germany has 1,968 MiB RAM and
  approximately 9.7 GiB available disk. Source has approximately 7.4 GiB available.
- Iran's existing ten-service synthetic rehearsal remains running, with nine
  healthchecks healthy and migrations previously exited zero. Germany has one
  healthy isolated QA Agent. These are not production deployments. Source's eleven
  running services retain healthy configured healthchecks.
- The required immutable application images and pinned PostgreSQL, Redis and
  Caddy images are already present on Iran. Production env permissions are 0600.
  Existing rehearsal and restore volumes were preserved. Four current signing/
  authentication/encryption settings matched the source privately; no values were logged.
- A fresh read-only exported PostgreSQL transaction snapshot was dumped and
  encrypted locally with age. The snapshot contains 249 users and 150 public tables.
  All 150 table counts **and all 150 row fingerprints** matched after guarded restore
  into `fitician-current-restore-20261014`, a network-disabled PostgreSQL 18 container
  using the Compose-pinned image and a dedicated volume. Alembic `20261007_172`
  matched and zero foreign keys were unvalidated. The container is now stopped;
  its volume is retained. This snapshot is not a final frozen snapshot.
- UFW now permits TCP 80/443, preserving SSH. A temporary Caddy probe using the
  existing restored certificate returned HTTPS 200 with TLS verification zero
  through loopback, Iran's public IP and the local client's direct public connection.
  Germany-to-Iran HTTPS timed out. The probe was stopped after testing. This proves
  certificate/ingress operation from the tested contexts, not application readiness
  or ACME renewal.
- A one-shot container on a normal Docker bridge, using current Iran settings,
  performed private S3 write/read/delete, confirmed cleanup, and confirmed anonymous
  private-read denial. The earlier internal-network rehearsal failed external
  probes by design; those failures must not be treated as production network proof.
- SMS TCP/TLS is reachable from host and bridge. Real OTP receipt/account acceptance
  is untested without an owner test destination. SMTP timed out. Google/FCM network
  probes failed; FCM is unconfigured/disabled on source and destination. No messages
  or pushes were sent. Public exercise GIF and MP4 delivery passed MIME/signature checks, with
  MP4 byte-range support; the sanitized integration evidence records these checks.
- Hosted workflow `38547484242` passed Germany SSH diagnostics and failed Iran
  before authentication, classified as a network failure. All production/component/
  regional CD workflows remain manually disabled.
- Fresh credential-name discovery found no Cloudflare candidate in the scoped env
  inventory or configured GitHub secrets, and no connected authenticated browser
  session was available. Apex and API A records still resolve to `141.11.0.99`.

## AI outage behavior implemented in this candidate

The shared error code is `agent_network_unavailable`, with Persian text
`اینترنت بین‌الملل در دسترس نیست`. Only Agent connect/DNS/connect-timeout failures
emit it. Certificate failures, slow generation/read/pool timeouts, authentication,
model errors and HTTP/internal failures retain their own categories. Direct
OpenRouter/Zen paths retain their provider-specific errors.

Before model requests, an idempotent health probe uses at most two attempts and
three-second timeouts. Generation POSTs are not automatically replayed by the
probe. Body-analysis admission checks connectivity before charging quota or
creating a job. Existing accepted jobs remain durable; Agent connection outages
requeue body/food jobs without exhausting their generation attempt budgets.
Other failures retain bounded retry limits. Deleted/expired jobs and lease checks
retain their existing handling. No AI disable flag, fake production provider,
startup dependency or environment toggle was introduced.

Web/PWA and native Android share the error catalog, show persisted queued outage
messages, and retain deterministic workout fallback. A successful deterministic
fallback emits a transient notice only for the Agent network failure. While that
notice is visible, authenticated connectivity checks every 30 seconds clear it
when the network error disappears. The status endpoint never invokes a model.
Queued jobs automatically resume on a later worker attempt.

Tests cover connection failure, HTTP/auth/internal error separation, SSL errors,
no quota/job creation on failed admission, repeated worker outages beyond normal
attempt budgets, same-job recovery, and actual isolated loopback HTTP transport
recovery using the same provider without restart/configuration changes. Isolated
recovery is not evidence of a working Iran-to-Germany production link.

## Verification and remaining gates

Backend verification including focused AI/workers/workouts, authentication and
profile passed 628 tests; the existing explicitly opted-out live Zen test remains
unexecuted. Socket/admission/connectivity tests also passed separately. Ops passed 215
checks. Shared catalog, Web and native UI checks/typechecks passed. OpenAPI was
regenerated and its check passed. Baseline comparison found no new Ruff, format
or mypy debt in the changed backend domains; the repository has existing debt.
Exact final-SHA CI/image qualification is still required after this candidate is
committed. Evidence is under `artifacts/regional-cutover/current-20261014/` and is
not committed; private encrypted payloads remain in protected ignored storage.

Cutover remains blocked by authenticated DNS access, a qualified private Agent
path, final runtime/user acceptance and release evidence. Agent URL DNS currently
fails from Iran; returning international access alone has not qualified that path.
SMTP/Google failures and certificate renewal need explicit acceptance or repair.
Real registration/login/OTP from Iran, production profile/plan persistence,
admin acceptance and physical Android acceptance are not claimed.

Before freezing source writers, clear the remaining gates and preserve the
existing rollback procedure. Drain/freeze the verified six source writers, take
another transaction-consistent encrypted final snapshot and quiesced Agent auth
snapshot, validate the final target again, then adopt the final volumes through
regional deployment tooling. Stop only synthetic rehearsal services when final
runtime preparation needs their resources; never remove real/back-up volumes.
Only one production writer/consumer set may become active. After target writes,
rollback requires target freeze and reconciled reverse restoration, not DNS alone.

Android uses the existing domain, so DNS routing alone does not require an APK.
The new native outage presentation is compiled application code and requires a
new qualified app build for existing installed clients to receive that behavior.
