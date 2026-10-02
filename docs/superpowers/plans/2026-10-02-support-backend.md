# Support Backend Implementation Plan

**Goal:** Deliver the private support-ticket API before building member/admin screens.
**Architecture:** Dedicated support records, existing authentication/admin guards,
transactional notification inbox/outbox. No program-conversation or health-data access.
**Tech stack:** FastAPI, SQLAlchemy, PostgreSQL, Alembic, pytest.
**Spec:** `docs/support-progress-phase0.md`, approved option 1.
**Execution:** Main agent only; one bounded Phase 1 step, then stop as instructed.

## Constraints and review focus

- Member queries always constrain ownership; unauthorized resources return 404.
- Authenticated support works without a completed profile or paid entitlement.
- Cookie mutations require trusted Origin; native bearer follows existing auth.
- Request UUID retries preserve messages/status/activity and never duplicate notifications.
- Closed replies fail, except an exact retry of an already accepted request.
- Read cursors belong to the ticket, not another owner's thread.
- Metadata permits only platform/version/build/locale, with bounded input lengths.
- Admin responses expose support records only; no health/profile joins.
- Rate limits use existing Redis with isolated DB fallback, bounded per-user writes.

## Task 1: Support domain and API

Files: `backend/app/support/{enums,models,schemas,service,router,limits}.py`,
`backend/alembic/versions/20261002_166_support_tickets.py`, `backend/alembic/env.py`,
`backend/app/main.py`, `backend/app/config.py`, `backend/app/notifications/content.py`,
`backend/tests/support/test_api.py`, generated OpenAPI/Core contracts.

Interfaces: member `/api/v1/support/tickets` list/create/detail/messages/read;
admin `/api/v1/support/admin/tickets` queue/count/detail/messages/status.
Create/reply/status accept request UUIDs. Detail includes viewer, ordered message page,
unread count, and older cursor. Queue supports status/category/search and activity cursor.

- [x] Write API regression tests: create/list/ownership, CSRF, input validation,
  request conflict/replay, member/admin replies, closed/reopen/status audit,
  read state, stable private pagination, admin filters/counts, notification/outbox.
- [x] Run tests and verify missing routes fail with 404.
- [x] Implement support schema/migration, owner/admin services, bounded API and limits.
- [x] Run focused support, conversation, notification regressions; Ruff/strict mypy.
- [x] Generate/check OpenAPI, rebuild Core, and verify shared contracts.
- [x] Review diff and schema parity.
- [ ] Commit/push only named files after checks.

Attachments/assignment remain optional deferred work. Contact/help UI and native
notification deep links remain later phases; backend replies publish the dedicated event now.

## Phase 1 verification record

- Initial API regressions: 12 failed with missing-route 404 responses before implementation.
- Added locked-status regression: failed before refreshing locked ORM state, passed after.
- Support, program-conversation, notification suites: 66 passed; existing dependency
  deprecations and unrelated nutrition metadata cycle warnings remain.
- Core: 120 tests passed; TypeScript build passed.
- Focused Ruff and strict mypy for the seven support modules passed.
- OpenAPI regeneration/reproducibility/check passed; existing schemas and routes are unchanged.
- Migration upgrade/downgrade and support model/schema comparison passed; head 20261002_166.
- Reply/inbox/outbox rollback, concurrent request deduplication, CSRF, owner/admin boundaries,
  rate-limit retries, private cursors, status reopen/closure are covered.
- No production migration, Web/Mobile UI, native routing, full CI, or deployment performed.

Ruling: feature implementation moved to `feat/support-progress`; the documentation-only
Phase 0 commit was pushed on main before switching. Unrelated untracked work was preserved.
