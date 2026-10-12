# Regional readiness audit — 2026-10-12

**Configuration files are ready for an approved SCP transfer. A complete offline
installation package and production deployment are NOT ready.** No files were transferred,
no remote directories were created, and no production state was changed. Compose validation
was streamed through SSH stdin with synthetic values, without saving remote files.

Branch: `feat/iran-netherlands-architecture`; starting HEAD `cc276f9c`.
No tracked local changes at entry; unrelated untracked work was preserved.
No push, merge, registry pull, VPN connectivity test or GitHub deployment was performed.

## Verified hosts

The SSH aliases, checked with `ssh -G` before other work, are authoritative:

| Alias | HostName | User | Port | IdentityFile |
| --- | --- | --- | --- | --- |
| `iran` | `194.33.105.56` | root | 9011 | `~/.ssh/id_ed25519_iran` |
| `alman` | `141.11.175.252` | root | 9011 | `~/.ssh/id_ed25519_alman` |

| Read-only observation | Iran | Germany |
| --- | --- | --- |
| Architecture / CPU / RAM | x86_64 / 2 / 3916 MiB | x86_64 / 1 / 1968 MiB |
| Available RAM at audit | 3381 MiB | 1463 MiB |
| Root disk / available | 30 GiB / about 23 GiB | 20 GiB / about 13 GiB |
| Docker / Compose | 29.1.3 / 2.40.3 | 29.9.0 / 5.6.0 |
| Running containers / volumes | None / none | None / none |
| Existing directory | `/opt/fitician` | `/opt/fitician-agent` |
| Required target directory | `/opt/fitician-iran` absent | `/opt/fitician-agent` present |
| Images | Infrastructure tags only | None |
| Public listeners | SSH 9011 only | SSH 9011, Xray 443, x-ui 2096 |
| Host firewall | Allows SSH only | Allows SSH and 443 |
| Backup prerequisites | age installed; AWS CLI absent | age and AWS CLI absent |
| VPN prerequisite | Tailscale command absent | Tailscale installed; connectivity untested |

Iran has Caddy's exact pinned digest. Its installed PostgreSQL and Redis tags do **not**
resolve to the exact digests required by the regional contract; `docker image inspect`
of those pinned references fails. Matching tag names alone are insufficient.
Both hosts use `json-file` logs without daemon-level rotation. The regional contracts
now bound each container to three 10 MiB log files without changing host configuration.

## Architecture and checks

- Iran owns PostgreSQL, Redis, two APIs, four durable workers, migrations, frontend and
  Caddy. Only 80/443 are published. The implicit Compose bridge is host-local; there is
  no Docker network shared across hosts. No Iran service depends on local Agent health.
- Germany owns only Agent, published at `127.0.0.1:9001`. Its only persistent mount is
  the explicitly named external auth volume. No application env file, DB/S3 credentials
  or private media volume is injected. HTTPS private ingress remains a deferred prerequisite.
- All persistent volumes are external and must be provisioned/restored separately.
  Iran bind mounts are release-relative `Caddyfile` and `ops/redis/redis.conf`, read-only.
  Germany uses init, a read-only root filesystem, bounded tmpfs, dropped capabilities and
  no-new-privileges. Worker heartbeats and API/DB/Redis/Agent health contracts were inspected.
- Application images use full Git SHA tags; infrastructure images are digest-pinned.
  Offline deployments require `IMAGE_SOURCE=preloaded` and every exact image reference
  must pass inspection before runtime mutation. Do not replace digest pins with mutable tags.
- Deployment now measures host RAM/CPU and checks **both regions before pull or mutation**.
  The DB gate now reads rendered API/worker pools and env-file budget values, rejecting
  unbounded pools. It does not establish the live PostgreSQL `max_connections` value.
- Default Iran envelope, including migrations: 2944 MiB / 2.40 CPU limits; 972 MiB RAM
  headroom on the measured host. Germany: 448 MiB / 0.40 CPU; 1520 MiB headroom.
  Default DB pool ceiling: 32 connections + 4 reserve, below the configured budget of 40.
  Full monitoring adds 512 MiB and would fail Iran's 750 MiB headroom requirement.
- These are resource ceilings, not measured load/backup/CLI-concurrency acceptance.

Passed: 124 ops tests; 10 CI contract tests; isolated split simulation with 46 Backend
tests and real HTTP bearer/capabilities/multipart, private-media resolution, Agent outage,
API readiness during outage, recovery and workspace cleanup; local and remote Compose
rendering with synthetic settings; measured-host capacity; Ruff, shell syntax and actionlint.
The split simulation used a fake CLI and new local project volumes, retained by its cleanup
contract. It did not use production authentication or real vendor services.
Shellcheck is unavailable in the local PATH; its check remains pending.

## Transfer manifest — configuration only

Use `/opt/fitician-iran/releases/<SHA>/` on Iran and
`/opt/fitician-agent/releases/<SHA>/` on Germany. `<SHA>` must be the separately reviewed
full image SHA, with matching release/CI evidence. No deploy script should be run now.

| Local file | Iran destination relative to release | Germany destination relative to release |
| --- | --- | --- |
| `compose.prod.iran.yaml` | `compose.prod.iran.yaml` | — |
| `compose.prod.germany.yaml` | — | `compose.prod.germany.yaml` |
| `Caddyfile` | `Caddyfile` | — |
| `ops/redis/redis.conf` | `ops/redis/redis.conf` | — |
| `ops/deploy-regional.sh` | `ops/deploy-regional.sh` | `ops/deploy-regional.sh` |
| `ops/verify-regional.sh` | `ops/verify-regional.sh` | `ops/verify-regional.sh` |
| `ops/check-runtime-capacity.py` | `ops/check-runtime-capacity.py` | `ops/check-runtime-capacity.py` |
| `ops/check-db-connection-budget.py` | `ops/check-db-connection-budget.py` | — |
| `ops/backup-production.sh` | `backup-production.sh` | — |
| `ops/env/iran.env.example` | `templates/iran.env.example` | — |
| `.env.example` | `templates/application.env.example` | — |
| `ops/env/germany.env.example` | — | `templates/germany.env.example` |

Planned commands below require separate transfer/directory-creation approval. They were
**not executed**. They use SSH alias ports and pinned known hosts, create a new release
directory, and never overwrite a runtime `.env` or an existing release.

```sh
SHA=<reviewed-full-image-SHA>
printf '%s' "$SHA" | grep -Eq '^[0-9a-f]{40}$' || exit 1
IR=/opt/fitician-iran/releases/$SHA
DE=/opt/fitician-agent/releases/$SHA
ssh -o StrictHostKeyChecking=yes iran "set -eu; test ! -e '$IR'; mkdir -p '$IR/ops/redis' '$IR/templates'"
ssh -o StrictHostKeyChecking=yes alman "set -eu; test ! -e '$DE'; mkdir -p '$DE/ops' '$DE/templates'"
scp -o StrictHostKeyChecking=yes compose.prod.iran.yaml Caddyfile iran:"$IR/"
scp -o StrictHostKeyChecking=yes ops/redis/redis.conf iran:"$IR/ops/redis/"
scp -o StrictHostKeyChecking=yes ops/deploy-regional.sh ops/verify-regional.sh ops/check-runtime-capacity.py ops/check-db-connection-budget.py iran:"$IR/ops/"
scp -o StrictHostKeyChecking=yes ops/backup-production.sh iran:"$IR/backup-production.sh"
scp -o StrictHostKeyChecking=yes ops/env/iran.env.example iran:"$IR/templates/"
scp -o StrictHostKeyChecking=yes .env.example iran:"$IR/templates/application.env.example"
scp -o StrictHostKeyChecking=yes compose.prod.germany.yaml alman:"$DE/"
scp -o StrictHostKeyChecking=yes ops/deploy-regional.sh ops/verify-regional.sh ops/check-runtime-capacity.py alman:"$DE/ops/"
scp -o StrictHostKeyChecking=yes ops/env/germany.env.example alman:"$DE/templates/"
```

Compare source and destination SHA-256 hashes after any approved transfer. The protected
runtime env locations remain `/opt/fitician-iran/.env`, `/opt/fitician-iran/backup.env` and
`/opt/fitician-agent/.env`; operator provisioning is separate. Never SCP the populated
Iran env to Germany. Templates contain no real credentials.

## Blockers for a complete offline preparation

1. Select and qualify immutable backend/frontend/Agent images. Prepare a trusted image
   archive/manifest containing every exact app and infrastructure reference; verify save/load
   preserves references accepted by `docker image inspect`, especially digest pins. No complete
   candidate archive exists from this audit. Source + rollback image sizes, archive size,
   encrypted DB/auth snapshot sizes and peak staging disk usage remain unknown. Retain at
   least 20% disk free after staging and restoration; current empty-host disk is insufficient
   evidence of that requirement.
2. Prepare compatible offline installers for missing prerequisites (Iran Tailscale and
   AWS CLI; auth-backup tooling where needed), with checksums and dependency closure.
   No installer was downloaded or installed. Source DB restore, four Iran volumes, Germany
   auth-volume restore and a single baseline Agent are still required; Germany initial adoption
   intentionally rejects an empty host. Preserve existing signing/encryption/token values.
3. Defer VPN/Serve/ACL/Docker forwarding, cross-host DNS/TLS, S3, SMTP, SMS, OAuth, push,
   payments, registry/CDNs and exact-SHA GitHub deployment qualification until connectivity
   returns. Germany's existing wildcard 443 Xray listener needs coexistence validation before
   private Serve is enabled. Iran needs approved ingress firewall and valid certificate
   preparation; existing public DNS cannot qualify the new host's Caddy certificate offline.
4. Require source-state inventory, encrypted backup/isolated restore evidence, schema review,
   real load/backup memory checks, CI acceptance and explicit cutover approval. No production
   smoke, migration, live secret check, provider acceptance or deployment is claimed here.

Next: approve configuration-only transfer if desired; complete the image/installer/backup
manifest locally before authorizing any server preparation. Network and cutover work stay deferred.
