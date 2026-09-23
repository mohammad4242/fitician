# Fitician EAS release configuration

`mobile/eas.json` defines four isolated profiles:

- `development`: internal development-client build (APK on Android, IPA on
  iOS) on the `development` channel;
- `preview`: remotely signed internal-test build (AAB on Android, IPA on iOS)
  on the `preview` channel;
- `production-device`: remotely signed, installable release APK using the
  production environment, application ID, runtime values, and Android keystore;
- `production`: remotely signed auto-incremented store build on the
  `production` channel, submitted as an internal-track draft on Android.

All profiles use EAS-managed versions and remote signing. The app uses the
`appVersion` runtime policy, so an OTA update cannot cross a native runtime
change. The app config permanently links to the existing EAS project, so
`EAS_PROJECT_ID` is optional and is not required for ordinary EAS commands.
Build-time API values still come from the matching EAS environment; production
OTA updates require an explicit release review.

Production API and frontend values must both be the public origin
`https://fitician.fit`. The API base is an origin because request paths already
start with `/api`. The production app-link host is exactly `fitician.fit`.

Configure these values in EAS environments or protected CI secret storage:

| Name | Type | Scope |
| --- | --- | --- |
| `EXPO_PUBLIC_API_BASE_URL` | environment value | mobile builds and updates |
| `EXPO_PUBLIC_FRONTEND_ORIGIN` | environment value | mobile builds and updates |
| `EAS_PROJECT_ID` | optional environment override | exceptional project tooling only |
| `EXPO_UPDATES_URL` | environment value | mobile builds and updates |
| `FITICIAN_APP_LINK_HOST` | environment value | verified production associated domain |
| `GOOGLE_SERVICES_JSON` | protected file secret | Android FCM build config |
| `EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID` | environment value | Google native sign-in |
| `FCM_SERVICE_ACCOUNT_JSON` | protected backend/worker secret | notification delivery |

Never commit signing files, Google service files, FCM service accounts, API
keys, or `.env` files. `GOOGLE_SERVICES_JSON` is consumed only as a protected
file path by `app.config.ts`; it is not checked into the repository.

The required commands are:

```bash
eas build --profile development --platform android
eas build --profile preview --platform android
eas build --profile production-device --platform android
eas build --profile production --platform android
eas build --platform ios --profile development
eas build --platform ios --profile preview
eas build --platform ios --profile production
eas update --channel development --platform android
eas update --channel preview --platform android
```

Production channel updates and production submissions remain manual release
steps after the acceptance matrix and crash/ANR review pass.

Build and install `production-device` on a physical phone first. Produce the
store `production` AAB only after the signed APK passes launch and a real
network-backed production workflow with no local backend or port forwarding.
