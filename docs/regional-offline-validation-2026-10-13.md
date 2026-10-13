# Regional offline validation — 2026-10-13

Completed with two Luna agents and root review. Production Netherlands, DNS,
primary volumes and existing credentials were not changed. No Full CI was
manually dispatched. Changes are on `ops/regional-offline-completion-20261013`;
main was not modified. This is preparation, not production cutover acceptance.

## Current verification

- 203 Ops tests passed: manual-only workflow/CD safety, SSH 9011, exact repository
  and SHA checks, digest pins, rollback baseline availability, unchanged/changed
  Agent auth rollback, snapshot/freeze guards, encrypted upload/download SHA
  verification, isolated restore/DNS rollback gates, and rehearsal storage/host guards.
- Real isolated split Docker simulation passed 46 focused Backend tests. Authenticated
  HTTP/multipart requests, private image cleanup and Agent outage/recovery passed;
  both API replicas remained healthy during Agent outage. This uses a fake Agent
  runner, not vendor qualification or real Iran-to-Germany network acceptance.
- Root directly reran `ops/rehearse-final-sync.py --run-id root-20261013-final`.
  It calls the production `execute_snapshot` pipeline against a unique Compose
  PostgreSQL 18 database with network disabled and no published ports. An exported
  repeatable-read/read-only snapshot supplied both metadata and pg_dump; age
  encryption/decryption and transactional pg_restore passed. All four synthetic
  tables, two fingerprints, Alembic and zero unvalidated FKs matched. The generated
  metadata passed the existing restore validator. Source freeze-state verification
  is substituted only inside the QA process after isolation checks, and independently
  regression-tested; no real source writer was frozen. QA containers/volumes and
  temporary identity/archive were cleaned. The private age identity stayed local.
- Ruff passed for all Python files changed in this task; ShellCheck passed at warning
  severity; workflow actionlint passed with only its known unsupported existing
  `concurrency.queue` schema diagnostic excluded. `git diff --check` passed.
  Unchanged Ops files retain pre-existing findings under the stricter root Ruff
  configuration; no repository-wide clean-lint claim is made.
- Fresh read-only Iran audit: ten rehearsal services running, all nine configured
  Docker healthchecks healthy, zero OOM/restarts. Actual rendered config passed the
  strengthened validator: internal network, dedicated volumes, no host namespaces/
  privileges/devices, reviewed read-only config binds, loopback-only ports and
  synthetic database. Caps total 3,136 MiB and 2.95 CPUs on a 3,916 MiB/two-CPU host;
  about 2,192 MiB was available at the first sample. These are bounded snapshots,
  not sustained load acceptance.
- Germany rehearsal Agent healthy with zero OOM/restarts; network internal, no public
  Docker port, read-only root filesystem and all capabilities dropped. Loopback
  health returned 200; unauthenticated capabilities returned 401. First sample:
  156.1 MiB / 448 MiB, CPU 0.26%, host available 1,427 MiB. Existing host ports
  443/2096 were preserved; this is not a public/private ingress qualification.
- A real Docker permission probe found that a UID-zero process with all capabilities
  dropped cannot read Agent-owned 0600 auth files. The inventory now uses the image
  user. The actual shell function passed twice on a dedicated synthetic auth volume
  with unchanged digest; no production auth volume was mounted.
- The unrelated local APP_ENV=local notification Worker had a stale 96 MiB Docker
  cap and repeated OOM/restarts. Raising that runtime cap to 256 MiB restored
  healthy operation at about 172 MiB; no further restart occurred during observation.
  No application code or Netherlands Worker settings were changed.
- Read-only Netherlands inspection: all eleven services running and ten configured
  healthchecks healthy; age/aws/python3/docker available. Nothing was transferred,
  restarted or frozen there.
- Created GitHub `production-iran` and `production-germany`, set and read back four
  non-secret variables in each. Existing `Production` and repository secret values
  were untouched. Regional workflow remains `disabled_manually` in GitHub; source
  now supports only an owner-approved manual dispatch after successful validation.

## Retained sanitized evidence

`.codex-tmp/regional-completion/ops-tests-final.log`, `split-test.log`,
`root-20261013-final.evidence.json`, `root-final-sync.log`, `runtime-audit.json`,
`rehearsal-validation.json`, `auth-inventory-permissions.json`, and
`github-references.json`. These are local,
ignored artifacts and are not committed. They contain no real secret values.

## Owner and future execution gates

See [operator settings](regional-offline-operator-settings-2026-10-13.md) for exact
Secrets/Variables, panel paths and Cloudflare permissions/settings. Reviewer/branch
protections and SSH secrets still need owner input. Deployment is still disabled
in the GitHub panel. International connectivity, private WireGuard/TLS, enabled
external integrations, final release SHA validation/images, public ingress/certificate
renewal, sustained capacity and physical Android acceptance remain future gates.
Neither synthetic tests nor old snapshots satisfy those gates. Final freeze and
cutover require a new authorized window; original data/auth volumes and backups
must remain retained. Changed Agent auth refuses automatic image rollback and
requires encrypted-auth recovery. No automatic DNS or post-write data rollback
was executed or claimed.
