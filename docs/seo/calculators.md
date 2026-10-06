# Public calculators — BMI and UI delivery

## Scope and inspection

Continued `feat/public-seo` from `3c9cfae4`. Inspected current calculator logic/UI, public content and registry, server rendering, metadata tests, E2E suite, prerender script, client entry, stylesheet, build manifest, Vite/PWA configuration, Docker/nginx test harness and SEO architecture documentation before editing. Existing SEO infrastructure is retained.

## Behavior

Exactly three tools: calorie/TDEE, protein, BMI. Shared compact tool header, privacy chip, crawlable switcher, unit-labelled controls, focus/error treatment and result panels. `/tools` presents three linked premium cards. Forms accept Latin, Persian and Arabic digits, including the Persian decimal separator. Invalid or empty input clears the result and focuses the affected field. Values are never stored, added to a URL, or sent to a server. Submit is disabled in server HTML until hydration; no-JavaScript pages remain readable and cannot submit personal values.

BMI = weight in kg / (height in cm / 100)². Inclusive bounds: height 130–220 cm; weight 35–250 kg. Non-finite values are rejected. Display uses one decimal; categories use the unrounded ratio at 18.5, 25 and 30. The segmented bar interpolates within four visual bands and clamps its ends; visible labels and an active-category label make interpretation independent of color.

Adult reference interpretation is explicitly for ages 20+ following CDC. Copy distinguishes BMI from body composition, muscle mass, body fat, metabolic health, fitness and medical diagnosis. Muscular individuals and other limitations are addressed without treatment recommendations. Sources:

- https://www.cdc.gov/bmi/adult-calculator/bmi-categories.html
- https://www.cdc.gov/bmi/about/index.html

Calorie results retain the Mifflin–St Jeor equation and current activity factors; maintenance and resting energy remain estimates. Protein retains 1.4–2.0 g/kg with no preference for the upper bound.

## SEO and safety

Added `/tools/bmi-calculator` to the existing content registry, which automatically supplies canonical URL, index/follow, breadcrumbs, WebPage/BreadcrumbList JSON-LD, meaningful prerendered HTML and sitemap inclusion. Unique Persian title and description; contextual links to body analysis, nutrition, workout programming and the other calculators. Total canonical pages: 36. No fake calculator rich-result schema.

No changes to registry machinery, prerender script, nginx, robots generation, sitemap generation, member routes/providers, API, backend or mobile. Public runtime remains local and avoids member APIs, landing video and vision packages. No new dependencies. Reduced-motion rules explicitly override the existing global transition duration for tool controls/cards.

## Verification

- Focused calculator/SEO/rendering Vitest: **3 files, 20 tests passed**.
- Full frontend Vitest: **150 files, 1,236 tests passed** (27.09 s final run).
- TypeScript: passed through `tsc -b` and final production build.
- Oxlint: **0 errors; 2 existing warnings** in `WeeklyNutritionPlan.tsx` and `webTransport.test.ts`; no new warnings.
- Final `npm run build --workspace frontend`: passed; **36 pages prerendered**, final Workbox generation passed.
- Production Docker image built: `fitician-frontend:seo-check`, `sha256:8f96a840bbdb3d102233e906d4b947940a3ed50ce6efc1373cf603a680485841`; nginx configuration passed.
- SEO Playwright against the real production nginx image: **39 passed**, desktop Chromium, mobile Chromium, WebKit (**23.2 s** final run). Includes HTML before JS, metadata, sitemap, local calculation/no API calls, no-JavaScript privacy, member guards, real 404s, exercise pages and PWA/offline regressions.
- All three tools tested at **360, 390, 430, 768 and 1280 px** in all three browser projects: no horizontal overflow, controls at least 44 px, visible focus, correct results including maximum supported weight, reduced-motion behavior.
- Screenshots visually inspected across all five widths, plus complete mobile/desktop hub and default BMI pages. RTL, labels, spacing, result hierarchy and long Persian text checked. Local evidence: `frontend/test-results/` (ignored build/test artifacts).
- `git diff --check`: passed.

The first browser run caught a reduced-motion cascade conflict; corrected the scoped CSS and reran the full suite. No tests disabled. Production was **not deployed**. No remaining implementation blocker.

## Exact changed files

- `frontend/src/seo/Calculator.tsx`
- `frontend/src/seo/Calculator.test.tsx` (new)
- `frontend/src/seo/Tools.tsx` (new)
- `frontend/src/seo/tools.ts` (new)
- `frontend/src/seo/calculators.ts`
- `frontend/src/seo/PublicPage.tsx`
- `frontend/src/seo/public.css`
- `frontend/src/seo/content.ts`
- `frontend/seo-e2e/seo.spec.ts`
- `docs/seo/architecture.md`
- `docs/seo/routes.md`
- `docs/seo/calculators.md` (this report)
