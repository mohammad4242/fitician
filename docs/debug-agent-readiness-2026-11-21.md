# Debug-agent readiness: owner decisions and remaining gates

No production deployment, database migration, service restart, automatic SMS activation,
mobile store release, VPS purchase or resize is authorized by this readiness record.
PR 41 stays Draft and unmerged. Historical acceptance PRs 42/43 must not be merged.

## Dedicated GitHub credential

The existing local secure store is `.codex-tmp/sentry-setup/github-automation-credential.json`.
It is excluded from Git, mode 0600. The exact same credential was provisioned, without
overwriting another credential, at the existing Germany runtime's
`/opt/fitician-debug-runtime/automation-private/github.json` (UID 10001, mode 0600).
Repository authentication from Germany returned 200. No service was started or restarted.
The automation `worker.json` and runtime `connector.json` are still absent: credential
installation alone does not enroll a production worker or connect the panel.

The local credential file was last modified November 20 at 11:42 UTC. On November 21,
both the local process and Germany read the same secure credential and attempted the
reviewed, read-only `diagnose-regional-ssh.yml` dispatch on main. Both returned 403,
`Resource not accessible by personal access token`, requiring `actions=write`; rate
limits were not exhausted. This rules out a stale credential in an already running
Germany broker: no enrolled broker exists yet. It does not prove which token was
edited in the owner's GitHub Settings. No broader credential was substituted.

The owner must save **Actions: Read and write** on the specific fine-grained PAT
represented by this secure file, resource owner `mohammad4242`, selected repository
**only `fitician`**. If a different token was edited, replace only this secure credential
file locally; never paste it in chat. Repository-selection details cannot be established
from public repository reads alone. No connected GitHub Settings browser was available;
the REST API cannot edit this personal token's grant. Workflows write and Administration
are not needed for dispatch. [Official dispatch permissions](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event).

## Iran capacity and current public prices

SSH alias `iran` still targets `194.33.105.56:9011`; live hostname is
`vps-second-264143`, KVM. Reverse DNS is `ip-194-33-105-56.Hosted-by.PARSVDS.com`,
strongly indicating ParsVDS hosting; the actual billing account/reseller has not been
authenticated. This is not an invoice or proof of the current paid plan. The official
customer panel is [my.parsvds.com](https://my.parsvds.com/).

Observed capacity remains 2 CPU / 3916 MiB RAM; approximately 1409 MiB available.
Existing service limits plus planned diagnostics workers and 750 MiB reserve require
4654 MiB. The current activation budget fails. Existing workers were not squeezed.

Public list prices read November 21, 2026, from the
[current official NVMe table](https://parsvds.com/virtual-server/iran-ssd/):

| Plan | CPU | RAM | Disk | Monthly list price (toman) | Meets requested minimum |
| --- | --- | --- | --- | --- | --- |
| IR_VPS_03 | 2 | 4 GB | 30 GB | 966,000 | no |
| IR_VPS_04 | 2 | 6 GB | 50 GB | 1,399,000 | no: CPU |
| IR_VPS_05 | 4 | 10 GB | 80 GB | 1,880,000 | yes |
| IR_VPS_06 | 6 | 16 GB | 120 GB | 3,400,000 | yes |

The first qualifying listed plan costs 914,000/month more than the current public
4 GB listing. Actual incremental billing, tax, renewal and eligibility are unknown
until the existing service's upgrade quote is read. Search snippets/legacy pricing
pages differed from the live page and were not used. No new-provider migration is proposed.
The [provider's upgrade guide](https://parsvds.com/wiki/upgrade-vps/) says the invoice is
prorated by remaining days; its public page says an upgrade preserves IP and data.
Neither establishes this service's downtime. Treat a reboot/maintenance window as possible;
retain a fresh restore-tested backup and independently verify disk/filesystem and services
after any separately approved upgrade. Do not initiate payment or resize from this record.

## Germany production integration

The existing supervised commissioning connector remains on `4a70812f`, not the current
candidate. Its independent Codex home is authenticated with a free account; discovery
listed `gpt-6-luna`, `gpt-5.6-terra`, `gpt-5.6-luna`. This does not prove production model
execution or inherit laptop Plus authentication. The old image lacks the matching helper
present in the current pinned 0.167.2 build. Its liveness is not panel readiness.

Public `141.11.175.231:9011` and private `100.108.24.126:9011` both reached the same pinned
Germany host. Iran addressing/keys were preserved. About 2.27 GiB disk remains; the guarded
release needs at least 3 GiB plus the staged archive. It must fail until approved safe
space recovery or added capacity is available; do not prune unrelated images/previous
artifacts/volumes or weaken the guard. The existing generation Agent remains separate.

The already downloaded CI runtime artifact from run 44907651271 passed GitHub ZIP digest,
inner archive SHA-256 and canonical image identity verification. It identifies tested PR
merge candidate `316ab34e6befe4e9afca434bd940a546293db378`, not source head `e3b8bc30` or main.
Actual isolated hosted rollout, idempotent replay, failure rollback and retained state passed.
Production requires approved main integration, successful full main CI and its own exact
artifact; this PR artifact is not a production release authorization.

## Controlled replay and resolution boundary

The owner selected controlled GitHub Actions replay. The existing reviewed validation
workflow is reused; no second runner, production shell, admin replay or production credential
is introduced. New durable `replay` operations bind the selected occurrence, successful
deployment/readback artifact, manifest, deployed source commit, fresh matching host-image
observation, requesting admin and the published repair's exact test profile/file selection.
Only the server can select these tests; a chat/log instruction cannot authorize them.
Main policy and ancestry are checked before a single journaled workflow dispatch. No new
candidate branch, tag, commit or PR is created. Unknown acknowledgement is reconciled rather
than dispatched again. Cancellation and artifact verification reuse the existing broker.

The panel presents this as **isolated source regression replay**, not executing the deployed
container or replaying production requests. The test sandbox uses trusted policy dependencies;
its image is recorded independently of the release image. A passed replay remains
`production_business_outcome_verified=false` and `verified_resolved=false`. It does not alter
local issue status. A controlled, approved affected-business scenario through the actual
production path and an observation window remain required for verified resolution.

## Migration and rollback packet

Production is still 175. Migration 187 only expands the durable operation-kind check;
it sets a bounded lock timeout. Its downgrade refuses to erase replay audit. On the same
fresh encrypted snapshot, isolated PostgreSQL 18 restore and upgrade 175→187 preserved
155 source-table counts, 11 protected fingerprints and valid FKs; target has 169 tables.
The owned networkless tmpfs container was removed. No application ran on restored real data.
Refresh the snapshot/rehearsal before the actual approved release as needed.

An additive database upgrade does **not** establish compatibility with the old 175 image.
In particular the old SQLAlchemy `AITaskType` cannot deserialize a persisted `debug_agent`
row when listing AI settings. Do not downgrade/delete configuration or repair audit to make
an old image appear compatible. Prepare a tested compatibility release/roll-forward artifact
before activation; database restore is a separate disruptive owner action with an explicit
data-loss window. No automatic production rollback is claimed from this rehearsal.

## Next approval boundary

First repair the actual PAT grant and complete safe CI/isolated acceptance. Then present
the actual provider upgrade quote before asking for a paid resize/maintenance approval.
Separately prepare the exact protected-main release command, fresh backup identity,
compatible recovery artifact, resources and service impact before asking for merge,
production migration/runtime/application release or automatic SMS activation. None of
those approvals is inferred from the replay decision or credential provisioning.
