# SEO delivery: foundation release history

## Original state

Audited current main `1da32cc319ec71da30c01f5f79003d1f36d7267b` in an isolated worktree. Original HTML was an empty SPA root with shared title/description. There were no canonicals, robots metadata, sitemaps, social metadata or structured data. Unknown routes redirected to dashboard; nginx and Workbox broadly returned the SPA shell. Exercise/member/nutrition data required authentication. See [full original audit](audit.md).

## Implemented architecture

Vite build-time React rendering plus the existing member SPA; no framework migration or runtime rendering server. React 19 owns typed head metadata. The central registry defines title, description, canonical, robots, OG, Twitter, language, optional alternates and JSON-LD; typed page overrides are supported. Only actual Persian pages are published; no invented English hreflang.

New reading/tool pages hydrate their own embedded page payload. They do not load all article/exercise data, member providers, product translations, cinematic media or private APIs. Native anchors cross public/member entry boundaries. Home uses the existing cinematic components, styles, videos and product CTAs, with a restrained discovery footer. Reduced-motion initialization is server-safe; signed-in home still redirects into the member app. Existing help/privacy/install components have server HTML and keep their original client behavior.

Private routes retain existing guards. A central startup handoff removes server-owned head tags only when switching a legacy page to client rendering, preventing duplicate metadata. The generated member URL pattern drives nginx and Workbox together; trailing-slash catalogue refresh remains supported.

## Index policy

| Route class | Policy | Reason |
| --- | --- | --- |
| Home, topic pillars, published guides, tools, selected exercises, About/editorial | index, follow | Public useful canonical content |
| `/support`, `/privacy`, `/install` | index, follow | Public trust/help/product-access information |
| Login, register, password/email verification/reset | noindex, follow | Account utility; reset/query tokens are not canonical content |
| `/get-started`, `/onboarding` | noindex, follow | Interactive acquisition/profile wizard, not a standalone knowledge page |
| Dashboard, profile, progress, personal workout/nutrition/body analysis, member catalogues | noindex, follow | Account-specific product experience |
| Plans, billing, specialist workspaces, admin and tickets | noindex, follow | Protected transactional/workflow surfaces |
| `/delete-account` | noindex, follow | Account-lifecycle utility; remains publicly reachable from privacy |
| Unknown public URL/static miss | 404, noindex | Real missing resource; no dashboard redirect or soft-404 shell |

Robots directives never substitute for authentication. API/admin/private-media contracts were not changed.

## Sitemap and HTTP delivery

The canonical registry generates robots.txt, a sitemap index and URL shards (10,000 entries per shard; hard maximum 50,000). Only indexable self-canonical public routes qualify. No invented lastmod, priority or changefreq. `https://fitician.fit/sitemap.xml` is advertised in robots.txt.

nginx serves generated public HTML, explicit noindex member shells and a Persian 404 page. Missing assets and unknown paths return 404; API/media proxy behavior is preserved. Internal audit reports are removed from output and denied at nginx. Relative redirects work behind HTTPS ingress. `/index.html` remains a stable service-worker precache URL with homepage canonical metadata.

Workbox is regenerated after prerendering, so revision hashes describe the delivered HTML. Its fallback covers known member routes only. Public/unknown routes retain network HTTP behavior. Offline home is supplied by its actual precached HTML. Prompt-based updates remain intact.

## Public exercises

18 exercise pages are generated from canonical `ExerciseSeed` records and curated safety text on every build. A strict projection permits names, muscle/equipment taxonomy, difficulty, execution and safety text. No DB access, anonymous API, user data, source IDs, engine metadata or editing surface is introduced. This is a selected foundation, not a claim to publish the whole live catalogue. Media is deliberately withheld until public asset availability is verified. Expanding to imported DB records requires a real publication/review/licensing process. The projection freshness check passed.

## Tools and content

- Calorie/TDEE: Mifflin–St Jeor resting-energy estimate and explicitly approximate activity multipliers; adults only, finite bounded inputs, limitations visible.
- Protein: educational 1.4–2.0 g/kg range for healthy active adults; references and clinical limitations visible.
- Both tools work without signup. Inputs/results remain in browser memory; they are not transmitted, persisted or added to share URLs. Sharing the page does not share personal results.
- Three topic pillars cover workout programming, nutrition and body analysis. Three supporting guides cover beginner three-day organization, four-day Upper/Lower and daily protein. Hub/contextual links, breadcrumbs and onboarding CTAs connect the foundation.
- Publisher attribution, real source links and initial article dates are visible. No physician/coach review or individual expert credentials are fabricated. Optional real update dates are supported; no fake update/review timestamps are assigned. Editorial and correction rules are documented in [editorial.md](editorial.md).

## Structured data

Organization and WebSite on home; WebPage on public pages; BreadcrumbList on deep public pages; Article on the three actual guides, with organizational publisher/author and supporting references. No fake reviews/ratings/offers, FAQ rich-result claims, medical schema or invented specialist review. SoftwareApplication was evaluated but not added without a distinct fully documented public app listing. Tool/exercise pages use truthful WebPage/BreadcrumbList rather than pretending to have a special calculator/exercise rich result.

## Performance

Public tools/exercise pages made zero API, video or MediaPipe requests in browser tests. Their page data is isolated, supporting future content growth without bundling every record. A fresh mobile calculator visit transferred 76,759 compressed JS bytes in the local nginx measurement; no horizontal overflow was observed. This is a local payload measurement, not a field CWV score. Hashed static assets receive long caching; HTML is revalidated; gzip covers public HTML/JS/CSS without changing API/media compression behavior. Required route CSS is present in returned HTML, including the original cinematic home styles.

Home still carries its video/scroll-story costs. Initial server content removes the auth/JS gate for first meaningful HTML, but no field LCP/INP/CLS claim is made. Local responsive checks/screenshots passed; real-user 75th-percentile performance, production CDN/media delivery and Search Console metrics remain unverified. See [Search Console steps](search-console.md) and [sources](references.md).

## Verification

- Focused SEO/route/landing/install regression tests: 76 passed before final additional contracts; latest focused SEO + App run: 50 passed.
- Final complete frontend Vitest: **149 files, 1,228 tests passed** (45.90s).
- TypeScript: passes through `tsc -b` in production build.
- Oxlint: passes with two existing warnings in WeeklyNutritionPlan.tsx and webTransport.test.ts; neither was modified or disabled.
- Production frontend build: 35 canonical public pages generated; sitemap/robots and final Workbox generation passed.
- Actual production nginx image browser suite: **30 passed**, desktop Chromium, mobile Chromium and WebKit. Includes all public raw HTML/metadata, private exclusions/guards, API/media misses, 404s, tools, exercises, home CTA, all new reading-page responsiveness, SW navigation and offline home.
- Offline WebKit uses an isolated forwarding origin which is actually stopped. This avoids the confirmed Playwright `setOffline` bug without dropping the assertion: https://github.com/microsoft/playwright/issues/42775.
- Python public exporter: Ruff passed; projection freshness passed. Backend runtime code did not change, so backend pytest/mypy suites were not required.
- `git diff --check`: passed. Mobile/backend/shared-core source diffs against the base are empty.
- Dedicated scoped `Public SEO delivery` CI is added. Remote CI execution is not claimed from local checks.

Final local production frontend image: `fitician-frontend:seo-check`, ID `sha256:bbd50cf5327fef6b26a1d1e0ed62e8f48000797c8b8ed7f36e661665b4365ba3`. nginx configuration and health endpoint passed in isolated containers. Backend responses in HTTP tests come from an explicit non-production fixture, not live user data. **No production deployment or production health verification occurred.**

## Owner actions and opportunities, ranked

1. Deploy through the normal reviewed release gates, verify production HTML/status/CDN behavior, verify Search Console DNS ownership and submit sitemap; inspect core URLs.
2. Arrange real qualified scientific/editorial review and a named correction/review workflow before expanding health content. Update actual publication history as releases occur.
3. Establish DB exercise publication approval/deactivation and media-rights/availability checks; then publish the larger authoritative catalogue.
4. Collect field CWV/CrUX and Search Console query data. Optimize home video/poster delivery only with measured evidence and visual acceptance.
5. Improve existing guide depth using real Persian queries, then add focused volume/recovery/home-training clusters and reviewed nutrition topics. Avoid day-count doorway variants and supplement filler.
6. Add evidence-based muscle/equipment navigation when enough approved exercise records justify it. Preserve unique canonicals and reject indexable filter permutations.

See [exact public route map](routes.md).

Exact created/modified files: [files.md](files.md). Build and browser logs remain ignored in the workspace.

## Public product upgrade

The product upgrade replaces the plain discovery/footer and generic topic templates, shares the real member exercise presentation, and adds a separately authenticated-safe anonymous API. The historical text-only/no-API measurements above apply to the foundation release. Current public exercise pages intentionally fetch bounded safe GET projections and load approved exercise media; calculators retain their existing workspace and remain isolated from exercise/auth/admin bundles. Publication and revocation rules are documented in [public-product-design.md](public-product-design.md).
