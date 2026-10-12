# Selective regional release implementation plan

**Goal:** Merge the validated regional architecture and publish three exact-main-SHA
Docker Hub images while production CD remains disabled.

**Architecture:** Reuse a recent, successful, same-repository Full CI ancestor only
after verifying its run, complete job results, artifact SHA, ancestry and cumulative
changed paths. A narrow ops/CI/regional-Compose allowlist runs current ops/workflow/Compose,
security/dependency and regional HTTP checks; unknown or application changes retain Full CI.
Release gates recompute this evidence, and skipped required checks never count as success.

**Tech stack:** Existing GitHub Actions, Python classifier/release gate, Docker Buildx,
Docker Hub; no VPS, production database or external object-storage readiness dependency.

- [ ] Disable existing production workflows through GitHub before any merge; make every
  production deployment job unreachable in source and remove automatic CD triggers.
- [ ] Test and implement verified Full CI baseline discovery, selective classification
  and exact-SHA release proof. Preserve all complete suites and unknown-path fallback.
- [ ] Connect current ops, workflow lint, Compose, split HTTP smoke, dependency and secret
  checks to selected image publication. Remove object-store HEAD probes from image CI.
- [ ] Run local focused tests/lint and official branch selective CI. Push focused commits.
- [ ] Merge to main without rewriting history; verify final main CI and each published
  SHA image/digest, then confirm CD is still disabled. No SSH/deployment/migration.

Review focus: failed/skipped baseline jobs; fork/PR or expired evidence; non-ancestor or
application/dependency differences; forged selective plans; any reachable deployment job.
