# Full public exercise library correction

**Goal:** Publish the real reviewed Fitician catalogue instead of the 18 seed exercises.
**Architecture:** Keep the existing explicit per-exercise approval, public projection, publication manifest and prerender workflow. Export production educational data only; approve the reviewed release set through a guarded additive data migration. Preserve member/admin routes and all SEO URLs.
**Authorization:** Owner requested the full public browsing correction on 2026-10-07. Media permission for imported videos is pending explicit confirmation because existing license fields are null.

- [x] Audit live active/reviewed records, names, instructions, safety and public storage delivery.
- [x] Add failing tests for imported chest browsing, public media controls, release publication and bounded catalogue payload.
- [x] Produce the explicit safe snapshot and immutable approval migration; keep 99 flagged review records and three unfinished instruction records out.
- [x] Publish only rights-verified public media, retain truthful fallback for missing safety notes/media, and reduce catalogue payload to card fields.
- [ ] Run focused tests, frontend/backend checks, SEO/browser/build and required CI classification.
- [ ] Commit/push, review PR, merge, exact-SHA release with encrypted backup, then verify live counts, chest selection, media carousel, pagination, SEO and mobile.

## Known audit results

Production currently has 435 active records and 821 media asset rows. 336 records have completed review (335 exercises and one guide), including 24 chest exercises. All reviewed records have bilingual names and at least three Persian instruction steps. 137 imported exercises lack dedicated safety notes; show an explicitly labeled general form/safety reminder without inventing exercise-specific review. Existing media permissions must be confirmed before replacing their fallback.

Three additional records have importer placeholder instructions despite a cleared review flag. The release excludes them, leaving 333 educational records (332 exercises and one guide). All 626 asset paths belonging to the initial reviewed set exist in the public S3 namespace; permission confirmation is separate from object availability.

Local verification: 1,257 frontend tests, 424 exercise/admin backend tests, TypeScript production build, lint, focused mypy and 57 nginx-backed SEO browser checks. The calendar-dependent nutrition test selected an unchanged date on October 7; its input now selects ten days earlier, with all 42 focused nutrition tests passing. Snapshot candidates were exported read-only from production; no production approval or media rights mutation has occurred yet.
