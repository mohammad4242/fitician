# Native Welcome artwork regression — 2026-10-14

## Root cause

The approved native Welcome implementation was committed on feat/support-progress
as 2e121be8; 506ce2da subsequently adjusted image sizing and used an enhanced PNG.
Neither commit is an ancestor of the Android release source 765c16c3.
PublicLandingScreen in that release still rendered the cinematic landing.
Its signed code-12 APK contains the cinematic JavaScript and neither Welcome
image hash. This is missing branch integration, not a server, cache or S3 failure.

## Correction

Restore the original uploaded 720x1280 JPEG, unchanged, at
mobile/assets/landing/pic_land.jpg. Original size: 156259 bytes.
SHA256: 92e8977e4d62f13699b70c82aa4d600a16eece4de6a33f020d2eedbe370398fe.

Use the previously approved native Welcome layout: black full-screen background,
locally bundled cover image with explicit full width/height, bottom safe-area
clearance, Start (شروع کنیم) and Sign in (ورود). Keep existing public onboarding
and sign-in destinations and the public RouteGuard. The bitmap already includes
branding; the screen adds native touch controls. The approved Welcome has no
cinematic/marketing panels. Registration campaign code is untouched.
No Web/backend source changes, image generation, recompression or network image
URL are part of this correction.

## Regression evidence

Before implementation, both focused native regressions failed (missing Welcome
background/Start button), and both Welcome contracts failed against cinematic
source. After restoration, all 63 native suites / 402 tests passed, including
safe-area controls. Nine focused Welcome/onboarding/nutrition contracts passed.
TypeScript, production validation, tracked-secret scan and diff checks passed.
The image contract checks exact original SHA256 so a different asset cannot
silently replace the approved gym artwork. Public route guards remain unchanged.

## Signed Android acceptance

A new signed APK is required because code 12 does not contain this screen or
image. Build from the committed source in an isolated clean worktree with frozen
existing Production credentials. Verify APK package/version/signature and the
SHA256 of the embedded JPEG against the original before installation.
Use adb install -r only; never uninstall or clear user data.

At correction time adb devices lists no connected phone. The owner was asked to
reconnect for actual Welcome display/control acceptance. Asset export/hash and
unit tests alone do not establish displayed pixels on a physical device.
Record final artifact and actual acceptance in the workspace release evidence.
This fix does not certify unresolved authentication, FCM or other release gates.
