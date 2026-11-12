# Diagnostics and debug-agent implementation status

Production deployment is owner-authorized after the approved verification gates pass.
Regional CD remains disabled. No external delivery, symbolication, native crash acceptance,
repair runtime, GitHub access or deployment is established merely by enabling an SDK.

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
Sentry CLI installation scripts currently require review under the repository's npm script policy;
private upload and native release verification remain outstanding until that gate is satisfied.
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
The debug worker sends actual analysis requests to the selected OpenRouter API model. It does
not silently use generation runners for interactive work. Models without a connected interactive
adapter cannot execute tools. Such requests report `interactive_runtime_not_configured` or
`repair_executor_not_configured`; these are blocked states, not successful fixes.
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

The full six-phase task is not complete. Still required: interactive App Server and API tool
orchestration adapters; isolated repair worktrees, test execution, GitHub branch/PR broker;
artifact-bound deployment authorization/broker and post-deployment verification; optional
personal connector; external notification routing/delivery; source-mapped Sentry evidence
synchronization; full propagation and transport-drop health; native crash/privacy acceptance;
and tests for all four workflow outcome/quota invariants. These are engineering work, not merely
missing credentials. Production has not been changed.

External configuration still not installed on production/CI: Sentry DSNs and event-read API token,
private artifact upload token and CLI installation-script gate; EAS release builds/native artifacts;
dedicated debug-worker secret configuration/network/image; provider key/encryption access;
Codex runtime authentication and protocol compatibility; GitHub App permissions; deployment
broker targets/host keys/credentials; connector enrollment; notification provider credentials.
Use server secret configuration, GitHub Environments and EAS secret channels, never chat.

## Continuation: occurrence binding and external readiness

The selected occurrence is now controlled by `IssueDetail` and shared by `IssueEvidence` and
`DebugConversation`. It is included in the serialized submission, idempotency hash, immutable
run evidence and returned run provenance, including occurrences without captured stacks.

Read-only inspection on 2026-11-12 confirmed Iran SSH access and mixed existing component
releases; no deployment was performed. Main requires `Required CI` with admin enforcement.
The owner confirmed no Sentry account exists yet. Sentry must remain **not configured** until
an account/projects and scoped credentials are supplied through approved secret channels.
This blocks external Sentry verification, not independent implementation.

## Sentry account setup (connection not yet completed)

An account has now been created. The initial handoff was rejected by Sentry because the
redeeming network differs from the originating browser network (HTTP 403, IP pinning).
Sentry reported that the handoff was not consumed. No token, DSN or project configuration
was acquired. The existing SDK installation has not been repeated.

Create or let the authorized handoff configure these private projects in the Fitician organization:

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

The paused handoff must be regenerated with Advanced options → Use IP pinning disabled
for this execution network. Put that short-lived code in the private, locally excluded file
`.codex-tmp/sentry-setup/handoff-code` with mode 0600; never commit it. A successful connection
must be followed by private artifact upload, a synthetic event and server-side ingestion lookup.
Generated IDs alone remain unconfirmed delivery.


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

Production DSNs, durable least-privilege automation tokens and CI release-upload secrets still
need secure installation. Synthetic ingestion and source-map verification must be reported
separately from account/project configuration. No production deployment has occurred.
