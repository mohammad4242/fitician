# Original SEO audit — 6 October 2026

Inspected origin/main `1da32cc319ec71da30c01f5f79003d1f36d7267b`, not the unrelated working branch.

- React 19/Vite 8 SPA, createRoot, BrowserRouter. Source HTML root is empty. No public server rendering.
- Shared title/description; no canonical, robots metadata, OG, Twitter, JSON-LD, robots.txt or sitemap. No scattered document.title implementation was found.
- `/`, `/support`, `/privacy`, `/install`, `/delete-account`, `/get-started`, and auth entry routes are reachable without membership. Exercise and nutrition catalogues require authentication/profile completion. Admin and personal plans retain guards.
- Unknown client routes redirect to dashboard; nginx falls back to index.html for arbitrary paths and missing assets. Real 404 handling is absent outside explicit asset exceptions. High soft-404 risk.
- Default browser robots policy permits indexing every SPA response, including authentication and private route shells. Authentication protects data; robots is not access control.
- Persian lang/fa and RTL source HTML; persisted English preference changes content at the same URL. No separate translated URLs; no valid hreflang set exists.
- Cinematic home has actual headings and product CTAs after JS; supporting public topic links are absent. Member exercise detail has safe instructional fields but its response also contains source IDs/review flags; do not republish that response wholesale.
- Exercise seed records and curated safety notes are canonical maintained source data. Imported DB content has review/licensing concerns. Seed media is owner-authorized, but availability is deployment-dependent.
- Nutrition catalogue includes administration and pricing. Personal nutrition and body analysis cannot be republished. Only product descriptions and generic evidence-based education may be reused.
- Workbox uses index.html navigation fallback with only API/media exclusions. This can hide invalid-page status and replay generic HTML. API/private media are excluded from precache.
- Home film autoplays and uses metadata preload; scroll scenes use requestAnimationFrame. Poster and several illustration assets are sizeable. Auth bootstrap currently delays home rendering. New content should use an independent entry without landing media or member providers.
- Caddy redirects www to configured apex and routes API/media to backend. Frontend is static nginx built in Docker. CDN public media is separate; no runtime rendering service exists.
- Existing Vitest App/guards/landing/PWA tests and Playwright responsive/PWA/member tests provide regression coverage. Existing Playwright starts an isolated database/backend; SEO HTTP tests must additionally run against actual nginx.

This is source/config evidence, not a production crawler or field CWV measurement. Production status, indexing, rankings and 75th-percentile CWV remain unverified.
