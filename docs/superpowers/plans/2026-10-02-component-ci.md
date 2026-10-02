# Component CI Implementation Plan

Goal: select one safe validation and release path for each change.
Architecture: central CI router, reusable component workflows, isolated serialized CD.
Spec: docs/superpowers/specs/2026-10-02-component-ci-design.md

Global constraints: retain current full gates, exact immutable SHAs, backup/migration
approval, SSH host pinning, environment protection, health checks, and rollback.
Use main directly as requested; preserve unrelated untracked files; no subagents.

- [x] Test classifier examples, mixed paths, worker imports, unknown/deleted paths.
- [x] Implement conservative classifier and backend suite selection.
- [x] Test component tag isolation and rollout/rollback failures.
- [x] Implement component deploy script and mixed-tag full rollback.
- [x] Refactor frontend workflow; add reusable backend validation/image workflow.
- [x] Route CI paths exclusively; add nightly; remove obsolete mobile-resume bypass.
- [x] Gate CD on exact run evidence; retain full release approval gates.
- [x] Document operations; run classifier/script/Compose/YAML/actionlint checks.
- [ ] Commit/push; monitor exact-SHA full CI and production gates; fix root causes.

Review focus: cancelled predecessors, mixed rollback, pending schemas, worker consumers,
manual high-risk component dispatch, scheduled deployment, and duplicate releases.

Local evidence: 80 ops/classifier/release tests pass; workflow YAML, shell syntax,
Compose contracts, and quality baseline comparisons pass. Actionlint 1.7.12
requires one narrowly scoped exception for GitHub-supported concurrency queue:max.
