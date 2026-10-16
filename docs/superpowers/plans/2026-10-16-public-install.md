# Public installation page plan

Goal: a compact Persian-first dark installation page for Instagram visitors.
Design: existing logo and fonts, centered mobile column, persistent Android/iPhone SVG tabs, turquoise primary action. No new dependencies.

1. Verify the latest successful production APK from October 15: EAS history, manifest, production certificate, SHA-256. Preserve the artifact outside Git and frontend images.
2. Add OS-selected accessible tabs in PublicInstallPage.tsx and installEnvironment.ts; retain installed-state detection, real Chromium prompt, Safari steps, Instagram handoff and copy link. Store actions remain disabled until listings are verified.
3. Replace publicInstall.css with responsive dark/turquoise styling and reduced-motion support.
4. Test platform detection, tabs, PWA/clipboard behavior, narrow layouts and direct route SEO; run focused tests, TypeScript and production build.
5. Publish verified APK behind permanent /download/android using existing infrastructure only when access/release gates allow. Verify full public download hash.
6. Review scoped diff, commit and push current branch. Deploy only through the established enabled workflow; report any disabled release gate.

Review focus: iPad desktop mode, Instagram on both platforms, standalone mode, denied clipboard, absent install prompt, server prerendering, no invented store links.
