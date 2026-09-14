# Persian date input migration

Date: 2026-09-14

## Audit snapshot

- Web date inputs: access audit `from_datetime`/`to_datetime`; campaigns
  `available_from`/`available_until`; user access `starts_at`/`ends_at`;
  billing offers `available_from`/`available_until`; nutrition tracking
  `rangeStart`; nutrition labs `testDate`; nutrition estimate `startDate`;
  profile/onboarding `birth_date`; workout start and reschedule dates.
- Mobile date inputs: public onboarding birth date, onboarding/profile
  `birth_date`, workout start/reschedule dates, nutrition plan start date,
  nutrition adherence range start, and nutrition clinical lab date. These are
  currently native-like text/date controls rather than shared Jalali controls.
- Display-only dates are separate from editable values. Existing timeline and
  API values are ISO date-only strings; timestamps are ISO instants.

## Invariants

- Persian presentation and selection use Jalali; English presentation and
  selection stay Gregorian.
- Date-only values remain `YYYY-MM-DD` Gregorian/ISO in form state, API, and
  database, with no timezone conversion.
- Datetimes remain ISO timestamps. Persian datetime input interprets the wall
  clock in `Asia/Tehran` before producing the ISO instant.
- No backend, database schema, migration, or subscription business logic is
  changed.

## Implementation sequence

1. Add failing Core conversion tests, install the small Jalali dependency, and
   implement the typed Iran calendar API as the single conversion source.
2. Add reusable Web date/date-time pickers and migrate every editable Web date
   field while preserving ISO parent state and API payloads.
3. Add shared Android/iOS pickers and migrate every editable Mobile date field,
   including onboarding and profile birth dates.
4. Audit editable versus display-only date formatting, remove duplicated
   timezone-sensitive page conversions, and verify Persian accessibility and
   responsive behavior.
5. Run focused Core, Web, and Mobile tests, typechecks/builds, and the final
   repository regression searches.

## Verification

- Core conversion and formatting tests cover Jalali month lengths, leap
  Esfand, invalid values, date-only round trips, Tehran datetime round trips,
  and machine-timezone independence.
- Web and Mobile picker tests cover rendering, selection, clear/cancel,
  min/max, accessibility, and API-facing ISO output.
- Existing profile, onboarding, workout, nutrition, and admin tests retain
  their Gregorian/ISO assertions at the API boundary.
