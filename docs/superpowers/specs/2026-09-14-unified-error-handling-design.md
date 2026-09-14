# Unified Error Handling System

## Status

Approved design for implementation on 2026-09-14.

## Goal

Create one error path for Fitician:

`Backend error -> ApiError -> shared resolver -> audience/context presentation -> Web / Android / iOS`

The system preserves the safest known cause of an error while preventing internal
implementation details, credentials, private notes, and sensitive user data from
reaching clients or user-facing UI.

## Architecture

### Backend contract

`backend/app/errors.py` owns the response envelope and normalization helpers. The
envelope is returned under `detail` and may contain `code`, `message`, `retryable`,
`fields`, `meta`, and `request_id`.

`backend/app/main.py` adds a validated `X-Correlation-ID` middleware and central
handlers for `HTTPException`, request validation, database failures, known domain
exceptions, and unknown exceptions. Existing response headers such as
`Retry-After` and session-cookie deletion headers are preserved. Unknown server
failures use `INTERNAL_SERVER_ERROR` and never expose their cause.

Existing public domain codes remain unchanged. Legacy string details are normalized
at the boundary and high-value domain routes are upgraded with explicit stable
codes where the current cause is known. No database migration or success-response
change is part of this work.

### Shared core

`@fitician/core` remains framework-independent. `ApiError` keeps its current
constructor and `details` property for compatibility while adding normalized
validation details, safe metadata, retryability, and request ID. A pure payload
parser and a transport/runtime error type are shared by Web and Native.

`packages/fitician-core/src/errors/` contains the single resolver and catalog. The
resolver is code-first, then context, HTTP status, and runtime error kind. It
supports `member`, `admin`, `coach`, and `physician` audiences and normalizes
`doctor` to `physician` only at the presentation boundary.

### Client transport

Web and Native transports use the same core parser. Every request sends a generated
`X-Correlation-ID`; the backend returns it in the response header and error detail.
The clients preserve object details, validation arrays, safe metadata, retryability,
and request IDs. Offline, network, timeout, HTTP, and abort outcomes remain
distinct. Navigation aborts are silent.

### Presentation

Web uses a small adapter that passes the active locale to the core resolver. Mobile
uses the same resolver directly through shared UI helpers. Pages provide only their
audience and context. Known API errors no longer become generic boolean messages;
local validation and genuinely local camera/media failures remain local.

Admin presentation may show safe diagnostic code, status, retryability, and request
ID. Member presentation is Persian, actionable, and non-technical. Coach and
physician presentation explains the relevant workflow cause without exposing
private notes or provider internals.

## Error contexts

The resolver supports `auth`, `profile`, `workout`, `workout_generation`,
`nutrition`, `body_analysis`, `body_photo`, `billing`, `access`,
`specialist_review`, and `generic`.

## Testing strategy

Tests are added before implementation for:

- core `ApiError`, runtime classification, catalog, and resolver behavior;
- Web and Native parsing, correlation IDs, structured validation, and runtime errors;
- Mobile request-state classification and silent abort handling;
- Backend envelope, redaction, validation normalization, correlation headers, and
  existing entitlement/body-analysis behavior;
- representative member, admin, coach, and physician UI states.

Targeted tests run after each logical step. Relevant package lint/typecheck and
full relevant suites run at the end. Existing tests are updated to the new contract
without weakening their business assertions.

## Security rules

Error responses and presentation never include stack traces, SQL, filesystem paths,
API keys, tokens, authorization headers, cookies, provider secrets, internal
prompts, private medical notes, or unnecessary email/phone/user data. Safe metadata
is allowlisted rather than copied wholesale.
