# Diagnostics and debug-agent implementation status

Production deployment is owner-authorized after the approved verification gates pass.
The current regional CD flags are enabled; manual full/Agent releases retain their owner
environment gate and automatic delivery is limited to eligible main CI/component paths.
No external delivery, symbolication, native crash acceptance,
repair runtime, GitHub access or deployment is established merely by enabling an SDK.

## Revalidated completion checklist — 2026-11-13

The existing design and execution authorization remain in effect. Work continues on
`feat/regional-cicd`; no replacement stack or competing admin application is planned.
At baseline HEAD `16a7b637`, remote branch and draft PR 41 match. `origin/main` remains
`7c03e50d`; feature work is not merged or deployed. Local mobile release-identity changes
and this document are preserved. PR 42 remains a synthetic acceptance PR, never a main merge.

| Capability | Code | Tested | External configuration | Deployed | Live verified |
| --- | --- | --- | --- | --- | --- |
| SDK capture, exact-event sync, private web maps | committed | isolated SDK/DB/browser | server/GitHub secrets installed | new application release: no | backend/web staging: yes |
| Issue chat, occurrence/model provenance, Codex connector | committed | API, browser, real Codex | staging enrollment only | no | staging only |
| API model tool loop | committed | mocked provider protocol | production selection/probe pending | no | actual API tool call pending |
| Isolated repair/test/PR | committed, limited unittest profile | real seeded failure/fix/test/PR 42 | local GitHub broker | no | synthetic staging only |
| FarazSMS aggregation/receipt worker | committed, migration 181 | isolated DB/provider protocol | recipient/key present; auto sending disabled | no | one operator SMS delivered; automatic path pending |
| Native exact release identity/iOS ingestion | implemented | 34 backend, 14 core, 7 mobile tests; native crash pending | EAS Sentry variables absent at last inspection | no | no native release crash proof |
| Artifact-bound deployment and verification | incomplete | pending | existing regional owner gates retained | no | pending |

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

Fresh infrastructure evidence: private pinned Germany SSH on 9011 works after reboot;
`ssh`, Docker and Tailscale are active. Agent container remains healthy on its prior image,
with no restart by this session. Existing proxy is still `Created`, release
`83d56ca78ae0`, checksums verified, current symlink absent. Public SSH still times out.
Latest feature CI [43279620964](https://github.com/mohammad4242/fitician/actions/runs/43279620964)
failed in the complete backend-suite step; Android, mobile, frontend/browser, Agent,
Compose, regional smoke, dependency and secret checks passed. Publication was skipped.
A green release gate is still required; these observations do not authorize bypassing it.

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
