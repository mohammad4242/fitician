# Fitician release artwork

The canonical source for the current installed and launcher icon is the
repository-root `../../../logo.jpg`. It contains the full Fitician mark,
wordmark, and `Fit with Science` slogan on a dark square background.

The PNGs used by `mobile/app.config.ts` are generated from that source:

- `fitician-icon.png` preserves the full square composition.
- `fitician-adaptive-foreground.png` preserves the same composition inside a
  centered safe area for Android launcher masks.

The existing SVG files are legacy vector references and are not the current Expo
input. `fitician-splash.png` remains unchanged because this rollout changes
installed and launcher icons only. The release PNGs remain free of product
screenshots, user data, and third-party marks.
