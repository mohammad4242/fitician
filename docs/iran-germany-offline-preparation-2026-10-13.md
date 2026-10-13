# Iran + Germany offline preparation — 2026-10-13

## Decision and scope

**Offline preparation completed; production cutover remains blocked.** Netherlands
is still the authoritative database and serves `fitician.fit`. No DNS changes,
source write freeze, source restart, production-volume deletion or automatic CD
enablement occurred. Iran's international connectivity is an owner-reported
provider restriction; no additional VPN workaround was attempted in this phase.

## Actual runtime

| Location | Verified state |
| --- | --- |
| Iran, isolated rehearsal | PostgreSQL, Redis, two Backends, four Workers, Frontend and Caddy running: 10 services; nine Docker healthchecks healthy. Caddy has no Docker healthcheck, but trusted HTTPS returned 200. |
| Iran migrations | Exited 0; Alembic `20261007_172`. Fresh synthetic database migrations succeeded. |
| Germany, isolated Agent | Healthy, unauthenticated capabilities rejected, authenticated capabilities accepted. Actual `POST /v1/generate` returned 200 and schema-valid `{"ok":true}` in 7.475 seconds. |
| Netherlands | All 11 services running; ten configured healthchecks healthy. Read-only source inspection found 249 users and Alembic `20261007_172`. |

Iran rehearsal lives at `/opt/fitician-iran/rehearsals/offline-20261013`, with
explicit project `fitician-offline-rehearsal`, database
`fitician_offline_rehearsal` and dedicated `fitician_offline_rehearsal_*_20261013`
volumes. It uses synthetic accounts, never restored customer data as a writable
application database. The default Docker network is internal; sensitive ports
are unpublished. Caddy is restricted to loopback, with restored certificates
mounted read-only; manual trusted TLS avoids external ACME requests.

Memory caps total 3,136 MiB including the stopped migration job, leaving 780 MiB
against the measured 3,916 MiB host. Aggregate CPU caps are 2.95 on two CPUs.
No OOM events or automatic restarts were observed. The original customer restore
and the additional restore-kit container are stopped; their volumes are retained.
This is bounded rehearsal evidence, not production load acceptance.

Germany rehearsal lives at `/opt/fitician-agent/rehearsals/offline-20261013`.
The Agent has no default route, no public Agent port, an internal Docker network,
a read-only root filesystem and a separate writable QA clone of the auth home.
Its loopback forwarder is `127.0.0.1:19001`. The nine original authentication files
still match their restored hashes, ownership and modes. Original restored auth
is retained untouched. The temporary, narrowly filtered Germany-only vendor TLS
proxy and its exact firewall rule were removed after the real AI test.

Only the Codex `codex-gpt-5.6-luna-low` profile was qualified with generation.
Codex and Antigravity local authentication matched source. Antigravity generation
and other models were not qualified. Claude was already unauthenticated on source;
enabling Claude requires authentication, independently of Iran Internet access.

## Evidence and repairs

- 36 expected-status API checks passed, including secure web cookies, password
  rejection, origin protection, cross-replica sessions, profile/catalogue reads,
  native-origin mobile login, refresh, logout and revoked-token rejection.
- Desktop and Pixel-7 browser rendering/login passed with certificate verification,
  no page errors and no first-party HTTP 5xx. This was Android browser testing,
  not a physical Android app acceptance test.
- Verified apex HTTPS 200 and `www` HTTPS 308 to the canonical hostname. A read-only
  40-request health smoke at concurrency eight returned 40 HTTP 200s; p50 279.2 ms,
  p95 534.7 ms. This does not establish sustained production capacity.
- The preliminary encrypted source backup restored successfully: all 150 public
  table counts and 11 selected fingerprints matched; 249 users, 56 access grants,
  161 workout plans and 77 nutrition weekly plans. Alembic matched and no foreign
  keys were unvalidated. Encrypted S3 upload/download SHA verification passed.
- A second, synthetic encrypted backup exercised the new restore CLI end to end
  into a separate, network-disabled PostgreSQL 18 target. All 150 tables, 11
  fingerprints, migration revision and foreign keys matched. Exact PostgreSQL
  image pin and complete public-table inventory were independently rechecked.
  The age identity stayed local, not on a VPS.
- 171 focused Ops tests passed; repository Ruff and `git diff --check` passed.
  No Full CI was manually dispatched and no image pull was needed.
- Increased measured-tight worker memory budgets to food 256 MiB and
  scheduler/notification 192 MiB. All worker healthchecks now allow a 120-second
  cold start. Rehearsal-only migration CPU is 0.75; production migration CPU is
  unchanged.
- Added explicit Compose project isolation, internal networking, synthetic DB
  guards, dedicated volume names and bounded-resource startup. Fixed restore
  guards for exact PostgreSQL version/image and unexpected public tables.
- Corrected the QA Agent writable-home requirement and temporary CONNECT parser
  restrictions. Earlier failed diagnostic attempts are retained in evidence;
  the final Agent API request succeeded. No application image was changed.

Application images retain the exact CI-qualified source SHA
`bf182dd42d97304aa55d39e7f51a92a073f9e021`; configuration changes are reviewed
separately. No automatic-CD workflow was enabled.

Sanitized local evidence is retained under `artifacts/regional-cutover/`:
`iran-offline-runtime-final.json`, `iran-offline-http-evidence.json`,
`iran-offline-browser-evidence.json`, `qa-kit-restore-evidence.json`,
`germany-agent-rehearsal.json`, `germany-agent-one-prompt-evidence.json`,
`database-restore-evidence.json` and `ops-test-results.txt`.
These artifacts are not committed. Credentials and encrypted payloads remain in
protected, ignored storage; do not stage the artifact directory.

## Prepared operational tooling

`ops/rehearse-regional.py config|start --env-file <protected-QA-env>` explicitly
sets the separate Compose project, validates topology/resources and uses
`--pull never`. Provision fresh dedicated QA volumes first; never reuse production
volumes. The helper requires mode-0600 env files and a `REHEARSAL_ID`.
The resource check uses Docker host totals, not parent-cgroup constraints; initial
host/volume inspection remains required.

`ops/regional-cutover.py` and
[the operator checklist](regional-cutover-checklist.md) prepare backup, restore,
integrity, HTTPS, DNS patch and rollback steps. Plans are dry-run by default.
The encrypted restore path was actually executed and verified only against an
isolated target. DNS plans preserve unrelated/MX/TXT records and require an exact
reviewed target record set. Gate attestations require live evidence; they are not
automatic proof of readiness. Source freeze and DNS writes were not executed.

## Pending gates

**Dependent on Iran international connectivity:** WireGuard handshake/private
routes and firewall acceptance, Docker-to-Agent authenticated TLS, real AI/media
flows from Iran, Google OAuth, S3, SMTP/email, SMS and other enabled external
integrations. Retry the existing WireGuard design once connectivity is available;
do not install Tailscale or change protocols merely to bypass the present outage.

**Separate access/acceptance gates:** Cloudflare credentials were not found in
the existing safe access inventory. Final DNS execution needs a secure session
or scoped token with Zone Read and DNS Read/Edit for `fitician.fit`. No secret
should be pasted into logs or committed. Public Iran ingress, certificate renewal,
physical Android acceptance, production load/recovery acceptance and enabled
provider/model qualification remain unverified.

The last read-only DNS inspection found apex/api A `141.11.0.99`, `www` CNAME
`fitician.fit`, TTL 300 and no AAAA. Cloudflare proxy state must be read through
the authenticated zone API before patching. Verify actual `api` usage; preserve
mail and unrelated records. This phase did not alter them.

## Limited final sequence after connectivity returns

1. Qualify WireGuard/private TLS, Agent uploads/outage recovery and the enabled
   external integrations. Verify public HTTPS directly with `curl --resolve`,
   certificate renewal, capacity and final exact image/configuration references.
2. Stop only the isolated QA services to release RAM, retaining their volumes.
   Stage the reviewed configuration; use one production writer/consumer set.
3. During the separately authorized cutover window, drain and freeze Netherlands
   writers and all four workers, quiesce Agent auth writes, take fresh encrypted
   DB/auth snapshots and restore into a new isolated target. Compare all public
   tables, selected fingerprints, subscriptions/plans and auth files; reconcile
   outstanding jobs/leases. Preliminary snapshots cannot replace this step.
4. Adopt the freshly validated database/auth volumes and start the final Iran
   application stack and Germany Agent. Verify authenticated critical operations,
   direct HTTPS and rollback gates before changing the exact Cloudflare records.
5. Test real web, Android and API traffic, monitor errors/resources and take fresh
   backups. Retain Netherlands and valid backups until stability is confirmed.
   If target writes began, rollback first freezes target writes and reconciles
   data for validated reverse restoration; DNS-only rollback is prohibited.

No traffic transfer is authorized by the current offline-preparation instruction.
