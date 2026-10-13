# Regional offline completion: operator settings

Preparation only: automatic CD stays disabled; the regional manual workflow stays
disabled in GitHub. The main deploy job is also unconditionally disabled in source under the latest
readiness-audit instruction; the separate SSH diagnostic is manual and read-only.
Netherlands and DNS were not modified. This document names
settings only; it contains no secret values. Existing production signing/encryption
keys and original volumes must be preserved.

## GitHub environment settings

Repository: `mohammad4242/fitician`.
Panel: **Settings → Environments**. `production-iran` and `production-germany`
were created and their four non-secret variables were set and read back.
The existing `Production` environment was not changed and is not a substitute. Configure deployment branches/tags for the reviewed release
branch (`main` after integration). Add a required reviewer if supported by the
repository plan; ensure the owner can approve the eventual manual deployment.
These rules are additional to the source deployment gates. If you enable
**Prevent self-review**, add a second authorized reviewer who can approve the run.
No environment SSH secrets or reviewer selections were created on your behalf.

In **each environment → Environment secrets → Add secret**:

| Secret | Required value source |
| --- | --- |
| `VPS_HOST` | That environment's audited server hostname/IP |
| `VPS_SSH_PRIVATE_KEY` | Private deploy key authorized only on that server; compatible with non-interactive ssh-agent |
| `VPS_KNOWN_HOSTS` | Verified host-key entry for `[hostname-or-IP]:9011`; confirm fingerprint through trusted console/access, never trust scan output alone |

Already set and verified in **each environment → Environment variables**:

| Variable | Iran | Germany |
| --- | --- | --- |
| `VPS_USER` | `root` (existing audited account) | `root` (existing audited account) |
| `VPS_SSH_PORT` | `9011` | `9011` |
| `VPS_APP_DIR` | `/opt/fitician-iran` | `/opt/fitician-agent` |
| `COMPOSE_PROJECT_NAME` | `fitician-iran` | `fitician-agent` |

The same names resolve independently through the selected environment; deployments
have separate concurrency locks. The SSH port defaults to 9011 and all SSH/SCP
operations use it. Never point a production environment at a rehearsal directory.

## Repository settings

Panel: **Settings → Secrets and variables → Actions → Secrets / Variables**.
Read-only inspection found these already present by name (values were not read):

| Type | Name | Use |
| --- | --- | --- |
| Secret | `DOCKERHUB_USERNAME` | Image namespace/build/login and regional registry login |
| Secret | `DOCKERHUB_TOKEN` | Image build/push and regional registry login; must have appropriate repository permissions |
| Secret | `EXPO_TOKEN` | Android/iOS release only; unrelated to the server migration |
| Variable | `VITE_GOOGLE_CLIENT_ID` | Frontend build-time OAuth client |
| Variable | `VITE_MEDIA_PUBLIC_BASE_URL` | Frontend build-time media base |

Repository secrets are inherited by environment jobs unless overridden. Use an
environment-specific read-only Docker Hub token for deploy if desired; CI's token
must retain push permission. Do not replace known working values merely for this
migration. `GITHUB_TOKEN`/`github.token` are automatic; no personal GitHub token
is required by these workflows. `VPS_APP_DIR` as a **secret** is legacy optional
fallback in old Netherlands workflows; regional deployment requires the variable.

### Complete references extracted from current workflow source

| secrets name | Referencing workflows |
| --- | --- |
| `DOCKERHUB_TOKEN` | `backend-only.yml`, `ci.yml`, `deploy-component.yml`, `deploy-production.yml`, `deploy-regional.yml`, `frontend-appearance-release.yml`, `frontend-only.yml` |
| `DOCKERHUB_USERNAME` | `backend-only.yml`, `ci.yml`, `deploy-component.yml`, `deploy-production.yml`, `deploy-regional.yml`, `frontend-appearance-release.yml`, `frontend-only.yml` |
| `EXPO_TOKEN` | `android-release.yml`, `ios-release.yml` |
| `VPS_APP_DIR` | `deploy-caddy-production.yml`, `deploy-component.yml`, `deploy-production.yml`, `frontend-appearance-release.yml` |
| `VPS_HOST` | `deploy-caddy-production.yml`, `deploy-component.yml`, `deploy-production.yml`, `deploy-regional.yml`, `frontend-appearance-release.yml` |
| `VPS_KNOWN_HOSTS` | `deploy-caddy-production.yml`, `deploy-component.yml`, `deploy-production.yml`, `deploy-regional.yml`, `frontend-appearance-release.yml` |
| `VPS_SSH_PRIVATE_KEY` | `deploy-caddy-production.yml`, `deploy-component.yml`, `deploy-production.yml`, `deploy-regional.yml`, `frontend-appearance-release.yml` |

| vars name | Referencing workflows |
| --- | --- |
| `COMPOSE_PROJECT_NAME` | `deploy-regional.yml` |
| `VITE_GOOGLE_CLIENT_ID` | `ci.yml`, `frontend-appearance-release.yml`, `frontend-only.yml` |
| `VITE_MEDIA_PUBLIC_BASE_URL` | `ci.yml`, `frontend-appearance-release.yml`, `frontend-only.yml` |
| `VPS_APP_DIR` | `deploy-caddy-production.yml`, `deploy-component.yml`, `deploy-production.yml`, `deploy-regional.yml`, `frontend-appearance-release.yml` |
| `VPS_SSH_PORT` | `deploy-regional.yml` |
| `VPS_USER` | `deploy-caddy-production.yml`, `deploy-component.yml`, `deploy-production.yml`, `deploy-regional.yml`, `frontend-appearance-release.yml` |

## Server-only settings: already staged, preserve securely

GitHub does not inject application/provider credentials. Regional deploy reads the
protected mode-0600 `.env` already on each server. Use `ops/env/iran.env.example`
and `ops/env/germany.env.example` as names-only templates; do not upload populated
files to GitHub or copy Iran's database/S3 settings to Germany.

Iran must retain exact original signing/HMAC/encryption keys and explicitly bind
`POSTGRES_VOLUME_NAME`, `REDIS_VOLUME_NAME`, `CADDY_DATA_VOLUME_NAME` and
`CADDY_CONFIG_VOLUME_NAME` only after the final restored data is validated. Germany
retains `AGENT_SERVICE_TOKEN`, provider/model allowlists and the adopted
`AGENT_HOME_VOLUME_NAME`. A failed Germany release automatically restores the old Agent only when the
read-only auth-home inventory is unchanged. Changed/unreadable auth blocks
automatic restart and requires the reviewed encrypted-auth recovery procedure.
Preserve restored auth; authenticate Claude separately
only if it will actually be enabled.

Server `backup.env`: `DB_BACKUP_BUCKET`, `DB_BACKUP_AGE_RECIPIENT`, `S3_ENDPOINT`,
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`. Keep the age
private identity on the trusted recovery/operator machine, not either VPS.
The public recipient is not the private identity. Preserve existing backup bucket
policies; independently verify retention/recovery and available disk before the
final window. No Cloudflare secret/variable is referenced by current workflows.

## Cloudflare: later, during the authorized cutover window

1. **My Profile → API Tokens → Create Token → Create Custom Token**: scope to
   `fitician.fit` only, with **Zone → Zone → Read**, **Zone → DNS → Read** and **Zone → DNS → Write**
   (the dashboard may label write permission **Edit**). Keep token in protected operator storage;
   the current cutover helper plans DNS updates and does not call Cloudflare.
   Record the zone ID from the zone Overview/API. These are operator inputs,
   not invented GitHub workflow secrets. Alternatively use the authenticated panel.
2. **Websites → fitician.fit → DNS → Records**: first export exact record IDs,
   current content, TTL and proxy flags for rollback. After final data/runtime
   gates pass, change only the reviewed A records for `@` and `api` to the
   independently verified Iran public IPv4. Keep `www` CNAME → `fitician.fit`,
   preserve MX/TXT/CAA/mail/unrelated records and existing proxy flags. Unexpected
   AAAA/conflicting records require review; the helper rejects them. Do not
   publish the Germany Agent as a public DNS endpoint.
3. **SSL/TLS → Overview**: if Cloudflare proxy is in use, validate **Full (strict)**
   with a valid hostname-matching origin certificate and HTTPS port 443 before
   traffic changes. **DNS only** bypasses Cloudflare HTTP traffic entirely; it
   requires public trusted origin TLS and tested certificate renewal. Current
   proxy flags could not be authenticated; do not silently select/change them.
   Preserve existing WAF/cache/redirect rules and verify authenticated APIs are
   not cached. No Cloudflare change is required for isolated tests.

Official panel references:
[GitHub environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments),
[Cloudflare tokens](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/),
[proxy status](https://developers.cloudflare.com/dns/proxy-status/),
[Full strict](https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/full-strict/).

## Final acceptance and deployment sequence

After connectivity returns, qualify the existing WireGuard/private TLS route,
Iran Docker-to-Agent authentication/uploads, real enabled AI models, S3/media,
SMTP/SMS/OAuth and public ingress/TLS renewal. Germany's existing 443 listener
must coexist with the private Agent endpoint; never replace it blindly. Rehearsal
resource snapshots are not sustained-load acceptance or physical Android proof.

Integrate the reviewed infrastructure branch before using it. Regional deployment
checks out `image_tag` for the entire immutable contract; an older app SHA also
selects the older tooling. Use an exact SHA with these changes and successful
required validation/images; never bypass the release gate with `main`/`latest`.
Do not repeat Full CI merely to test these scripts. If the final release gate
requires Full CI for the final cumulative diff, run it once for that release SHA.
Iran can use the fully verified preloaded image set; no registry pull is needed
for the existing isolated runtime. Verify artifact completeness before offline use.

The regional workflow remains disabled in GitHub. Later use **Actions → Deploy
Fitician regional production → Enable workflow** only after the release/cutover
decision and environment setup. The source deployment condition must also be separately reviewed and re-enabled
after Cutover readiness; never restore a push/workflow_run production trigger. All legacy
Netherlands production jobs remain disabled in source and GitHub. Later manual **Run workflow** requires
`target`, `deploy_kind`, full `image_tag`, successful exact-SHA `ci_run_id` and
`owner_approved=true`. Initial Iran adoption additionally needs
`initial_deploy=true`, `first_scalability_release_approved=true` and the exact
successful `scalability_evidence_run_id`. Keep schema permission false unless
reviewed migrations are required. Germany uses `target=germany`,
`deploy_kind=agent` and independent environment settings.

Follow `docs/regional-cutover-checklist.md`: drain/freeze the six source writers
only in the final authorized window, snapshot DB/auth freshly, restore into fresh
isolated volumes, compare all table counts/fingerprints and schema/auth, reconcile
jobs, then adopt one target writer/consumer set. Preliminary snapshots cannot
replace this. After target writes, rollback must freeze target and reconcile/reverse
restore data before DNS; DNS-only rollback is rejected. Retain Netherlands,
original volumes and encrypted backups until stability is accepted.
