# Fitician Error Handling

Fitician uses one error path across the API, `@fitician/core`, Web, Android, and
iOS:

`Backend error -> ApiError -> shared resolver -> audience/context presentation`

The shared implementation lives in `backend/app/errors.py`,
`packages/fitician-core/src/transport.ts`, and
`packages/fitician-core/src/errors/`.

## Backend error envelope

Expected API failures are returned under `detail`:

```json
{
  "detail": {
    "code": "PROFILE_WEIGHT_REQUIRED",
    "message": "وزن در پروفایل ثبت نشده است. ابتدا وزن را تکمیل کنید.",
    "retryable": false,
    "fields": [
      {
        "field": "weight_kg",
        "code": "required",
        "message": "وزن وارد نشده است."
      }
    ],
    "meta": {},
    "request_id": "8ab123..."
  }
}
```

`code`, `message`, `retryable`, `meta`, and `request_id` are normalized for every
handled error. `fields` is included when the error is field-specific. The backend
may preserve additional safe response headers such as `Retry-After`.

Known domain errors must have a stable code. Unknown server failures use
`INTERNAL_SERVER_ERROR`; their internal cause is logged server-side and is not
sent to a client.

## `ApiError`

`ApiError` is the framework-independent client representation:

```ts
{
  status: number;
  code: string | null;
  message: string;
  validationDetails: ApiValidationDetail[] | null;
  details: ApiValidationDetail[] | null; // compatibility alias
  retryable: boolean;
  meta: JsonObject;
  requestId: string | null;
}
```

Web and Native use `parseApiErrorPayload` from `@fitician/core`. It accepts
structured objects, legacy string details, Pydantic validation arrays, and
non-JSON bodies. Legacy status codes remain available for backward compatibility;
the resolver can refine generic authentication codes using the actual auth flow.

## Audiences and contexts

The resolver API is:

```ts
resolveAppError(error, {
  audience: "member" | "admin" | "coach" | "physician",
  context: ErrorContext,
  locale: "fa" | "en"
})
```

Supported contexts are `auth`, `profile`, `workout`, `workout_generation`,
`nutrition`, `body_analysis`, `body_photo`, `billing`, `access`,
`specialist_review`, and `generic`.

`doctor` is accepted only as an input alias and is normalized to the canonical
`physician` presentation audience. Existing database values, enums, and domain
behavior are unchanged.

Presentation rules:

- `member`: Persian-first, actionable, non-technical copy.
- `coach`: the cause relevant to coach review and decision-making.
- `physician`: clinical-workflow context without private clinical notes.
- `admin`: safe diagnostics including code, HTTP status, request ID,
  retryability, and allowlisted metadata.

The resolver returns `title`, `message`, `action`, `severity`, `retryable`,
`code`, `status`, `requestId`, `fieldErrors`, `meta`, and whether technical
details may be shown.

## Resolver behavior

Resolution is code-first:

1. `ApiError.code`
2. context-specific status mapping
3. HTTP status
4. transport/runtime error kind
5. safe unknown fallback

HTTP status alone is not treated as a domain cause. For example,
`ENTITLEMENT_REQUIRED`, `COACH_ROLE_REQUIRED`, and
`SPECIALIST_RELATIONSHIP_REQUIRED` have different messages even though they may
all be `403`. Likewise, generation-in-progress, duplicate, and review-state
conflicts remain distinct `409` codes.

Validation details are converted to localized field errors. Important field labels
include `weight_kg` (وزن), `height_cm` (قد), `date_of_birth` (تاریخ تولد), and
`training_days` (تعداد روزهای تمرین). Raw Pydantic messages are not displayed.

Transport failures remain separate:

- offline: `OFFLINE`
- network/DNS/connection failure: `NETWORK_ERROR`
- timeout: `REQUEST_TIMEOUT`
- navigation cancellation: `REQUEST_ABORTED` with silent severity
- HTTP failure: `ApiError`

An unknown runtime error uses `UNKNOWN_ERROR` in the resolver. It must not be
described as an offline, timeout, or server-capacity problem without evidence.

## Correlation ID

`X-Correlation-ID` is the only correlation header. Web and Native generate one for
each request and send it to the backend. The backend:

1. accepts a safe incoming value or generates one;
2. stores it in `request.state.request_id`;
3. returns it in the `X-Correlation-ID` response header;
4. includes it as `detail.request_id` for errors;
5. attaches it to server exception logs.

The header is allowed by CORS and exposed to Web. Admin diagnostics can use the
request ID to find the corresponding server log entry.

## Security and redaction

Error responses and UI must never expose stack traces, SQL, filesystem paths, API
keys, tokens, authorization headers, cookies, provider secrets, internal prompts,
private medical notes, or unnecessary email/phone data.

Backend and client metadata are allowlisted. Current safe metadata includes values
such as `retry_after_seconds`, `reset_at`, `entitlement`, `maximum_weeks`,
`requested_weeks`, and `current_state`. Adding a metadata key requires confirming
that its value is safe for the relevant audience.

## Adding a new error code

1. Add the stable code and safe Persian message to `backend/app/errors.py`.
2. Add the code and localized copy to `packages/fitician-core/src/errors/catalog.ts`.
3. Use the code in the domain route or exception handler; do not change success
   responses.
4. Add targeted backend, core resolver, transport, and representative UI tests as
   applicable.
5. Choose the page’s audience and context when rendering `AppErrorNotice`, or the
   equivalent shared Mobile presentation.
6. Add only required safe metadata and update this document if the contract shape
   changes.

Do not rename an existing public code without a compatibility requirement.

## Role examples

### Member

`PROFILE_WEIGHT_REQUIRED` in workout generation is shown as:

> برنامه تمرینی ساخته نشد چون وزن شما در پروفایل ثبت نشده است. ابتدا وزن را در
> پروفایل تکمیل کنید.

No HTTP status, provider name, or internal detail is shown.

### Coach

`COACH_ROLE_REQUIRED` or an incomplete review explains the coach workflow, for
example that the operation is available only to a coach or that the member’s
training information is incomplete.

### Physician

`SAFETY_DECISION_NOT_FOUND` is shown as:

> بررسی این برنامه ممکن نیست چون ارزیابی ایمنی کاربر هنوز ثبت نشده است.

### Admin

`BODY_ANALYSIS_PROVIDER_UNAVAILABLE` may show:

```text
سرویس ارائه‌دهنده تحلیل بدن فعلاً در دسترس نیست.
کد خطا: BODY_ANALYSIS_PROVIDER_UNAVAILABLE
HTTP: 503
شناسه پیگیری: 8ab123...
قابل تلاش مجدد: بله
```

This still excludes provider secrets, raw exceptions, SQL, tokens, and private
medical data.
