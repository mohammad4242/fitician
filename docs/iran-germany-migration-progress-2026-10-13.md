# Regional migration progress — 2026-10-13

**Cutover has not occurred. Netherlands remains the authoritative, live production.**
The owner has fully authorized deployment, DNS and cutover; no renewed approval is
required. Essential Cloudflare and Tailscale access is still missing.

## Executed and verified

- Source SSH works as `mohammad@141.11.0.99`. Docker and deployment files are accessible;
  passwordless sudo is unavailable and was not required. All source services with health
  checks remained healthy; PostgreSQL restart count and new OOM counters remained zero.
- Existing reviewed configuration transfers were retained rather than repeated.
  The application images at `bf182dd42d97304aa55d39e7f51a92a073f9e021` match the source
  Docker descriptors and registry descriptors. Backend/frontend were staged in Iran;
  Agent was staged in Germany. Required PostgreSQL, Redis and Caddy digest pins were
  inspected successfully. Both destinations retain more than 20% available disk.
- PostgreSQL was backed up from a read-only exported transaction snapshot and encrypted
  with age. Its encryption identity remains in a mode-0600, Git-ignored local file; it
  was not sent to a VPS. The encrypted artifact was transferred to Iran and uploaded to
  the existing backup bucket, then downloaded and SHA-256 compared successfully.
- Actual `pg_restore --single-transaction --exit-on-error` succeeded in a separate
  PostgreSQL 18 container on Iran, with network disabled and no published ports.
  All 150 table counts matched the snapshot, including 249 users. All 11 selected
  table fingerprints matched, covering users, profiles, web/mobile sessions and tokens,
  provider settings/credentials, device tokens and media references. Alembic
  `20261007_172` matched; zero foreign keys were unvalidated after restore.
- A full preliminary Agent-home snapshot is retained locally, encrypted. A separate
  small snapshot of the existing authentication/configuration files was encrypted,
  transferred to Germany, and restored into a new isolated volume. All nine file
  fingerprints and parent-directory ownership/modes matched. Codex and Antigravity
  local auth probes matched the source as authenticated. Claude was unauthenticated
  in both, using a bounded 20-second CLI status probe. No external provider task
  was tested.
- Destination env files are mode 0600. Source signing/HMAC keys and Agent token were
  preserved. Germany received no application database or S3 credentials. Both regional
  Compose contracts rendered successfully against the destination settings.
- Germany's existing Tailscale node issued a trusted certificate for its private name;
  its separate evidence is `germany-certificate-evidence.json`. Source Caddy data was
  encrypted and restored into a new Iran volume. Certificate/key
  pairing, domain and validity checks passed. A temporary loopback HTTPS test returned
  HTTP 200 and TLS verification result 0, and its process was stopped. This does not
  establish public Iran ingress, application readiness or certificate renewal.
- The documented WireGuard fallback was tested with peer-only routes/firewall rules.
  Both hosts sent UDP packets but received no peer packets; there were no handshakes
  or ping replies. Experimental keys/configs, interfaces, services and firewall rules
  were removed. Existing routes, SSH, Xray and Tailscale protections were preserved;
  the installed WireGuard tooling remains available.

## Backup evidence

Encrypted PostgreSQL snapshot: 25,854,634 bytes.

SHA-256: `e94fb79a070f011762faad576276da2cf309484ac61dc0ff8784b7cec4c85d1c`.

Backup object:
`s3://fitician-db-backups/postgres/regional-migration/fitician-20261012T225042Z.dump.age`.
Upload/download integrity is verified; object-lock retention was not verified.
These are preliminary snapshots, not the final write-frozen cutover snapshots.

Sanitized runtime evidence is under `artifacts/regional-cutover/`:
`status.json`, `image-staging.json`, `database-restore-evidence.json`,
`backup-upload-evidence.json`, `agent-restore-evidence.json`,
`agent-auth-probe-evidence.json`, `tls-restore-evidence.json`,
`germany-certificate-evidence.json`, `source-runtime-evidence.json`,
`agent-backup-checksum.json` and `wireguard-evidence.json`.
Private keys, env files and encrypted payloads are excluded
from Git; this document contains no credentials or individual user data.

## Access blockers and remaining gates

1. Provide a secure-file path or authenticated administration session for Cloudflare
   DNS of `fitician.fit`.
2. Provide enrollment/ACL access for Iran to the existing Germany Tailscale tailnet.
   WireGuard's upstream UDP path did not qualify. Cross-region authenticated HTTPS,
   Docker forwarding, capabilities, uploads, real providers and outage/recovery must
   pass before production adoption.
3. Complete new-region runtime/resource/load acceptance and controlled real
   web/mobile/API/auth/media/AI/worker/email/SMS/push/enabled-payment checks. These
   checks were not replaced by static configuration checks or simulated tests.
4. Prepare public HTTPS/renewal and rollback, then drain and freeze source writes and
   consumers. Take fresh encrypted DB and quiesced Agent snapshots, reconcile leases,
   restore/compare again and run only reviewed necessary migrations. Start only one
   production Agent and one set of job consumers. Switch A/AAAA only after all gates pass.
5. Verify propagation and actual client operations, monitor stability and fresh backups,
   and retain the Netherlands server and valid backups. After target writes begin,
   rollback requires a target-write freeze and reconciled reverse data restoration;
   a DNS-only rollback is insufficient.

No DNS or traffic change, source write freeze, source service stop, original-volume
deletion, production target consumer startup, or automatic-CD enablement was performed.
No migration success or new-region production readiness is claimed.
