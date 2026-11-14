# Diagnostics and debug-agent implementation status

Production deployment is owner-authorized after the approved verification gates pass.
The current regional CD flags are enabled; manual full/Agent releases retain their owner
environment gate and automatic delivery is limited to eligible main CI/component paths.
No external delivery, symbolication, native crash acceptance,
repair runtime, GitHub access or deployment is established merely by enabling an SDK.

## Revalidated completion checklist — 2026-11-14

The existing design and execution authorization remain in effect. Work continues on
`feat/regional-cicd`; no replacement stack or competing admin application is planned.
At baseline HEAD `16a7b637`, remote branch and draft PR 41 match. `origin/main` remains
`7c03e50d`; feature work is not merged or deployed. Local mobile release-identity changes
and this document are preserved. PR 42 remains a synthetic acceptance PR, never a main merge.

| Capability | Code | Tested | External configuration | Deployed | Live verified |
| --- | --- | --- | --- | --- | --- |
| SDK capture, exact-event sync, private web maps | committed | isolated SDK/DB/browser | server/GitHub secrets installed | new application release: no | backend/web staging: yes |
| Issue chat, occurrence/model provenance, Codex connector | committed | API, browser, real Codex | staging enrollment only | no | staging only |
| Independent Germany execution service | committed | CI image/protocol/isolation/restart; server limits | own login and production enrollment pending | commissioning service on Germany | health/limits/image yes; inference/panel no |
| API model tool loop | committed | mocked provider protocol | production selection/probe pending | no | actual API tool call pending |
| Isolated repair/test/PR | controlled CI profiles and separate durable publication broker committed | four CI profiles; occurrence/idempotency/PR transport tests; old synthetic PR 42 | dedicated Germany GitHub credential absent | no | no Germany PR publication proof |
| FarazSMS aggregation/receipt worker | committed, migration 181 | isolated DB/provider protocol | recipient/key present; auto sending disabled | no | one operator SMS delivered; automatic path pending |
| Native exact release identity/iOS ingestion | implemented | 34 backend, 14 core, 7 mobile tests; native crash pending | EAS Sentry variables absent at last inspection | no | no native release crash proof |
| Artifact-bound deployment and verification | schema-compatible full/Agent broker and explicit review UI implemented; schema-change review/scenario resolution remain open | isolated broker/API/host-gate tests | existing regional owner gates retained; dedicated broker credential absent | no | pending |

Execution order and gates:

- [x] Phase 0: reconcile Git/PR/runtime evidence, preserve local changes, identify latest CI failure.
- [ ] Phase 1: resume the existing owned Germany proxy; verify authenticated Iran retrieval,
  allowlist/auth failures, existing Agent identity unchanged. Rehearse fresh backup restoration
  before any production migration. Public SSH and hosted deployment access are separate gates.
- [ ] Phase 2: finish release/platform identity and telemetry health/coverage; preserve local
  lifecycle and exact occurrence counts; execute sensitive-fixture and outage checks.
- [ ] Phase 3: persistent facts/hypotheses/findings with evidence references and stale-evidence
  handling; remove error-type-only confirmed-cause inference; verify RTL/mobile/refresh.
- [ ] Phase 4: real selected Codex and OpenRouter tool runs through the panel, explicit execution
  target, supervised independent runtime, bounded audited server-evidence tools. Keep laptop
  enrollment explicit and never substitute a runtime silently.
- [ ] Phase 5: current-branch repair with failing-release comparison; add controlled backend,
  isolated PostgreSQL/migration, frontend/type/build and Agent test profiles; bind successful
  tests, patch, commit and draft PR. Verify cancellation/restarts/uncertain results.
- [ ] Phase 6: additive durable deployment records/authorization, admin preview/authorize/status
  endpoints and issue UI; fixed CI workflow broker only, exact commit/artifact/environment,
  stale-authorization rejection, existing owner gates, idempotency and target locking. Verify
  rollback/migration compatibility and scenario evidence before verified-resolution status.
- [ ] Phase 7: activate existing Faraz worker only after migrated release readiness; one controlled
  automatic error/aggregation/SMS/receipt acceptance, preserving existing dispatch limits.
- [ ] Phase 8: immutable digest release manifest, worker startup/readiness/rollback integration,
  exact-candidate CI, safe migration/restore gates, gated regional deployment and live panel probe.
- [ ] Phase 9: EAS configuration/private symbols and actual supported release-crash acceptance;
  four-workflow outcome/quota/recovery regression matrix; unavailable native platforms remain
  explicitly unverified. Final complete path must use the intended deployed panel.

### Immutable full-release artifacts — implementation gates

A fixed read-only host collector and protected-main Actions workflow now capture scoped
regional metadata without exporting Docker environment values or executing model commands.
The collector reports actual container/image IDs, image-label commit only when available,
health/restarts, resource capacity and a read-only Alembic revision. Logs require the selected
trace ID and export only bounded allowlisted JSON identifiers/error codes; raw and unrelated
messages are omitted. A baseline hash binds container/image identity and DB revision for later
stale-deployment checks. Seven injection/privacy/contract tests passed. Real pinned-SSH reads
observed all ten Iran services and Germany Agent Service; Iran remains at revision 175.
Germany readback showed one CPU, about 1393 MiB available RAM and 2457 MiB disk free.
These are direct operator acceptance observations. The workflow is not yet installed on main;
live execution through a production model and the deployment broker remain separate gates.

The selected runtime now exposes `fitician_observe_server` through the same controlled CI
broker, with an explicit Iran/Germany target. Durable `observe` operations bind the issue,
selected occurrence/trace, environment, administrator and snapshotted worker. An expired or
foreign runtime lease cannot enqueue an observation. A persisted single-use dispatch intent
precedes GitHub dispatch; uncertain acknowledgements are reconciled without resending.
Cancellation targets only the recorded, identity-checked workflow. The broker verifies the
private artifact hash and rebuilds an allowlisted packet before database/model access.
Incomplete identities cannot be reported as complete. Capacity is numeric only; unrelated
logs/free text/unknown fields are discarded. A completed observation has an immutable evidence
ID usable in same-run findings; it cannot establish a confirmed cause or business resolution.
Migration `20261114_185` extends the operation-kind check; downgrade refuses to delete an
existing observation audit. The panel displays occurrence, workflow and bounded evidence.

Verification of this integration: 62 backend tests on isolated PostgreSQL, 14 conversation/
automation UI tests, five-file mypy, focused Ruff/Oxlint and frontend TypeScript passed.
Tests cover expired/foreign credentials, idempotency, restart reconciliation, dispatch order,
cancellation, target/policy identity, artifact tampering and cross-run evidence rejection.
Production is still revision 175. A second isolated full-backup rehearsal through 185 now
passed: all 155 source tables and 11 protected fingerprints matched, 168 target tables remained
consistent after migration, and the owned networkless tmpfs database was removed. No production
migration was applied. Read-only Germany inspection
found no independent runtime auth file or active device-login process. The dedicated broker
credential file remains empty. These are external blockers, not reasons to stop code work.

### Artifact-bound regional deployment broker — code/integration state

An administrator can request a deployment preview below a published repair using a recent,
same-occurrence host observation and exact release CI run. The broker requires the selected
repair PR to be merged into the current main commit, successful canonical CI for that commit/
attempt, and a hash-verified private immutable release manifest. A preview cannot dispatch.
Explicit admin authorization is a separate CSRF-protected, issue/environment-scoped action,
bound to the preview hash, actor, commit, CI run, manifest hash, target baseline and 30-minute
expiry. Model tools and broker receipts cannot create this authorization. It is journaled
without credentials. Cancellation also records the administrator actor.

The broker dispatches only the existing `deploy-regional.yml`, on main, preserving the
`production-owner-approval` environment and regional secrets. Both the database target
reservation and host `flock` prevent conflicting releases. The server rechecks expiry and
container/image/DB baseline under that lock, including after backup/image preparation before
application mutation. Lost acknowledgements, 5xx and malformed mutation responses remain
uncertain; no repeated dispatch occurs. A later network/authentication failure retains the
reservation while remote outcome is unknown. Restart reconciliation searches only the exact
recorded workflow identity. Original branch protections and automatic CD scope are unchanged.

A successful workflow transitions to `verifying`, with deployed=false. A separate private
readback artifact verifies canonical image digests, actual running container/image identity,
commit, target, manifest hash and healthy services. Only that bound artifact can record
deployed=true. It explicitly leaves business outcome/resolution unverified and never changes
the Fitician issue status. The Persian/English panel separates review, authorization, running
image verification and unverified business resolution, with retry-safe request identities.

This first broker path deliberately rejects schema-changing/initial deployments: those still
require the existing separately reviewed migration/bootstrap path and actual restore evidence.
Extending panel migration review and scenario-specific post-deployment resolution remains
engineering work; this is not a claim that all deployment acceptance is complete. The current
feature installation itself needs reviewed migration 175→185 before this panel path is usable.
The new workflow/broker/UI are not on main or deployed, and no production dispatch was used
to prove them. Rollback remains the existing regional release script; it retains prior images/
configuration and treats schema changes separately rather than assuming image rollback undoes
migrations. Verification: 72 backend tests on isolated PostgreSQL, 61 release/host/workflow tests,
16 conversation/automation/deployment UI tests, seven-file mypy, focused Ruff/Oxlint,
OpenAPI consistency, TypeScript and the production web/SSR/prerender build passed. The web
build emitted its existing chunk-size warning. These are isolated checks, not production
release acceptance. Current CI also needs to finish for the final pushed candidate.


The dedicated Iran backup service/timer is now installed from hash-checked committed helpers.
Its first real supervised `pg_dump → age → private S3 → downloaded hash` run completed; the
journal contains its verified encrypted-backup receipt and successful unit completion. The
new dedicated timer is enabled/active for 02:00 UTC daily, with CPU/memory/time bounds and
shared backup locking. Existing application/generation containers, volumes and secrets were
preserved. A future scheduled firing is still a distinct observation, and the local recovery
identity must be retained securely outside disposable build cleanup.

Conversation pagination now returns the runs associated with each message page plus the
current active run, instead of an unrelated latest-20 slice. The panel retains historical run
model/occurrence/evidence when loading older messages and fetches old tool journals on demand;
completed journals are no longer polled continuously. Current issue/environment authorization
continues to scope every page and event request. Fourteen backend history/run regressions and
nine conversation UI cases passed; these remain local/integration checks, not live panel proof.


Operator submissions now reject recognizable structured medical forms, raw request/response
payloads, AI prompt/completion payloads, embedded image data and credential fields **before**
creating a conversation, message or run. Nested JSON keys (including Unicode escapes) are
checked; code identifiers and evidence references remain usable. The panel explains rejection
without echoing payloads, and quoted credentials in sanitized model/tool text are masked.
This is a bounded syntax guard and operator collection policy, not a guarantee of semantic
personal-data detection in arbitrary prose. Twenty-five run/gateway/API/runtime tests, eight
conversation UI tests, Ruff/mypy, TypeScript and targeted Oxlint passed. No provider request
or production application deployment was used to prove these local checks.

The verified S3 ciphertext was restored off-server into PostgreSQL 18 with network disabled,
no published ports and database files only in bounded tmpfs. All 155 source table counts,
11 protected-table fingerprints, revision and FK validation state matched the same source
snapshot. Migration rehearsal from `20261018_175` to `20261113_184` passed on this isolated
copy (168 target tables); existing counts and protected fingerprints remained unchanged.
Only migration code ran against the copy; no application workers or providers were started.
The owned database container/tmpfs was removed afterward. Initial harness startup/socket-path
failures are retained privately; they did not modify production. Production remains at 175.


Docker 29 containerd and classic image stores exposed different `.Id` values for the same
pinned PostgreSQL artifact. Release manifest production, offline export and deployment guards
now compare the canonical OCI config digest: hashed config bytes, or an authenticated OCI
index/platform-manifest descriptor chain when containerd omits the config blob from `save`.
Running containers are checked against the verified alias ID on that same host. A real read-only
probe on both laptop and Iran resolved the same config digest without changing Docker storage,
pulling replacement production images or restarting services. Six backend contract tests and
50 release/workflow tests passed. Both failed CI infrastructure jobs in run 43478297131 shared
one stale test fixture missing the new optional manifest-hash input; the fixture now includes
that input and checks its injection rejection. The complete current CI must still pass.

The dedicated private S3 backup now contains a transaction-matched encrypted production dump
and encrypted metadata. Server-side object readback matched both ciphertext hashes; both were
also downloaded and verified off-server. Snapshot evidence records 155 tables at revision
`20261018_175`. The private recovery identity remains on the laptop only. This is confirmed
backup transport evidence, not yet a restored/migration-tested release gate. Nightly activation,
production migrations and application replacement have not occurred.


Restore preparation exposed a pre-existing bug in the retained snapshot metadata generator:
building one `json_build_object` argument list per schema table exceeds PostgreSQL's 100-argument
limit once there are more than 50 tables. The isolated PostgreSQL 18 integration test reproduced
SQLSTATE `54023` on the complete migrated schema. Inventory/fingerprint objects now aggregate
rows instead, preserving the existing output and all historical freeze/source authorization
guards. Two real database cases (selected and empty fingerprints) and ten existing snapshot/
final-sync tests passed after correction. This is developer-side repair evidence, not proof that
the panel agent performed a repair or that production has migrated.

Full CI now records a strict release manifest containing exact registry digest references,
locally read-back image configuration IDs, CI run/attempt and source commit. The already tested
independent runtime archive is included by checksum/image identity; its automation smoke must
also prove isolation, graceful stop and restart persistence. Source-map upload state and the
completed public-layer privacy gate are explicit. Backend image dependencies now use the
existing pinned uv tool and frozen lockfile, instead of resolving broad pyproject ranges again.

The regional full/Agent release gate downloads the manifest from the exact successful CI run;
optional `expected_manifest_sha256` binds panel authorization to its original bytes. Protected
owner approval and branch policy remain. The deployment job rechecks the hash before SSH and
refuses overwriting an existing SHA release directory with a different manifest. Registry mode
pulls exact digest references, validates their image IDs and assigns the existing local SHA
aliases. Application startup still uses `--pull never`; immutable identity is checked before
migrations/startup and again against each actual running container's `.Image`. Infrastructure
images retain their existing pinned references and volumes.

The same already built Iran backend/frontend images are exported once into a CI offline
artifact. Preloaded full deployment downloads it from the same verified run, validates manifest
and archive hashes, checks transfer/load headroom, then loads images without restarting services.
Loaded IDs must match the reviewed manifest before deployment proceeds. Archives and previous
images are preserved; no global Docker cleanup or volume recreation was added. Existing component
fast paths retain their separate contracts; the repair deployment broker is not yet implemented.

Local checks passed two strict manifest tests, five image/archive/authorization guard tests,
the existing 52 release/regional regressions, Bash syntax, YAML parsing and focused Ruff/mypy.
Actual image publication/offline transfer/new full release has not run: those paths require a
reviewed main release, current CI artifacts, production backup/isolated restore and existing
owner gates. Iran's configured backup service/timer and dedicated backup.env were absent at
readback; the backup destination remains a genuine external prerequisite. No production DB
migration or deployment was performed.

Follow-up: the owner selected creating a dedicated private backup bucket in the existing S3
account. That bucket was created successfully, its owner-only ACL and 30-day lifecycle were
read back, an authenticated synthetic object read succeeded, and anonymous object/list reads
both returned 403. The synthetic probe was removed. Bucket/configuration evidence remains in
ignored private setup files; no keys or destination credentials entered Git. Encryption identity,
backup transport installation and actual backup/isolated restore are still pending; bucket
creation alone does not pass the migration gate. Existing media buckets/policies were untouched.

Regional backup supervision now has its own Iran service/timer and a wrapper that resolves only
the currently running database's retained regional Compose contract. It supplies the existing
application env file explicitly; deployment and scheduled backup share a bounded flock lock.
The original legacy backup units remain unchanged. Forty-five backup/regional regressions and
systemd unit verification passed. Secure backup configuration was created separately with mode
0600; the application env was not edited. A new X25519 recovery identity remains only in the
ignored local setup directory, while the VPS receives its public recipient. Encryption using
the VPS's existing age 1.1.1 and decryption using verified local age 1.3.2 passed with synthetic
data; the private recovery identity never left the laptop. This is compatibility evidence,
not a database restore. No backup timer is activated
and no restore gate is claimed complete yet.

All four controlled validation profiles passed in
[CI 43462627498](https://github.com/mohammad4242/fitician/actions/runs/43462627498)
for `d9ba8c78` before its remaining long-running jobs were superseded. That run was cancelled
by the next scoped commit; it is profile evidence, not a green required-CI or release gate.

### Durable Germany automation channel — code verification

[CI 43464283837](https://github.com/mohammad4242/fitician/actions/runs/43464283837)
passed the independent runtime image smoke, including the new automation process lifecycle.
Its backend job passed 1161 tests and failed the existing OpenAPI contract gate: five automation
responses still exposed unstructured top-level dictionaries. Those responses now use strict
named schemas for heartbeat, leased job polling, authorization and progress; generated shared
contracts were refreshed without weakening the existing test. Fifteen focused contract/API/
publication tests passed after correction. A complete green CI for the current commit remains
required; none of these profile/image results authorizes a production deployment by itself.

Draft PR publication now uses that same separate broker. `fitician_ci_publish_pr` is offered
only for an explicitly authorized repair run; it requires an actual successful validation
operation for the same thread/occurrence/worker and an unchanged snapshot. Connection probes
and failed CI cannot authorize publication. The broker reads the original GitHub run and
artifact again, compares their exact identities, checks the immutable branch and current main,
and rejects a stale base or unrelated diff. It cannot merge, update main or deploy.

Publication intent is durable before POST. Lost acknowledgements reconcile the existing draft;
unknown outcomes never trigger another create request. Closed PRs are not reopened. The panel
retains its PR link and explicitly distinguishes a proposal from deployment or verified
resolution. Forty-two focused backend tests and 15 diagnostics/conversation UI tests passed,
with TypeScript/Ruff/mypy. Live Germany publication remains unverified: its dedicated GitHub
credential is still absent. The developer's laptop GitHub session was not copied to the service.

Migration `20261113_184` adds immutable issue/run/occurrence-bound operations and explicitly
separates runtime and automation connector identities. One active automation worker per
environment is enforced by PostgreSQL. Lease recovery never blindly repeats a workflow
dispatch: intent is persisted before the external mutation, ambiguous results remain uncertain,
and retries reconcile the existing UUID-named workflow. Cancellation is separately recorded
and cannot claim success before GitHub confirms it. Actor, environment and lease authority
are checked again at each privileged step.

The outbound broker uses a dedicated private GitHub credential, never the model runtime's
or developer session's credentials. Candidate code and trusted policy are separate exact
commits; immutable policy tags pin workflow execution. Validation artifact download checks
the archive digest, bounded content, candidate/policy/profile/test identities and exercised
test counts; authorization is not forwarded to the signed artifact host. Preflight is cached
for one minute and invalidated on credential rotation. Only sanitized structured results are
stored or shown. The optional supervised automation container has its own state/private
mounts and 192-MiB/0.1-CPU limits, no Docker socket, inbound port or application credentials.

Existing AI Settings now exposes explicit automation enrollment; the issue panel shows
durable jobs, selected occurrence, exact CI evidence and cancellation. An explicit connection
check submits a fixed isolated test through this channel without a paid model request; it is
labeled separately from repair validation. Viewing or refreshing the panel never submits a job.

Local verification: 34 focused backend tests, 43 settings/diagnostics/conversation UI tests,
TypeScript, Oxlint and debugging mypy passed. Isolated PostgreSQL migration rehearsal passed
183→184, audited downgrade refusals and 184→183→184 without production changes. Broker
credentials, actual GitHub dispatch from Germany, model tool wiring, PR publication and
production enrollment are still pending. Deployment operation kinds in the schema are
reserved, not an implemented deployment capability. No production release is claimed.

### Controlled GitHub Actions validation — in progress

The Germany connector and API-model catalog now expose `fitician_ci_validate` and
`fitician_ci_status` only when explicitly enabled and a broker is bound in the run snapshot.
Submission captures the exact isolated worktree and selected profile/tests; the model receives
a durable queued operation, never a fabricated test success. Status reads are restricted to
the authorized live call, same issue/environment and selected occurrence. Local Docker/GitHub
authority remains disabled on Germany. Heartbeat reports actual broker availability separately
from connector health. Fifty-five focused connector/gateway/API-loop/automation tests passed,
including an actual snapshot submission through the outbound client and occurrence isolation;
these are not proof of selected provider inference or production execution.

Frontend failure was reproduced in the real local networkless image: Vitest could not create
its `/tmp/.../client` communication endpoint on the read-only root. The bounded writable
scratch directory is now its explicit `TMPDIR`. The unchanged candidate then exercised all
seven conversation tests successfully, versus one suite error before the correction. Hosted
CI must still confirm the corrected image. Root filesystem and dependency isolation remain.

[CI 43454623527](https://github.com/mohammad4242/fitician/actions/runs/43454623527)
passed backend, migration and Agent sandbox profiles. Frontend now passes the compiler stages
but fails at Vitest stage 3 with one suite error and no accepted test result. The fixed cache
layout cleared the prior compiler failure; hosted frontend execution remains unverified.

[CI 43448535517](https://github.com/mohammad4242/fitician/actions/runs/43448535517)
again passed backend/migrations/Agent and reported frontend failure at stage 2. Its dependency
CLI resolution is now tested locally, but frontend config also writes TypeScript build info
under `node_modules/.tmp`. Linking the entire dependency directory made that cache read-only.
The sandbox now links individual read-only package entries while allowing cache directories
inside the bounded workspace tmpfs. A regression proves caches do not write into the dependency
image. Global TypeScript codes and `EROFS` are now retained without raw messages. Hosted
frontend acceptance remains pending; the component is not declared operational from these tests.

Follow-up [CI 43443756523](https://github.com/mohammad4242/fitician/actions/runs/43443756523)
confirmed backend, migration and Agent profiles successful. Frontend still failed at compiler
stage 2 with zero exercised tests. A new resolver test failed before implementation and now
passes: the fixed Node adapter resolves the CLI through the current workspace's installed
package, covering both nested and hoisted dependency layouts. Actual local readback selected
TypeScript 5.9.3 at root and 6.0.3 in frontend, plus Vitest 4.1.10. No package was upgraded.
The next hosted run must establish whether this clears frontend's remaining setup failure.

Live CI [43441455318](https://github.com/mohammad4242/fitician/actions/runs/43441455318)
executed the new images/profiles: Agent and isolated migration profiles succeeded; backend
reported one failing test and frontend stopped before exercising tests. Neither failed profile
is accepted as operational. The setup exposed concrete gaps: a 256-MiB scratch filesystem
cannot satisfy repository workspace admission's 2-GiB free-space policy; frontend's locked
nested dependencies and generated public exercise projection were not prepared. The correction
retains a 2-GiB actual RAM limit, explicitly forbids swap and enlarges only scratch's logical
ceiling. It links the committed nested frontend dependencies, uses its TypeScript compiler,
prepares the public projection and runs the frontend build helpers with Python 3.12.

Failure evidence now carries only safe test function/class/type, compiler code/file/line,
missing-module identity and failed command stage. Test parameters, assertion values, error
messages, raw stdout/stderr and private fixture strings remain excluded. Schema validation
rejects unexpected report fields. The next CI run must verify these corrections; passing
local contract checks alone does not clear the previously failing profiles.

[CI 43407136137](https://github.com/mohammad4242/fitician/actions/runs/43407136137)
completed successfully for source commit `71533606465c0bd8b145bdf63c70e8502968960a`.
This confirms the previous candidate's checks, not a production release or the new profiles.
A new independent Germany device challenge was generated and saved only to the ignored
0600 local instructions file; no authentication file existed at subsequent readback.

The repair snapshot contract now binds exact base commit, bounded canonical file contents,
workspace tree digest and snapshot digest. Privileged release files, dependency manifests,
path escapes, duplicates and credential-bearing source are rejected. Source checkout/state
remain untouched. Sanitization can validate the complete bounded 128-KiB source instead of
silently truncating validation at 32,000 characters; ordinary output limits are unchanged.

`ops/debug-validation.py` and the trusted dependency/policy images define fixed backend,
isolated PostgreSQL/migration, Agent, frontend/type and frontend-build profiles. Candidate
code runs as a non-root user with CPU/RAM/PID/tmpfs bounds, no host Docker socket/secrets,
and no external network. Only backend profiles reach a separately created ephemeral internal
PostgreSQL network. Test output stays in bounded temporary storage; only counts and exact
candidate/policy/image/profile identities are exported. Missing/all-skipped/failing test
results cannot count as success. Candidate source is exported from exact Git history without
Git credentials; archive symlinks/path escapes are rejected and dotenv templates omitted.

The reusable/manual `debug-validation.yml` workflow checks out its own policy revision
separately from the candidate, disables persisted checkout credentials and passes no production
Environment secrets. Required CI now exercises backend, migrations, frontend and Agent
profiles; full image publication requires this gate. The selected source/policy identity follows
[GitHub's workflow context](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts),
not a model-provided workflow/script. Contract/unit checks are passing; actual image/profile
execution in GitHub Actions remains the next verification. The Germany runtime still reports
`github_actions_not_connected`; the durable broker, scoped GitHub credential, runtime tool
wiring, PR publication and production enrollment are unfinished. These contracts do not make
those capabilities available or satisfy the production repair/deployment acceptance gate.

### Independent login lifecycle

The independent runtime image now includes the same pinned Sentry 2.74.0 privacy policy and
locked urllib3 dependency. Headless initialization does not import FastAPI/Starlette or enable
unsafe automatic integrations. Each dedicated service optionally reads its own private
`telemetry.json` containing only `dsn` and `environment`; for this SaaS setup DSNs must use
HTTPS Sentry ingestion hosts. No privileged sync/upload token belongs in either file. Service
tags/releases distinguish `debug-runtime` and `debug-automation`; initialization state is
reported separately from delivery. Missing/invalid telemetry configuration does not stop service.

SIGTERM/SIGINT cancel the supervised task and invoke the existing two-second bounded flush.
Twenty-five focused privacy/lifecycle/runtime tests and five Compose/package checks passed.
The CI image smoke now also starts the separate networkless automation process, checks its
limits, graceful shutdown and persistent state across restart. That additional image acceptance
is not yet claimed passed: local image construction failed while downloading Debian package
metadata; hosted CI remains the image verification gate.

Fresh Germany private and public SSH readback matched the trusted host and showed one CPU,
about 1392 MiB available RAM, 2550 MiB free disk and low current load. Broker limits add only
192 MiB/0.1 CPU. Worktree admission and image/archive headroom remain enforced; these samples
are not load-test evidence. The existing generation service was not replaced or reconfigured.

The headless device-login helper now records `pending`, `expired`, `failed`,
`runtime_unavailable` or `authenticated` in its private result file. A 900-second timeout
terminates the login subprocess and persists `expired`; it no longer leaves a missing result
that could be mistaken for a running challenge. Challenge output is forced to mode 0600,
symlinks are rejected, existing authentication is preserved and CLI exit zero without its
own authentication file is a failure. These are login-state checks, not proof of model access.
Two regressions failed before implementation. The focused runtime/client/protocol suite passed
26 tests with one explicitly disabled external protocol check skipped; Ruff/mypy passed.

Public and private SSH were rechecked against the same pinned hostname/boot identity. The
production generation container identity and start timestamp are unchanged. The commissioning
runtime remains unauthenticated/unenrolled; requesting a new code does not complete either gate.

### Passive server evidence and occurrence binding

`fitician_server_evidence` is available to the explicit Codex/API tool adapters. It reads
selected-occurrence diagnostic records, allowlisted current body/food job columns, aggregate
impact, process-reported commit/configuration presence and previously recorded infrastructure
probes. It never loads medical forms/results, user identifiers, error free text, raw logs,
secrets or a production shell. Observations are bounded and sanitized before immutable storage
in the existing run-event journal. Historical probes carry timestamps/staleness and explicitly
unverified current health; environment-reported commits are not container image proof.

The native connector uses a call/lease-scoped authenticated endpoint. The API worker collects
inside its own authorized run lease. Cancellation, admin revocation and environment changes
reject collection. Retry keys return the same snapshot/evidence ID. Admin readback is scoped
by issue/environment and only returns recorded observations; refresh never initiates probes
or paid analysis. Facts/hypotheses can cite these IDs, but server status cannot replace real
regression proof or self-confirm a cause. The conversation labels this distinction explicitly.

A failing regression exposed default submissions borrowing an older occurrence's stack when
the newest occurrence had no stack. Submission now pins the latest occurrence before building
its evidence package. Retries retain that original choice even when another failure arrives.
Focused PostgreSQL verification passed 39 tests, including privacy, passive collection without
count inflation, wrong lease, cancellation, cross-issue access, admin revocation, citation
rules and actual connector HTTP dispatch/idempotent replay. Backend Ruff/mypy passed.
Seven conversation UI tests, TypeScript build checking, Oxlint and regenerated OpenAPI/core
contracts passed. Physical host/container
inspection and live sanitized service-log collection remain unavailable; this tool does not
claim to implement them. This code is not yet in the production application.

Fresh commissioning readback: one CPU, 1399 MiB available RAM, 2562 MiB free disk; independent
runtime and generation service healthy with zero restarts. Runtime still reports
`awaiting_enrollment`, unauthenticated and no verified models. The previous device challenge
expired without an authentication file. A fresh owner login is required; no laptop credentials
were copied. New code is not claimed deployed from this liveness check.

### Germany execution target — owner selection, 2026-11-13

The owner selected a separate supervised Germany runtime; the laptop remains optional.
Fresh pinned SSH checks reached the same host/boot through public `141.11.175.231:9011`
and private `100.108.24.126:9011`. Capacity: one CPU, 1967 MiB RAM, 1464 MiB available,
2047 MiB unused swap, 3730 MiB free disk. Existing generation and install services remain
separate. Planned runtime limits: 512 MiB RAM, 0.25 CPU, two isolated workspaces;
heavy validation belongs in GitHub Actions. Its authentication must be provisioned separately.

Workspace admission now accepts a bounded operator policy (1–40 workspaces, minimum
1 GiB free disk), preserves the existing laptop defaults, and counts workspace manifests
without charging test journals as extra workspaces. Reuse consumes no additional slot.
Five tests failed before implementation; the focused gateway/client suite then passed
20 tests with two explicitly unconfigured container tests skipped. Ruff and mypy passed.
This is code/test evidence, not enrollment or runtime availability.

The existing Sentry proxy failed during host boot with `cannot assign requested address`
for its private Tailscale bind; restart policy alone did not recover this Docker networking
failure. Starting that same owned container restored healthy status. Generation container
identity, start timestamp and mounts were unchanged. Boot ordering still needs correction;
prior notes describing public SSH timeout/proxy Created state are historical observations.

Independent runtime implementation now uses `compose.debug-runtime.yaml` and
`docker/debug-runtime/Dockerfile`, a separate non-root/read-only image with no application
database credentials, generation mounts, host shell endpoint or Docker socket. Its only
mounts are dedicated persistent state and read-only connector configuration; no inbound
port is published. State includes private Codex authentication, App Server thread/SQLite
state and retry-safe call journals. Admission allows two workspaces and requires 1.5 GiB
free before new checkouts/fetches. Generation isolation is unchanged.

`server_runtime` remains alive while unenrolled and reports connection/authentication
separately from liveness. Missing credentials cannot advertise a cached Codex model catalog
as authenticated. Discovery is refreshed periodically; actual inference/tool entitlement
still requires its independent smoke probe. The server does not inherit laptop paths,
GitHub credentials, Docker test execution or generation authentication. Unsupported test,
commit and PR tools are hidden until the GitHub Actions validation/publication path exists.
Codex 0.167.2 is fetched from the official release with its published archive SHA-256;
minimal Python dependencies use the existing backend lock versions and wheel hashes.
Dedicated login uses the documented device-code flow; its output stays in a private file.

Validation: 39 backend tests passed, including real isolated test-container failure/fix,
cancellation and persistent gateway behavior; 21 operations/CI contract tests passed.
Focused Ruff/mypy passed. Local image construction timed out downloading external assets;
Germany reached GitHub, Debian and PyPI successfully. Neither a completed image build nor
server runtime deployment/authentication is claimed yet. Existing Required CI now builds
and exercises the exact runtime image in its split-region job, then exports that same
tested image with checksum and restart/isolation/protocol evidence for offline delivery.

### Reboot recovery and runtime artifact evidence

The proxy's post-boot failure had two observable layers: private-IP bind failure and an
orphaned running container with empty `NetworkSettings.Networks/Ports`. A process-only
health check was insufficient. `ops/recover-sentry-egress.py` now validates the exact owned
container, private binding and existing Compose bridge, starts it if necessary, restores
only its missing endpoint, and requires a real unauthenticated `407` listener response.
The dedicated systemd unit runs after Docker/Tailscale and retries failures. It is enabled
on Germany; no Docker daemon/generation restart or application volume change occurred.
Three focused tests and remote systemd validation passed. An actual host reboot was not
performed. Fresh Iran-to-Germany verification returned `407` without credentials, `403`
for an untrusted destination/port, `200` for the allowed tunnel, and authenticated Sentry
event retrieval `200` with exact event identity. TLS verification remained enabled.

CI run [43388391816](https://github.com/mohammad4242/fitician/actions/runs/43388391816)
passed its runtime build, networkless isolation/protocol/restart smoke and archive export.
Its exact tested PR merge candidate is `4a70812f00d45d266178d08d4792aeb2f1442b0b`,
source branch commit `c3c2f50d`; this is not a merged main release. Artifact `14019662048`
was staged on Germany, with GitHub archive digest and exported image checksum verified.
Image archive SHA-256: `158bec6a541df35dbbe5feffe1657245d925f24e1d60952cc26d7a6327707e40`.
The complete CI/release gate and panel enrollment remain separate from this image proof.

Current evidence supersedes the original Created/public-SSH-timeout notes: Germany's
public `141.11.175.231:9011` and private `100.108.24.126:9011` reach the same pinned host.
The generation Agent remains healthy without restart by this session. The Sentry proxy
is reachable again after restoring its owned network endpoint; authenticated retrieval
from Iran returned 200. Its separate boot-recovery unit is enabled. The independent runtime
commissioning service is healthy, with no production enrollment or verified inference yet.
The old complete-suite failure in CI 43279620964 concerned retained probe actor deletion;
migration 182 and account-deletion regressions corrected that failure. A green complete
release gate for the final candidate is still required before application rollout.

### Germany commissioning and explicit execution targets

The exact tested CI archive was imported without rebuilding. OCI index
`sha256:bfaa3e952feefe77dd50e269bf9c173f78840dec0f0cd536dfc999068f45cbff`
references configuration `sha256:92299b162c8b9357f4a969582bc794612180130cb4ba1cbff22f3357abc9df5d`.
The running independent service uses that same index and PR candidate
`4a70812f00d45d266178d08d4792aeb2f1442b0b`; GitHub comparison confirmed its source tree
matches branch commit `c3c2f50d`. This is not a production application release.
Service `fitician-debug-runtime-connector-1` uses `/opt/fitician-debug-runtime`, user 10001,
a read-only image, no inbound ports/Docker socket/application network, 512 MiB RAM,
768 MiB memory+swap, 0.25 CPU, 96 PIDs, bounded temporary/log storage and persistent
dedicated state. Disk remaining after import/start: 2562 MiB. Generation identity, start
timestamp and mounts were unchanged; no application migration or restart occurred.

The actual CLI reports 0.167.2. Independent authentication was absent; a dedicated
device-code login was started without copying laptop or generation auth. Instructions
went only into an ignored 0600 local file. Authentication/inference/model entitlement,
production API enrollment and the laptop-offline panel path remain unverified. A login
cache or model catalog alone will not complete those gates. Later source changes below
are not yet part of that commissioning image.

Migration `20261113_183` adds `AITaskConfig.debug_connector_id`, a nullable UUID with a
named RESTRICT FK and a check limiting it to `debug_agent`. API models use the explicit
saved target; an empty selection means analysis only. Unique-online auto-selection was
removed: tests reproduced silent laptop substitution when Germany was offline. Codex
profiles retain their explicit offline target in provenance. Runs snapshot target name
and capabilities. Offline/revoked/wrong-environment targets block before provider/tool
execution; changed capabilities invalidate verification and queued-call authority.
Unsupported tools are excluded from API orchestration. AI Settings selects API execution
targets and enrolls Germany or an optional laptop with distinct private paths and an
explicit pinned Codex executable. Conversations show the actual execution target and
a simple Persian offline explanation.

Final focused validation: 117 backend debugging/admin/account tests passed, including
real pinned Codex protocol/catalog checks and isolated Docker test/cancellation checks.
All 54 diagnostics/AI-settings UI tests passed. Strict mypy passed 26 relevant source files;
focused Ruff/Oxlint, TypeScript project build, core build and regenerated OpenAPI checks
passed. Isolated PostgreSQL rehearsed `183 -> 182 -> 183`; a separate test confirmed
downgrade refuses to erase a selected target. No production schema change was applied.

Commissioning rollback: stop only the separate connector through
`/opt/fitician-debug-runtime/current/compose.debug-runtime.yaml` and adjacent `runtime.env`
(`docker compose -p fitician-debug-runtime --env-file ... -f ... stop connector`). Keep
the dedicated state and private configuration; never remove volumes. Generation, the
application stacks and their database are outside this operation. Full feature rollout
and rollback still require the independent backup, compatibility and release gates.

Authentication readback: the dedicated server CLI returned exit 1 and `Not logged in`;
no dedicated `auth.json` exists. Its device-code attempt ended without approval and the
challenge expired. This is an outstanding user sign-in step, not an inherited laptop
session, a verified model call or evidence of provider entitlement. A fresh challenge
must be generated when the owner is ready; no code/token belongs in chat or Git.

Germany's two-checkout policy now recycles only clean, owned read-only caches, keeping
their Git branch, identity manifest, test evidence and native conversation state so the
same exact source can be restored. Repair workspaces, manual modifications, unknown
directories and malformed/unowned metadata are never discarded. Laptop cache recycling
stays opt-in. Source identity and cleanliness are checked before reusing a read-only
checkout. Capacity/missing-source/interrupted-call failures are persisted as bounded
blocker codes with Persian explanations; a missing source cannot trigger a paid turn.
Runtime packaging imports the new workspace module in its real image smoke test. CI now
caches runtime layers and normalizes the pinned binary timestamp to avoid duplicating
the large CLI layer on every release. New-image cache reuse is still a CI verification gate.
Focused validation: 47 backend tests (including real isolated Docker tests/cancellation),
six conversation UI tests, 21 CI/operations contracts, Ruff, strict mypy and TypeScript
project checks passed. These latest lifecycle changes are not deployed on the server yet.

## Sentry capture foundation

Pinned dependencies: Python 2.74.0, React/Vite plugin 11.12.0, React Native 8.34.0.
Each independently built Python service has a byte-identical privacy module, checked by tests.
Capture is optional (`SENTRY_DSN`); Python initialization failures fail open. Browser and mobile
initialization failures also fail open. Python process shutdown has a two-second flush budget.
The serialized event allowlist removes request content, identity, breadcrumbs, local variables,
source context, arbitrary messages, AI content and arbitrary span attributes. Exception ordering
and permitted source coordinates remain. React component names survive without local paths.
Mobile capture passes the original Error object to the SDK, rather than creating a new stack.

Configuration channels (never supply credentials in a conversation):

- Server secret configuration: `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, exact `APP_BUILD_SHA`.
- Web build variables: `VITE_SENTRY_DSN`, `VITE_SENTRY_ENVIRONMENT`, `VITE_APP_BUILD_SHA`.
- EAS environment: `EXPO_PUBLIC_SENTRY_DSN`, `EXPO_PUBLIC_SENTRY_ENVIRONMENT`.
- Private build secrets: `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT`.

Web source maps are generated only for configured private uploads, and deleted after upload.
The upload plugin does not receive a privileged token in client code. The mobile Expo plugin
and Metro integration prepare release artifact support; a native rebuild is required.
The existing artifact CLI 3.8.2 is executable. Native release verification remains outstanding.
`SENTRY_BUILD_ARTIFACTS=1` injects Debug IDs without build credentials or upload. The Docker
`sentry-artifacts` target exports private bundles/maps; the public stage removes maps before
copying to the final image. Local upload mode still deletes maps after a successful upload.
DSNs are public ingestion identifiers, not privileged API tokens.

## Verification boundaries

Unit tests exercise the real Python SDK with an in-memory transport, chained exceptions,
deduplication, and sensitive fixtures. This proves serialization behavior, not external ingestion.
Isolated PostgreSQL regressions exercise existing diagnostics behavior and migration startup.
JavaScript tests/typechecks do not prove native crash capture or native redaction.

## Durable evidence and analysis conversation

Additive migrations `20261112_176` through `20261112_178` add immutable exception evidence,
external event/group references, the `debug_agent` task constraint, and durable issue threads,
messages, leased runs and sequenced events. The API validates admin authorization, CSRF,
issue ownership of occurrences/runs, and idempotency-key payload identity. Each run snapshots
the configured model and evidence. Configuration and secrets are separate; credentials remain
encrypted in the existing provider store. No default model is forced.

The optional `compose.debugging.yaml` overlay runs two independent backend-image workers.
It requires a tested image digest, an explicit existing network and a dedicated secret file.
The debug worker now supports selected OpenRouter API models through bounded function-tool
orchestration, and a version-pinned Codex App Server through an explicitly enrolled laptop
connector. Models without tool capability remain analysis-only. Missing connector/runtime
requests are blocked honestly. Existing generation runners retain their original sandbox.
Temperature, confidence thresholds and automatic model fallback are not claimed as effective
in analysis mode. Supported routing restrictions are applied without changing the selected model.
The UI persists conversation history, keeps retry identities across reconnects, consumes durable
progress events through authenticated SSE, and uses authenticated polling as a fallback.

Sentry correlation uses bounded exact-event polling. There is no list pagination because each
lookup addresses one known event ID. The worker checks event, local occurrence and environment
identity, rejects redirects, limits response bytes, and uses durable attempts/backoff/leases.
It never changes local issue counts/status from remote grouping. Retry exhaustion and last error
are visible in evidence responses. No Sentry webhook is exposed by this implementation.

## Remaining implementation and acceptance work

The full six-phase task is not complete. Implemented adapters and repair gateways need the
remaining acceptance coverage and production configuration. Still required: artifact-bound
deployment broker and post-deployment verification; automatic production notification activation; complete
propagation and transport-drop health; native crash/privacy acceptance; all four workflow
outcome/quota regression gates; and release pipeline/production acceptance. These are engineering
work as well as external prerequisites. Production application containers have not been replaced. Sentry secret configuration was prepared separately without restarting services.

External configuration installed during continuation: Iran and Germany Sentry DSN/sync
credentials in their existing mode-0600 server environment files, and Sentry upload/sync secrets in GitHub Environments
`production-iran` and `production-germany`. Iran web build variables identify the configured
organization/project/DSN/environment. No existing unrelated server setting was changed.
Services were not restarted; running old images have not adopted this configuration.

Still outstanding: live activation and regional egress verification; EAS/mobile release
configuration and native artifacts; production debug/sync worker image/network/secret wiring;
production connector enrollment; scoped long-term GitHub/deployment broker credentials and
automatic notification activation. Codex protocol/authentication were verified on the enrolled local staging
connector, not the production panel. Use secret files, GitHub Environments and EAS channels.

## Continuation: occurrence binding and external readiness

The selected occurrence is now controlled by `IssueDetail` and shared by `IssueEvidence` and
`DebugConversation`. It is included in the serialized submission, idempotency hash, immutable
run evidence and returned run provenance, including occurrences without captured stacks.

Read-only inspection on 2026-11-12 confirmed Iran SSH access and mixed existing component
releases; no deployment was performed. Main requires `Required CI` with admin enforcement.
The initial account prerequisite was resolved during continuation; see verified connection below.

## Sentry account configuration channels

The following private projects are configured in the Fitician organization:

| Project | Platform | Processes |
| --- | --- | --- |
| `fitician-backend` | Python / FastAPI | API, body/food workers, scheduler, notifications, debug and sync workers |
| `fitician-agent` | Python / FastAPI | Germany Agent Service |
| `fitician-web` | JavaScript / React | Web and PWA |
| `fitician-mobile` | React Native / Expo | Android and iOS release builds |

Use environments `production-iran`, `production-germany`, `staging`, and `development` as
appropriate. Environment is an event attribute, not a separate project per environment.
Disable public issue sharing, Replay, screenshots, view hierarchy, and automatic AI/content logs.
Keep source artifacts private. Add server-side scrubbing as defense in depth.

Secret configuration channels:

- Iran dedicated server configuration: backend DSN, `SENTRY_ORG`, backend `SENTRY_PROJECT`,
  `SENTRY_ENVIRONMENT=production-iran`, `DIAGNOSTICS_ENVIRONMENT=production-iran`,
  and `SENTRY_API_TOKEN` with `project:read` restricted to these projects.
- Germany Agent configuration: its own project DSN and `SENTRY_ENVIRONMENT=production-germany`.
- GitHub Environment `production-iran`: private artifact upload token; organization/project
  identifiers and public web DSN as build configuration, never a privileged client token.
- EAS production environment: mobile DSN as `EXPO_PUBLIC_SENTRY_DSN`; private upload token
  in EAS secrets, plus organization/project names. Rebuild native binaries before native QA.
- Select `SENTRY_API_REGION=us` or `de` to match the Sentry organization; `global` is supported
  for the global API entry point. Redirects to arbitrary hosts are intentionally rejected.

## Sentry connection verified during continuation

The second handoff exchange returned HTTP 200, but CLI setup-code redemption returned
`invalid_grant`. No private `handoff-code` input file existed; stale file contents were not used.
The CLI's device login also received a 403 denial. An independent standards-based device flow
succeeded, the owner approved it in the browser, and the OAuth token was stored only in a
mode-0600 locally excluded file. The account and `fitician` organization were independently
verified with HTTP 200. The regional API is `https://us.sentry.io`; team slug is `fitician`.
The global identity endpoint is used for account verification because the regional API root
returns 404. Authenticated CLI status also succeeded using the protected environment token.

All four named projects now exist and their server-side data scrubbing, IP removal, TLS
verification, disabled JavaScript scraping and zero raw crash-report retention were read back
and verified. Only public DSNs were extracted to private local configuration; private DSNs and
project key secrets are never exported. No SDK/package reinstall was performed. A modern
account CLI was installed because it was absent.

Least-privilege automation tokens were subsequently validated and securely configured as
described below. Synthetic ingestion, private artifact upload and source mapping were verified
separately. No production application deployment has occurred.

## Live isolated evidence (not production deployment)

On 2026-11-12 the tracked backend synthetic probe ran against a separate
`fitician_sentry_verification` PostgreSQL database with synthetic identity only. Sentry API
retrieval confirmed event `a974a9a05f434d21b7a77533910dbbed`, staging environment, local
occurrence `eea0346c-fe67-4449-a051-49702949a12e`, and release
`fitician-backend@ec236693a56b00d10570c666242dfc8953fbd401`. The real synchronization worker
linked local issue `33b7edd3-b47c-4e14-9877-ce15a9dd0df2` to Sentry issue
[7844463309](https://fitician.sentry.io/issues/7844463309/). Authenticated admin issue and
evidence endpoints returned observed delivery, exact commit and sanitized remote source.
These prove backend ingestion and admin API linkage in isolation; production, rendered browser
chat, native crashes and web symbolication are separate gates. The UI now exposes the observed
Sentry issue link. Permanent sync/upload automation credentials are held in the mode-0600 excluded local
configuration file. They are never emitted by setup commands, logs or reports.

## Enrolled runtime and tool execution

Additive migration `20261112_180` stores revocable connector credentials as SHA-256 hashes,
leased/idempotent tool calls, and separate read-only runtime probes. Each connector is scoped to
one environment and `mohammad4242/fitician`. Every claim/progress/completion rechecks authority;
admins can revoke enrollment. Enrollment/revocation is recorded in the existing AI audit log.
Only outbound HTTPS is accepted, with a localhost HTTP exception for isolated tests.

The laptop client is `python -m app.debugging.connector --config /private/configuration.json`.
The file must have mode 0600. The existing Admin AI Settings page can enroll/revoke connectors
and download the once-returned credential without displaying/storing it in browser storage.
Set repository/workspace paths, a dedicated private Codex home with authentication, and a
trusted SHA-256-pinned test image. No daemon inherits this interactive development session.
The isolated verification connector was enrolled explicitly and uses a separate private runtime
home populated from the owner's already-authorized local CLI account.

Codex CLI 0.167.2 is the currently supported protocol, checked before startup. The adapter uses
persistent App Server threads and turns, and interrupts cancelled turns. Native shell, unified
execution, apps, web search and external MCP are disabled. Only schema-validated gateway tools
are supplied. Dedicated runtime configuration and project Codex overrides are rejected. Unknown
approval requests are denied. Model IDs are discovered, never substituted or defaulted to SOL.
Profiles require a real model/tool smoke before enablement; the usual generation profile
verification remains intact. Current local profiles do not claim image, structured generation,
web, temperature or output-token controls.

The API adapter queries model tool capability, uses the selected model with fallback disabled,
and runs at most eight bounded rounds. Without reliable tool support it explicitly uses analysis
mode. Tool execution requires an unambiguous online enrolled connector, snapshotted per run.
API protocol tests use HTTP mock transport; a live OpenRouter tool run is not yet established.

Source reads/searches are bounded and sanitized. Writes affect only `debug/run-<UUID>` worktrees
at the selected exact release commit. Secrets, traversal, symlinks and privileged release files
are rejected. Tests execute a meaningful Python unittest file in a pinned, networkless, read-only,
non-root container with resource limits. Test evidence is bound to the tree digest; commits and
the GitHub draft-PR broker require matching evidence. Other test profiles (including database
integration and frontend suites) are not yet executable through this gateway. Gateway tests
proved a seeded subtraction bug can be patched, tested and committed without changing the
original checkout. Publication uses the owner's authorized local GitHub credential through a
fixed repository/branch broker, not model-selected destinations. A real seeded repair PR 42 was subsequently verified (see acceptance evidence below);
feature PR 41 alone is not proof of the repair flow. Broader test profiles remain outstanding.

Tool activity, model selection and occurrence identity persist beneath the issue. Per-call local
journals replay completed acknowledgments without re-executing actions. An interrupted uncertain
call returns a blocked/error result requiring a new run; it never silently repeats mutations.
Codex completed calls can be recovered after a worker restart. API tool-loop interruption may
require a new run if replayed arguments differ. Queues, tool counts, input/output sizes and local
workspace capacity are bounded. Offline clients fail closed and show stale heartbeat state.
Deployment is not exposed as a model tool; its artifact-bound broker remains outstanding.

Follow-up repair runs reuse a connector-owned worktree keyed by issue thread, exact release,
environment and authorized action. Other issues/releases and read-only investigations receive
separate workspaces and runtime histories. Missing Codex authentication advertises no Codex
models without disabling API-model repository tools. Cancelling an active test stops its own
networkless container, invalidates previous test authorization and waits for cleanup. Test output
is bounded on disk; no test body becomes a host shell command. Real-container regression tests
cover cancellation and confirm no test container survives it.

### Actual isolated acceptance evidence

- Real Codex smoke: selected catalog model `gpt-6.1-sol`, CLI 0.167.2, actual read tool, 16.55s.
  This is a verification choice, not a configured product default.
- Issue run `c6f5ae6d-65ce-46f5-bb98-ca2b23d3c4b6` completed through the authenticated admin
  route, durable worker and laptop connector. It analyzed occurrence
  `eea0346c-fe67-4449-a051-49702949a12e`, executed `fitician_read_file`, and cited the persisted
  evidence ID in its Persian reply.
- Chromium at width 390 rendered that issue, Sentry link and conversation; refresh preserved
  messages, with no horizontal document overflow. This was the local isolated staging path.
- Actual web event `d8a41b2cef2e4ca99dda7a8381b4f675` was ingested at
  [Sentry issue 7844485882](https://fitician.sentry.io/issues/7844485882/) with release
  `fitician-web@59f7d3c9c566a791cd38760ffbadc21fa5f5e2f2`. Private artifact upload succeeded;
  Sentry returned the original tracked `sentrySyntheticProbe.ts:3` with no symbolication errors.
  The isolated probe was bundled with real web initialization/privacy code; no public production
  trigger was installed. Native release/crash acceptance remains unperformed.

Production has neither this connector enrollment nor its runtime yet. Permanent automation
credentials, production worker installation, pipeline release gates and a verified deploy are
separate states and are not claimed by the above evidence.

## Automation credential verification and configuration

`automation-tokens.json` is excluded by local Git rules and has mode 0600. Roles were assigned
explicitly: `fitician-upload` to `upload`, `fitician-sync` to `sync`. Authenticated API readback
confirmed upload scope `project:releases`, and sync scopes `event:read`, `project:read`.
The sync token fetched the real synthetic event and matched its event ID. Artifact CLI 3.8.2
completed an actual source-map upload/assembly check with the upload token (exit 0).
No token values appear in this document or committed files.

Iran server configuration was atomically prepared and read back as mode 0600, preserving all
unrelated settings and leaving running containers untouched. GitHub environment secret updates
succeeded for both production regions. CI build/release wiring and server-origin connectivity
are separate verification gates. Germany direct public SSH was unavailable; its existing private Tailscale path and pinned host key
were verified. Its existing server secret file was also atomically configured and read back as
mode 0600 without restarting services or altering unrelated settings.

## Private release pipeline wiring

The active full and frontend component image paths use the existing `production-iran` GitHub
environment with `deployment: false`: build jobs receive scoped secrets without creating false
production deployment records. Branch policy and main-only publication guards remain enforced.
The upload credential is a BuildKit secret, never a Docker ARG/ENV or client variable. The Vite
upload allowlist contains only emitted JavaScript and JavaScript source maps. The public image
removes all maps before COPY, and nginx returns 404 even if a map file is accidentally present.
A host-side archive check scans every image layer for maps and configured privileged credentials,
including files removed by later layers, before pushing the same verified image.

Release images identify their exact source SHA. Agent Service now receives its build SHA, and
its Germany Compose contract explicitly passes optional capture configuration. Its generation
CLI version and read-only execution policy are unchanged. The interactive debug runtime remains
a separate 0.167.2 laptop adapter. Disabled legacy appearance/CD paths were not enabled.

The all-layer check correctly rejected a historical local image containing service-worker maps.
A real isolated nginx test returned 404 for both an existing fixture asset map and `sw.js.map`,
while health remained 200. A build with the new contract and live CI is still a distinct gate.

Iran-origin authenticated Sentry API access currently returns an HTML `403 Forbidden`; the same
sync credential retrieves and identifies the event with HTTP 200 from the authorized laptop.
This establishes a regional access failure, not its underlying network/provider cause.
Germany SSH was recovered through its existing Tailscale address and the pinned known host key;
no host verification was disabled. Server configuration/readback and egress verification continue.

## Restricted regional egress (owner-selected architecture)

The owner selected a restricted Germany HTTPS proxy after authenticated reads returned
403 HTML from Iran and 200 with matching event identity from Germany. The versioned
`compose.sentry-egress.yaml` service is separate from Agent Service and all application volumes.
`ops/sentry-egress.py` generates an exact Sentry-host allowlist; only authenticated CONNECT to
port 443 is permitted. TLS remains end-to-end; there is no TLS interception or request logging.
The service binds only its explicitly configured private Tailscale address, runs as UID 13 with
a read-only filesystem, no capabilities, disabled core dumps and bounded CPU/memory/processes.
Authentication uses a separately mounted password hash; no credential is baked into the image.

The image was built from the existing verified Ubuntu 24.04 digest with security-updated
Squid `6.14-0ubuntu0.24.04.5`; the tested local immutable image ID is
`sha256:f95103c40d0c56506738e7e2db5302213e81792f6c333349e60d2152e4e9a515`.
Local real-proxy checks returned 407 without authentication, 403 for an unrelated destination,
and 403 for a non-443 port. An authenticated allowed destination completed normal verified TLS;
its Iran-origin upstream response remained 403. Germany activation and Iran-through-Germany
event retrieval are separate acceptance checks, not inferred from local startup.

Only Sentry SDK transport and the synchronization worker read `SENTRY_HTTPS_PROXY`. Global
HTTP/provider routing is unchanged. SDK internal errors are excluded from the diagnostics log
bridge to prevent recursive issue/alert creation during a Sentry/proxy outage.

The actual private web BuildKit test at commit `f5ff7092c74784b0cc3f9b9c0123b3f9be085c7d`
completed, including private upload and all-layer credential/map inspection. Its local image is
`sha256:413d98dbd61169b9d1d9264162511843cd65ef63b77f0b07697ed1cc643734f2`
with the matching source label and staging configuration. This image has not been deployed.
Docker Buildx v0.39.0 was installed locally from its official checksum-verified release because
the CLI plugin was absent; SDK installation was not repeated.

### Durable tool evidence

Instrumented repository/test tool results are sanitized and persisted as immutable run events,
with server-assigned evidence UUIDs returned to both Codex and API tool loops. The conversation
shows expandable tool output and citation identities after refresh. Outputs are bounded to
30 KB per tool; hidden model reasoning is not accepted. Progress retries reuse the evidence ID
and reject conflicting content. Every write/read/stream retains issue/environment/admin scope
and cancellation/lease validation. No new database migration is required for these run events.

### Client occurrence correlation

Web global handlers and React root handlers share application-owned capture identity. React
rethrows do not create a second Sentry event or local occurrence; original errors and cause
chains reach the SDK. The local UUID is tagged on the external event, and the generated Sentry
ID is a pending reference, never proof of delivery. Authenticated ingestion accepts only the
reference (not client-supplied stacks), selects an explicitly configured project by platform,
and preserves issue counts under retries. Set `SENTRY_WEB_PROJECT=fitician-web` and
`SENTRY_MOBILE_PROJECT=fitician-mobile` on the backend and synchronization worker. The worker
polls only those configured projects and validates occurrence/environment identity before
accepting remote evidence. Unauthenticated events and observations lost before persistence
remain outside this exact-ID synchronization path; broad project discovery is not implemented.

The PR broker accepts `main` or an explicitly configured isolated `debug/seed-<UUID>` acceptance
base. Models cannot select the base. The tested commit must descend from the current remote
base; a stale production-release branch is rejected before push, preventing accidental reversal
of subsequent main changes. No merge or production deployment authority is added.

The debug worker accepts `JOB_HEARTBEAT_PATH`, matching the existing healthcheck and sync-worker
contract. This permits a supervised laptop/staging worker without privileged `/run` writes;
production retains `/run/fitician/heartbeat.json` by default.

### Actual isolated repair and PR acceptance

A real Codex App Server 0.167.2 run (`5fffdc57-2c8f-4728-8c49-fe1beefe5b69`) used the selected
catalog model `gpt-6.1-sol` and selected occurrence `ff2affa4-59c1-4633-b6f6-77144c6bdbf7`.
The supervised worker and enrolled laptop connector observed a failing isolated unittest,
changed only `backend/debug_agent_acceptance/fixture.py`, observed the same test pass, committed
`365404e91c918c6f8c51ce17755c23e2fefae60d`, and published draft
[repair PR 42](https://github.com/mohammad4242/fitician/pull/42). The remote head and configured
isolated seed base were checked against tool evidence. This PR targets a synthetic acceptance
branch; it must not be merged into production. The user's checkout was not patched by the run.
The final Persian reply cites the persisted failure/test/diff/commit/PR evidence UUIDs.

Chromium at 390 pixels rendered the real repair conversation and PR, retained them after refresh,
and expanded the persisted tool evidence without horizontal overflow. This proves the isolated
staging path, not deployment or production connector connectivity.

### FarazSMS channel

The owner selected FarazSMS for operational alerts. The destination is kept in private server
configuration (`DIAGNOSTICS_ALERT_PHONE`, excluded from model/Sentry context), not Git or UI
responses. The adapter reuses the configured API key and sender line via the documented
[`/sms/simple`](https://docs.iranpayamak.com/send-simple-sms-13909967e0) endpoint, independently
of the OTP pattern. Messages contain deterministic Persian feature/failure text, occurrence count
and an authenticated issue deep link. HTTP acceptance is distinct from phone delivery; an
ambiguous dispatch timeout must not trigger an automatic resend. Automatic production activation remains separate from the operator-only delivery check below.

Migration `20261112_181` adds environment-scoped SMS aggregation and immutable dispatch attempts.
The independent `diagnostics-alert-worker` profile in `compose.debugging.yaml` uses a dedicated
`FITICIAN_ALERT_ENV_FILE`; missing configuration cannot enable sending. Explicit activation time
prevents historical issue floods. Default policy: a 60-second aggregation window (critical issues
immediate), one-hour issue cooldown, at least 30 seconds between any dispatches, and 20 dispatches
per hour. Regressions can bypass the issue cooldown while retaining the global limits. Existing
internal alert thresholds remain unchanged. Resolved/ignored queued issues are suppressed.

Dispatch is leased and committed before provider I/O. Uncertain dispatches and expired worker
leases are never automatically resent. Only explicit rate-limit/connect-before-send failures are
retried, at most five times. An opaque notice UUID in the authenticated deep link permits narrow,
read-only receipt recovery after lost acknowledgments; recipient identity and matching notice
must both match. Provider receipt polling is bounded and never follows response pagination URLs.
The admin panel shows queued, rejected, accepted/unconfirmed, unknown and provider-reported
receipts separately, without exporting the configured phone. Closed settled delivery audit expires
after 90 days; pending dispatches and repair conversations remain pinned.

On 2026-11-12 one operator-only test used the committed adapter on the existing Iran server,
without changing/restarting application containers or applying migrations. The request returned
an unexpected reference shape, so no resend was attempted. A subsequent narrowly matched
provider report returned HTTP 200, reference `30536259`, `total_count=1`, `delivered_count=1`,
and no delivery failure. The owner independently confirmed receipt on the phone. The test links
to synthetic issue `2652f0a0-1ac4-406f-8af0-ed88be41ac75` at the authenticated production panel.
The destination is stored only in mode-0600 local/server configuration. Automatic production
sending remains disabled until the migrated worker release passes the release gates.

Isolated PostgreSQL rehearsal passed upgrade to 181, downgrade to 180, and re-upgrade to 181.
No production database migration or application release was performed for this check.

### Coupled React occurrence and original-source verification

A compiled Chromium fixture using the committed React root handlers at
`16a7b637d480e20571822db17c9bde0b2780a35d` produced exactly one client ingestion request
(HTTP 202) despite rethrowing the same original error through the window handler. The two-link
exception chain reached Sentry event `9320b37fb8884fbba8b66df1474a9f8e`. Exact UUID/environment/
release checks linked Fitician issue `6393ac5b-b0e8-41a0-83b0-be9deb0cd34c`, occurrence
`43f1f853-5e30-407f-ab64-ed471c770b78`, to
[Sentry issue 7845084554](https://fitician.sentry.io/issues/7845084554/). Local issue count remained
one. The observed source release matched `fitician-web@16a7b637d480e20571822db17c9bde0b2780a35d`;
private artifacts resolved the original tracked `sentrySyntheticProbe.ts:3` with no symbolication
errors. This proves coupled web capture/correlation/source mapping in isolated staging, not a
production web deployment or native crash acceptance.

### Germany reboot and suspended activation — historical outage

After the owner restarted Germany, the initial Iran health probe returned 200, then the peer
became offline (Tailscale last-seen `2026-11-12T18:30:00.1Z`). Subsequent SSH/TCP checks on 9011
from the laptop, Iran and [CI](https://github.com/mohammad4242/fitician/actions/runs/43280568630)
failed at the network stage; fresh health/capability probes timed out. No new server deployment
was attempted. The last successful pre-reboot readback showed the transferred proxy image and
its container in `Created`, without passing readiness or activating the current symlink. Its
post-reboot state and existing Agent image/volume state require readback after host connectivity
returns. Do not claim the restricted regional egress operational from a completed transfer.

### Germany recovery and release-identity correction — 2026-11-13

Pinned private SSH on 9011 recovered. Existing proxy container was started after immutable
image/config checksum and private-binding checks; it is healthy on manifest
`sha256:e1cef74666dfd59712e949c97777713740601d6ce6edd43bfa852e3f3903541f`.
No second proxy was created. Existing Agent container identity/start time/mounts were unchanged.
Iran authenticated Sentry event retrieval through that proxy returned HTTP 200 with the exact
known event identity. Negative checks returned 407 without authentication and 403 for an
unrelated host or non-443 port; TLS verification stayed enabled. `SENTRY_HTTPS_PROXY` was
atomically installed in the existing mode-0600 Iran environment file. Running application
containers were not restarted and have not adopted the new release/configuration.
Public Germany SSH still times out; hosted release access must be verified separately.

Native iOS now remains `ios`, distinct from `ios_pwa`, throughout shared contracts, authenticated
ingestion and mobile Sentry project selection. Mobile diagnostics and SDK release metadata use
only a known 40-character commit; the native build number is a separate distribution identifier.
The EAS post-install guard rejects unknown/conflicting configured releases and missing private
upload credentials. Unconfigured builds remain independent. Generated OpenAPI/types were
regenerated and checked. Focused verification: 34 backend tests on isolated PostgreSQL, 14 core
tests, 7 mobile tests, 80 mobile foundation tests, mobile TypeScript, focused Ruff/mypy/Oxlint.
Native release/crash acceptance and EAS secret configuration are still outstanding.

### CI account-deletion regression and safe probe retention

Retrieved complete backend job logs for CI 43279620964. Three shards passed (1134, 1134,
1133 tests); the last shard reported 1131 passed, one intentional skip and exactly one failure:
`test_all_user_references_are_safe_for_account_deletion`. `debug_connector_probes.actor_id`
used `ON DELETE RESTRICT`, conflicting with existing account deletion. This is an implementation
regression, not an infrastructure timeout. Migration `20261113_182` changes that reference to
nullable `SET NULL`; the audit remains, and queued/running probes lose execution authority when
the administrator is deleted. Existing connector tokens also remain unusable without their actor.
The 181→182→181→182 cycle passed on isolated PostgreSQL. If retained actorless probes exist,
downgrade explicitly refuses to erase audit or invent identities; keep schema 182 and roll forward.
Production schema was not changed.

Private artifact upload was also reverified through the restricted Germany proxy: the existing
exact-release web bundles/maps for `fitician-web@16a7b637d480e20571822db17c9bde0b2780a35d`
uploaded successfully (CLI exit 0, TLS verification enabled). This is artifact-upload evidence,
not proof that a new application image is deployed.

### Persistent investigation findings and explicit review

Findings reuse the existing issue/run event journal; no parallel conversation store or new
findings migration is introduced. Both tool-capable runtime paths expose
`fitician_record_finding` for observed facts, hypotheses and next checks. The backend validates
every citation against the selected run's occurrence/snapshot or actual scoped tool evidence.
Unknown IDs, cross-run evidence, unsupported classifications and model self-confirmation are
rejected. Proposal retries preserve the original evidence ID and reject conflicting content.

`GET /api/v1/admin/diagnostics/issues/{issue_id}/findings` provides occurrence/environment-scoped
pagination, model/run provenance, stale-evidence state and available regression proof IDs.
`POST .../findings/{finding_id}/verify` requires an authenticated administrator, CSRF, idempotency
and the exact evidence version. A completed repair must contain a failing then passing
instrumented regression test with the same command/image, exercised tests and different tree
digests. Explicit review records its note/actor/proof IDs in a separate immutable event. It does
not resolve an issue or claim deployment. New source evidence marks old conclusions stale.
A test proves a downgrade with actorless probe audit refuses data loss.

The Persian/English issue page separates observations, hypotheses/previous reviews, reviewed
findings and next checks. Review controls select actual test evidence, rather than accepting
model-provided success assertions. Legacy capture confidence is no longer interpreted by the
UI as cause verification; a trusted ZeroDivisionError and source line no longer self-confirm a
cause. Typed OpenAPI/shared contracts were regenerated. Verification: 61 backend tests on
isolated PostgreSQL, 21 diagnostics UI tests, focused Ruff/mypy/Oxlint and frontend TypeScript
passed. Real updated-runtime/panel acceptance remains the next gate; no production release
was performed by this step.

### Independent Codex executable pin

The laptop's general Codex command changed to 0.168.0 between sessions. The debug adapter
correctly rejected that unverified protocol, so no Codex tools ran; the panel recorded blocked
runs with `interactive_runtime_not_configured` instead of silently using another runtime.
The previously verified standalone 0.167.2 executable still exists. Connector configuration
now requires an explicit absolute, executable, non-group/world-writable `codex_executable`
when `codex_home` is supplied; discovery, probes and turns use it consistently. The global CLI
and generation runner were not changed. The private staging configuration now selects the
existing 0.167.2 binary. Fifteen tests passed, including an actual protocol handshake/model
catalog against that explicitly selected executable. Model-list output is a catalog, not proof
of model entitlement; inference acceptance remains separate.

[Official App Server documentation](https://developers.openai.com/codex/app-server) was
rechecked; the installed 0.168.0 schema was inspected but that version was not added to the
accepted protocol list. Two blocked panel submissions executed no tools or inference and
were retained as offline/unsupported-runtime evidence; a deliberate new investigation after
restoring the connector remains the live acceptance gate.

Hosted SSH readback from [main run 43380399467](https://github.com/mohammad4242/fitician/actions/runs/43380399467)
failed at network connection, before host-key verification or authentication. The prior feature
run was rejected by environment branch policy and is not SSH evidence. Private SSH works;
sshd listens on 0.0.0.0/[::]:9011, and the host firewall has explicit 9011 allow rules. No firewall
or environment protection was changed. Public/hosted deployment connectivity remains a gate.

### Public Germany endpoint repaired; current runtime acceptance is still failing

The verified host reports public IPv4 `141.11.175.231`; the former public endpoint
`141.11.175.252` is stale. Public SSH to the current address passed the existing pinned host
key and matched hostname and the original Agent container identity. Only the Germany GitHub
Environment endpoint and known-host aliases were updated; the existing private key, host
authorization and branch protections were preserved. Exact-target-hash readback from
[main run 43381682486](https://github.com/mohammad4242/fitician/actions/runs/43381682486)
succeeded. This clears hosted SSH access, not application release readiness.

The updated real panel accepted the selected occurrence and selected Codex model. Pinned
runtime startup worked, but authenticated model-catalog retrieval timed out and the inference
stream failed before any repository tool ran. These failed/blocked runs remain in history;
updated findings are not claimed live-verified from those attempts. A direct authenticated
catalog probe also timed out, while an unauthenticated request returned 401. Dedicated auth
metadata reports a non-expired access token, which alone does not prove provider acceptance.
No model substitution or successful analysis was fabricated.

Codex plugins are now explicitly disabled at process and thread configuration, alongside
the existing native shell/apps/MCP restrictions. Actual config/read verifies the setting.
A provider transport experiment was not retained as an effective fix: configuration readback
alone did not establish the observed transport or solve the failed inference.

Fresh Iran readback: API image `93413ad3`, workers/scheduler `2bde2fa9`, frontend `7c03e50d`,
PostgreSQL pinned digest `9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15`,
Alembic `20261018_175`; checked services healthy. Database size was about 291 MB and disk
free about 10.7 GB. Compose lives in the release directory reported by Docker labels, not
at the application root. No migration or application replacement occurred. Backup configuration
and restore availability remain under investigation; no backup gate was claimed passed.

### Effective API budget and declared limits

The API tool loop previously subtracted the requested maximum allocation before each response,
so a 4096-token configuration could stop after two short tool rounds. It now subtracts validated
provider-reported completion usage; missing/invalid usage conservatively reserves the entire
requested allocation. Usage source and remaining budget are durable progress events. A response
reporting consumption above its allocation is rejected. The independent eight-round, tool-count
and payload bounds remain. Provider usage is reported evidence, not a billing guarantee.

Debug settings now reject unsupported limits instead of silently clamping them: timeout 10–600
seconds, API output budget 128–16384 tokens. The existing AI Settings page shows these ranges.
Historic unsupported configurations are blocked before runtime execution. Codex output-token
controls remain unsupported/disabled; no model is substituted. Focused verification passed
57 backend tests and 30 settings/conversation UI tests, mypy/Ruff, TypeScript and Oxlint.
Actual selected OpenRouter model inference/tool acceptance remains unverified: the public model
catalog also timed out from the laptop during the connectivity check.

### Regional diagnostics worker lifecycle — implemented, not activated

Full Iran releases now ship the existing `compose.debugging.yaml` and a fixed
`ops/diagnostics-release.py` lifecycle helper. The existing regional host lock and owner gates
remain authoritative. A private host-owned `diagnostics-workers.json` (0600) explicitly selects
services; absent policy cannot activate workers, and removing policy from an active installation
fails closed. Example policy structure (no credentials):

```json
{"version":1,"services":["debug-worker","diagnostics-sync-worker","diagnostics-alert-worker"]}
```

Each selected service uses its own 0600 file in the regional application directory:
`debug-worker.env`, `diagnostics-sync-worker.env`, or `diagnostics-alert-worker.env`.
Do not copy the application's whole env file. All need `DATABASE_URL`; debugging needs the
existing `AI_CREDENTIAL_ENCRYPTION_KEY`; sync needs `SENTRY_ORG`, `SENTRY_PROJECT`, and the
scoped `SENTRY_API_TOKEN` (plus the existing restricted `SENTRY_HTTPS_PROXY` where required).
Alerts need the configured Faraz key/sender/recipient and explicit
`DIAGNOSTICS_ALERT_ENABLED=true` / `DIAGNOSTICS_ALERT_ENABLED_AT`; preserve the activation-time
and receipt safeguards. Optional DSN/project/environment settings follow the existing capture
policy. Privileged upload/GitHub/S3 credentials are rejected, and sync/SMS/AI credentials cannot
be shared across these worker files. Compose raw env format preserves literal credential
characters; it requires Compose 2.30+, verified as 2.40.3 on the laptop and Iran server.

Before pulling images, backup, migration or application mutation, preflight checks private
configuration and the full candidate resource envelope, including other bounded running
projects, 750 MiB memory headroom and CPU oversubscription limits. After backup and the final
authorization check, previous workers stop before migration. The candidate uses the exact
locally manifest-verified backend image, existing application network, and a separate supervised
diagnostics Compose project. No new network, host ports, production volume or image pull is
created by the worker helper. Read-only filesystems, dropped capabilities, CPU/RAM/PID limits,
bounded logs, heartbeat health checks and startup grace remain explicit. Successful startup
also requires running-image and health readback. State and previous configuration fingerprints
are retained privately for rollback; changed secrets or incomplete transactions require explicit
operator reconciliation. Schema failure quiesces workers and requires database recovery instead
of attempting an incompatible image-only rollback. Emergency quiescence needs no secret file.

Verification: all 355 ops tests passed, including actual Compose rendering with synthetic
credentials, resource rejection, pre-mutation ordering, worker failure rollback, schema failure
quiescence and manual-input injection. Focused Ruff and shell syntax checks passed. Standalone
debug/sync worker ORM mapper initialization also passed without the API lifespan.
CI run 43531645428 exposed an unset-new-input fixture in regional workflow tests; the fixture
now supplies the three optional panel fields and tests injection into each. Its failed run is
not reported as successful; the next exact-commit CI result remains a separate gate.

Live read-only Iran inspection: 3916 MiB total RAM, about 1633 MiB available, 9974 MiB root disk
free, and 2880 MiB aggregate existing service memory limits. All three default diagnostic
workers need another 1024 MiB plus 750 MiB headroom: the existing 4 GiB host cannot meet this
envelope (even before any larger candidate application limits). No limits were lowered, no
worker was activated, and production schema remains unchanged by this step. Capacity must be
resolved before activating the complete worker set. Independent Germany login instructions
were freshly saved locally with mode 0600; browser authorization and dedicated broker GitHub
credential remain external gates. Neither login instructions nor a healthy container prove
model execution, automatic SMS, production enrollment or end-to-end acceptance.

### Retention of conversation occurrence anchors

Periodic diagnostics cleanup now retains occurrences referenced by any persisted run or durable
operation, even when that occurrence has no exception/Sentry snapshot. Completed/failed run
history retains the same protection. References are scoped through the conversation's issue;
legacy null/malformed JSON references neither cause UUID-cast errors nor pin unrelated events.
Unreferenced old events remain eligible for bounded cleanup. The regression first demonstrated
loss of the selected occurrence, then passed with the fix. All 55 evidence/diagnostics/run/
findings tests passed on isolated PostgreSQL; focused mypy and Ruff passed. No migration,
production cleanup or deployment was performed by this step.

### CI-backed finding review

Artifact-verified durable CI completions now expose immutable run-event evidence IDs; receipt
replay returns the same ID. The agent can cite successful or genuinely test-failing scoped CI
evidence. The existing findings view lists these receipts alongside local unittest evidence.
An explicit administrator review can compare failing/passing runs only when profile, selected
tests, base commit, policy commit and immutable test image match, and the candidate commit/tree
actually changed. Cancelled, unverified, foreign-occurrence, empty-test or infrastructure-only
failures cannot establish a regression comparison. Persisted audit includes both CI artifact/
workflow identities. Current evidence-version and idempotency checks remain. This records a
reviewed finding; it does not declare the production issue resolved or dispatch deployment.

Focused verification passed 34 backend tests on isolated PostgreSQL, eight findings/automation
UI tests, two-file mypy and Ruff. The initial regression showed the missing CI evidence ID.
External Actions execution through the independently enrolled production Germany runtime
remains unverified; no real provider/runtime execution is claimed from these synthetic tests.

### Scoped diagnostics worker health evidence

The fixed Iran host collector reads only known service names from the private activation
policy. Activated diagnostics workers are inspected under their separate Compose project;
container/image/commit/health/restart evidence and trace-scoped sanitized logs use the existing
limits. Their identities also participate in the deployment baseline hash. Disabled workers
are not fabricated as running or missing. The API admits only these three additional Iran
service names and rebuilds the sanitized packet; arbitrary containers remain inaccessible.
Nine collector tests and 16 host/deployment backend tests passed, with Ruff/mypy checks.
This is code and scoped operator-read acceptance, not model-initiated production acceptance.

The broader combined debug/diagnostics/Sentry regression invocation exposed three failures
(270 passed, three skipped): leaked test telemetry environment affected sync/probe and queue
identity expectations. Investigation identified `test_debug_process` directly changing process
environment after `monkeypatch.delenv` on previously absent keys. These failures must be corrected
and the combined invocation rerun; it is not reported as a passing complete regression gate.

The isolation regression reproduced the exact leak for previously absent environment keys.
The test now registers restoration before `initialize_telemetry` writes its private values;
no application queue-priority or sync behavior was changed to hide the failures. The combined
33-file debug/diagnostics/Sentry invocation then passed **277 tests with one explicit skip**.
An existing local Python image was resolved to its immutable Docker ID, enabling both isolated
repair-container tests (previously skipped). The remaining local App Server test requires the
explicit supported CLI: the laptop default is 0.169.0 whereas this runtime contract pins
0.167.2. Focused Ruff passed. The existing FastAPI/Starlette deprecation warning remains.

### Diagnostics database connection budget

Each dedicated diagnostics worker now has a fixed pool of one connection and zero overflow.
The existing regional connection-budget check includes the explicitly selected workers before
resource/container inspection, backup or release mutation. Failure to render/check the budget
blocks activation without misreporting a configuration failure as proven database saturation.
At default application settings, three workers raise the possible connection count from 32
to 35; four reserved connections still fit strictly below the budget of 40. RAM/CPU/disk gates
remain independent and unchanged. All 359 ops tests and focused Ruff checks passed, including
real Compose rendering and rejection when the combined connection budget is insufficient.
These changes are not deployed; Iran memory capacity and independent Germany authentication/
broker enrollment remain external gates. No production schema or worker activation changed.

### Isolated nutrition validation and broader regression acceptance

The repair test gateway now provides the separate `fitician_nutrition_audit` URL on its own
internal ephemeral PostgreSQL network. Previously the nutrition autouse fixture fell back to
localhost:5432, so backend nutrition profiles could not initialize despite main test database
configuration. The trusted child environment preserves only the three exact synthetic database
URLs and rejects other database destinations; host/provider credentials remain excluded.
Both validation image targets include the same environment policy. Regression tests first
demonstrated the missing audit URL and now verify propagation and rejection of host secrets.

The existing 221-test business selection (body execution/reviews/correlation, food queue and
estimation, nutrition/clinical review, workout API, jobs, alert/SMS) passed on isolated local
PostgreSQL, after an earlier food-photo request returned a transient 503. That failure did not
reproduce alone or in the complete repeat; its cause remains unconfirmed. Its assertion now
reports only the safe domain error code if it recurs. Existing 534 deprecation warnings remain.
The full Agent Service suite passed 283 tests using the installed backend development Python
environment; this does not replace its dedicated frozen-environment CI gate. Diagnostics UI
tests passed 66 tests across 11 files. These results do not establish live provider, deployed
panel, automatic SMS, native crash or complete production business-scenario acceptance.

### Validation filesystem and CI regression coverage

A restrictive operator umask could leave extracted source directories unreadable to sandbox
UID 10001. The regression reproduced mode 0700; extraction now explicitly gives source-only
directories mode 0755 and files 0644 inside the existing bounded read-only bind. No credentials,
Docker socket or host authority were added. All 363 ops tests passed, including traversal/
symlink rejection and the private-umask regression. The image context explicitly includes its
child-environment helper. Required controlled backend CI now also exercises the actual food
photo queue and estimation suites, covering the separate nutrition audit database path.

Local full Python validation-image construction remains blocked by public dependency DNS
failures (`files.pythonhosted.org`), after a registry mirror 502; neither is a test pass. An
initial local cached image was the frontend target and lacked pytest, so its failed Python
invocation is not application-test failure evidence. The new hosted matrix must pass on the
exact candidate. Frontend TypeScript/Oxlint checks and nine mobile adapter/logging tests plus
three release-identity script tests passed. No actual native binary/crash was tested.

### Actionable runtime and automation blockers

Known independent Codex login, protocol-version and isolation-configuration failures now remain
specific blocked runs through the connector journal, gateway and worker instead of becoming
an unspecified provider failure. Replaying an acknowledged blocked call does not execute it
again. Discovery reports only a closed set of failure codes, never raw provider errors, and
keeps Codex models unavailable when authentication/catalog discovery fails. A new optional
heartbeat field carries this state to the admin connector view; old connector payloads remain
valid. A panel connection does not imply model authentication or successful inference.

Conversation, connector and repair/CI views share Persian/English next-action descriptions for
these states, missing GitHub credentials, stale deployment approval and uncertain dispatch.
Unknown codes retain their technical identity without a fabricated cause. OpenAPI/shared types
were regenerated. Focused verification passed 71 backend tests (one explicit pinned-CLI skip)
and 69 diagnostics/settings UI tests, four-file mypy, Ruff, TypeScript, Oxlint and OpenAPI drift
checks. No runtime credential or sandbox permission was broadened. Deploy API/contracts before
the matching connector image because the previous API rejects unknown heartbeat fields.

Independent Germany login instructions were refreshed privately with mode 0600 during this
continuation. Browser authorization, independent broker credential, production enrollment,
Iran worker capacity, exact-release CI and live end-to-end acceptance remain separate gates.
No production application release, database migration or automatic SMS activation occurred.

### API provider failure identity and hosted validation evidence

The selected API tool model now preserves `provider_rate_limited` for HTTP 429 and
`provider_rejected` for other rejected responses. It does not retry uncertain actions,
change models or export provider response bodies. Three regression cases first failed
with the previous generic error; the combined API tools/run selection passed 27 tests.
Sixteen conversation/automation UI tests, focused Ruff/mypy and Oxlint passed; an existing
Starlette deprecation warning remains. Persian/English guidance uses the same closed codes.

Hosted CI run `43539769610` passed all four controlled validation profiles. Its backend
artifact records 56 exercised tests, zero failures/skips, including the actual food photo
queue and estimation suites. The candidate/policy commit `10aea44f9e8e3610a8289b0d925399bc52ada8b4`
is GitHub's PR merge candidate, whose tree matches branch commit `41cf61877b2c182a19b304f52720bb90c814e6ea`.
The overall CI run was still in progress at inspection; this is not deployment or panel
runtime acceptance. Production remains unchanged.

### Diagnostics workers in artifact-bound deployment readback

Deployment requests snapshot the diagnostics worker names from the selected occurrence's
verified host observation. Post-deployment readback must include precisely those workers,
with the tested backend image and healthy containers in the separate diagnostics project.
The fixed host guard validates private activation state, configuration fingerprints and
release commit before inspecting containers. Missing, unexpected or stale worker evidence
fails the release gate; the original service-only receipt remains valid for installations
without activated diagnostics workers. This does not assert business resolution.

Regression tests demonstrated the previous missing selection/binding. Eight deployment
backend tests, all 365 ops tests, focused Ruff/mypy and shell syntax checks passed. The
workflow and host release script both pass the explicit application directory. This wiring
is implemented and locally tested, not deployed or live verified.

Read-only Iran inspection also found one encrypted provider credential and one encrypted
proxy setting while the effective application encryption key is absent (both runtime
settings and the host configuration). No replacement key was generated and no encrypted
data was modified. Recover the previous key securely or explicitly reconfigure those
credentials before enabling API-model/debug workers. The existing Sentry proxy destination
uses the verified private Germany address, independently of public-IP routing.

### Dedicated worker secret preparation and alert activation preflight

The release preflight now rejects missing/non-HTTPS panel origins, credentials/path/query/
fragment in an origin, and invalid or timezone-naive SMS activation timestamps. Seven
regression cases reproduced the prior acceptance; all 366 ops tests and focused Ruff
checks passed. Runtime alert formatting already rejects these origins; the release now
fails before worker startup instead of discovering the problem in its sending loop.

On Iran, existing provider values were copied by exact service-specific allowlists into
`/opt/fitician-iran/diagnostics-sync-worker.env` and
`/opt/fitician-iran/diagnostics-alert-worker.env`, with mode 0600 and matching private
readback. Files were created without replacing existing secret files; the application
environment and activation policy were unchanged. Sync includes the backend, web and
mobile project names. Alert configuration includes the real HTTPS frontend origin and
explicitly keeps automatic sending disabled, without an activation timestamp. Debug worker
configuration awaits the existing encryption key. No worker was started and no SMS sent.

A fresh authenticated project-events read from Iran through the existing restricted
Germany proxy returned HTTP 200 with an available event. This verifies current retrieval
connectivity, not capture or original-source evidence from a newly deployed release.
