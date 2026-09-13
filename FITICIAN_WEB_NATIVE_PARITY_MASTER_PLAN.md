# Fitician Web-as-Source Native Adaptation Master Plan

> **Execution owner:** Luna  
> **Repository:** `mohammad4242/fitsho`  
> **Primary implementation scope:** `mobile/`  
> **Primary visual reference:** current `frontend/` implementation on the checked-out commit  
> **Goal:** Rebuild the native Android experience page by page so that **Web is the Visual Source of Truth**, while preserving the parts that should remain genuinely native: navigation, touch interaction, safe areas, keyboard behavior, Android Back, camera, offline/cache behavior, secure storage, native sheets, media lifecycle, and platform accessibility.

---

## 0. Read this before changing any code

This document changes the design authority for the native app.

The repository already contains earlier mobile visual-direction documents, including:

- `docs/superpowers/specs/2026-09-09-mobile-visual-parity-design.md`
- `docs/superpowers/plans/2026-09-09-mobile-visual-parity.md`
- `m.md`
- `mobile.md`

Some of those documents intentionally pushed the native UI toward a separate **cinematic / media-first mobile interpretation**. That direction is the reason several native screens now have a different hierarchy from the website.

For this rebuild, use the following authority order:

1. **This file** — architecture and execution rules for Web-as-Source + Native Adaptation.
2. **The current web page/component and its CSS** — visual hierarchy, content order, component proportions, typography hierarchy, surface treatment, state presentation, and user-facing copy.
3. **The current native feature logic** — API adapters, React Query ownership, offline state, secure storage, camera/media behavior, native navigation, route guards, and platform-specific interactions.
4. Older mobile visual documents — keep their valid engineering, security, performance, accessibility, and verification constraints, but **ignore visual instructions that conflict with this document or the current web UI**.

Do **not** delete the older design documents. Just do not let them override this plan.

### The core rule

For every native screen, ask two separate questions:

**What should it look like and what information should appear first?**  
Answer from the current web implementation.

**How should that interaction work on a phone?**  
Answer from native platform conventions and the current native architecture.

Example:

- Web uses a compact workout-day card with an image, title, duration, and expandable details.
- Native should use essentially the same visual hierarchy and density.
- Native may use a `Pressable`, Android Back, tactile press feedback, a 48 dp touch target, and a native expansion animation instead of copying a `<details>` element literally.

That is **Native Adaptation**. It is not permission to redesign the screen.

---

# 1. Non-negotiable boundaries

## 1.1 Web is read-only during this project

Default implementation scope is `mobile/`.

Read web code and CSS freely, but do not “fix” the website to make native implementation easier.

Do not modify `frontend/`, backend code, database schemas, API contracts, or shared persisted models unless a real functional blocker is proven and the user explicitly expands scope.

## 1.2 Preserve domain behavior

Do not change:

- workout-generation algorithms
- nutrition engine/ranking algorithms
- coach approval rules
- physician approval rules
- Body Analysis processing/threshold algorithms
- authentication security
- secure token storage
- profile persistence semantics
- offline cache rules
- PDF persistence
- private-media security
- Body Analysis image-upload/crop contracts
- specialist role boundaries
- API request/response contracts

A visual rebuild must not become a business-logic rewrite.

## 1.3 Native behaviors that must remain native

Keep or improve:

- `SafeArea` handling
- bottom tab navigation
- Expo Router / native stacks
- Android system Back
- keyboard avoidance and focus behavior
- `Pressable` interaction
- at least 48 dp touch targets
- native `Sheet` / modal behavior where it improves phone usability
- camera capture
- image picker
- native permission recovery
- React Query caching
- stale/offline presentation
- secure storage
- private media storage
- PDF storage/opening
- media pause/resume on navigation/background
- `FlatList` / virtualized list behavior where appropriate
- TalkBack accessibility

Do **not** replace React Native screens with WebViews.

## 1.4 What “visual parity” means

Native should inherit from web:

- page information architecture
- ordering of major sections
- primary vs secondary emphasis
- colors
- typography roles
- spacing rhythm
- border style
- radius language
- status colors
- density
- card hierarchy
- media prominence
- button hierarchy
- labels/copy where the feature semantics are the same
- empty/error/loading hierarchy
- what is visible in the first viewport
- which information is collapsed/secondary

Native does **not** need to copy:

- desktop multi-column layouts literally
- CSS hover behavior
- browser breadcrumbs literally
- browser file handling
- web-only responsive breakpoints
- HTML `<details>` mechanics
- browser navigation chrome
- pointer-specific interactions

When native intentionally differs, the reason must be one of:

1. touch usability
2. accessibility
3. phone-width limitation
4. platform navigation convention
5. keyboard/camera/media requirement
6. performance
7. existing native security/offline constraint

“Looks better to me” is not a valid reason.

---

# 2. Shared visual contract already present in the repository

Before creating anything new, read:

### Web
- `frontend/src/styles/tokens.css`
- `frontend/src/styles/primitives.css`
- `frontend/src/index.css`

### Native
- `mobile/ui/tokens.ts`
- `mobile/ui/layout/Screen.tsx`
- `mobile/ui/components/Card.tsx`
- `mobile/ui/components/Button.tsx`
- `mobile/ui/components/ScreenHeader.tsx`
- `mobile/ui/components/MetricStrip.tsx`
- `mobile/ui/components/MetricRing.tsx`
- `mobile/ui/components/DisclosureCard.tsx`
- `mobile/ui/components/Feedback.tsx`
- `mobile/ui/components/Input.tsx`
- `mobile/ui/components/SectionHeader.tsx`
- `mobile/ui/components/Overlay.tsx`
- `mobile/ui/components/Sheet.tsx`
- `mobile/ui/components/index.ts`
- `mobile/ui/rtl.ts`
- `mobile/ui/layoutMetrics.ts`
- `mobile/ui/accessibility.ts`

The current native tokens already closely mirror the web palette. Do not introduce a second theme.

The visual contract is approximately:

- canvas: `#020607`
- deep petrol: `#091817`
- raised surface: `#101e1c`
- ink: `#e8f4f1`
- muted: `#94aba5`
- aqua: `#50dfce`
- amber/coral/success stay semantic status colors
- Persian body: Vazirmatn
- short Persian display headings: Lalezar
- English/numeric display: Sora
- spacing rhythm based on 4 / 8 / 12 / 16 / 24 / 32 / 48
- rounded cards, restrained borders, restrained shadows
- no permanent neon/glow treatment around every surface

---

# 3. Phase 0 — Create a real Web ↔ Native parity inventory

Do this **before the first implementation edit**.

## Files to create

- `mobile/artifacts/parity/web-native-page-matrix.md`
- `mobile/artifacts/parity/component-parity.md`
- `mobile/artifacts/parity/baseline.md`

Do not store private screenshots or body photos in Git.

## Step 0.1 — Record exact baseline

Record:

- branch
- commit SHA
- dirty paths
- installed native package versions
- Android device/model used for screenshots
- logical screen width
- font scale
- language
- product mode
- account state used in comparison

Do not overwrite unrelated dirty files.

## Step 0.2 — Build the route matrix from real code

Read:

- `frontend/src/App.tsx`
- `mobile/app/`
- all Expo Router route groups

Map these categories:

### Public / account
- landing
- get started / public onboarding
- sign in
- register
- forgot password
- reset password
- verify email
- privacy
- delete account

### Member
- Home / dashboard
- workout
- exercise catalogue
- exercise detail
- nutrition overview
- nutrition plan
- nutrition tracking
- food catalogue
- meal catalogue
- Body Progress / Body Analysis landing
- Body Analysis capture
- Body Analysis result
- Body Analysis history
- profile
- more

### Specialists
- coach workout review
- physician nutrition review

### Admin
Admin remains **web-only** in this project. Do not create native admin screens.

## Step 0.3 — Compare equivalent states, not random screenshots

For each core screen capture the same state on web/native where possible:

- normal populated
- loading
- empty
- error
- offline/stale
- pending approval
- historical/read-only where applicable

Primary comparison widths:

- 360 dp
- 390 dp
- 430 dp

Stress checks:

- 320 dp
- 200% font scaling
- English/LTR smoke test

## Step 0.4 — Classify each difference

Every difference should be one of:

- `VISUAL_HIERARCHY`
- `SECTION_ORDER`
- `TYPOGRAPHY`
- `SPACING`
- `COMPONENT_SHAPE`
- `COPY`
- `STATE_PRESENTATION`
- `NATIVE_ADAPTATION`
- `MISSING_EXISTING_CAPABILITY`
- `FUNCTIONAL_BUG`
- `OUT_OF_SCOPE`

Do not implement until the affected screen has an inventory row.

### Gate

No core page rebuild starts until its web reference, native implementation, all existing native actions, and all relevant states are documented.

---

# 4. Phase 1 — Build the Shared Design System bridge

The goal here is **not** to create another design system. The goal is to make existing native primitives able to express the current web system without each page inventing local approximations.

## Web references

- `frontend/src/styles/tokens.css`
- `frontend/src/styles/primitives.css`
- `frontend/src/index.css`

## Modify only as required

- `mobile/ui/tokens.ts`
- `mobile/ui/layout/Screen.tsx`
- `mobile/ui/components/Card.tsx`
- `mobile/ui/components/Button.tsx`
- `mobile/ui/components/ScreenHeader.tsx`
- `mobile/ui/components/DisclosureCard.tsx`
- `mobile/ui/components/Feedback.tsx`
- `mobile/ui/components/Input.tsx`
- `mobile/ui/components/SectionHeader.tsx`
- `mobile/ui/components/index.ts`

## Create only if current primitives cannot express the web pattern cleanly

Recommended focused additions:

- `mobile/ui/components/PageHeading.tsx`
- `mobile/ui/components/SegmentedControl.tsx`
- `mobile/ui/components/GroupedList.tsx`
- `mobile/ui/webParityPrimitives.test.ts`

### Why `PageHeading`

Current `ScreenHeader` always introduces a FITICIAN brand row. Several web member pages do not begin with a large brand/header block. They use a compact page heading.

Do not force `ScreenHeader` onto those pages.

`PageHeading` should support:

- optional eyebrow
- page title
- optional compact supporting text
- optional opposite-side action/metric
- RTL/LTR
- compact phone first viewport
- no mandatory FITICIAN wordmark

Keep `ScreenHeader` for pages where a branded header is actually appropriate.

### Why `SegmentedControl`

Reuse it for:

- auth method
- workout generation method
- any true two/three-state web segmented choice

Requirements:

- 48 dp outer touch target per option
- selected visual matches web: restrained aqua surface/border/text
- RTL logical order
- loading/disabled state
- accessibility role/state

### Why `GroupedList`

Reuse it for:

- More
- account/profile utility sections
- possibly specialist menu groups

It should mirror the web grouped-list rhythm while remaining a full-width native press target.

## Token rule

When a web value already has a native token, use the token.

Only add a token if:

1. the value appears repeatedly in the current web design, and
2. at least two native screens need it.

Do not add literal copies such as `#50dfce` inside page styles.

## Card rule

Do not globally make every native card “hero”, glass, glowing, or cinematic.

Default web parity should be:

- quiet dark surface
- 1 px-equivalent border
- restrained radius
- minimal shadow
- clear section separation

Use `CinematicSurface` only where the current web source itself is media-led/atmospheric, not as a default page wrapper.

## Tests

Add rendered tests for:

- RTL ordering
- selected segmented option
- 48 dp interaction target contract
- PageHeading with/without action
- GroupedList press behavior

Do not use source-string tests as proof of visual quality.

### Gate

Before page migrations:

- shared primitives work at 360/390/430
- no existing screen is globally broken by token/component changes
- native Home, a form, a list, and a modal render without layout regressions

---

# 5. Phase 2 — Navigation and primary Information Architecture

There is an important structural parity gap:

The web AppShell treats these as primary member destinations:

1. Home
2. Workout
3. Nutrition
4. Body Progress
5. More

The current native bottom tabs expose:

1. Home
2. Workout
3. Nutrition
4. More

Body Analysis is currently only a secondary route, and `/member/body-analysis` directly launches the capture wizard.

For Web-as-Source parity, Body Progress should become a primary native destination **without making the camera wizard the tab root**.

## Read

### Web
- `frontend/src/shared/AppShell.tsx`
- `frontend/src/shared/authenticatedHeader.css`
- `frontend/src/App.tsx`

### Native
- `mobile/app/(member)/member/(tabs)/_layout.tsx`
- `mobile/app/(member)/member/body-analysis.tsx`
- `mobile/bodyAnalysis/BodyAnalysisHistoryScreen.tsx`
- `mobile/ui/navigation/BackBehaviorProvider.tsx`
- current navigation tests

## Modify

- `mobile/app/(member)/member/(tabs)/_layout.tsx`

## Create

- `mobile/app/(member)/member/(tabs)/body-analysis.tsx`

The new tab route should display a Body Progress/Analysis landing experience, not open the camera immediately.

Prefer reusing/refactoring `BodyAnalysisHistoryScreen` into a tab-safe progress landing rather than duplicating its data logic.

## Preserve

Keep existing routes:

- `/member/body-analysis` = capture/resume wizard
- `/member/body-analysis-history`
- `/member/body-analysis-result/[sessionId]`

Existing deep links must continue to work.

## Native adaptation

Bottom tabs are correct for native. Do not copy the web bottom navigation markup.

The native tab should:

- use the existing icon system
- retain safe-area behavior
- retain capability guards
- retain Back behavior
- preserve tab state
- use the same active aqua semantics as web

## Test

Update navigation tests so they verify:

- five member destinations where capabilities allow
- Body Analysis tab opens progress landing
- “New analysis” opens capture wizard
- existing direct capture/history/result routes still resolve
- product-mode capability gating still works

### Gate

Primary native IA now mirrors the web product IA while keeping native tab behavior.

---

# 6. Phase 3 — Home / Dashboard

## Visual source of truth

- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/dashboard.css`
- relevant shared web components used by Dashboard

## Native files

Modify:

- `mobile/home/MemberHomeScreen.tsx`
- `mobile/home/WorkoutTodayCard.tsx`
- `mobile/home/NutritionSummaryCard.tsx`
- `mobile/home/QuickActionCard.tsx`
- `mobile/home/homePresentation.ts` only if presentation helpers are needed

Tests:

- `mobile/home/homeCards.rntl.test.tsx`
- `mobile/home/homeModel.test.ts`
- `mobile/home/homePresentation.test.ts`
- add `mobile/home/MemberHomeScreen.rntl.test.tsx` if no screen-level rendered test exists

## Step 3.1 — Preserve data ownership

Do not rewrite:

- current React Query requests
- profile loading
- product-mode logic
- workout query
- nutrition query
- cache/offline behavior
- action routes

Inventory every current card action before moving anything.

## Step 3.2 — Port the web first viewport

Native first viewport should follow web hierarchy:

1. compact welcome/profile area
2. current/today workout as the primary training action
3. current nutrition summary
4. quick secondary actions

Do not begin with a large generic mobile hero if the web page does not.

## Step 3.3 — Workout card

Match web relative emphasis:

- current day/session
- current plan status
- lead exercise media when available
- session title
- duration
- primary action

Native adaptation:

- entire meaningful card region can be pressable
- keep 48 dp touch target
- media must have stable aspect ratio
- pause video on navigation/background
- use fallback without layout jump

## Step 3.4 — Nutrition card

Match the web calorie/macro hierarchy:

- target/current calorie status
- real progress ring
- protein / carbs / fat compact strip
- no fabricated progress
- missing target is not zero

## Step 3.5 — Quick actions

Keep web media-led identity for Body Analysis and nutrition/food actions.

At 390/430 dp:

- two-up if readable

At 360 or high font scale:

- allow one-column fallback

Do not sacrifice readable Persian labels to preserve two columns.

## Acceptance

- same primary decision is obvious on web and Android
- no decorative block consumes first viewport before useful status
- all three product modes still behave correctly
- offline/stale state does not replace the whole page with generic warnings
- long Persian name does not clip primary action

---

# 7. Phase 4 — Workout Plan

This is one of the highest-priority parity rebuilds.

## Visual source of truth

- `frontend/src/features/workouts/WorkoutPlanPage.tsx`
- `frontend/src/features/workouts/workoutPlan.css`
- `frontend/src/features/workouts/WeeklyCheckInCard.tsx`
- `frontend/src/features/workouts/EndCycleFeedbackCard.tsx`
- `frontend/src/features/workouts/prescriptionFormatter.ts`

## Native files

Modify:

- `mobile/workouts/WorkoutPlansScreen.tsx`
- `mobile/workouts/WorkoutCyclePanel.tsx`
- `mobile/profile/profileApi.ts` only to reuse its already-existing profile read/update capability from the workout screen; do not change API contract

Update tests:

- `mobile/workouts/workoutMedia.nativeContract.test.ts`
- `mobile/workouts/workoutPresentation.nativeContract.test.ts`
- existing workout model/API/cycle tests

Create if missing:

- `mobile/workouts/WorkoutPlansScreen.rntl.test.tsx`

## Step 4.1 — Remove the separate mobile design hierarchy

The current native page is dominated by:

- `ScreenHeader`
- large `CinematicSurface`
- large `MetricStrip`
- stacked `Notice` cards

That hierarchy is not the current web page.

Do not delete those shared components globally. Stop using them where they conflict with this page.

## Step 4.2 — Port the exact web content order

Top of native Workout should be:

1. `برنامه تمرینی من`
2. compact duration badge (`4 / هفته`)
3. compact four-cell plan context strip:
   - current status
   - cycle duration
   - training days
   - session duration
4. compact coach-review banner
5. generation-method selector
6. weekly heading + update action
7. day cards
8. secondary status/check-in/PDF/history sections

## Step 4.3 — Plan context strip

Translate `.workout-plan-context` to React Native.

Requirements:

- one outer container
- four compact cells
- logical RTL dividers
- no four separate cards
- values from real plan
- text can wrap to two lines at 360
- no horizontal scrolling

## Step 4.4 — Coach review

Port `CoachReviewBanner` behavior.

Do not render several giant warnings for the same effective pending state.

Preserve execution guards, but visually consolidate related state.

Approved/rejected/historical states still need their correct copy and tone.

## Step 4.5 — Generation method

Web already exposes:

- `fitsho_coach`
- `ai`

Use existing:

- `mobile/profile/profileApi.ts`
- `getProfile()`
- `updateProfile()`

Add the web-equivalent segmented selector:

`چه کسی برنامه‌ات را بنویسد؟`

Do not add backend endpoints.

On save failure:

- restore previous selection
- show compact inline error
- do not reload whole page

## Step 4.6 — Weekly heading

Port:

- `برنامه هفتگی`
- `روزهای تمرین تو`
- compact `به‌روزرسانی برنامه`

Keep current generation mutation and pending-review disable rules.

## Step 4.7 — Day cards

Use web `WorkoutDays` and CSS as the visual source.

First/focus day:

- meaningful exercise media
- “next session” cue where valid
- day title
- lead exercise + duration
- expansion action

Other collapsed days:

- compact
- numbered badge
- title
- duration
- expansion action
- no large media block for every day

Native adaptation:

- use `Pressable`
- use `AppIcon` chevrons
- keep tap target 48 dp
- expansion may animate natively
- do not copy HTML `<details>` literally

## Step 4.8 — Expanded exercises

Preserve:

- warmup/main/cooldown group semantics
- media
- sets
- reps
- RIR
- rest
- superset
- instructions
- exercise-detail navigation
- replacement
- AI/coach explanation

Match web density and row hierarchy.

Do not add redundant “guide” buttons if the whole exercise row already opens details.

## Step 4.9 — Internal warning codes

Never render:

```ts
plan.warnings.join("\n")
```

to the user.

Map supported user-facing warnings to Persian/English copy using the same principle as web.

Internal enums/reason codes should not leak into UI.

## Step 4.10 — Cycle/check-in

In `WorkoutCyclePanel.tsx`:

- keep all queries/mutations
- keep check-in
- keep pain/limitation
- keep replacements
- keep end-cycle feedback

But style them as secondary sections of the same Workout page.

Do not insert a second cinematic hero after workout days.

## Step 4.11 — PDF and history

Preserve native advantages:

- cached PDF
- open local PDF
- re-download
- offline persistence
- native file opening

Visually place these after primary workout content, similar to web secondary/history regions.

## Acceptance

At 360/390/430:

- top 4-cell strip fits
- first workout day resembles web information hierarchy
- pending plan is never executable
- raw enum codes never appear
- profile generation method changes correctly
- PDF/history/replacement/cycle behavior is retained

---

# 8. Phase 5 — Exercise Catalogue

## Visual source of truth

- `frontend/src/features/exercises/ExerciseCatalogPage.tsx`
- `frontend/src/features/exercises/exercises.css`

## Native files

Modify:

- `mobile/exercises/ExerciseCatalogScreen.tsx`
- `mobile/exercises/ExerciseMedia.tsx` only if catalogue media presentation needs a parity-safe adjustment

Tests:

- `mobile/exercises/ExerciseCatalogScreen.rntl.test.tsx`
- `mobile/exercises/exerciseCatalogPresentation.test.ts`
- relevant exercise API/model tests

## Step 5.1 — Keep the good native adaptation already present

The native catalogue already has a useful foundation:

- search
- guided region → muscle → focus selection
- advanced filter Sheet
- media cards
- query state

Do not throw this away.

## Step 5.2 — Port web ordering and emphasis

The web guided hierarchy is the source:

1. search
2. body region
3. target muscle
4. muscle focus where relevant
5. advanced filters
6. result count/results

On native, advanced filters may remain in `Sheet`.

That is a valid Native Adaptation.

## Step 5.3 — Filter chip density

Match web semantics and relative visual weight.

Primary hierarchy controls:

- upper body
- lower body
- core / equivalent regions

Then muscle region/focus.

Secondary tags such as mobility/stretching/cardio/full-body/all exercises must be visually smaller and less dominant.

## Step 5.4 — Results

Exercise results should become the main visual content after filters.

Preserve:

- pagination/current API limits
- current search params
- cache
- list position when returning from detail
- media fallback

Use a virtualized list if the current implementation requires it; do not replace efficient list behavior with a giant stack just to resemble web markup.

## Acceptance

- filter sequence matches web mental model
- active filters are obvious and removable
- advanced controls do not bury results
- empty search/error/offline remain distinct
- returning from exercise detail does not lose useful list state

---

# 9. Phase 6 — Exercise Detail

## Visual source of truth

- `frontend/src/features/exercises/ExerciseDetailPage.tsx`
- `frontend/src/features/exercises/exercises.css`
- web `ExerciseMediaCarousel`

## Native files

Modify:

- `mobile/exercises/ExerciseDetailScreen.tsx`
- `mobile/exercises/ExerciseMediaCarousel.tsx`
- `mobile/exercises/GenderMediaSelector.tsx`
- `mobile/exercises/ExerciseMedia.tsx` only when necessary

Tests:

- `mobile/exercises/ExerciseDetailScreen.rntl.test.tsx`
- `mobile/exercises/ExerciseMediaCarousel.rntl.test.tsx`
- `mobile/exercises/GenderMediaSelector.rntl.test.tsx`

## Step 6.1 — Media first, like web

The detail screen should visually begin with:

- compact native back/breadcrumb affordance
- large exercise media carousel
- male/female presentation selector
- current media index
- exercise name

Do not add an unrelated giant page hero above the exercise media.

## Step 6.2 — Media behavior remains native

Preserve:

- swipe between media
- correct `1/2`-style count when multiple media items exist
- gender presentation
- offline/cache behavior
- video lifecycle
- Android Back

Do not reproduce browser video controls.

## Step 6.3 — Details

Port web order:

1. overview/facts
2. instructions
3. safety

Use native `DisclosureCard` for collapsible sections if that is cleaner on phone.

That is preferable to rendering three huge permanently-open cards.

## Step 6.4 — Language

When Persian is selected:

- show Persian primary exercise name
- do not let English secondary title compete visually unless web intentionally shows it

When English is selected:

- mirror accordingly

Keep mixed-script direction correct.

## Acceptance

- media is the first dominant content
- swipe/presentation selector works
- overview/instruction/safety order matches web
- all existing offline media behavior survives

---

# 10. Phase 7 — Nutrition Overview

The current native `NutritionFoundationScreen` contains many sections stacked into one long page. The web Nutrition Estimate page has a much clearer daily hierarchy.

## Visual source of truth

- `frontend/src/features/nutrition/NutritionEstimatePage.tsx`
- `frontend/src/features/nutrition/nutritionEstimate.css`
- web shared progress-ring components

## Native files

Modify:

- `mobile/nutrition/NutritionFoundationScreen.tsx`
- `mobile/nutrition/NutritionSummaryCard.tsx`

Potentially modify only presentation/order in:

- `mobile/nutrition/NutritionClinicalSection.tsx`
- `mobile/nutrition/NutritionAdherenceSection.tsx`

Tests:

- `mobile/nutrition/NutritionFoundationScreen.rntl.test.tsx`
- current nutrition model/API tests

## Step 7.1 — Port the first viewport

Native first hierarchy should be:

1. compact `امروز / تغذیه` heading
2. primary tools:
   - ثبت تغذیه
   - کاتالوگ
3. current real calorie/target state
4. macro status
5. current plan state/action

This should be understandable before scrolling through profile/safety details.

## Step 7.2 — Preserve deeper functionality without letting it dominate

Do not delete:

- nutrition profile
- safety evaluation
- structured exercise context
- physician review requirement
- estimate details
- catalogue
- tracking
- adherence
- clinical/labs/supplements

But move less-frequent administrative/clinical information below the daily user task, using quiet groups/disclosures where appropriate.

## Step 7.3 — Real values only

Never fabricate:

- calorie progress
- macro completion
- plan approval
- adherence percentage

Missing values must remain visibly unavailable.

## Native adaptation

Use native navigation to open dedicated nutrition plan/tracking/catalogue routes rather than reproducing every web tool inline.

## Acceptance

A user can answer “what should I do in Nutrition now?” from the first viewport.

---

# 11. Phase 8 — Nutrition Plan

## Visual source of truth

- `frontend/src/features/nutrition/NutritionEstimatePage.tsx` — `PlanArea`, plan comparison, regenerate flow
- the current web `WeeklyNutritionPlan` component and CSS
- current web budget vs ideal plan selection UI

## Native files

Modify:

- `mobile/app/(member)/member/nutrition-plan.tsx`
- `mobile/nutrition/NutritionPlanSection.tsx`
- `mobile/nutrition/NutritionShoppingList.tsx`
- `mobile/nutrition/NutritionThumbnail.tsx` only if required for card parity

Tests:

- existing `NutritionPlanSection` tests
- add a rendered `NutritionPlanSection.rntl.test.tsx` if not already present
- relevant nutrition API/model tests

## Step 8.1 — Plan status first

Show:

- active/pending/blocked status
- plan role
- date/week context
- relevant approval state

Do not start with a generic native card title that hides what plan is active.

## Step 8.2 — Budget vs ideal comparison

The web currently supports two related outputs from the same generated bundle.

Port the information architecture:

- comparison explanation
- budget plan
- ideal plan
- cost
- key macros
- selection state
- active-plan badge

Native adaptation:

- use vertically stacked selectable cards instead of forcing a desktop side-by-side layout
- use a Sheet/Disclosure for deep comparison details if needed
- selected state must remain obvious

Do not change nutrition engine logic.

## Step 8.3 — Weekly days and meals

Port web day/meal hierarchy.

On native:

- horizontally scrollable day selector or compact segmented day tabs are acceptable
- only the selected day’s detailed meals need to dominate
- meal cards retain image when available
- preserve replacement rules and states

## Step 8.4 — Regeneration

Match web hierarchy/copy:

- explain that the current plan remains if rebuild fails
- show loading
- show safe user-facing failure reasons
- do not expose raw internal reason codes

## Step 8.5 — Shopping list

Keep native list interaction, but align headings, grouping, quantities, and cost emphasis with web.

## Acceptance

- user can distinguish budget/ideal/active plan
- selection persists correctly
- day/meal navigation is usable at 360 dp
- no backend algorithm changes

---

# 12. Phase 9 — Nutrition Tracking

## Visual source of truth

- `frontend/src/features/nutrition/NutritionTrackingPage.tsx`
- related tracking CSS/components

## Native files

Modify:

- `mobile/app/(member)/member/nutrition-tracking.tsx`
- `mobile/nutrition/NutritionTrackingSection.tsx`
- `mobile/nutrition/NutritionThumbnail.tsx` if needed

Tests:

- `mobile/nutrition/NutritionTrackingSection.rntl.test.tsx`
- tracking model/API tests

## Port

Match web hierarchy for:

- selected date/day
- calorie/target state
- meal slots
- recorded items
- add/confirm action
- photo/manual entry if already supported by native/backend
- consumed vs remaining values

## Native adaptation

Prefer:

- native date picker/sheet if already used
- keyboard-safe numeric entry
- full-width pressable meal rows
- native camera/image picker for photo input

## Preserve

- Persian decimal handling
- offline restrictions
- duplicate submission protection
- current date semantics
- cache invalidation

Do not silently alter timezone logic as part of visual work.

---

# 13. Phase 10 — Food Catalogue and Meal Catalogue

## Visual source of truth

- `frontend/src/features/nutrition/FoodCataloguePage.tsx`
- `frontend/src/features/nutrition/MealCataloguePage.tsx`
- relevant catalogue CSS

## Native files

Modify:

- `mobile/app/(member)/member/food-catalogue.tsx`
- `mobile/app/(member)/member/meal-catalogue.tsx`
- `mobile/nutrition/NutritionCatalogueSection.tsx`
- `mobile/nutrition/NutritionThumbnail.tsx`

Tests:

- existing catalogue tests
- add RNTL coverage for route mode and details Sheet if missing

## Current native strength to preserve

`NutritionCatalogueSection` already uses:

- foods/meals modes
- search
- category chips
- detail `Sheet`
- media
- offline state

The `Sheet` is a good native adaptation. Keep it.

## Rebuild goals

Food route should visually feel like the web Food Catalogue page:

- page heading
- search
- category/filter hierarchy
- results
- food card hierarchy
- detail information

Meal route should start directly in meals mode and match web Meal Catalogue hierarchy.

Do not force the user through a confusing extra mode selection if they entered a dedicated Food or Meal route.

## Privacy/product rule

Do not expose member-hidden prices or internal preparation data if web intentionally hides them.

## Acceptance

- dedicated routes open correct mode
- search/filter order matches web
- card density is phone-friendly
- detail Sheet shows the same user-facing information hierarchy as web

---

# 14. Phase 11 — Nutrition Labs and Supplements / Clinical tools

Web exposes dedicated pages:

- `frontend/src/features/nutrition/NutritionLabsPage.tsx`
- `frontend/src/features/nutrition/NutritionSupplementsPage.tsx`

Native currently consolidates clinical tools under:

- `mobile/nutrition/NutritionClinicalSection.tsx`

For this pass, **do not create new native routes merely to achieve route-count parity** unless the existing clinical screen becomes unusably dense.

Use the web pages as the visual/content source for the corresponding subsections.

## Native files

Modify:

- `mobile/nutrition/NutritionClinicalSection.tsx`

Potential new routes require a separate explicit decision after inspecting the rebuilt section.

## Preserve

- physician approval
- scientific detail
- safety labels
- no unapproved supplement recommendation
- current API boundaries

---

# 15. Phase 12 — Body Progress / Body Analysis landing and history

The web treats Body Progress as a primary member destination. Native currently sends `/member/body-analysis` directly into the photo wizard.

This phase separates **progress/overview** from **capture**.

## Visual source of truth

- `frontend/src/features/bodyPhotos/BodyProgressPage.tsx`
- `frontend/src/features/bodyPhotos/bodyPhotos.css`

## Native files

Modify:

- `mobile/bodyAnalysis/BodyAnalysisHistoryScreen.tsx`
- `mobile/bodyAnalysis/BodyAnalysisOverviewCard.tsx` where shared overview presentation belongs
- `mobile/app/(member)/member/body-analysis-history.tsx` only if route composition needs adjustment
- new tab route from Phase 2

## Keep capture route separate

- `mobile/app/(member)/member/body-analysis.tsx`

must remain the capture/resume wizard route.

## Port the web progress hierarchy

The tab/landing page should make clear:

- current/latest Body Analysis status
- latest meaningful result summary when available
- start new analysis
- resume incomplete analysis
- timeline/history
- comparison/progress

Do not make a “New analysis” button the entire page.

## History cards

Use web status hierarchy and dates.

Keep native-only:

- secure private data handling
- resume action
- native delete confirmation
- native navigation

## Acceptance

Tapping the Body Analysis tab shows progress/history context. Starting a capture is an explicit action.

---

# 16. Phase 13 — Body Analysis capture wizard

## Visual source of truth

- `frontend/src/features/bodyPhotos/BodyPhotoWizard.tsx`
- `frontend/src/features/bodyPhotos/bodyPhotos.css`
- current web instructional copy and view order

## Native files

Modify presentation only where needed:

- `mobile/bodyAnalysis/BodyAnalysisWizard.tsx`
- `mobile/bodyAnalysis/BodyAnalysisRequirements.tsx`
- `mobile/bodyAnalysis/BodyPhotoCapture.tsx`

Only inspect/modify visual overlay styling with extreme care:

- `mobile/bodyAnalysis/GhostOverlayGuide.tsx`

Tests:

- existing body-analysis wizard/privacy/pose tests
- add/update `BodyAnalysisWizard.rntl.test.tsx`

## Critical boundary

Do not change:

- Ghost geometry contract
- privacy cut line behavior
- photo crop semantics
- pose validation algorithms
- backend preflight/analysis logic
- photo transformation sent to analysis
- capture thresholds

unless separately authorized as a functional bug.

## Native adaptation

Camera capture must remain native.

Keep:

- camera permission
- permission recovery
- capture/retake
- native preview
- interrupted-session resume
- upload progress
- Android Back semantics

## Visual parity

Match web:

- preparation instructions
- step ordering
- front / side / back progression
- concise helper text
- progress meaning
- action hierarchy
- error copy

Do not fill the capture screen with decorative cards around the camera.

## Acceptance

Visual parity improves without changing the actual analysis input.

---

# 17. Phase 14 — Body Analysis result

## Visual source of truth

- `frontend/src/features/bodyPhotos/BodyAnalysisResultPage.tsx`
- `frontend/src/features/bodyPhotos/BodyAnalysisResult.tsx`
- current V4 result component(s), including the current body/muscle/body-composition sections
- `frontend/src/features/bodyPhotos/bodyPhotos.css`

## Native files

Modify:

- `mobile/bodyAnalysis/BodyAnalysisResultScreen.tsx`
- `mobile/bodyAnalysis/BodyAnalysisOverviewCard.tsx`

Potentially create focused presentation components under:

- `mobile/bodyAnalysis/components/`

only if they reduce the current giant result screen and directly mirror stable web sections.

Tests:

- result model tests
- private-media tests
- comparison tests
- add/update result RNTL tests

## Step 14.1 — Preserve result orchestration

Do not rewrite:

- session fetch
- analysis fetch
- start/retry
- 3-second polling
- comparison fetch
- private-media loading
- result state
- specialist review data

## Step 14.2 — Remove debug-like prominence

Current native result exposes items such as result version/schema/source in generic cards.

If these are not primary in web, move them to a quiet technical/details disclosure or omit non-user-facing metadata from the main flow.

Do not delete data from the model.

## Step 14.3 — Port current web result order

The exact current web V4 structure is authoritative.

Read it immediately before implementation; do not rely on an old screenshot or memory.

Port its current sequence of:

- body/muscle visualization
- body-composition / fat-LBM section
- symmetry/balance metrics where present
- strengths
- priorities/weaknesses
- specialist review
- progress/comparison
- privacy/disclaimer
- photos as secondary details

Use the same user-facing labels and status classifications as web.

## Step 14.4 — Native presentation

Use:

- responsive phone-width maps
- native pressable muscle/body regions where web is interactive
- vertically flowing sections
- Disclosure for secondary photo/details
- stable aspect ratios

Do not force desktop side-by-side map proportions.

## Processing/failure states

Mirror web language and information hierarchy.

Do not invent fake percentages or ETAs.

## Acceptance

The same analysis tells the same visual story in the same order on web and native, while native private-media/security behavior is unchanged.

---

# 18. Phase 15 — Profile

## Visual source of truth

- `frontend/src/features/profile/ProfilePage.tsx`
- `frontend/src/features/profile/profile.css`
- current web profile field/components

## Native files

Modify:

- `mobile/profile/ProfileScreen.tsx`
- `mobile/profile/ProfilePhotoControl.tsx`
- local presentation helpers if needed

Do not change:

- `mobile/profile/profileApi.ts`
- `mobile/profile/profileModel.ts`

unless an actual behavior parity bug is found.

Tests:

- existing profile API/model tests
- profile-photo tests
- add/update `ProfileScreen.rntl.test.tsx`

## Port outer hierarchy

Web profile should determine:

1. identity/account summary
2. profile photo
3. core body/personal metrics
4. goal/activity context
5. relevant progress/measurements
6. editable sections

## Native adaptation

Keep the current section-by-section form flow if it works better with the keyboard.

Do not convert a phone edit flow into one enormous desktop form.

The summary/read mode should visually match web; edit mode may remain native step/section based.

## Preserve

- private photo upload
- photo error/delete
- validation
- health-related fields
- workout profile
- nutrition profile
- draft/save semantics
- Android Back from edit section

## Acceptance

Before editing, a user sees approximately the same profile summary hierarchy as web. Editing remains native and keyboard-safe.

---

# 19. Phase 16 — More

This is currently a major feature/IA parity gap.

## Visual source of truth

- `frontend/src/pages/MorePage.tsx`
- `frontend/src/pages/more.css`

## Native file

Modify:

- `mobile/more/MoreScreen.tsx`

Potentially use:

- `mobile/ui/components/GroupedList.tsx`

Tests:

- existing More/navigation tests
- add `mobile/more/MoreScreen.rntl.test.tsx` if missing

## Port web groups

Recreate equivalent logical groups such as:

- product/tools
- profile/account
- privacy/account actions
- specialist workspaces when role allows
- language/settings where supported
- logout

Use real existing native routes.

## Role behavior

Show:

- coach workspace only to coach-capable user
- physician workspace only to physician-capable user
- no fake admin native screen

If an admin-only web destination has no native equivalent, do not show a dead native row.

## Native adaptation

Use full-width grouped pressable rows instead of desktop link cards.

Preserve:

- route guards
- logout flow
- privacy/delete-account path
- capability filtering

## Acceptance

More is no longer just a few large cards; it matches web product/account organization while remaining thumb-friendly.

---

# 20. Phase 17 — Public Landing / Native entry

## Visual source of truth

- `frontend/src/features/landing/PublicLandingPage.tsx`
- `frontend/src/features/landing/publicLanding.css`
- `frontend/src/features/landing/landingStory.css`
- `frontend/src/features/landing/CinematicStory.tsx`
- `frontend/src/features/landing/ProcessStory.tsx`
- `frontend/src/features/landing/BodyIntelligence.tsx`

## Native file

Modify:

- `mobile/app/(public)/index.tsx`

Reuse:

- `mobile/assets/public-entry-hero.jpg`

Do not bundle a large marketing video merely to copy the web page.

## Native adaptation decision

The native entry does **not** need the full long-scroll marketing website.

It should preserve the same first impression:

- brand
- hero image/atmosphere
- core promise
- primary CTA
- sign in
- register
- compact proof/process context

Use the web for:

- visual identity
- type hierarchy
- copy hierarchy
- CTA priority

Use native for:

- concise app-entry length
- navigation
- touch targets
- safe area

## Acceptance

A user opening the app and website immediately recognizes the same product, without turning the app into a marketing WebView.

---

# 21. Phase 18 — Authentication family

## Visual source of truth

- `frontend/src/shared/AuthShell.tsx`
- `frontend/src/features/auth/LoginPage.tsx`
- `frontend/src/features/auth/RegisterPage.tsx`
- `frontend/src/features/auth/ForgotPasswordPage.tsx`
- `frontend/src/features/auth/ResetPasswordPage.tsx`
- `frontend/src/features/auth/VerifyEmailPage.tsx`
- auth CSS in `frontend/src/index.css` and feature styles

## Native shared files

Modify:

- `mobile/auth/AuthScaffold.tsx`
- `mobile/auth/authStyles.ts`

## Native routes

Modify presentation while preserving handlers:

- `mobile/app/(auth)/auth/sign-in.tsx`
- `mobile/app/(auth)/auth/register.tsx`
- `mobile/app/(auth)/auth/phone-otp.tsx`
- `mobile/app/(auth)/auth/forgot-password.tsx`
- `mobile/app/(auth)/auth/reset-password.tsx`
- `mobile/app/(auth)/auth/verify-email.tsx`

Tests:

- current auth tests
- route/native auth RNTL tests

## Step 18.1 — Simplify scaffold to match web

Web auth is primarily:

- clean form panel
- compact heading
- fields
- one primary action
- auth tabs where needed
- divider/provider action
- alternative link

Do not wrap every auth screen in a large unrelated cinematic card plus nested glass form card if web does not.

Use `PageHeading`/auth-specific equivalent and quiet surface rhythm.

## Step 18.2 — Sign in

Port:

- email/phone segmented choice
- email/password hierarchy
- forgot-password placement
- primary action
- Google divider/action
- register alternative

Keep native phone OTP as a separate route if current architecture uses it. This is valid Native Adaptation even though web handles OTP inline.

## Step 18.3 — Phone OTP

Preserve:

- SMS autofill hints
- countdown
- resend
- normalized phone
- keyboard type
- return/onboarding source

Visually match the web OTP step.

## Step 18.4 — Register/recovery/verify

Use the corresponding web page as source for:

- field order
- status copy
- primary/secondary action
- error placement

## Accessibility

- focused input never hides behind keyboard
- password/OTP input is readable
- TalkBack announces errors
- disabled/loading states are explicit

---

# 22. Phase 19 — Public onboarding

## Visual source of truth

- `frontend/src/features/publicOnboarding/PublicOnboardingPage.tsx`
- `frontend/src/features/publicOnboarding/GuidedSharedProfileQuestions.tsx`
- `frontend/src/features/publicOnboarding/GuidedTrainingQuestions.tsx`
- `frontend/src/features/publicOnboarding/publicOnboarding.css`

## Native files

Modify:

- `mobile/onboarding/PublicOnboardingScreen.tsx`
- `mobile/onboarding/onboardingForms.ts` only for presentation/question grouping when current data contract remains unchanged

Preserve:

- `mobile/onboarding/nativeOnboardingDraftStore.ts`
- `mobile/onboarding/onboardingController.ts`
- `mobile/onboarding/onboardingModel.ts`
- API/draft contracts

Tests:

- `mobile/onboarding/onboardingPresentation.nativeContract.test.ts`
- `mobile/onboarding/onboardingQuestionFlow.test.ts`
- draft/handoff/controller tests

## Port

Web owns:

- question order
- copy
- progress meaning
- choice hierarchy
- recommended combined mode treatment
- validation messaging

Native owns:

- one question / tight logical group per phone step
- Android Back to previous question
- keyboard
- native choice controls
- draft recovery after process restart

## Critical rule

Progress must represent real completed questions.

Do not create fake progress merely for visual effect.

---

# 23. Phase 20 — Authenticated onboarding

## Visual source of truth

- `frontend/src/features/profile/OnboardingPage.tsx`
- current web profile/onboarding field components

## Native file

Modify:

- `mobile/onboarding/OnboardingScreen.tsx`

Potentially modify presentation mapping:

- `mobile/onboarding/onboardingForms.ts`

Preserve:

- controller
- API
- validation
- draft
- product mode
- resume behavior

## Goal

The native flow should ask the same effective questions in the same logical sequence as web, but retain the better phone interaction of one step/tight group at a time.

Do not turn it into one long desktop-style form.

---

# 24. Phase 21 — Account deletion and privacy

## Visual source of truth

- `frontend/src/features/accountDeletion/AccountDeletionPage.tsx`
- `frontend/src/features/accountDeletion/PrivacyPolicyPage.tsx`
- related CSS

## Native files

Modify presentation only:

- `mobile/accountDeletion/AccountDeletionScreen.tsx`
- `mobile/accountDeletion/AccountPrivacyLinks.tsx`

Tests:

- `mobile/accountDeletion/accountDeletion.nativeContract.test.ts`
- API/model tests

## Preserve

- confirmation
- re-auth/security requirements
- destructive-action semantics
- status polling if present
- privacy URL/source
- no accidental delete on one tap

Native confirmation can remain a native modal/sheet if current behavior is safer.

---

# 25. Phase 22 — Coach workout review

## Visual source of truth

- `frontend/src/features/workoutReviews/CoachWorkoutReviewPage.tsx`
- `frontend/src/features/workoutReviews/coachWorkoutReview.css`

## Native files

Modify:

- `mobile/coach/CoachWorkoutReviewScreen.tsx`

Do not rewrite unless a proven parity bug:

- `mobile/coach/coachWorkoutReviewApi.ts`
- `mobile/coach/coachWorkoutReviewModel.ts`

Tests:

- `mobile/coach/coachWorkoutReview.nativeContract.test.ts`
- API/model tests
- add rendered interaction tests for changed navigation/editor behavior

## Port web workspace semantics

Web owns:

- queue hierarchy
- selected review context
- plan rationale/evidence ordering
- editable workout sections
- approve/reject hierarchy
- status/ownership presentation

## Native adaptation

Do not copy a desktop queue sidebar literally.

On phone use:

- queue screen → selected case screen
- or compact top selector + case body
- segmented tabs/disclosures for deep evidence

Preserve:

- claim/lease semantics
- review ownership
- edit/save
- approve/reject
- note
- role guard

---

# 26. Phase 23 — Physician nutrition review

## Visual source of truth

- `frontend/src/features/nutrition/PhysicianNutritionReviewPage.tsx`
- `frontend/src/features/nutrition/physicianWorkspace.css`
- related current nutrition review components

## Native files

Modify:

- `mobile/physician/PhysicianNutritionReviewScreen.tsx`

Do not rewrite unless a proven parity bug:

- `mobile/physician/physicianNutritionReviewApi.ts`
- `mobile/physician/physicianNutritionReviewModel.ts`

Tests:

- `mobile/physician/physicianNutritionReview.nativeContract.test.ts`
- API/model tests
- rendered interaction tests for changed workspace navigation

## Port

Web owns:

- queue/status hierarchy
- selected case context
- plan
- labs
- supplements
- notes/rationale
- approval/rejection
- read-only approved state

## Native adaptation

Convert desktop multi-pane workspace into phone-friendly:

- queue → case
- segmented case tabs
- sticky/safe final decision area where appropriate
- native Back returns to queue

Preserve role and review safety.

---

# 27. Phase 24 — Cross-screen copy and status cleanup

After all primary pages are migrated, perform one dedicated pass.

## Search for user-visible internal codes

Search native UI for patterns such as:

- `.join("\n")` on warning/reason arrays
- raw `SCREAMING_SNAKE_CASE`
- raw schema versions
- raw provider error messages
- raw message keys
- raw enum values

Examples that should not leak:

- `SOFT_WEEKLY_VOLUME_BELOW_MINIMUM`
- `PLANNED_VOLUME_REDUCED_DURING_SESSION_FIT`
- untranslated Body Analysis message keys
- raw nutrition reason codes

## Rule

If web already maps the code to user-facing copy, native should use equivalent copy.

If code is internal-only and web does not expose it, do not display it in member UI.

Do not alter backend payloads just to hide UI codes.

---

# 28. Phase 25 — RTL / LTR / typography parity

Audit every rebuilt page.

## Persian primary acceptance

- correct `writingDirection`
- correct logical row order
- numerals/units remain readable
- icons that imply direction use logical direction
- no accidental mirroring of media
- no clipped joined Persian glyphs
- Lalezar only for short display headings
- Vazirmatn for body/forms
- Sora for appropriate numeric/English display

## English smoke

Do not require pixel parity during this Persian-first pass, but:

- no overlap
- no backwards order
- no clipped button
- no hardcoded Persian in a feature that already supports English unless existing native localization architecture has not yet been migrated; record it explicitly

---

# 29. Phase 26 — Accessibility and Native Adaptation verification

For every rebuilt core screen verify:

- 48 dp touch targets
- TalkBack labels
- button state
- loading announcement
- error announcement
- modal/sheet focus
- keyboard dismissal
- Android Back
- 200% text scale
- safe-area ownership
- gesture navigation
- three-button navigation

If achieving a web-like dense look would violate 48 dp interaction size, keep the **visual element compact** but enlarge the invisible/pressable hit area.

This is the preferred Native Adaptation.

---

# 30. Phase 27 — Performance verification

Visual parity itself is not a reason for slower code.

Do not add:

- WebView
- global blur layers
- several nested atmospheric surfaces for every card
- large decorative animation libraries
- unnecessary image copies
- autoplaying catalogue videos
- expensive gradients/shadows on huge scrolling lists

## Measure instead of guessing

Inspect existing performance tooling/docs before changing performance code:

- `docs/mobile-performance.md`
- `mobile/platform/performance.ts`
- `mobile/platform/performanceMeasuredCommit.tsx`
- `mobile/platform/queryDefaults.ts`
- media/video cache code

Check:

- cold start
- screen transition
- list scrolling
- media loading
- memory during video/camera
- image processing
- Body Analysis capture
- long nutrition lists

Use `FlatList`/virtualization where current implementation needs it, even if web uses simple mapped DOM nodes.

---

# 31. Testing protocol for every page task

For each page, follow this exact loop.

## 31.1 Read before editing

Read:

1. web component
2. web CSS
3. native screen
4. native child presentation components
5. native API/model
6. current tests

## 31.2 Write a short page parity note

Before code, add/update the page row in:

`mobile/artifacts/parity/web-native-page-matrix.md`

Record:

- web first viewport
- web section order
- native current order
- actions to preserve
- states to preserve
- intentional Native Adaptations
- exact file allowlist

## 31.3 Test behavior, not screenshots with source strings

Use:

- RNTL for rendered interaction
- model/API tests for logic
- narrow source-contract tests only for true invariants
- real screenshot/device inspection for appearance

A test that only checks `source.includes("CinematicSurface")` is not visual acceptance.

## 31.4 Implement smallest coherent unit

One screen/flow at a time.

Do not mix:

- Workout + Nutrition + Profile

in one giant diff.

## 31.5 Run focused verification

Use the repository’s installed scripts/tools.

Inspect `package.json` first because scripts can change.

Current relevant commands include:

```bash
npm run build:core
npm run typecheck:mobile
npm run test --workspace @fitician/mobile
npm run test:native --workspace @fitician/mobile
npm run test:mobile:foundation
npm run validate:mobile
git diff --check
```

For a focused native RNTL test, use the existing mobile Jest configuration and exact test path.

For focused Vitest tests, use the installed Vitest binary / package script without installing a new tool.

Run Oxlint against exact changed TypeScript files using the existing repository configuration.

## 31.6 Device inspect

For every visual page:

- 360 dp
- 390 dp
- 430 dp
- Persian
- normal text scale
- 200% stress
- relevant loading/error/offline state

If the physical device is not available, mark:

`implemented-awaiting-device-check`

Do not mark the page visually verified.

## 31.7 Diff review

Before completion:

- `git diff --check`
- inspect exact changed files
- no unrelated dirty files
- no secret/token
- no backend accidental change
- no removed action
- no newly exposed private/internal data

---

# 32. Recommended execution order for Luna

Do not jump randomly between screenshots.

Execute in this order because later pages depend on earlier shared decisions.

## Milestone A — Foundation

1. Phase 0 parity inventory
2. Shared Design System bridge
3. 5-destination member navigation

## Milestone B — Daily member experience

4. Home
5. Workout
6. Exercise Catalogue
7. Exercise Detail
8. Nutrition Overview
9. Nutrition Plan
10. Nutrition Tracking
11. Food/Meal catalogues
12. Clinical/labs/supplement presentation

## Milestone C — Body and account

13. Body Progress landing/history
14. Body capture
15. Body result
16. Profile
17. More
18. Account deletion/privacy

## Milestone D — First-use flow

19. Public entry
20. Auth family
21. Public onboarding
22. Authenticated onboarding

## Milestone E — Specialist workspaces

23. Coach
24. Physician

## Milestone F — Final quality

25. raw-copy/status cleanup
26. RTL/LTR
27. accessibility/native adaptation
28. performance
29. complete regression/device matrix

---

# 33. Per-page completion checklist

A page is not “done” because TypeScript passes.

For every page, all applicable boxes must be true:

- [ ] current web component read
- [ ] current web CSS read
- [ ] current native implementation read
- [ ] all existing native actions inventoried
- [ ] first viewport hierarchy matches web
- [ ] section order matches web unless documented native reason
- [ ] colors/tokens match shared design system
- [ ] no unnecessary giant mobile hero
- [ ] native touch targets remain ≥48 dp
- [ ] Android Back works
- [ ] keyboard works
- [ ] offline/stale works
- [ ] loading works
- [ ] empty works
- [ ] error/retry works
- [ ] approval/read-only state works
- [ ] no raw internal code leaks
- [ ] no fake metric/progress
- [ ] 360 dp verified
- [ ] 390 dp verified
- [ ] 430 dp verified
- [ ] Persian RTL verified
- [ ] 200% text stress checked
- [ ] focused tests pass
- [ ] typecheck passes
- [ ] lint for changed files passes
- [ ] `git diff --check` passes
- [ ] before/after evidence recorded
- [ ] no unrelated files changed

---

# 34. Visual acceptance rule

For every rebuilt page, compare native to web by **composition**, not screenshot pixel dimensions.

Score from 0–4:

- hierarchy
- typography/RTL
- spacing/density
- surfaces/components
- media
- state clarity
- interaction clarity

Definitions:

- `0` broken
- `1` major mismatch
- `2` usable but clearly different product
- `3` convincingly same product with proper native adaptation
- `4` very strong parity and polish

A core page may not be called complete if any category is below `3`.

The user owns final aesthetic acceptance.

---

# 35. What Luna must NOT do

Do not:

- redesign from personal taste
- create a new palette
- create a second parallel component library
- globally change `CinematicSurface` just to fix one screen
- make every screen cinematic
- put FITICIAN brand header above every member page
- copy desktop columns literally onto 360 dp
- remove functionality to match one screenshot
- disable safety warnings/approval guards
- expose raw warning codes
- alter backend algorithms
- replace native with WebView
- force-push
- stage unrelated worktree changes
- claim visual parity from unit tests alone
- claim device verification without device evidence
- create native admin screens in this roadmap

---

# 36. What Luna SHOULD do when web and native disagree

Use this decision algorithm:

### Case A — purely visual disagreement

Example: web uses a compact status rail; native uses three giant warning cards.

**Choose web.**

### Case B — interaction differs because platform differs

Example: web uses `<details>`; native has `DisclosureCard`.

**Keep native interaction, match web visual hierarchy.**

### Case C — web uses a desktop two-column workspace

**Preserve information order and relationships, convert to stack/tabs/sheets for phone.**

### Case D — native has additional platform capability

Example: cached PDF/open file, camera permission, offline private media.

**Preserve native capability and place it in the nearest equivalent web secondary section.**

### Case E — web has capability not present natively

First verify that the backend/native API already supports it.

- If existing native contract supports it: add UI parity.
- If it requires new backend/domain work: record as `MISSING_EXISTING_CAPABILITY` and stop that sub-feature. Do not silently expand scope.

### Case F — old mobile spec conflicts with current web

**This plan + current web wins visually.**

---

# 37. Recommended implementation report after each page

Use this concise report:

```text
Page: <page name>

Web source:
- <web tsx>
- <web css>

Native changed:
- <file>
- <file>

Preserved:
- <queries/actions/offline/security/native interactions>

Native adaptations:
- <specific justified differences from web>

Verified:
- <tests>
- <typecheck/lint>
- <device widths/states>

Remaining differences:
- <difference + technical/native reason>

Status:
- implemented-awaiting-device-check | verified | blocked
```

---

# 38. Final acceptance journey

After all phases, test one controlled account through this exact native journey:

1. open public entry
2. register or sign in
3. complete/resume onboarding
4. inspect Home
5. open Workout
6. inspect first and secondary workout days
7. open an exercise
8. return to catalogue and change filters
9. inspect Nutrition overview
10. inspect/select active nutrition plan where applicable
11. track an existing supported meal/food action
12. open Body Analysis progress
13. start/resume capture
14. inspect result/history
15. edit Profile
16. inspect More/account/privacy
17. disconnect internet and revisit cached screens
18. reconnect and refresh
19. background/foreground app during media
20. restart app and verify persisted state

Then run role-specific journeys for:

- coach
- physician

Do not test with real private body photos in committed evidence.

---

# 39. Final verification commands

Re-read package scripts first, then run the repository-equivalent of:

```bash
npm run build:core
npm run typecheck:mobile
npm run test --workspace @fitician/mobile
npm run test:native --workspace @fitician/mobile
npm run test:mobile:foundation
npm run validate:mobile
git diff --check
```

Also run the applicable Maestro flows documented in:

- `docs/mobile-e2e.md`

and verify current release/device docs:

- `docs/mobile-release.md`
- `docs/mobile-eas.md`
- `docs/mobile-performance.md`
- `docs/mobile-accessibility.md`
- `mobile/device-matrix.json`

A successful Metro bundle or TypeScript compile is not physical-device visual verification.

---

# 40. Start instruction for Luna

Read `AGENTS.md`, this file, current Git status, current `frontend/src/App.tsx`, and current `mobile/app/` routes.

Then read the older mobile design/quality documents only for useful engineering constraints.

**Start with Phase 0 only.**

Build the actual page matrix and component matrix before changing UI.

Then execute the phases in the order above.

For every page:

1. read the exact current web TSX + CSS
2. read the exact current native screen + children + tests
3. preserve native feature logic
4. port web visual hierarchy
5. document Native Adaptations
6. verify behavior and real rendering
7. continue until that page passes its gate

Do not ask for a new visual direction: the direction is already decided.

**Web = Visual Source of Truth.**  
**Native = platform-appropriate implementation of that same product.**

Ask only when there is a serious product/domain ambiguity that cannot be resolved from the repository.

Do not stop after making the screen “less ugly”. The completion target is a coherent, page-by-page native product that is visibly the same Fitician design system as the website, while still behaving like a professional native Android application.
