# Independent installation page (Germany)

Build only the public page with `npm run build:standalone-install --workspace frontend`.
Output: `frontend/dist-standalone/`. No API, authentication providers, service
worker, application manifest, database, media server, or Iran request is required
to render it. The existing React component, styles, fonts, and logo are reused.
Only the standalone entry displays the Persian VPN notice.

Android `/download/android` redirects to the existing Arvan release object.
iOS opens `https://fitician.fit/install` so Safari installs the real application
on its original origin. Instagram copy also copies that canonical application
URL. The main site's installation page is unchanged.

## Proposed isolated runtime — approval prerequisite

Germany port 443 currently belongs to Xray/Reality. Never stop, reconfigure,
replace, or move it. Port 80 and 8443 were free during the read-only preflight.
The supplied Compose project is separate from the Germany Agent and uses only
80 and 8443, a read-only static directory, and dedicated certificate volumes.
Caddy obtains and renews a public certificate through HTTP-01 on port 80.
TLS-ALPN validation on 443 is explicitly disabled.

**The owner must approve the limited Cloudflare routing before deployment.**
Required external configuration, restricted to `install.fitician.fit`:

1. Proxy the existing DNS record (orange cloud).
2. Add an Origin Rule matching `http.host eq "install.fitician.fit"` with
   destination port override `8443` for HTTPS traffic.
3. Preserve HTTPS end to end using Full (strict); never downgrade the zone.
   Ensure port 80 ACME challenges reach the origin for certificate renewal.

Do not alter the apex domain, Iran routes, unrelated DNS records, or global
security settings. A direct DNS-only record cannot reach this site on default
HTTPS while Xray retains 443. A second dedicated public IP is an alternative,
but is not configured by this proposal.

## Deployment and rollback

Before any write, record existing container IDs, images, restart counts, process
start times, health, and port bindings. Validate the Caddyfile and compare those
values after deployment. Preserve an existing site's directory before switching
new static releases. No Agent Compose command or database operation is needed.

Set `INSTALL_CADDY_IMAGE` to a verified immutable Caddy digest. Copy the build as
`site/` next to the Caddyfile and compose.yaml, then use a dedicated project:

```
docker compose -p fitician-install --env-file release.env -f compose.yaml up -d --no-deps install-site
```

First-deployment rollback removes only the new `fitician-install` site service;
leave its TLS volumes available. For an existing site, restore only the previous
static release and the site's own configuration. Never use `down` on Agent or
regional projects. Keep all GitHub Actions CD workflows disabled.
