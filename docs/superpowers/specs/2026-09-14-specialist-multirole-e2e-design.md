# Specialist multi-role E2E design

Date: 2026-09-14

## Goal

Prove the real member, coach, and physician workflows through the Web UI, real
FastAPI endpoints, and an isolated PostgreSQL database. Also keep the existing
native test contract intact and investigate any reproducible native failure
before changing code.

## Chosen approach

Use a guarded Python CLI fixture with a dedicated E2E PostgreSQL database.

- Playwright creates accounts and completes member profile data through the real
  authentication/profile APIs.
- The fixture CLI connects to the E2E database only. It grants the selected
  access package and inserts the existing `UserSpecialistRole` row for a
  registered coach or physician. It is not an HTTP endpoint and is never
  enabled as a production role-escalation path.
- A preparation command validates that the database name ends in `_e2e`, resets
  only that public schema, runs Alembic, and seeds the minimum exercise,
  nutrition, and template catalogues.
- Playwright starts the test FastAPI process and Vite preview. Vite preview
  proxies `/api` and `/media` to the real FastAPI process.

## Browser isolation

Every role uses a separate Playwright `BrowserContext`, so cookies and session
state cannot cross roles. Test users and specialist accounts use unique
run/test email addresses. The suite asserts that a member is denied specialist
routes, admin status alone does not grant physician access, a second specialist
cannot claim or approve an assigned case, and one member's medical/workout data
is not returned for another member.

## Member to coach flow

1. Register and complete a member fitness profile through the real API.
2. Generate a deterministic workout plan with the real coach-review entitlement.
3. Confirm the pending review using the member's API session.
4. Register a separate coach, grant the real coach package/role through the
   fixture CLI, and open `/coach/workouts` in the coach context.
5. Claim the member's case, change a real prescription, save the draft, and
   approve it through the UI.
6. Read queue state and the member's plan/history through real API calls. Assert
   the approved revision is active, the source revision is superseded, and the
   review is approved. Assert the coach change is visible to the member.

## Member to physician flow

1. Register an independent member and complete shared, nutrition, safety, and
   structured-exercise inputs through the real APIs.
2. Generate a nutrition plan with the real physician-review entitlement.
3. Register a separate physician, grant the real physician package/role through
   the fixture CLI, and open `/physician/nutrition` in the physician context.
4. Claim the case, read only its assigned medical context, add a user-visible
   note, and approve the plan through the UI.
5. Read the member's latest/active plan and history through the member context.
   Assert the approved revision, physician review status, physician display
   name, and note are the values persisted for that member.
6. Use a separate independent review case to request `CBC` with the exact
   user-visible reason `برای بررسی ایمن‌تر برنامه`, then verify the member sees
   the request through the real UI/API.

## Assertions beyond UI

UI actions are followed by API reads from the appropriate independent context.
The final assertions cover persisted lifecycle/review fields, revision
relationships, lease ownership, and user-visible notifications/lab requests.
No frontend API route is mocked in the specialist suite.

## CI

The browser job receives a separate PostgreSQL service/database, installs the
backend environment, runs the guarded E2E preparation, starts FastAPI, then
executes the existing command:

```bash
npm run test:e2e --workspace frontend
```

The existing mocked/presentation E2E specs remain unchanged and run alongside
the real specialist suite.

## Native scope

The exact requested baseline command is run before edits. If it remains green,
no native production or test change is made merely to create a diff. Any later
native failure is reproduced with its exact test and fixed at the production or
real Jest setup boundary without weakening assertions.

## Verification gates

- Focused backend workout-review and clinical-review tests.
- Frontend Vitest, Playwright, and build/lint checks.
- Mobile Vitest, Jest Native, foundation, typecheck, and validation checks.
- CI-compatible backend preparation plus the full browser command.
