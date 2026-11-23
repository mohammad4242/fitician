# Owner activation checklist

Implementation uses mocks until you supply credentials. No real sandbox or live
payment has been claimed. Do not edit application source code.

## 1. Sandbox acceptance (isolated server/database)

- [ ] In TetraPay gateway Settings enable sandbox for Fitician. Keep the API key secret.
- [ ] Use an isolated nonproduction Fitician backend/database and HTTPS host under `fitician.fit` (for example `sandbox.fitician.fit`); arrange its callback routing and merchant-domain approval. Do not connect it to the production database.
- [ ] Set `FRONTEND_ORIGIN=https://sandbox.fitician.fit` (your isolated host), an isolated `DATABASE_URL`, `APP_ENV=local`, `BILLING_DEFAULT_PROVIDER=tetrapay`, `BILLING_FAKE_PROVIDER_ENABLED=false`, `TETRAPAY_ENABLED=true`, `TETRAPAY_MODE=sandbox`, `TETRAPAY_BASE_URL=https://api.sandbox.tetra98.com/api/v1`, `TETRAPAY_API_KEY=<gateway API key>` in that server's private env file.
- [ ] Point `TETRAPAY_CALLBACK_URL` to `https://sandbox.fitician.fit/billing/checkout-result` and `TETRAPAY_WEBHOOK_URL` to `https://sandbox.fitician.fit/api/v1/billing/webhooks/tetrapay` (substitute your isolated host). Both paths are fixed.
- [ ] Initially leave `TETRAPAY_WEBHOOK_ENABLED=false`. Authenticated verification and scheduler recovery work without it.
- [ ] Complete sandbox **online success** and **card success**. Confirm correct IRR price, order/token ownership, one paid transaction, one subscription grant, refreshed access and admin history.
- [ ] Repeat browser refresh, back navigation, duplicate callbacks and verification. Confirm no second entitlement or checkout transaction.
- [ ] Exercise pending, cancellation, unsuccessful attempt and expiry. Created/pending must remain unpaid/recoverable; cancellation does not itself invalidate the link.
- [ ] Try partial-payment behavior through an authorized sandbox fixture/scenario. Fitician always sends `allow_partial=false` and never accepts underpayments. Never change this in production just to test. The mocked suite additionally tests a provider response with `status=paid` and insufficient received funds: no grant.
- [ ] Finish payment without returning; verify the scheduler recovers it. Test lost connectivity, restarting an API/scheduler, resuming/terminating an explicitly gated internal Android build, and recovery after the internal TTL.
- [ ] Confirm the actual hosted URL stays on the allowed HTTPS TetraPay domains. If official behavior differs, leave checkout disabled and have engineering verify the new contract.
- [ ] Add the separate webhook key using step 3 on this sandbox server; test signed delivery, duplicate delivery, invalid signature, stale timestamp, webhook/customer-return races, and rotation. Check the existing diagnostic codes without exposing secrets.
- [ ] Verify sandbox events sent to the production endpoint cannot grant production access. Production rejects enabled sandbox configuration and sandbox header/body markers; tokens are isolated by API host.
- [ ] Record evidence without API keys, signatures, full tokens, payment URLs or personal payment data. Confirm rollback and scheduler health.

The same gateway API key/signing key are used in sandbox and live, but base URLs,
backend/database and webhook destinations must stay separate. Sandbox tokens expire
from provider storage after 12 hours. No live payment is needed for these checks.

## 2. Production API key (requires deployment approval)

- [ ] Approve the reviewed release and additive migration after sandbox acceptance.
- [ ] On the **Iran application server**, edit the existing private file `/opt/fitician-iran/.env` using a secure editor. Do not replace the file or print/copy it into Git.
- [ ] Preserve every unrelated setting and existing secret. Set exactly:

```dotenv
BILLING_DEFAULT_PROVIDER=tetrapay
BILLING_FAKE_PROVIDER_ENABLED=false
TETRAPAY_ENABLED=true
TETRAPAY_MODE=live
TETRAPAY_API_KEY=<OWNER_PROVIDED_SECRET>
TETRAPAY_BASE_URL=https://api.tetra98.com/api/v1
TETRAPAY_CALLBACK_URL=https://fitician.fit/billing/checkout-result
TETRAPAY_WEBHOOK_ENABLED=false
TETRAPAY_WEBHOOK_SECRET=
TETRAPAY_WEBHOOK_URL=https://fitician.fit/api/v1/billing/webhooks/tetrapay
```

- [ ] Keep `APP_ENV=production`, existing secure-cookie/encryption/database settings, and the env file's restricted permissions.
- [ ] In TetraPay confirm gateway Fitician for `https://fitician.fit` is Active, desired online/card methods are enabled, and the merchant/customer commission split is correct. No commission percentage belongs in Fitician config.
- [ ] Have the deployment operator use the approved **full Iran** release procedure with backup/restore rehearsal and explicit migration approval. Recreate both API containers and scheduler so the env file is reread. Never deploy to Germany for this change.
- [ ] Check `/api/v1/billing/checkout-methods`: only `tetrapay` should be enabled/default. Check both API replicas, scheduler heartbeat, migrations and admin offers/prices.
- [ ] Authorize and perform the final small live-payment validation separately. Confirm one entitlement, correct full amounts, history and access. Do not start live automated tests.

## 3. Optional separate webhook signing key

- [ ] In TetraPay gateway **Settings**, generate the webhook signing key (`whsec_...`); save it securely when displayed. It is **different from the API key**.
- [ ] Register `https://fitician.fit/api/v1/billing/webhooks/tetrapay` as the live webhook URL. Never point sandbox payments at live callbacks.
- [ ] In `/opt/fitician-iran/.env`, set `TETRAPAY_WEBHOOK_SECRET=<OWNER_PROVIDED_WEBHOOK_SIGNING_KEY>` and `TETRAPAY_WEBHOOK_ENABLED=true`.
- [ ] Apply an approved rollout/recreation of both API containers and scheduler. Keep server clock synchronized.
- [ ] Verify an authorized real signed event and retry behavior. Without a valid signing key the endpoint rejects delivery; never disable signature checks to resolve an error.
- [ ] On rotation update the server key immediately: TetraPay uses the new key even for old event retries. New webhook destinations apply only to newly created links.

## 4. Mobile and rollback

- [ ] Keep Google Play/EAS store and all iOS external checkout disabled. Separate store billing/approval is still required.
- [ ] For an approved **direct Android** build only, set build env `FITICIAN_EXTERNAL_BILLING_ENABLED=true` and `FITICIAN_DISTRIBUTION_CHANNEL=direct`; rebuild the app. EAS `production` always stays closed. Review any regional store policy separately.
- [ ] If payments malfunction, disable new purchases through admin offer availability first; keep verification/scheduler running to recover existing payments.
- [ ] Reconcile outstanding money with TetraPay before disabling credentials or rolling back workers. Retain all transaction history.
- [ ] Apply the recorded prior images through existing regional rollback procedures after approval. Keep the additive migration; never drop payment records as a rollback step.

Detailed architecture, testing and release controls: [tetrapay.md](tetrapay.md).
