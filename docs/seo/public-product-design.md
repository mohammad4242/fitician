# Public Fitician product experience

Approved publication choice: explicit approval per exercise (owner selection, 2026-10-06).

Reuse the actual member catalogue presentation, category/focus controls, cards, media carousel and detail accordions. Keep authentication/admin adapters in member entry files; public entries consume only educational types and safe GET endpoints. Preserve /exercises and /exercise-library route bases and query state. Public filters use buttons/history state, with clean catalogue canonicals and no query sitemap entries.

Add is_public (default false). Backfill only the 18 previously published seed slugs. Active + reviewed + explicit approval is required for the API. Project names, anatomy, equipment, difficulty, instructions and safety into dedicated schemas. Rights-check stable /media/exercises paths; otherwise show the existing placeholder. No signed URLs, private paths, source IDs or admin/engine fields. Anonymous reads have bounded filters, distributed rate limiting and no-store responses to honor revocation immediately.

Prerender exercise detail content using an explicitly refreshed public projection. Keep existing seed canonicals and meaningful HTML. Approved DB pages require a safe projection snapshot and reviewed web release before becoming crawlable; never create an indexable wildcard SPA. The release must verify the snapshot against live approval before publishing. Keep unpublished slugs out of discovery.

Use the established dark/turquoise palette, Lalezar display and Vazirmatn text. Share BrandLogo and a compact public navigation/footer. Retain calculator workspaces and cinematic home unchanged. Give workout, nutrition, body analysis, Learn and About distinct layouts with real HTML, existing sources and truthful boundaries. Discovery uses six restrained feature cards, followed by one footer.

Verify API projection/security, member/admin regressions, public interactions/back navigation, SSR content, metadata/sitemap/404/PWA, and 360/390/430/768/1440 layouts. Run the repository classifier and all resulting gates. Release through a reviewed PR and exact-SHA production gates, then verify production directly.

## Publishing exercises

From `backend/`, run `uv run python -m app.exercises.public_export --output ../frontend/src/seo/exercise-publications.json` against the intended database. Review and commit the safe snapshot together with `backend/app/exercises/publication_slugs.json`. Build exports reject manifest mismatches. A null snapshot preserves the existing 18 seed pages; an array is a full approved snapshot, including an empty array for no published exercises.

Before release, compare the snapshot with live active/reviewed/public approvals. Revocations immediately stop API reads; remove the projection and rebuild to remove static HTML and sitemap entries. The current release retains the 18 previously published, owner-authorized seed exercises. It does not approve imported records automatically.
