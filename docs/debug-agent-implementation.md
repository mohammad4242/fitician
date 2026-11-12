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

Not yet implemented: external issue synchronization, durable evidence snapshots, debug-agent
configuration, durable chat, runtime orchestration, isolated repair execution, deployment broker,
notification routing, complete trace propagation and delivery health indicators. These remain
part of the authorized six-phase task; this foundation must not be presented as full completion.
