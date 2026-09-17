# Public media S3 migration

## Scope

The migration keeps database values as stable `/media/...` paths and maps them to provider-neutral
object keys. Private media, source imports, reports, application icons, and bundled Web or Mobile
assets are excluded.

| Local source | Object key prefix |
| --- | --- |
| `backend/var/media/exercises/seed/` | `public/exercises/seed/` |
| `backend/var/media/exercises/<slug--id>/` | `public/exercises/<slug--id>/` |
| `backend/var/media/food-catalogue/` | `public/food-catalogue/` |
| `backend/var/media/meal-catalogue/` | `public/meal-catalogue/` |

Landing assets remain in the frontend bundle. Their existing compile-time imports are deterministic,
and changing that delivery contract is outside this migration.

## Runtime contract

`MEDIA_STORAGE_BACKEND=local` serves the retained local files. `MEDIA_STORAGE_BACKEND=s3` checks S3
and redirects an existing public object to `MEDIA_PUBLIC_BASE_URL`. A missing or temporarily
unavailable remote object uses the local copy and adds `X-Fitician-Media-Fallback: local` while
logging the fallback. A provider failure without a local copy returns HTTP 503.

Nutrition PDF rendering reads catalogue images through the same storage abstraction. Each image is
cached for one PDF render. Private media continues to use its existing authenticated local routes.

Required S3 configuration:

```text
MEDIA_STORAGE_BACKEND=s3
S3_ENDPOINT=
S3_BUCKET=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
S3_REGION=
S3_PUBLIC_OBJECT_ACL=public-read
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
`exercise-seed`, `exercises`. The command writes resumable manifests and state under the ignored
`backend/var/media-s3-migration/` directory. It refuses conflicting content and unexpected keys,
stores SHA-256 as object metadata when the provider returns it, and hashes same-size remote content
when a provider replica omits that metadata. Uploads use bounded multipart transfer for large files,
and accept a lost upload response only after authenticated size/hash verification. Verification
downloads every object and never deletes local or remote objects.

## Verified migration snapshot

Verified against ArvanCloud on 2026-09-17. The 12 large exercise objects that had lost multipart
responses were completed with an immutable transfer fallback and then verified by this tool.

| Category | Objects | Bytes | SHA-256 verified | Public reads |
| --- | ---: | ---: | ---: | ---: |
| Food catalogue | 59 | 6,578,091 | 59 | 59 |
| Meal catalogue | 39 | 4,612,176 | 39 | 39 |
| Exercise seed | 17 | 8,545,365 | 17 | 17 |
| Exercise media | 1,874 | 2,581,556,510 | 1,874 | 1,874 |
| **Total** | **1,989** | **2,601,292,142** | **1,989** | **1,989** |

The local directories remain the rollback source after verification. Existing administrative write
routes still write to local media; a later dual-write step is required before all new public uploads
are S3 native.

35 incomplete multipart upload sessions from interrupted exercise attempts remain in the bucket. They
are not completed objects and are outside the readable media namespace. They were not aborted because
this migration is prohibited from deleting remote data. Review and abort them in a separate, explicitly
authorized storage-maintenance task.

## Previous reconciliation commit size

Commit `dca8f514` added 81,334 lines because `docs/media-reconciliation.json` contains 80,522
lines (3,856,492 bytes) covering 5,532 deterministic records. Its loose Git object is about 454 KiB
after compression. The commit's 19 media files reused existing blobs through renames. No base64
media, private per-file inventory, credentials, or host-absolute private path was added. The
repository's existing 3.11 GiB pack size predates that commit. The manifest remains useful,
reviewable reconciliation evidence and is retained.
