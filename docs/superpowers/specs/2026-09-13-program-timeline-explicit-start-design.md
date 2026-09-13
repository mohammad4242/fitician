# Program Timeline and Explicit Plan Start

## Goal

Make Fitician’s workout and nutrition programs aware of the member’s local calendar position without changing workout generation or creating daily nutrition rows.

## Architecture

The backend owns calendar semantics through `app.time_context`, including IANA timezone validation, local dates, UTC local-midnight conversion, and Fitician weekday numbering. `UserProfile.timezone` stores the best-effort preference, while start requests and timeline reads may carry the current device timezone to avoid a persistence race.

Workout plans remain content definitions. An explicit workout start creates one `WorkoutCycle` and concrete `WorkoutCycleSession` rows for each persisted workout day, repeated by rolling program week. Session status is limited to scheduled, completed, or skipped; overdue is derived from scheduled date and the member’s local date. Existing cycles without session rows are represented as legacy cycles and never receive fabricated history.

Nutrition plans retain their seven `NutritionWeeklyPlanDay` template rows. Generation, selection, and physician approval produce `ready_to_start`; an explicit start sets `started_at`, the requested local `start_date`, and `active`. Timeline reads map dates by modulo seven, allowing future active starts to report `scheduled_start` without a scheduler.

`program_timeline` is a read-model module only. Its today endpoint joins the current executable workout plan, current cycle/session state, selected nutrition plan, recurring nutrition day, and timezone into one response. Web and mobile use generated OpenAPI aliases and pass the resolved device timezone on every timeline request.

## API boundaries

- `PUT /api/v1/profile/timezone` persists a validated member timezone.
- `POST /api/v1/workout-cycles/start` starts one active executable workout plan idempotently by logical local start date.
- `POST /api/v1/workout-cycles/current/sessions/{session_id}/complete` completes one scheduled session.
- `POST /api/v1/workout-cycles/current/sessions/{session_id}/skip` skips one scheduled session.
- `POST /api/v1/workout-cycles/current/sessions/{session_id}/reschedule` moves one scheduled session with transactional date-collision and cycle-start checks.
- `POST /api/v1/nutrition/plans/{plan_id}/start` explicitly starts the selected eligible nutrition plan.
- `GET /api/v1/program-timeline/today` returns the combined local-date workout and nutrition state.

All state-changing endpoints require authentication and trusted origin. Ownership, lifecycle, and transition errors map to the specified 404, 409, and 422 responses.

## Client behavior

Shared core exports local-date helpers and generated timeline aliases. Web and mobile show explicit start controls, focus workout days by timeline session IDs, show rest/overdue/completed/legacy states, and use the nutrition pattern index rather than the first template row. Existing weekly check-ins, replacement flows, plan history, and nutrition editing remain secondary or historical-compatible features.

## Verification

Backend domain tests cover timezone conversion, session generation and transitions, lifecycle changes, recurring nutrition dates, and every timeline precedence state. OpenAPI is regenerated from the backend. Core, web, and mobile tests verify transport paths, timezone race tolerance, query invalidation, and presentation regressions for `days[0]` and UTC calendar assumptions.
