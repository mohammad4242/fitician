# Debugging release audit — November 23, 2026

## Authority and immutable baseline

The owner authorizes review, protected-main integration and production deployment after all
existing safeguards pass. No protection bypass, direct main push, paid upgrade, destructive
cleanup, automatic SMS activation or unverified migration is authorized.

- Initial PR41: head `680d997294fe8ffce9e6becaa3dbac6c40208736`, base
  `7c03e50d0355d3f28b87559af4c6f5d46d5ff7e2`; 337 files, 113 commits.
- All four file pages and both commit pages were fetched; counts matched GitHub. Main is an
  ancestor of the feature head, with no main-only commits. Unrelated local changes in
  `agent-tailscale-operations.md` and `iran-germany-architecture.md` are preserved.
- Main requires up-to-date `Required CI` from GitHub Actions, with admin enforcement and no
  force pushes. Required approving review count is zero. Production full/Agent releases have
  a separate `production-owner-approval` Environment reviewer; it must not be self-bypassed.
- Automatic CD was found enabled. Only `REGIONAL_AUTO_CD_ENABLED` was set to false, as
  explicitly requested. Manual CD and all branch/Environment gates remain intact.

## Scope separation

Two independent fixes are excluded from PR41's final source diff and preserved as Draft PRs:

- [PR44](https://github.com/mohammad4242/fitician/pull/44): quota timestamp after the user lock;
  15 tests passed against isolated PostgreSQL using the original-main application schema.
- [PR45](https://github.com/mohammad4242/fitician/pull/45): public pagination hydration;
  9 focused frontend tests passed. Its delayed-script browser test remains with that fix.

Fresh clones now ignore the entire root `.codex-tmp/`, including connector state and release
evidence, without depending on an operator-only `.git/info/exclude`. An isolated Git
repository regression failed before this correction and passed afterward. No private files
were staged or removed.

The existing public-browser wait-for-response correction remains in PR41 because the full
cross-browser release suite must wait for the fixture refresh before navigation cancels it.
This changes test synchronization, not coverage or application behavior. A food-photo test's
assertion adds an error code on failure without changing its expected outcome.

The readiness threadpool correction is retained because diagnostic writers use the bounded
connection pool; health checks must not block the event loop while waiting for that pool.

Generated OpenAPI/shared contracts, pinned Sentry dependencies, the documented CommonJS
security-fixed decoder compatibility archive, native symbol configuration, backup fixes,
release/observation/validation guards and regression tests are feature dependencies retained
for review. Historical independent-runtime code is retained for compatibility; Option A still
uses the existing Agent Service for AI and the laptop for repository execution.

## Critical workflow and trust-boundary review

Both trusted debug workflows now pin every third-party action to a verified full commit SHA,
and all their checkouts disable persisted GitHub credentials. This follows the official
[GitHub secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use).

`debug-validation.yml` checks exact 40-character candidate identities, canonical UUIDs and
fixed allowlisted profiles/test paths. Trusted policy and candidate checkouts are separate;
credentials are not persisted. Policy builds dependencies; candidate code runs as UID10001 in
read-only, capability-dropped, resource/time/output-bounded containers, without host Docker,
provider credentials or production data. Frontend/Agent tests have no network; backend tests
use a dedicated ephemeral PostgreSQL network. Results publish bounded structured facts, not
raw candidate logs. The broker checks workflow/repository/policy identity, candidate SHA,
artifact name/size/SHA256/content and tested image before authorizing publication.

The broker first requires policy on protected main, pins it with an immutable checked tag,
rejects stale main-based repairs, reconciles uncertain mutations, detects duplicate workflow
runs and reuses an existing Draft PR for the same immutable validation. Publishing requires a
separate occurrence-bound administrator action. Neither tool output nor issue text can grant
publication or deployment authority.

`debug-server-observation.yml` runs only from main, validates the immutable policy SHA and
closed target/trace inputs, uses region-specific Environment credentials and strict host pins,
and runs a fixed read-only collector. It does not accept a model-provided command. Observation
artifacts retain their digest/provenance and cannot establish business resolution.

## Broker-only release boundary

The previous `debug_runtime` path always selected the legacy inference connector alongside
GitHub automation. Unified Option A now uses the same owner-gated regional workflow with
`deploy_kind=debug_runtime`, `automation_only=true`, `image_source=preloaded`. It replaces only
`automation`, including only that service's new resource allocation while preserving and
budgeting all other containers. It does not install or authenticate another AI environment.

The broker has its own active-contract marker and component receipt under
`releases/<sha>/automation/`. Legacy connector releases remain separate. A later combined
legacy rollout fails closed rather than assuming both components share a rollback image.
First-enrollment rollback stops only the new broker; it never passes an empty service list to
Compose (which would start unrelated services). An actual hosted smoke at candidate `b991492f` failed before rollout because the unprivileged
CI operator could not traverse the worker-owned0700 directory. Preflight now uses a bounded,
networkless64MiB container running as10001:10001 with a read-only credential mount. It opens
only the two fixed files to check regular-file type, exact0600 mode/ownership and readability;
it never reads their contents. A real Docker regression passed for valid private files and
rejected0644 permissions and symlinks. The production permissions were not relaxed.

All original owner, immutable image, archive,
concurrency,3072MiB-plus-transfer, memory and authentication-volume guards remain.

The existing actual Docker rollout/rollback smoke now also exercises broker-only replacement,
idempotent replay and rollback while checking the legacy connector's identity. Publication
requires those additional proof flags. Empty isolated fixture configuration deliberately tests
liveness without claiming provider authentication or enrollment. A real local Docker probe
also confirmed that the host cannot write UID10001 private directories and that the fixture
creates both0600 files as10001:10001, without extra capabilities. The existing CI already
stops its own Buildx builder before exercising production resource guards. Hosted execution remains a
fresh-CI gate; unit tests alone do not establish live broker deployment.

The stateless Agent Service can be updated first. Broker registration and the selected laptop's
production enrollment require the new Iran API/schema, so their activation follows that API
rollout. CLI authentication remains in the existing Agent Service volume throughout.

Hosted run45219967334 exposed a further broker-only startup defect: an unquoted YAML flow
sequence split the `/tmp` mount options into four mounts. Compose rejected the invalid mount
before a broker process started. The fixed contract quotes the entire mount string; an actual
`docker compose config` regression failed with four entries before correction and now verifies
one private16MiB mount. Release failures emit only closed operation/error families and bounded
container health fields, never arguments, environment values or probe output. Observer failure
cannot prevent rollback. Exported failed-smoke images are retained for investigation, but a
failed run still cannot produce a valid release manifest or pass the deployment gate.

## Pending schema review (175 to 187)

| Revision | Upgrade behavior |
| --- | --- |
|176 | New immutable evidence and external-correlation tables/indexes |
|177 | Expand the AI task check constraint; no default model or row inserted |
|178 | New conversation/run/event tables and active-run uniqueness |
|179 | Nullable sanitized source-evidence column |
|180 | New connector/call/probe tables |
|181 | New alert delivery/attempt audit tables |
|182 | Relax probe actor nullability and preserve audit on account deletion |
|183 | Nullable execution-target FK, limited to the debugging task |
|184 | Connector kind and durable operation tables/constraints |
|185 | Expand operation kind for read-only observations |
|186 | New native-discovery cursor table |
|187 | Expand operation kind for controlled replay |

All upgrades set a bounded DDL lock timeout. No upgrade deletes existing rows or removes a
business column. Constraint expansion can still require a short table lock; timeout must abort
rather than be increased silently. Downgrades can destroy new evidence and several correctly
refuse when provenance exists: prefer compatible application roll-forward, not data deletion.

Before any live migration, obtain a fresh encrypted consistent snapshot, verify S3 readback,
restore into networkless tmpfs PostgreSQL, compare protected fingerprints/all existing counts
and foreign keys, then rehearse these exact migrations. Production remains at175 until this
and the region/runtime gates pass. An old pre-feature SQL enum cannot load a saved debug task;
image-only rollback to that application is not assumed safe after debug configuration exists.
Activate debugging only after the new application is healthy; retain a compatible release and
use a reviewed roll-forward after configuration/audit is in use. Any database restore requires
an explicit write-freeze/reconciliation procedure to avoid losing subsequent user writes.
The existing regional failure guard stops application writers after a schema-changing failure;
it does not automatically revert the schema or assume old-image compatibility. That guard is
retained. Its availability/recovery procedure must be accepted before any live cutover.

## Fresh production observations

Both region observations used existing pinned SSH identities without changing destinations.

| Region | CPU | Available RAM | Free root disk | Application state |
| --- | --- | --- | --- | --- |
| Iran |2 |1507 MiB |9768 MiB | Existing API/web/DB/Redis/workers healthy; schema175 |
| Germany |1 |1314 MiB |2153 MiB | Existing Agent Service healthy; restart count0 |

These are instantaneous measurements, not peaks or a sum of configured limits. Previous
container images and authentication volumes remain intact. Older images without verified
revision labels retain unknown source provenance rather than being relabeled from main.

Germany fails the unchanged3072MiB runtime guard before archive transfer overhead. No image,
volume, backup, persistent file or authentication cache has been removed. Exact candidate
layers and a separately owner-approved storage plan are required before rollout can proceed.

## Acceptance ledger

- [x] Fetch complete initial PR inventory, commits, exact-head checks and protection rules.
- [x] Preserve unrelated work and isolate the two independent product fixes.
- [x] Disable automatic CD without disabling manual owner-gated release.
- [x] Recheck all existing regional service health and original production schema.
- [x] Broker-mode and action-pin regressions observed failing before correction.
- [x] Local release checks:435 ops tests,410 focused backend tests (3 explicit local skips),
  1397 frontend tests, OpenAPI, actionlint, Ruff and secret checks.
- [ ] Fresh exact-head CI and actual broker rollout smoke after release hardening.
- [ ] Merge normally; verify trusted workflows and full CI on actual merged main.
- [x] Fresh encrypted snapshot/S3 readback verified; isolated restore and175→187 rehearsal
  preserved155 existing table counts and11 protected fingerprints, with all FKs valid.
  Result:169 tables. No plaintext backup file, application execution or production mutation.
  Refresh the snapshot if cutover is delayed beyond the existing release freshness guard.
- [ ] Resolve Germany capacity with separate owner approval; no deletion assumed.
- [ ] Deploy exact tested images, enroll workers/connectors, verify live panel workflow.
  The saved Germany broker credential matches the authorized local credential, has0600 mode
  and10001:10001 ownership, and repository/Actions/PR reads returned200. Its production
  `worker.json` is absent; enrollment follows the new Iran schema/API, without copying AI auth.
- [ ] Production Sentry/model/repair/CI/PR acceptance; SMS stays disabled.

Private evidence is under ignored `.codex-tmp/main-integration/`. No credential, raw production
row, private source context or raw production log is included in this document.
