# Fitsho authentication setup

Fitsho keeps users and sessions in its backend. Email/password, phone OTP, and Google
authentication all create the same `User` and `AuthSession`, then use the existing session cookie.

## Configuration boundary

Backend values belong in `backend/.env`. Never expose SMTP passwords, IPPanel/Faraz SMS API keys, OTP
HMAC secrets, session settings, or other backend secrets through Vite or browser code.

The only authentication value intended for the frontend is the public Google client ID:
`VITE_GOOGLE_CLIENT_ID` in `frontend/.env`.

Start from the examples:

```bash
cp .env.example backend/.env
cp frontend/.env.example frontend/.env
```

## Local settings

Use these local origins unless the ports are changed:

```env
# backend/.env
FRONTEND_ORIGIN=http://localhost:5173
APP_ENV=local
COOKIE_SECURE=false
SESSION_COOKIE_NAME=fitsho_session

# frontend/.env
VITE_GOOGLE_CLIENT_ID=your-web-client-id.apps.googleusercontent.com
VITE_API_PROXY_TARGET=http://localhost:8001
```

The Vite proxy target must match the backend port. The normal local backend port is `8000`; use
`http://localhost:8000` when running Uvicorn directly. The Docker development compose setup uses
the port configured by that compose file.

## SMTP email

Set the backend provider to SMTP and provide the transactional SMTP account:

```env
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_ADDRESS=no-reply@example.com
SMTP_USE_TLS=true
PASSWORD_RESET_TTL_SECONDS=900
EMAIL_VERIFICATION_TTL_SECONDS=86400
```

The backend uses one SMTP delivery implementation for password-reset, email-verification, and
welcome messages. Password-reset and verification URLs use `FRONTEND_ORIGIN` and point to
`/reset-password` and `/verify-email` respectively. Provider failures are logged generically and
do not expose tokens or credentials in API responses.

## Faraz SMS / IPPanel OTP

For production, set the backend SMS provider and configure the Faraz SMS IPPanel Edge API:

```env
SMS_PROVIDER=ippanel
IPPANEL_API_KEY=...
IPPANEL_BASE_URL=https://edge.ippanel.com/v1/api
IPPANEL_FROM_NUMBER=...
IPPANEL_PATTERN_CODE=...
PHONE_OTP_HMAC_SECRET=...
PHONE_OTP_TTL_SECONDS=300
PHONE_OTP_RESEND_COOLDOWN_SECONDS=60
PHONE_OTP_MAX_ATTEMPTS=5
```

Fitician generates the six-digit OTP itself. The backend sends it as `params.code` for the approved
IPPanel Pattern, whose message body contains the `%code%` variable. The normalized phone number is
sent in Iranian E.164 format. The API key is backend-only: never expose the real key through Vite,
React Native, Expo configuration, frontend source, mobile source, or git.

## Google Identity Services

In Google Cloud:

1. Create an OAuth 2.0 **Web application** client ID.
2. Add `http://localhost:5173` to its authorized JavaScript origins for local development.
3. Add the final HTTPS Fitsho origin, for example `https://fitsho.ir`, to the authorized JavaScript
   origins for production.
4. Set the same client ID in backend `GOOGLE_CLIENT_ID` and frontend `VITE_GOOGLE_CLIENT_ID`.

Fitsho uses Google Identity Services to receive an ID token and verifies that token on the backend.
It requests identity only; it does not request Gmail mailbox access or require a Google client
secret. Keep the Google client ID consistent across each allowed frontend origin. See Google's
[ID-token verification guidance](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token).

## Production checklist

Use a real HTTPS origin and the production cookie contract:

```env
APP_ENV=production
FRONTEND_ORIGIN=https://fitsho.ir
COOKIE_SECURE=true
SESSION_COOKIE_NAME=__Host-fitsho_session
EMAIL_PROVIDER=smtp
SMS_PROVIDER=ippanel
GOOGLE_CLIENT_ID=your-web-client-id.apps.googleusercontent.com
```

Also set strong, backend-only values for `PHONE_OTP_HMAC_SECRET` and
`PRIVATE_FILE_SIGNING_KEY`. Configure `FRONTEND_ORIGINS` only when additional trusted browser
origins are required. Keep the auth rate-limit settings from `.env.example` enabled and tune them
after observing provider capacity.

The example file intentionally uses `fake` email/SMS providers for local tests. A real delivery
smoke test requires valid SMTP and IPPanel credentials and an approved Faraz SMS Pattern; no real
credentials belong in this repository.
