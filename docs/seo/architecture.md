# Public SEO architecture

Options evaluated: Vite SSG plus existing SPA (selected), request-time SSR, framework migration. Autonomous task authorization permits this reversible choice.

A typed public registry drives metadata, routes, server rendering and sitemap generation. React 19 owns head metadata. Public education/tools use a separate hydrated entry, without member APIs or cinematic assets. Existing home is rendered from its original components and hydrates with existing session redirect behavior. Existing legal/help/install routes retain their components and public metadata. Private routes use a noindex SPA shell and unchanged guards.

Canonical origin: https://fitician.fit, matching the repository's public support URL. Only Persian educational URLs are published; do not invent English hreflang. Personal language settings remain in the member app/home.

Public paths: `/workout-program`, `/nutrition`, `/body-analysis`, `/learn`, `/learn/beginner-training`, `/learn/upper-lower`, `/learn/protein`, `/tools`, `/tools/calorie-calculator`, `/tools/protein-calculator`, `/exercise-library`, `/exercise-library/:slug`, `/about`, `/editorial-policy`. Existing `/exercises` remains the member catalogue.

Initial exercise publication reads canonical ExerciseSeed/curated safety records through a field allowlist at build time. No new anonymous API, DB connection, user data, engine metadata or admin response is exposed. Rebuilds refresh the subset; DB-wide publication needs a separate review/licensing workflow. Media is omitted until a deployment-verified public asset source exists, rather than publishing broken or unlicensed URLs.

nginx serves generated public files, a separate app.html for explicitly known member/auth patterns, and a real 404 page for everything else. Static misses never receive SPA HTML. Workbox fallback is limited to member routes and home; public content and unknown URLs retain network status.

Sitemap index and size-bounded shards derive from canonical indexable registry records. Exclude all private/auth/onboarding/deletion URLs. Do not fake lastmod. Crawlable member shells carry noindex both in HTML and X-Robots-Tag; robots.txt does not prevent crawlers seeing noindex.

Organization, WebSite, WebPage and BreadcrumbList reflect visible site content. No fabricated expert authors/reviewers, FAQ eligibility, ratings, offers or medical schema. Educational pages show organizational attribution and references, with honest publication dates and no invented specialist review.

Verification: test contracts first; SSR output/head/RTL, calculator bounds, actual nginx status, private guards, Playwright desktop/mobile/hydration, PWA navigation, frontend gates and final Docker image.
