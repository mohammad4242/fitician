# Media reconciliation

Snapshot: 2026-09-16. The pre-change `main` checkout had no tracked edits and 94 pre-existing untracked status entries. No media was deleted or uploaded. The machine-readable public-media inventory is [media-reconciliation.json](media-reconciliation.json); private file names and storage keys are deliberately excluded from Git.

## Boundaries

- `backend/var/media/exercises/<slug--id>/media-<hash>` is the canonical published exercise hierarchy. Keep it unchanged.
- `backend/var/media/food-catalogue` and `meal-catalogue` keep their current key names.
- `frontend/public/exercises` remains the tracked Web source for curated GIFs. Backend `/media/exercises/seed/` is a served copy, not a replacement for the Web bundle.
- `backend/var/private/{body-photos,food-photos,profile-photos,nutrition-labs}` remains private. Never commit a per-file private inventory.
- The future ArvanCloud bucket is `fitician-media`, with `public/` and `private/` key prefixes. This document does not enable S3.

## Baseline findings

- Exercise database: 836 distinct `/media/exercises/` paths; 833 resolved on this host. Missing: `seed/cable-curl.gif`, `seed/rear-delt-fly.gif`, and `seed/overhead-dumbbell-extension.gif`.
- Current private database versus disk: body 22 keys / 2,030 files; profile 1 / 1; food 16 / 519, with nine keys missing on disk; labs 0 / 1,543. A current database mismatch alone does not establish that a disk file is disposable.
- The Web landing hero video has three byte-identical copies: active `frontend/src/assets/landing/hero-strength.mp4`, static legacy `frontend/public/image&videos/landing.mp4`, and ignored source `image_videos/landing.mp4`. Preserve all three for now.
- Web and mobile `landfilm.mp4` are identical, but each is an active build input. Preserve both.
- Root Body Analysis art has exact feature-owned Web/mobile copies. Preserve all copies until provenance and reference review is complete.

## Reconciliation results

- A hash-checked seed sync publishes all 17 approved tracked GIFs without overwriting different bytes. The three broken database targets now resolve; the remaining approved seed GIF is also staged for fresh databases.
- All 836 local exercise media paths in the current database resolve on this host. The only
  additional path is the existing `/exercises/exercise-placeholder.svg` fallback.
- The nine missing food-photo keys are historical records with `status=deleted` and `deleted_at` set. Their absent files agree with the delete workflow; no file or database row was recreated.
- All seven current food-photo keys, all 22 current body-photo keys, and the current profile-photo key resolve. There are no current nutrition-lab keys.
- The ignored detailed private report classifies 2,001 repeated tiny body-photo files and 512 repeated tiny food-photo files as `KNOWN_GENERATED`. All 1,546 lab files exactly match the two test PDF fixtures. Fourteen body-photo files remain `UNKNOWN`. Historical database backups contained three older body-photo keys, none matching current disk files.
- An active food-photo database row whose file is missing now returns explicit HTTP `503` with `FOOD_PHOTO_STORAGE_UNAVAILABLE`. Authorization remains required before this check.
- Six active Web ghost-guide photos moved from root `bodyanalysis/` to `frontend/src/assets/body-analysis/ghost-guides/`.
- Three unreferenced public report files moved to `reports/public-archive/`; ten root evaluation PDFs moved to `artifacts/fitician-coach-evaluation-10-profiles/`.

## Canonicalization decisions

The manifest uses `CANONICAL_RUNTIME`, `CANONICAL_SOURCE`, `DERIVED_COPY`, `LEGACY_COPY`, and `UNKNOWN`. `UNKNOWN` is a preservation decision. No file is deleted or moved merely because its bytes match another file or the current database lacks a pointer.

- `backend/var/media/exercises/` is `CANONICAL_RUNTIME`; `owner-video/` and `free-exercise-db/` are preserved `LEGACY_COPY` source namespaces.
- `exercise-import/raw/` is `CANONICAL_SOURCE`; `backend/var/imports/` and `media-migration-source/` are preserved working or derived copies.
- `frontend/src/assets/landing/hero-strength.mp4` is the active Web runtime copy. `image_videos/landing.mp4` is its source copy. `frontend/public/image&videos/landing.mp4` is preserved as a legacy copy because PWA configuration still explicitly names that directory.
- Web and mobile `landfilm.mp4` are both `CANONICAL_RUNTIME` for their respective builds.
- Web and mobile Body Analysis artwork remains separately bundled. Loose untracked root copies remain `UNKNOWN` and untouched.

## Future bucket keys

```text
fitician-media/
  public/
    exercises/<existing slug--id>/<existing media-hash filename>
    exercises/seed/<existing gif name>
    food-catalogue/<existing key>
    meal-catalogue/<existing key>
    landing/videos/<selected name>
    landing/images/<selected name>
  private/
    body-photos/<existing key>
    food-photos/<existing key>
    profile-photos/<existing key>
    nutrition-labs/<existing key>
```

The local `/media` URL and private authenticated API routes remain the current application contract. Public object keys are distinct from provider URLs. Private objects must remain behind authorization.

The backend now defines provider-neutral public/private object-key helpers and an `ObjectStorage` protocol with collision-safe local and S3-compatible implementations. `MEDIA_STORAGE_BACKEND=local` remains the rollback default; `MEDIA_STORAGE_BACKEND=s3` is available for verified public delivery through `MEDIA_PUBLIC_BASE_URL`. Private media remains local and authenticated.

## Verification and open items

The current database may not represent historical ownership of all files left on this disk. Keep every `UNKNOWN` and unreferenced private file until a separate retention review. Detailed private paths and hashes stay only in `backend/var/media-reconciliation/private-media.json`, which is ignored by Git.

Validation completed on 2026-09-16:

- Backend focused media tests: 264 passed; storage hardening follow-up: 14 passed.
- Backend Ruff, focused mypy, Compose configuration, and manifest validation: passed.
- Web focused media tests: 114 passed; build passed; lint passed with one existing warning.
- Mobile focused Vitest: 76 passed; native Jest: 53 passed; typecheck and release validation passed.

The canonical public exercise and catalogue collections are handled by the staged uploader described
in `docs/public-media-s3-migration.md`. Fourteen private body-photo files still have unknown
ownership and remain out of scope; no private object is uploaded by this workflow.
