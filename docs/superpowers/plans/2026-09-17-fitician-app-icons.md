# Fitician app icons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ] ) syntax for tracking.

**Goal:** Replace Fitician's Web/PWA, iOS, and Android installed/launcher icon artwork with the approved root logo.jpg while preserving existing paths and runtime behavior.

**Architecture:** Keep logo.jpg as the versioned local source and generate the existing PNG targets from it. Ordinary icons preserve the full square image; maskable/adaptive icons use centered safe padding. The frontend build and native binaries bundle the artwork; no backend route, database value, or Arvan S3 request is added.

**Tech Stack:** Vite PWA, Expo app config, PNG raster assets, Python Pillow for one-time generation, Vitest, Node test runner, TypeScript build.

**Spec:** docs/superpowers/specs/2026-09-17-fitician-app-icon-design.md

## Global Constraints

- Use the approved root image logo.jpg as the canonical local source.
- Preserve the full square source composition and its dark background.
- Resize without stretching or cropping ordinary icon variants.
- Create maskable/adaptive variants with centered safe padding.
- Keep existing PWA URLs, manifest entries, native config keys, and splash configuration stable.
- Change only install/launcher icon artwork; do not change the Web header, native BrandMark, or native splash artwork.
- Do not add S3, backend, database, runtime network, or dependency changes.
- Preserve unrelated dirty-worktree changes and stage only named task files.
- Never commit .env, credentials, API keys, or generated debug artifacts.

## File Map

- logo.jpg: approved canonical source image; add it to version control.
- frontend/public/pwa/icon-192.png: ordinary PWA icon at 192x192.
- frontend/public/pwa/icon-512.png: ordinary PWA icon at 512x512.
- frontend/public/pwa/icon-maskable-512.png: safe-area PWA maskable icon at 512x512.
- frontend/public/pwa/apple-touch-icon.png: iOS Web/PWA icon at 180x180.
- mobile/assets/branding/fitician-icon.png: ordinary native app icon at 1024x1024.
- mobile/assets/branding/fitician-adaptive-foreground.png: safe-area Android adaptive foreground at 1024x1024.
- mobile/assets/branding/README.md: source and generated-asset documentation.
- frontend/vite.config.ts and frontend/index.html: existing PWA consumers; verify only.
- mobile/app.config.ts: existing native icon consumers; verify only.
- frontend/src/test/viteProxyConfig.test.ts and mobile/scripts/appConfigPlatform.test.mjs: existing contracts; run only.

### Task 1: Generate the approved raster variants

Files:
- Read: logo.jpg
- Replace: frontend/public/pwa/icon-192.png
- Replace: frontend/public/pwa/icon-512.png
- Replace: frontend/public/pwa/icon-maskable-512.png
- Replace: frontend/public/pwa/apple-touch-icon.png
- Replace: mobile/assets/branding/fitician-icon.png
- Replace: mobile/assets/branding/fitician-adaptive-foreground.png

Interfaces:
- Consumes: square JPEG logo.jpg (1254x1254).
- Produces: six PNG files at the exact paths consumed by Vite PWA and Expo.

- [ ] Step 1: Confirm the source and target inventory.

Run from the repository root:

    file logo.jpg frontend/public/pwa/icon-192.png frontend/public/pwa/icon-512.png frontend/public/pwa/icon-maskable-512.png frontend/public/pwa/apple-touch-icon.png mobile/assets/branding/fitician-icon.png mobile/assets/branding/fitician-adaptive-foreground.png

Expected: logo.jpg is the approved 1254x1254 JPEG and all targets exist before replacement.

- [ ] Step 2: Generate ordinary and safe-area PNGs.

Run this exact one-time generator from the repository root. It preserves ordinary variants, uses the source corner color for the padded canvas, and scales safe-area variants to 70%:

    python3 - <<'PY'
    from PIL import Image

    source = Image.open("logo.jpg").convert("RGB")
    background = source.getpixel((0, 0))
    resampling = Image.Resampling.LANCZOS

    def save_full(path: str, size: int) -> None:
        image = source.resize((size, size), resampling)
        image.save(path, format="PNG", optimize=True, compress_level=9)

    def save_safe(path: str, size: int) -> None:
        inner_size = round(size * 0.70)
        inner = source.resize((inner_size, inner_size), resampling)
        canvas = Image.new("RGB", (size, size), background)
        offset = ((size - inner_size) // 2, (size - inner_size) // 2)
        canvas.paste(inner, offset)
        canvas.save(path, format="PNG", optimize=True, compress_level=9)

    save_full("frontend/public/pwa/icon-192.png", 192)
    save_full("frontend/public/pwa/icon-512.png", 512)
    save_safe("frontend/public/pwa/icon-maskable-512.png", 512)
    save_full("frontend/public/pwa/apple-touch-icon.png", 180)
    save_full("mobile/assets/branding/fitician-icon.png", 1024)
    save_safe("mobile/assets/branding/fitician-adaptive-foreground.png", 1024)
    PY

- [ ] Step 3: Inspect generated dimensions and file types.

Run:

    file frontend/public/pwa/icon-192.png frontend/public/pwa/icon-512.png frontend/public/pwa/icon-maskable-512.png frontend/public/pwa/apple-touch-icon.png mobile/assets/branding/fitician-icon.png mobile/assets/branding/fitician-adaptive-foreground.png
    test -s frontend/public/pwa/icon-192.png frontend/public/pwa/icon-512.png frontend/public/pwa/icon-maskable-512.png frontend/public/pwa/apple-touch-icon.png mobile/assets/branding/fitician-icon.png mobile/assets/branding/fitician-adaptive-foreground.png

Expected: 192x192, 512x512, 512x512, 180x180, 1024x1024, and 1024x1024; all are non-empty PNGs.

### Task 2: Align branding asset documentation

Files:
- Modify: mobile/assets/branding/README.md

Interfaces:
- Consumes: generated native PNG names from Task 1.
- Produces: documentation identifying logo.jpg as the source and recording that splash artwork is unchanged.

- [ ] Step 1: Update the README.

State that ../../../logo.jpg is the canonical source for current icon PNGs, ordinary and adaptive PNGs have different safe-area treatment, existing SVGs are not the current Expo input, and fitician-splash.png remains unchanged for this icon-only task.

- [ ] Step 2: Review only the documentation diff.

    git diff -- mobile/assets/branding/README.md

Expected: only the source/generation description changes.

### Task 3: Verify all Web and native consumers

Files:
- Verify: frontend/vite.config.ts
- Verify: frontend/index.html
- Verify: frontend/src/test/viteProxyConfig.test.ts
- Verify: mobile/app.config.ts
- Verify: mobile/scripts/appConfigPlatform.test.mjs

Interfaces:
- Consumes: six generated PNGs from Task 1.
- Produces: evidence that existing manifest, HTML, and Expo paths resolve the new artwork without a runtime storage dependency.

- [ ] Step 1: Run the focused frontend PWA contract test.

From frontend/:

    npm run test -- --run src/test/viteProxyConfig.test.ts

Expected: PWA identity and stable icon paths pass.

- [ ] Step 2: Run the focused native config test.

From mobile/:

    npm run test:foundation -- scripts/appConfigPlatform.test.mjs

Expected: Android preview and development config checks pass.

- [ ] Step 3: Build the frontend.

From frontend/:

    npm run build

Expected: TypeScript and Vite build complete and include the PWA icon files at their existing public paths.

- [ ] Step 4: Check the final scoped diff.

From the repository root:

    git diff --check
    git status --short

Expected: no whitespace errors; unrelated WIP remains untouched.

### Task 4: Commit and push the completed icon change

Files:
- Add: logo.jpg
- Add/replace: six generated PNGs from Task 1
- Modify: mobile/assets/branding/README.md

Interfaces:
- Consumes: verified artwork and documentation from Tasks 1-3.
- Produces: one focused commit on the current branch and a pushed remote branch.

- [ ] Step 1: Stage only the approved icon files.

    git add logo.jpg frontend/public/pwa/icon-192.png frontend/public/pwa/icon-512.png frontend/public/pwa/icon-maskable-512.png frontend/public/pwa/apple-touch-icon.png mobile/assets/branding/fitician-icon.png mobile/assets/branding/fitician-adaptive-foreground.png mobile/assets/branding/README.md

- [ ] Step 2: Inspect the staged file list.

    git diff --cached --stat
    git diff --cached --name-only

Expected: exactly eight paths: logo.jpg, six PNGs, and mobile/assets/branding/README.md.

- [ ] Step 3: Commit the behavior change.

    git commit -m "feat(branding): use approved logo for app icons"

- [ ] Step 4: Push the current branch.

    git push origin main

Expected: the focused commit is accepted without force-push or history rewrite.
