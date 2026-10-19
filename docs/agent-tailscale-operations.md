# Iran to Germany Agent connectivity

Iran Agent consumers use `extra_hosts` in `compose.prod.iran.yaml`. Backend-2
inherits Backend's mapping. Food-photo worker, body-analysis worker and scheduler
have the same mapping. Notification delivery does not call Agent Service.

Persist these non-secret settings in `/opt/fitician-iran/.env` (mode 0600):

```dotenv
AGENT_SERVICE_BASE_URL=https://fastcreate-560543.tail869ad5.ts.net
AGENT_SERVICE_HOST=fastcreate-560543.tail869ad5.ts.net
AGENT_SERVICE_PRIVATE_IP=100.108.24.126
```

Preserve `AGENT_SERVICE_TOKEN`. Keep the hostname in the HTTPS URL so certificate
and hostname validation remain enabled. Do not use the old `:9443` endpoint,
disable TLS verification, change host-wide DNS, or publish Germany port 9001.
Germany Tailscale Serve terminates private HTTPS on 443 and forwards to
`127.0.0.1:9001`. The Compose defaults match this deployment; set both mapping
variables explicitly when changing the Agent host or its tailnet address.

For a configuration-only rollout:

1. Securely back up `.env`, existing active marker (if present), image identities,
   container start times and immutable contract hashes on Iran before changing settings.
2. Create a new release contract under `releases/<configuration-commit>/`.
   Never overwrite a historical release. Keep current image tags. Preserve
   existing Caddy/Redis file contents and unrelated runtime settings; leave their
   running containers and mounts unchanged during this rollout.
   The current source already includes the required 120-second worker startup
   grace, superseding the October 18 startup override.
3. Render old and candidate contracts using the real environment, without
   printing secrets. Accept only the intended host mapping/environment change
   and the already-active worker startup grace. Do not run migrations or builds.
4. Recreate only `backend`, `backend-2`, `food-photo-worker`,
   `body-analysis-worker`, and `scheduler`, one at a time, using
   `up -d --no-deps --pull never --wait`. Wait for each Backend to be ready
   before proceeding. Use the existing project and production env file.
5. Test hostname resolution, verified HTTPS, `/healthz`, authenticated
   `/v1/capabilities` in all five containers. Run one synthetic structured
   request through the Backend's existing Agent provider, without user records.
   Confirm other container identities/start times and Germany Agent are unchanged.
6. Publish the new `.regional-iran-active-contract` marker atomically after
   verification. Future regional deployments ship the repository Compose mapping
   and retain the operator env settings; no CI/CD edits are needed. Existing
   scalability acceptance and deployment approval gates remain in force.

If verification fails, restore the saved `.env` and previous marker state, then
recreate only changed consumers with their original contracts and image tags.
Do not restore a database or downgrade a schema for this configuration change.

`extra_hosts`, `restart: unless-stopped`, and enabled Docker/Tailscale system
services persist across container recreation and host restart. A host reboot
is not required for verification; Agent requests can briefly fail while the
tailnet reconnects during boot.
