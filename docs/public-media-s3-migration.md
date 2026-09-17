# Public media S3 migration

## Scope

The migration keeps database values as stable `/media/...` paths and maps them to provider-neutral
object keys. Private media uses the separate private bucket; source imports, reports, application
icons, and bundled Web or Mobile assets are excluded.

| Local source | Object key prefix |
| --- | --- |
| `backend/var/media/exercises/seed/` | `public/exercises/seed/` |
| `backend/var/media/exercises/<slug--id>/` | `public/exercises/<slug--id>/` |
| `backend/var/media/food-catalogue/` | `public/food-catalogue/` |
| `backend/var/media/meal-catalogue/` | `public/meal-catalogue/` |
| `frontend/src/assets/landing/*.mp4` | `public/landing/videos/` |
| `frontend/src/assets/landing/body.png` | `public/landing/images/body.png` |

Landing videos and the large body image are remote runtime media. Small landing artwork, posters,
logos, icons, fonts, and bundled Body Analysis/MediaPipe assets remain in the frontend image.

## Runtime contract

`MEDIA_STORAGE_BACKEND=local` serves the retained local files. `MEDIA_STORAGE_BACKEND=s3` reads
verified public objects and uses `MEDIA_PUBLIC_BASE_URL` for direct public URLs. A missing or
temporarily unavailable remote object uses the local copy only when
`MEDIA_LOCAL_FALLBACK_ENABLED=true`. Production sets it to `false`, so a missing object is a real
storage error.

Nutrition PDF rendering reads catalogue images through the same storage abstraction. Each image is
cached for one PDF render. Private media uses the authenticated backend and the private bucket.

Required S3 configuration:

```text
MEDIA_STORAGE_BACKEND=s3
S3_ENDPOINT=
S3_BUCKET=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
S3_REGION=
S3_PUBLIC_OBJECT_ACL=public-read
S3_PUBLIC_BUCKET=fitician-media
S3_PRIVATE_BUCKET=fitician-private-media
MEDIA_LOCAL_FALLBACK_ENABLED=false
MEDIA_PUBLIC_BASE_URL=
```

Do not store credentials in Git. `MEDIA_PUBLIC_BASE_URL` may later point to a custom CDN domain
without changing database values.

## Migration command

Run from `backend/` with credentials supplied by the process environment:

```bash
uv run python scripts/migrate_public_media_to_s3.py --dry-run
uv run python scripts/migrate_public_media_to_s3.py --upload --resume --category food-catalogue
uv run python scripts/migrate_public_media_to_s3.py --verify --category food-catalogue
```

Repeat upload and verification in this order: `food-catalogue`, `meal-catalogue`,
`exercise-seed`, `exercises`, `landing-images`, `landing-videos`. The command writes resumable manifests and state under the ignored
`backend/var/media-s3-migration/` directory. It refuses conflicting content and unexpected keys,
stores SHA-256 as object metadata when the provider returns it, and hashes same-size remote content
when a provider replica omits that metadata. Uploads use bounded multipart transfer for large files,
and accept a lost upload response only after authenticated size/hash verification. Verification
downloads every object and never deletes local or remote objects.

Current-reference-only private migration is separate:

```bash
uv run python -m scripts.migrate_private_media_to_s3 --dry-run
uv run python -m scripts.migrate_private_media_to_s3 --upload --category body-photos
uv run python -m scripts.migrate_private_media_to_s3 --verify --category body-photos
```

It blocks on missing current files, excludes unknown/historical files, never prints private keys,
and never deletes local or remote objects. Anonymous access to the private bucket is denied.

## Verified migration snapshot

Verified against ArvanCloud on 2026-09-17. The 12 large exercise objects that had lost multipart
responses were completed with an immutable transfer fallback and then verified by this tool.

| Category | Objects | Bytes | SHA-256 verified | Public reads |
| --- | ---: | ---: | ---: | ---: |
| Food catalogue | 59 | 6,578,091 | 59 | 59 |
| Meal catalogue | 39 | 4,612,176 | 39 | 39 |
| Exercise seed | 17 | 8,545,365 | 17 | 17 |
| Exercise media | 1,874 | 2,581,556,510 | 1,874 | 1,874 |
| Landing images | 1 | 1,770,795 | 1 | 1 |
| Landing videos | 4 | 16,042,731 | 4 | 4 |
| **Total** | **1,994** | **2,619,105,668** | **1,994** | **1,994** |

The local directories remain the rollback source after verification. Existing administrative write
routes use the same provider-neutral storage abstraction. With `MEDIA_STORAGE_BACKEND=s3`, admin
exercise, food-catalogue, and meal-catalogue uploads write to the approved `public/` object key,
verify the remote size and SHA-256, and retain the local copy for fallback. Database commits happen
before replacement cleanup, and shared old image objects are retained. `local` keeps the original
local-only behavior. Current referenced private records are migrated separately to
`fitician-private-media`; unresolved and historical files are not uploaded.

The 35 incomplete multipart upload sessions from interrupted exercise attempts were confirmed to be
the approved migration keys (`public/exercises/...`) and aborted explicitly after migration. No
unrelated multipart sessions remained. No completed object or local file was deleted.

## Previous reconciliation commit size

Commit `dca8f514` added 81,334 lines because `docs/media-reconciliation.json` contains 80,522
lines (3,856,492 bytes) covering 5,532 deterministic records. Its loose Git object is about 454 KiB
after compression. The commit's 19 media files reused existing blobs through renames. No base64
media, private per-file inventory, credentials, or host-absolute private path was added. The
repository's existing 3.11 GiB pack size predates that commit. The manifest remains useful,
reviewable reconciliation evidence and is retained.
