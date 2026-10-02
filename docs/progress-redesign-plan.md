# Progress redesign

Approved scope: the user's detailed Progress brief, including autonomous production release.

Before: hero, repeated KPIs, body and calorie charts, training/recovery disclosures,
Body Analysis disclosure, repeated insights in one long dashboard.
After: title, horizontal category tabs, compact period selector, Overview cards;
one dedicated category panel at a time. Body Analysis loads only on selection.

Use existing dark Fitician tokens and fonts. Quiet rounded petrol cards pair a
large metric with a small truthful visualization. Overview is one column on
phones and two on desktop. Keep all six internal categories; unavailable product
categories are disabled and omitted from Overview. Preserve routes and entitlements.

Shared helpers own formatting, card summaries and chart series. Platform components
own navigation, rendering and interactions. Keep the existing measurement form,
backend formulas, target history, null intake, denominator and private media flow.
Body charts require at least two observations; recovery charts require two check-ins.

Steps:
1. Add failing navigation/state tests and shared presentation tests.
2. Build Web tabs, Overview, focused detail panels and responsive charts.
3. Match Native hierarchy with React Native components and direct chart taps.
4. Verify meaningful state coverage, RTL/LTR and 360/390/430/768/1440 layouts.
5. Run affected lint, types, tests/builds; review focused diff; commit and push.
6. Run exact-SHA Full CI release, verify immutable image digests, deploy through
   existing release gates, inspect production health/migration/SHA and Progress.

No new technologies, database changes or public navigation destinations.
