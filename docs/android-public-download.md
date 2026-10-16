# Public Android download

The installation page is `https://fitician.fit/install`. The frontend nginx configuration redirects `/download/android` with HTTP 302 and `Cache-Control: no-store` to:

https://fitician-media.s3.ir-thr-at1.arvanstorage.ir/public/download/android/latest.apk

Future releases replace this stable object only after release verification. Keep a separate immutable object per release; do not put APKs in Git or frontend images. Set `application/vnd.android.package-archive`, attachment disposition, public-read object access, and `Cache-Control: no-cache` on the stable key. Never change bucket policy to publish a release. Verify the full public download from Iran against the approved SHA-256 before announcing it.

## Verified October 15 release

- EAS build: `ca069509-a7b3-4604-9f79-5beee8516cd8`, Android `production-device`, FINISHED.
- Created: `2026-10-15T00:46:31Z`; completed: `2026-10-15T01:16:16Z`.
- Source commit: `d254a4e207b3a419dad68b183ca88bffc1c4ab0a`.
- Package: `com.fitician.app`; version: `0.1.3`; versionCode: `13`.
- Size: `225530203` bytes.
- APK SHA-256: `62bc0a7c89ba82e228c539394bf245811f737ad4ba18b9f0c823b3993198c10d`.
- Signature: APK Signature Scheme v2, one signer. Certificate SHA-256: `71e088feb1767f45d9e907ff3484ae6411e557d3623df88d843cdf964265562c`, matching the production certificate in `frontend/public/.well-known/assetlinks.json`.
- Immutable object: `public/download/android/fitician-0.1.3-13.apk` in the existing public Arvan bucket.
- Both objects return HTTPS 200 with the expected size, APK content type and attachment disposition. Full stable-object download from Iran matches the verified APK checksum.

## Installation page validation

Run the frontend production build, then `npm exec --workspace frontend -- playwright test --config playwright.install.config.ts`. This focused browser configuration needs no backend or database. Chromium/WebKit cover Android and iPhone user agents, Instagram, clipboard success/denial, platform switching, installed state, Chromium prompts, English/RTL, light-theme isolation and 320px layout. These are browser simulations, not physical-device acceptance.

October 16 checks: 26 focused unit tests, 26 browser checks, targeted Oxlint, TypeScript and production build passed. Native nginx syntax and the local no-store 302 redirect were verified.

## Publication status on October 16

The APK is published. The redesigned page and vanity download endpoint are committed but not deployed. Production component and regional CD workflows explicitly contain disabled `false &&` gates. Do not bypass them. From Iran the existing `/install` returns 200 and `/download/android` returns 404. A reviewed deployment re-enablement and required release validation are prerequisites for rollout. No new Full CI was dispatched for this task.

Cafe Bazaar and Myket listings were not verified; their page actions remain disabled as coming soon.
