# Fitician app icon design

## Goal

Use the approved root image `logo.jpg` as Fitician's installed application icon
for the Web/PWA, iOS, and Android surfaces. The image includes the dark square
background, the aqua mark, the `Fitician` wordmark, and the `Fit with Science`
slogan.

This change is limited to install/launcher icon artwork. It does not replace
the in-app Web header, native `BrandMark`, or the existing native splash artwork.

## Architecture

`logo.jpg` remains the canonical local source. Generated PNG variants are
committed with the application assets:

- Web/PWA: `frontend/public/pwa/icon-192.png`, `icon-512.png`,
  `icon-maskable-512.png`, and `apple-touch-icon.png`.
- Native: `mobile/assets/branding/fitician-icon.png` and
  `fitician-adaptive-foreground.png`, using the filenames already referenced by
  `mobile/app.config.ts`.

The icon is bundled into the frontend build and native binaries. It is not
served from Arvan S3 and does not require a backend route, database value, or
runtime network request. A future icon change therefore ships with a frontend
deployment and a new native build, which is the intended versioned behavior.

## Artwork rules

- Preserve the full square source composition and its dark background.
- Resize without stretching or cropping the ordinary icon variants.
- Create maskable/adaptive variants with centered safe padding so iOS and
  Android launcher masks do not cut off the wordmark or slogan.
- Keep the existing PWA URLs, manifest entries, native config keys, and splash
  configuration stable.

## Validation

- Confirm every generated PNG has the expected dimensions, non-zero size, and
  valid image data.
- Confirm the PWA manifest and HTML continue to reference the four existing
  icon paths.
- Confirm native Expo config still resolves the icon and adaptive foreground
  assets.
- Run focused frontend PWA tests, mobile app-config tests, frontend build, and
  `git diff --check`.

## Error handling

There is no runtime failure path for icon delivery. Missing or invalid artwork
must fail during asset inspection or build validation rather than silently
falling back to a remote object.
