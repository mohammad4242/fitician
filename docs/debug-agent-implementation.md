# Diagnostics and debug-agent implementation status

Production deployment requires explicit owner authorization for a concrete tested artifact.
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

External configuration not established: Sentry organization/projects/DSNs, event-read API token,
private artifact upload token and CLI installation-script gate; EAS release builds/native artifacts;
dedicated debug-worker secret configuration/network/image; provider key/encryption access;
Codex runtime authentication and protocol compatibility; GitHub App permissions; deployment
broker targets/host keys/credentials; connector enrollment; notification provider credentials.
Use server secret configuration, GitHub Environments and EAS secret channels, never chat.
