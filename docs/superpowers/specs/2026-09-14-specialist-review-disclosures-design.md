# Specialist review disclosures

## Goal

Make coach and physician case details compact on Web/PWA and the Android/iOS native app. Profile information, workout structure, and nutrition structure should be available through clear collapsible sections instead of one long page.

## Scope and invariants

- Presentation and interaction only.
- Keep existing API requests, payloads, persistence, validation, review leases, read-only rules, tabs, edits, approvals, and rejection flows unchanged.
- Apply the same disclosure hierarchy to Web/PWA and native screens while using platform-native controls.
- Keep safety and physician warnings visible in the compact case summary.

## Disclosure contract

The shared contract is a small set of stable section keys and defaults consumed by both clients. Every disclosure has a title, optional summary, a closed-by-default state, and an accessible expanded state.

- The case summary is visible by default.
- Detailed profile sections are closed by default.
- Workout days and nutrition days are closed by default.
- Nutrition meals inside a day are closed by default.
- Closing a section must not discard unsaved form values.

Web renders the contract with native HTML `details`/`summary` semantics. Native renders it with the existing `DisclosureCard`, including its mounted-but-hidden behavior for visited form sections.

## Web hierarchy

### Coach

- Keep the case header, compact metrics, and safety highlights visible.
- Split the complete profile into body/training, nutrition, and medical disclosures.
- Make the template rationale one disclosure, with score details inside it.
- Make each workout day a disclosure. Exercise editors remain inside the selected day so editing does not require extra per-exercise expansion.
- Keep the coach note and decision actions available after the plan sections.

### Physician

- Keep the current clinical tabs: plan, labs, supplements, and notes.
- Keep the case header, compact metrics, and safety highlights visible.
- In the plan tab, make evidence and nutrient validation disclosures, then make each day and each meal a disclosure.
- Preserve the existing labs, supplements, and notes behavior; only group long lists/forms into compact disclosures where useful.

## Native hierarchy

- Reuse `DisclosureCard` for coach rationale, profile sections, workout days, physician evidence, nutrient validation, nutrition days, and meals.
- Add the same live profile summary content to native coach and physician detail views using the existing profile-summary response data.
- Preserve native segmented controls, offline/read-only behavior, keyboard-safe editors, Android Back behavior, sheets, and action buttons.

## Accessibility and visual behavior

- Use real disclosure semantics on Web and `accessibilityState.expanded` on native.
- Keep keyboard focus, visible focus rings, RTL Persian text, LTR English text, and minimum touch targets intact.
- Use existing Fitician colors and disclosure primitives; add only scoped styles for hierarchy, chevrons, spacing, and mobile stacking.
- Respect reduced-motion settings.

## Verification

- Add Web tests that verify detailed content is hidden initially and appears after opening the relevant summary, for profile, coach days, physician days, and meals.
- Add native tests that verify collapsed/expanded accessibility state and that coach/physician detail data remains editable after expansion.
- Run focused Web Vitest tests, native Jest/RNTL tests, core tests/typecheck, Web lint/build, and native typecheck/lint where available.
- Inspect the final diff and stage only the design/feature files; do not include existing unrelated WIP.
