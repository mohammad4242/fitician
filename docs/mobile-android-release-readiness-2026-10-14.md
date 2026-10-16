# Android release candidate — 2026-10-14

Not Store Ready. Final APK/AAB builds remain gated on real login and member
acceptance. This report supersedes the Netherlands network snapshot for current
endpoint observations; yesterday's handset evidence remains historical.

## Build decision and existing artifact

A new build is required. Current code at db3493c9 adds Agent-network recovery
messages and resumable behavior that the retained APK source 2097c202 does not
contain. This candidate additionally bounds stalled native operations. Changing
DNS alone requires no app-origin change: Production remains https://fitician.fit.
There is no Netherlands IP in mobile source/runtime configuration.

Retained artifact, not a final release candidate:

- File: `/home/mohammad/project/fitician/artifacts/android-qa-20261013/Fitician-production-device-0.1.3-11-2097c202.apk`
- Size: 230238074 bytes. Version: 0.1.3. Version code: 11.
- Source: 2097c202b72b5a0b77a91c2432318fe688797347.
- SHA-256: `12afe8da98fabea05b0da8395958ac033482828e76096d80049458750f44b078`.
- Signature reverified: release certificate SHA-256
  `71e088feb1767f45d9e907ff3484ae6411e557d3623df88d843cdf964265562c`.
- Historical data-preserving update was verified on the phone on October 13.
  Reconnected October 14: Samsung SM-A127F, Android 13, arm64-v8a. Installed
  code 11 base-APK hash matches the retained artifact. The actual email entry
  screen was inspected with empty fields. The owner then personally completed
  email/password login with an authorized test account. Actual authenticated
  member tabs, existing workout/exercise lists and nutrition summary loaded.
  No new physical update is claimed today.

Before final builds, confirm the highest version code in both store consoles and
EAS, then use a strictly higher release code. Preserve remote Production signing.
Do not reset user data to resolve an update/signature mismatch. No store upload,
version increment, final APK, or final AAB was performed by this task.

## Current endpoint and provider evidence

- Direct no-proxy HTTPS health returned 200 with both HTTP/1.1 and HTTP/2 from
  194.33.105.56 (Iran). Yesterday's client HTTP/2 failure was not reproduced today;
  no protocol downgrade or server modification was introduced.
- Luna's read-only live App Links check found the expected package com.fitician.app
  and established certificate fingerprint. Device domain acceptance is unverified today.
- EAS Production inventory contains Android/Web Google IDs and the public media
  origin, but no GOOGLE_SERVICES_JSON or EXPO_UPDATES_URL. No values were exposed.
- Read-only Iran backend settings show Google IDs configured, frontend origin
  https://fitician.fit, public media origin
  https://fitician-media.s3.ir-thr-at1.arvanstorage.ir, FCM disabled and no service
  account. No provider was enabled and no Production/database setting was changed.
- Google signing registration, international verifier access, successful token
  exchange and current media rendering require real acceptance. ID presence alone
  does not establish working Google login.
- Both Iran backend replicas currently use image tag
  bf182dd42d97304aa55d39e7f51a92a073f9e021. New backend recovery behavior must
  not be assumed deployed. Read-only source inspection identified legacy Agent
  errors persisted as connection_failure rather than agent_network_unavailable.
  The legacy worker retries are bounded and eventually terminal if workers run.
  No deployment occurred.

## Local corrections and limits

- Authentication/profile HTTP requests retain 30-second deadlines. Other JSON,
  multipart uploads and binary downloads now have 180-second deadlines including
  response-body consumption. Native fetch is aborted; operations are not replayed.
  Existing 60-second AI completion remains supported. Timeout is an error, not an
  assertion that a mutating operation was rolled back on the server.
- Native Google stages share a 90-second deadline and safe Persian recovery text.
  Late responses cannot open fallback sheets or return credentials after timeout.
  Competing native retries remain blocked until the SDK operation actually settles.
  The SDK has no cancellation method. If it never settles after dismissal, email
  remains available; Google requires process restart. Physical behavior is unverified.
- Upload-manager structural cancellation still does not abort fetch immediately;
  real AbortSignal cancellation and the new timeout do. This predates the changes.
- AI features remain present. Existing Agent-network UI/worker recovery code is
  retained, including later retry/recovery without installing another app. Mock
  and isolated recovery tests are not physical Iran-to-Germany acceptance.
- EAS documentation now states the required public media/Web OAuth values, optional
  OTA behavior, actual FCM requirements and safe private reviewer-account handoff.
- Legacy Agent connection failures now display a generic service-connection
  message in body results rather than incorrectly naming OpenRouter. Other body
  providers keep their original messages. Food-photo responses omit provider
  identity, so their connection-error copy stays generic. Queued and terminal
  cases have regressions; no specific network cause is inferred from the legacy
  generic code. This is an app-only compatibility correction.
- Profile Edit now reveals the measured personal editor, including section
  switches, delayed initial layout and a cleared save notice. Screen exposes an
  optional scroll reference while retaining keyboard-focus scrolling. The
  defect was observed on the installed APK; the correction has native
  regressions and still needs physical acceptance on the updated signed APK.

## Verification and blocked acceptance

- Deadline regressions: 8 failures before implementation; focused final suite
  43 passed including late native settlement/retry behavior.
- Mobile suite: 152 files / 642 tests passed before the final additional focused
  retry case. Native suite: 63 suites / 392 tests passed.
- TypeScript, production mobile validation, tracked secret scan and diff checks passed.
- Existing main CI run 38549744694 failed in the body-analysis Agent E2E
  fixture after health preflight was added, and in an admin template deletion
  assertion. The admin file passed all 11 tests on focused local reproduction;
  no unrelated frontend code was changed. The Agent fixture now supports public
  health preflights and preserves the authenticated POST/image/result assertions.
  Its focused E2E passed on a new isolated local test database; Ruff checks passed.
  New candidate CI must pass.
- ADB confirmed the handset after reconnects on changing Wireless ADB ports.
  UI actions resolve the active authorized model afresh. No debugging/security
  settings were changed. Input values, passwords and OTPs were not output.
- Real email login: Pass on the retained signed APK. The owner confirmed the
  method and authorized test-account use; authenticated UI was observed via ADB.
- Cold-process session restore: Pass. ADB cold launch returned 2099 ms, and
  member home with existing plans returned without credential entry. The restore
  client invokes native refresh. The new process had zero observed fatal/JS
  error entries and zero ANR mentions during this checked window.
- Existing workout/exercise lists and nutrition calorie/macro summary: Pass
  for read-only content. Current account's generation/management access is
  expired or disabled per UI; no entitlement was granted or bypassed.
- Progress overview/body empty state: Pass. Populated measurement charts are
  unverified because the current test account has no measurement history.
- Exercise-detail media: Blocked/partial. The detail link was tapped, but
  UIAutomator could not obtain its hierarchy; Back returned correctly. Playback,
  GIF pixels and image rendering are not claimed verified.
- Profile loads. Submitting unchanged values returned to member home with no
  observed error; changed-value persistence has not been established. No profile
  field value was edited. The Edit control physically left the form below the
  viewport; manual scroll revealed it. A scoped editor-scroll correction and
  regressions now exist, but require a new signed-device build for acceptance.
- Legacy outage regressions: 2 failures before correction; 13 model/unit tests
  and 24 native UI tests passed afterward. TypeScript, production validation,
  diff checks and Luna review passed. CI for the latest candidate is still required.
- Phone and Google successful login: Pending personal entry/OTP on the phone.
- Profile saves, existing plans, exercise media, history, progress and settings:
  Partial as detailed above; profile writes and media/filled-history acceptance
  remain unverified.
- AI unavailable/recovery behavior on a phone: Blocked. Agent communication is
  disconnected per owner; no Production connectivity or feature flags were changed.
- Push token, delivery and notification navigation: Blocked by absent Firebase
  configuration/service account, disabled backend provider and no device session.
- Reviewer access: Blocked. Provision a dedicated least-privileged synthetic
  account through an explicitly authorized process; do not write the user database,
  borrow real member data, or bypass authentication. Supply credentials only in
  private store review fields after verifying normal sign-in.

Full CI 38564212249 passed for source 2bd04e8f, including backend, Android,
mobile and browser checks. Subsequent profile-scroll source changes passed all
63 native suites / 400 tests and TypeScript locally. Latest-source CI and signed
physical acceptance are still required before merge/release.

Fresh EAS inventory after reconnect confirmed GOOGLE_SERVICES_JSON absent,
Google Android/Web IDs and media origin present, EXPO_UPDATES_URL absent, and
remote Android version code 11. Local Firebase/service-account files were not
found. Final release code must still exceed the highest code in both stores.

All prior Bazaar/Myket defects are not confirmed resolved. The previous timeout
and overlapping-login fixes have historical handset evidence; today's new
deadline protection still requires a diagnostic signed-device test before final
APK/AAB approval. Final artifacts and Store Ready status must not be inferred
from local or CI tests.
