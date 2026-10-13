# Regional cutover preparation checklist

Status: preparation only. Iran currently has domestic Internet access only. Do not
attempt VPN enrollment/tunnels, DNS changes, source freeze, service stops, target
consumer startup, or volume removal as part of this preparation. The Netherlands
source `mohammad@141.11.0.99` remains live and authoritative. The default dry-run commands do not contact hosts or providers. Only the explicit
guarded `restore-plan --execute` path connects to the isolated Iran restore container;
it never freezes source writes, deploys services, changes DNS, or deletes volumes.

The local helper prints commands for later operator review, hashes local encrypted
artifacts, plans a pinned HTTPS probe and Cloudflare record patches, and validates a
sanitized JSON evidence manifest. It does not connect to Cloudflare/Tailscale or
execute a restore by default. Explicit restore execution targets only a verified
isolated `fitician-*-restore-*` container. The operator must build and verify that isolated target
before using the emitted pipeline.

## Isolated runtime guard

Run only on Iran with a dedicated mode-0600 rehearsal env and `REHEARSAL_ID`.
`python3 ops/rehearse-regional.py config --env-file <rehearsal.env>` checks the
real Compose render and capacity without starting services. `start` uses the
explicit project `fitician-offline-rehearsal`, overriding even a production
`COMPOSE_PROJECT_NAME`; it refuses non-synthetic database URLs, non-rehearsal
volumes, external networks, public bindings and insufficient memory/CPU budgets.
It uses `--pull never`, never deletes volumes and never contacts the source or DNS.
Provision fresh QA volumes, the isolated TLS copy and env before calling it. Do not
run an ad hoc Compose invocation with a production env and only the overlay.

## Prepared dry-run interface

```sh
python3 ops/regional-cutover.py plan
python3 ops/regional-cutover.py inventory --manifest 'sanitized-evidence.json'
python3 ops/regional-cutover.py integrity --file 'snapshot.dump.age' --sha256 'expected-sha256'
python3 ops/regional-cutover.py restore-plan --identity-file 'secure-key-path' --encrypted-file 'snapshot.dump.age' --expected-snapshot 'snapshot.json' --sha256 'expected-sha256' --restore-container 'fitician-regional-restore-run-id'
python3 ops/regional-cutover.py https-plan --address 'verified-target-ipv4'
python3 ops/regional-cutover.py dns-plan --snapshot 'sanitized-cloudflare-zone.json' --target-ipv4 'verified-target-ipv4'
python3 ops/regional-cutover.py validate --action cutover --manifest 'final-evidence.json'
python3 ops/regional-cutover.py validate --action rollback --manifest 'post-write-evidence.json'
python3 ops/regional-cutover.py dns-rollback-plan --manifest 'post-write-evidence.json' --before 'pre-cutover-zone.json' --current 'current-zone.json'
```

`inventory` displays only selected fields from a local manifest and makes no network
calls. `integrity` streams the local file and compares its SHA-256. The production
backup script verifies both uploaded size and a downloaded ciphertext SHA-256 before
it reports success. Final sync also runs `ops/final-database-snapshot.py`; it refuses
to dump unless the six listed writer IDs are stopped and source DB, Redis and Agent
remain running. It exports one repeatable-read, read-only PostgreSQL snapshot and
records all public-table counts, selected row fingerprints and Alembic revision from
that same snapshot as the dump. The metadata is separately age-encrypted before
upload. `restore-plan` only
prints an age-to-`pg_restore` pipeline by default. `--execute` requires
`--confirm-target` to exactly match the container name and runs remote preflight before
restore. It requires the fixed `iran` SSH alias, a local mode-0600 age identity, a
matching encrypted-file SHA-256, an inspectable `fitician-*-restore-*` container using
the exact Postgres 18 image and digest pinned in `compose.prod.iran.yaml`, Docker network mode `none`, no published ports, exactly one dedicated
`fitician_*_restore_*` data volume attached only to that container, and zero public
tables. After restore, it compares the complete public table inventory and every table
count to the snapshot; row fingerprints remain the selected subset recorded there.
This rejects the known production-volume naming scheme and any currently shared volume.
The archive streams from local `age` to destination `docker exec`; the
identity file never leaves the local host. Restore uses `pg_restore --single-transaction
--exit-on-error --no-owner --no-acl`, then compares every expected table count,
fingerprint, Alembic revision and unvalidated-FK count from the sanitized snapshot.
The helper never creates or deletes volumes. The target must be a newly prepared,
isolated restore container with no published ports. `https-plan` prints a `curl
--resolve` command and does not run it. `dns-plan` accepts a sanitized Cloudflare zone
snapshot shaped as `{"zone":"fitician.fit","records":[...]}` with provider record
IDs, produces patches only for changed A records at the apex, `api`, or `www`, rejects
unexpected AAAA/record layouts, and never writes. It
preserves `www` CNAME and unrelated mail/verification records. The older authoritative
DNS lookup artifact lacks Cloudflare record IDs and is intentionally insufficient as
input to `dns-plan`. `dns-rollback-plan` requires an explicit `writes_started` state and,
after writes, both freeze and reconciliation attestations. It compares before/current
record IDs and emits only changed owned-record patches; it does not call Cloudflare or
reconcile application data.

The manifest must contain no secrets, personal data, tokens, or environment contents.
Record secure-file paths only. Cutover validation requires `mode: "final"`; rehearsal
evidence cannot be promoted. Application CI must pass on the exact full candidate SHA, include a run ID, and
be no older than seven days. For `candidate_type: "stable-config"`, CI must match
`stable_application_sha`; the configuration candidate SHA is separate, and the
previously qualified unchanged application image can reuse older CI evidence. Boolean evidence fields remain operator
attestations: the helper checks consistency, SHA values and optional local artifact
bytes, but it cannot authenticate live-provider claims or establish current readiness.
Rollback requires an explicit `writes_started` boolean; after `true`, both
`target_writes_frozen` and `reconciliation_complete` are required.

## Gates and operator sequence

1. **External dependency and destination qualification — blocked now.** From an
   authorized Iran context, qualify authenticated private Iran-to-Germany Agent HTTPS,
   upload, provider paths, failover, public HTTPS, renewal, time/DNS, and actual enabled
   user operations. Iran currently has domestic access only; do not attempt a VPN now.
   Obtain the required authorized network and DNS administration access before any
   cutover sequence. Preserve current application/provider credentials.
2. **Read-only inventory.** Recheck source identity, running container IDs, image tags,
   health, PostgreSQL/Redis state, Agent volume attachment, DNS records, destination
   volumes, certificate and disk. Record the exact current API and four consumer IDs
   (food-photo, body-analysis, notification, scheduler). Inventory must confirm the
   original PostgreSQL, Redis, Agent service and Agent home volume are present and
   healthy. Never infer IDs or volume names from an old snapshot. Record exactly the
   current IDs for `backend`, `backend-2`, `food-photo-worker`, `body-analysis-worker`,
   `notification-worker`, and `scheduler`; the cutover gate rejects missing/extra IDs.
3. **Freeze and final snapshots.** Only in a separately approved cutover window,
   drain ingress and freshly inventory source container IDs and service labels. Stop
   the two verified API IDs with a 60-second grace period, then confirm both have
   exited before stopping the four verified consumer IDs with up to 450 seconds for
   in-flight jobs to finish. Confirm all six have exited. The `plan` command prints
   this ordered, non-executing sequence. Keep source PostgreSQL, Redis and Agent
   service/volume intact; do not remove volumes or run `down -v`. Stop new Agent
   auth/config writes through a reviewed access-drain procedure while keeping the
   Agent service and original home volume present. Capture fresh encrypted PostgreSQL
   and Agent snapshots after their writers are quiescent. Use the existing
   `ops/backup-production.sh` for the PostgreSQL encrypted upload path. The backup
   command in `plan` reuses this script without sudo. Create a mode-0600 freeze
   manifest from the just-verified IDs and stopped states; include `source_host`,
   `ingress_drained`, `freeze_complete`, `frozen_container_ids`, and
   `preserved_services` as required by `ops/final-database-snapshot.py`. Run with
   `FINAL_SYNC=1 FINAL_FREEZE_MANIFEST=<path>` so the helper validates those IDs
   against live Docker state before exporting the final snapshot. The helper never
   stops containers. Download the encrypted `.snapshot.json.age` companion and
   decrypt it locally for the `restore-plan --expected-snapshot` input.
   Verify local
   and remote SHA-256 with `integrity`, then run `restore-plan` without `--execute` to
   review the isolated database restore checks and command pipeline. For a later
   explicitly authorized QA restore, add `--execute --confirm-target <exact-container>`.
   Restore the Agent snapshot with its separately
   reviewed procedure. The printed database pipeline does not create or inspect its
   target; the operator must verify the restore container is isolated and disposable.
   Restore both snapshots into isolated destination volumes and compare table counts,
   selected fingerprints, Alembic head, Agent auth files, ownership and modes. The
   existing historical restore evidence is preliminary and is not final-freeze
   evidence. This kit does not provide an Agent restore workflow; do not improvise a
   production command from this checklist.
4. **HTTPS and runtime readiness.** Complete candidate deployment only through the
   reviewed `ops/deploy-regional.sh` workflow after all external gates pass. Keep target
   consumer startup and user writes disabled until the cutover decision. Run
   `ops/verify-regional.sh`, separate restored-data validation, TLS hostname/chain/
   renewal checks, authenticated Agent uploads, and controlled application acceptance.
   Require one active writer and one consumer set only.
5. **DNS write set.** Immediately before writes, query both authoritative nameservers
   and capture the current records. Change only the records demonstrably owned for this
   service: apex `@` A/AAAA, `api` A/AAAA, and `www` CNAME or its existing owned
   equivalent. Preserve MX, mail-related TXT, verification TXT, NS, and every unrelated
   record. Do not add AAAA without a verified working IPv6 ingress. Compare the full
   post-change zone view and verify propagation plus real Web/mobile/API operations.
   `dns-plan` can prepare a Cloudflare patch list from a fresh sanitized read-only zone
   export, preserving record IDs, TTL and proxy mode for changed A records. It does not
   call Cloudflare or apply patches. Record IDs, target IP and proxy behavior must be
   freshly verified by an authorized DNS operator.
6. **Rollback.** Before target writes begin, an approved DNS return can point these
   same owned records to the retained source after source health is checked. After any
   target write, DNS-only rollback is unsafe: freeze target writes and consumers, take
   a fresh encrypted target snapshot, reconcile every changed domain/table/queue and
   Agent auth state, restore/replay that data to the chosen authority, validate it,
   then approve DNS return. Keep source volumes and backups throughout. This helper
   blocks post-write rollback evidence unless freeze and reconciliation are both true.

## Evidence manifest contract

Use booleans and hashes from fresh, attributable evidence; do not copy `true` from
older rehearsal artifacts. Keep the manifest sanitized:

```json
{
  "mode": "final",
  "candidate_type": "application",
  "candidate_sha": "dddddddddddddddddddddddddddddddddddddddd",
  "ci": {
    "passed": false,
    "commit_sha": "",
    "run_id": "",
    "completed_at_utc": ""
  },
  "source": {
    "host": "mohammad@141.11.0.99",
    "live_preserved": true,
    "preserved_services": {"postgres": true, "redis": true, "agent": true},
    "frozen_container_ids": {
      "backend": "",
      "backend-2": "",
      "food-photo-worker": "",
      "body-analysis-worker": "",
      "notification-worker": "",
      "scheduler": ""
    }
  },
  "evidence": {
    "external_network_authenticated": false,
    "destination_https_dns_ready": false,
    "source_writes_frozen": false,
    "all_writers_drained": false,
    "agent_writes_quiesced": false,
    "database": {
      "encrypted": false,
      "sha256": "",
      "expected_sha256": "",
      "restore_verified": false,
      "data_validation_passed": false
    },
    "agent": {
      "encrypted": false,
      "sha256": "",
      "expected_sha256": "",
      "restore_verified": false,
      "auth_validation_passed": false
    }
  },
  "dns": {"owned_records_only": ["@", "api", "www"]},
  "writes_started": false,
  "rollback": {"target_writes_frozen": false, "reconciliation_complete": false}
}
```

For a configuration-only candidate that reuses an already-built application image,
set `candidate_type` to `stable-config` and provide `stable_application_sha`. CI must
match that exact application SHA; its age is not used as the freshness clock for the
configuration candidate. Application candidates still require CI within seven days.
This is manifest consistency checking, not independent proof that the image or CI run
is the one currently deployed.

The template deliberately starts blocked. Never store key material, passwords, bearer
tokens, env contents, or private user data in it. Report key-file and env-file paths
only in the operator's separately controlled records.
