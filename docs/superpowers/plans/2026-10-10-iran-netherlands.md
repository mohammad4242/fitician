# Iran and Netherlands implementation plan

**Goal:** Independently deploy the Iran application and Netherlands Agent without changing client or provider contracts.
**Architecture:** Separate standalone Compose contracts, host Tailscale Serve ingress, existing bearer token and multipart image transport. Legacy single-host and development configurations remain available until owner-approved cutover.
**Spec:** `docs/iran-netherlands-architecture.md`

## Constraints
- No live deployment, DNS edits, credential rotation, database migration or main push.
- No shared private media or S3 secrets on Netherlands; preserve existing Agent home volume by explicit external name.
- Independent rollback; Iran health must not depend on Netherlands.
- Immutable full Git SHA images and existing CI evidence gates.

## Review focus
- Failed backup must block Iran rollout.
- Failed Agent rollout must touch only Netherlands.
- Schema changes prohibit automatic image-only rollback.
- Actual Docker-to-Agent connectivity and multipart upload, without cross-region media mounts.
- Interrupted requests retain durable retry/lease semantics and bounded attempts.

## Tasks
- [ ] Audit all runtime/HTTP/queue/external dependency/release contracts; verify current Git and local services.
- [ ] Write failing regional topology/capacity tests; add standalone regional Compose and operator environment examples; validate rendered service placement, private ports, external volumes, CPU/RAM limits.
- [ ] Add regional deployment and verification scripts/workflow with executable failure tests; preserve legacy CI and component gates.
- [ ] Add isolated two-network simulation and remote provider regression tests; execute actual HTTP/auth/image transport and Agent-down replica smoke.
- [ ] Run focused provider, admin, queue, Agent and ops tests. Review delegated diffs and final combined diff.
- [ ] Document network gates, direct WireGuard fallback, registry transfer, backups/restore, staged cutover/rollback and exact limitations.
- [ ] Commit reviewed work on feature branch and push only that branch.
