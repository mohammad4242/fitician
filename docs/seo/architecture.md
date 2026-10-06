# Public SEO architecture

Options evaluated: Vite SSG plus existing SPA (selected), request-time SSR, framework migration. Autonomous task authorization permits this reversible choice.

A typed public registry drives metadata, routes, server rendering and sitemap generation. React 19 owns head metadata. Public education/tools use a separate hydrated entry, without member APIs or cinematic assets. Exercises have their own entry and reuse the member presentation through safe public adapters. Existing home is rendered from its original components and hydrates with existing session redirect behavior. Existing legal/help/install routes retain their components and public metadata. Private routes use a noindex SPA shell and unchanged guards.

Canonical origin: https://fitician.fit, matching the repository's public support URL. Only Persian educational URLs are published; do not invent English hreflang. Personal language settings remain in the member app/home.

Public paths: `/workout-program`, `/nutrition`, `/body-analysis`, `/learn`, `/learn/beginner-training`, `/learn/upper-lower`, `/learn/protein`, `/tools`, `/tools/calorie-calculator`, `/tools/protein-calculator`, `/tools/bmi-calculator`, `/exercise-library`, `/exercise-library/:slug`, `/about`, `/editorial-policy`. Existing `/exercises` remains the member catalogue.

Exercise publication requires explicit `is_public` approval, active status and completed review. Dedicated anonymous GET endpoints project only instructional fields. Stable public media is rights-checked; other media uses the existing fallback. Admin/member endpoints retain authentication. Build-time projections provide meaningful exercise HTML independently of API hydration. The publication manifest prevents API discovery before approved detail pages are released. See [publication workflow](public-product-design.md).

nginx serves generated public files, a separate app.html for explicitly known member/auth patterns, and a real 404 page for everything else. Static misses never receive SPA HTML. Workbox fallback is limited to member routes and home; public content and unknown URLs retain network status.

Sitemap index and size-bounded shards derive from canonical indexable registry records. Exclude all private/auth/onboarding/deletion URLs. Do not fake lastmod. Crawlable member shells carry noindex both in HTML and X-Robots-Tag; robots.txt does not prevent crawlers seeing noindex.

Organization, WebSite, WebPage and BreadcrumbList reflect visible site content. No fabricated expert authors/reviewers, FAQ eligibility, ratings, offers or medical schema. Educational pages show organizational attribution and references, with honest publication dates and no invented specialist review.

Verification: test contracts first; SSR output/head/RTL, calculator bounds, actual nginx status, private guards, Playwright desktop/mobile/hydration, PWA navigation, frontend gates and final Docker image.
