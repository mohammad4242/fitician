# Regional GitHub Actions readiness — 2026-10-13

## Germany SSH recovery — subsequent verification

[Run 38400390396](https://github.com/mohammad4242/fitician/actions/runs/38400390396)
completed successfully on source `67af46bab011190bff95c91c68f5696dcfd47702`.
The Iran job was intentionally skipped. Germany verified the expected target,
pinned host key and public-key authentication on port 9011. UID was 0; project
directory read/write permission predicates passed and Docker daemon access was
available. No remote application files were written by this diagnostic.

The local `id_ed25519_alman_cd` key pair matched, with private file mode 600.
Its public key was absent from root's standard `authorized_keys`; exclusive
authentication with this key failed. The existing SSH alias could connect using
another identity, which explained the misleading initial local success.

The CD public key was appended without removing existing authorized keys. The
existing directory/file permissions (700/600) and ownership were retained; no
SSH daemon policy was changed. Exclusive local authentication then succeeded.
`VPS_SSH_PRIVATE_KEY` in `production-germany` was set securely from the local key
file. The successful hosted runner's fingerprint hash matched that exact local
CD key. This supersedes the Germany authentication blocker below; Iran and the
release/cutover gates remain pending. Deployment remains disabled in source and
GitHub. Netherlands, DNS, database and application services were untouched.

## Result

The regional settings are present, but authenticated SSH from GitHub Actions is
not yet working. Iran fails at the network phase. Germany reaches SSH on port
9011, verifies the pinned host key, and offers its environment key; the server
rejects that key. No deployment was executed.

## Configuration inventory

Verified with GitHub CLI/API without displaying secret values:

| Scope | Secrets | Variables |
| --- | --- | --- |
| Repository | `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `EXPO_TOKEN` | `VITE_GOOGLE_CLIENT_ID`, `VITE_MEDIA_PUBLIC_BASE_URL` |
| `production-iran` | `VPS_HOST`, `VPS_SSH_PRIVATE_KEY`, `VPS_KNOWN_HOSTS` | `VPS_USER`, `VPS_APP_DIR`, `COMPOSE_PROJECT_NAME`, `VPS_SSH_PORT` |
| `production-germany` | `VPS_HOST`, `VPS_SSH_PRIVATE_KEY`, `VPS_KNOWN_HOSTS` | `VPS_USER`, `VPS_APP_DIR`, `COMPOSE_PROJECT_NAME`, `VPS_SSH_PORT` |

Both regional ports are 9011. Variable syntax checks passed; server-side directory
and Docker permissions remain unverified because authentication failed. Neither
regional environment currently has protection rules or a branch policy.

Panel: repository **Settings → Environments → production-iran / production-germany →
Environment secrets / Environment variables**. Repository settings: **Settings →
Secrets and variables → Actions → Secrets / Variables**.

## Actual GitHub Actions evidence

These are hosted runner tests, separate from any local SSH inspection.

| Target | Run | Verified result |
| --- | --- | --- |
| Iran | [38385989428](https://github.com/mohammad4242/fitician/actions/runs/38385989428) | Expected target matched, private key loaded, pinned host entry present; network failure before host-key verification or authentication |
| Germany | [38386969396](https://github.com/mohammad4242/fitician/actions/runs/38386969396) | Expected target matched, key loaded, pinned host key verified, key offered; `publickey_rejected` |

The Germany run tested source commit `59f64bb41b1be2106151e32c1619124288de1aff`.
Earlier diagnostics incorrectly reported host-key verification as false because
OpenSSH debug output uses CRLF. The parser was fixed and the Germany test rerun;
the final result above supersedes that earlier field.

`diagnose-regional-ssh.yml` has two independent environment-bound jobs and only
manual dispatch. The script pins host keys and key identity, disables interactive
authentication/forwarding, bounds connection time, and exposes only sanitized
status fields. Authenticated remote checks are limited to UID, directory access,
and read-only Docker daemon access. It never invokes Compose, migrations, DNS,
or service changes. Private material is held in protected ephemeral files and
removed on exit. SSH/SCP deployment paths use `-p`/`-P`; known-host matching uses
`[host]:9011`.

## CI and isolated validation

- 215 Ops tests passed, including regional workflow/CD safety, independent
  deployment selection, immutable SHA gates, rollback and preloaded images.
  Deployment/rollback simulations are isolated; they do not establish live
  server acceptance. Preloaded mode is supported for Iran; Germany rejects it.
- Regional workflows passed actionlint. The full workflow set passed with only
  the existing unsupported `concurrency.queue` key excluded by a narrow ignore.
- Relevant shell scripts passed ShellCheck at warning severity and syntax checks;
  changed Python tests passed Ruff; `git diff --check` passed.
- [Selective publication 38359328946](https://github.com/mohammad4242/fitician/actions/runs/38359328946)
  successfully logged into Docker Hub and published backend/frontend/Agent images
  for `914c17c773d3a6090abce0e610c6652b6f976aa9`. Independent registry HEAD checks
  returned HTTP 200 and matching published digests for all three tags.
- [Full CI 38359491911](https://github.com/mohammad4242/fitician/actions/runs/38359491911)
  succeeded on that same SHA but was scheduled. The current release gate rejects
  scheduled runs as release evidence. The selective publication does not satisfy
  the Full-CI requirement for Iran full deployment or Germany Agent deployment.
- No new images or Full CI were requested for this audit. Audit commits use
  `[skip ci]`; this does not qualify their SHA for deployment.

## Remaining gates

1. Restore/permit GitHub-hosted-runner connectivity to Iran port 9011, then repeat
   the diagnostic. The present network failure does not establish whether Iran's
   host key or authorized key is correct.
2. Match Germany's configured `VPS_USER` and `VPS_SSH_PRIVATE_KEY` to the server's
   authorized public key, ownership/permissions and SSH policy; repeat the
   diagnostic. Public-key rejection is confirmed; its server-side cause is not.
3. After authenticated checks pass, confirm project directory and Docker access
   from Actions. Review environment approval/branch policy before activation.
4. Qualify the final image SHA with the required trusted CI event and release
   evidence, plus cutover-specific migration/restore/network acceptance.
5. Only after cutover approval, intentionally remove the source deployment stop
   and enable the deployment workflow in **Actions → Deploy Fitician regional
   production → Enable workflow**. It remains disabled now, both in source and
   GitHub. Automatic CD remains off.

Netherlands production, DNS, databases, user data, volumes and server
configuration were not changed. Cloudflare and Iran international egress were
not prerequisites for local validation; Cloudflare configuration was untouched.
