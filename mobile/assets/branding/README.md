# Fitician release artwork

The canonical source for current mobile branding is the repository-root
`../../../logo1.jpg`. It is an opaque 1254x1254 RGB JPEG with the Fitician mark
on a near-black square background.

The bundled PNG assets are generated from that source with aspect-preserving
LANCZOS resizing:

- `fitician-icon.png` preserves the full square composition at 1024x1024.
- `fitician-adaptive-foreground.png` centers the artwork at 60% canvas size
  for Android launcher-mask safe padding. Its `#010101` background matches
  the source's near-black corners.
- `fitician-brand.png` preserves the full square composition for in-app
  `BrandMark` headers.

`mobile/app.config.ts` keeps its stable icon paths. `fitician-splash.png` and
legacy vector references remain unchanged. The release PNGs contain no product
screenshots, user data, or third-party marks.
