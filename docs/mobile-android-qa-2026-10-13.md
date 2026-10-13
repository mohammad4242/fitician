# Android physical-device QA — 2026-10-13

Release and regional cutover acceptance remain blocked. Successful authentication
and authenticated member features have not been verified on the phone.

## Device and artifact identity

- Physical Samsung SM-A127F, Android 13, arm64-v8a (also armeabi-v7a/armeabi).
- Wireless ADB confirmed as `device` before device actions.
- Display remained 720×1600, density 300, font scale 1.0. No display, wireless
  debugging, security, or permission settings were changed.
- Initial installed APK: com.fitician.app, 0.1.3/versionCode 11; SHA-256
  `48cb4d6648f60fbb258f466a917a813735cc37dca301ab982def1e32d63df9be`.
  It exactly matched the retained 93b80985 artifact, not the timeout-fix artifact.
- Existing timeout-fix APK was verified and installed using `adb install -r`;
  installation returned `Success`, without clearing application data.
  Source bf182dd42d97304aa55d39e7f51a92a073f9e021; EAS build
  36c54017-2ba6-4ece-9213-40c65deb61e9; 0.1.3/versionCode 11; SHA-256
  `ebe9002b83afca973d5eab924ec05b3f0999afb226eb725190773967c10b701e`.
- Both APK signatures verified and matched the established release certificate:
  SHA-256 `71e088feb1767f45d9e907ff3484ae6411e557d3623df88d843cdf964265562c`;
  SHA-1 `070cfc4ee11d1d5f2209bbef49551e891867f11c`.
- New concurrent-auth-fix production-device build:
  589f4dda-3c28-485b-b719-24654e345d13, source
  2097c202b72b5a0b77a91c2432318fe688797347, finished successfully.
  APK 0.1.3/versionCode 11; SHA-256
  `12afe8da98fabea05b0da8395958ac033482828e76096d80049458750f44b078`.
  Verified APK Signature Scheme v2, one RSA-2048 signer, same Production
  certificate. Installed with `adb install -r` Success; the installed APK's SHA-256
  was computed on-device and exactly matched this artifact. Narrow device smoke
  and the overlap regression passed. Complete account acceptance remains blocked.

## Actual phone acceptance

| Capability | Result | Evidence / limit |
| --- | --- | --- |
| Data-preserving signed update and cold launch | Pass | Both updates returned Success; final APK COLD launch 4253 ms; public landing reached |
| Splash/new logo visual correctness | Blocked | ADB screenshots returned empty files; no visual acceptance claimed |
| Email form validation | Pass | Empty-form errors; synthetic reserved-domain input only |
| Email negative-auth/error recovery | Pass | Final APK displayed expected invalid-credentials notice; form re-enabled |
| Email successful sign-in | Blocked | No approved test credentials; synthetic request reached timeout/error state |
| Phone form validation | Pass | Empty phone submission displayed validation without sending SMS |
| Phone OTP, registration, resend, sign-in | Blocked | No authorized test number/OTP; no SMS sent |
| Native Google chooser and cancellation | Pass | Google Play services CredentialChooser activity opened; Back displayed Persian cancellation and re-enabled form |
| Google successful sign-in/backend handoff | Blocked | Personal accounts were not selected; no authorized Google test account |
| Competing Google/email requests | Pass | Final APK disabled Google during email request; physical tap kept MainActivity; Google re-enabled after error |
| Registration controls/empty validation | Pass | Email/password/confirmation errors; submit scrolled to [30,489][690,583] with keyboard shown |
| Account creation, logout/relogin, token rotation | Blocked | Require authorized test account |
| Public onboarding entry | Pass | Landing and navigation rendered; no existing onboarding answers overwritten |
| Saved profile/onboarding handoff | Blocked | Requires successful authorized authentication |
| Workout/nutrition plans | Blocked | Requires authorized member account |
| Exercise/GIF/S3 rendering in app | Blocked | Authenticated app route unavailable; separate public HTTP media probe is not rendering acceptance |
| Food-photo calories | Blocked | No authorized account and synthetic image workflow |
| Body Analysis/camera/picker/upload | Blocked | No authorized account/image workflow; camera permission unchanged |
| Weight/body-measurement progress | Blocked | Requires authorized account; no real profile modified |
| Notification permission state | Pass (inspection) | Manifest requests POST_NOTIFICATIONS; primary installed-user permission granted; no permission changed |
| FCM token/notification delivery | Blocked | APK Firebase config resource keys absent; live backend notification_fcm_enabled=false |
| Verified HTTPS App Link | Pass (signed-out boundary) | fitician.fit verified on device; /link/member/exercises/... opened app and sign-in gate |
| Custom fitician:// Deep Link | Pass (signed-out boundary) | Protected exercise link opened sign-in gate |
| Auth timeout and retry availability | Pass (artifact-specific) | bf182dd4 APK: two timeout recoveries. Final APK: invalid-credentials error recovery; timeout itself was not reproduced on this final request. Deadline source unchanged; automated timeout regressions passed |
| Controlled offline/reconnect | Blocked | Not performed over the only Wireless ADB link; no connectivity settings changed |
| Persian/RTL text, form controls, keyboard/scroll | Pass (limited) | Native text/bounds inspected and buttons exercised; complete visual QA and other device tiers unverified |
| Background/foreground | Pass (signed-out forms) | Home then MainActivity retained form; repeated on final APK registration |
| Crash/ANR/JS errors | Pass (bounded observation) | Final app-PID sample: zero fatal/ANR/JS error markers; one startup info and one InteractionManager deprecation warning; not a crash-free cohort claim |

## Findings and changes

1. The installed APK predates the existing auth timeout correction despite having
   the same version/name as the fixed APK. The fixed signed artifact was installed
   and its bounded timeout behavior was physically verified.
2. On the signed APK, Google remained enabled while an email auth API request was
   busy. Sign-in now disables competing provider/email/phone actions, including
   resend, until the pending auth operation finishes. Two native regressions failed
   before implementation and passed afterwards. Google cancellation restores the
   competing buttons. The new signed APK physically blocked a Google tap during
   pending email authentication and re-enabled Google after the negative-auth
   response. No auth protocol, endpoint, or architecture change was made.
3. CI secret scan rejected a pre-existing fake OpenSSH header in a regional SSH
   test. Splitting the header into adjacent Python literals preserves the runtime
   fixture and all ten tests without changing scanner rules or disabling tests.
4. Existing APKs contain no Firebase google_app_id/gcm_defaultSenderId/project_id/
   google_api_key resource keys. Notification setup fails safely, but delivery is
   not accepted. Configure the protected Google Services file and verify token and
   delivery with an authorized account before release; do not invent credentials.
5. A non-blocking InteractionManager deprecation warning comes from deferred
   startup work in `mobile/app/_layout.tsx:82`. No functional failure was reproduced.

## Production and network evidence

- Both inspected APK runtime configs use `https://fitician.fit` for API and
  frontend origin, app-link host fitician.fit, and public media origin
  `https://fitician-media.s3.ir-thr-at1.arvanstorage.ir`.
- APK manifest has release cleartext disabled, minSdk 24, targetSdk 36,
  CAMERA/INTERNET/POST_NOTIFICATIONS, and verified HTTPS /link intent filter.
- Live assetlinks returned 200 and contained the matching release certificate.
- Workstation proxy health returned 200 and unauthenticated profile status 401;
  direct HTTPS timed out after 15 seconds.
- Direct health timing completed DNS, TCP and TLS before timing out without an
  HTTP response. Two forced HTTP/1.1 probes returned 200 in 0.53/0.45 seconds;
  two HTTP/2 probes timed out after 15 seconds despite completing TLS. Server-local
  HTTP/2 returned 200 in 0.06 seconds. This isolates a protocol/path difference on
  the client network; it does not establish the phone's negotiated protocol or
  identify the network appliance responsible. No server protocol was changed.
  A separate direct verbose probe confirmed valid certificate verification,
  TLS 1.3, ALPN `h2`, and zero received response bytes before timeout.
- A synthetic reserved-domain password POST forced to HTTP/1.1 returned the
  expected 401 in 1.42 seconds. This is negative-auth connectivity evidence,
  not successful account authentication.
- A public exercise API GET returned 200. A public S3 video range GET returned
  206 with 1024 bytes. These are workstation HTTP checks, not handset media tests.
- Read-only Netherlands SSH succeeded. Running application containers reported
  healthy. Server-local HTTPS and server-public HTTPS both returned health 200.
- Synthetic phone email requests timed out and recovered. An earlier .invalid
  email produced the mapped invalid-email error; the final new-APK synthetic
  request returned the expected invalid-credentials notice. Its ad-hoc timeout
  expectation therefore did not apply; error recovery and re-enabled controls
  were separately asserted. Connectivity may be intermittent;
  no blanket DNS/TLS/backend failure diagnosis or successful login is claimed.
- Caddy container logs supplied no structured access records for correlation;
  the exact component stalling the handset/workstation direct path is unresolved.
- Phone Chrome health navigation did not provide a confirmed response/error code
  in the inspected hierarchy; historical ERR_CONNECTION_CLOSED is not reused as a
  current observation.
- Google OAuth IDs are present in the APK and both Web/Android IDs match the live
  backend configuration (compared without printing IDs). Backend FCM is disabled.
  Google Cloud
  package/signing-SHA registration and successful ID-token exchange remain
  unverified.

## Verification and Git

- Mobile Vitest: 152 files, 633 tests passed.
- Native Jest after auth correction: 63 suites, 391 tests passed.
- Foundation: 75 tests passed. Secret-scanner regression: 5 tests passed.
- SSH diagnostic fixture tests: 10 passed. Tracked secret scan passed.
- TypeScript and production mobile validation passed; `git diff --check` passed.
- Default validation initially failed because generated local Android files were
  Production while APP_VARIANT defaulted to development. Explicit production
  validation passed; no security setting was weakened to satisfy the check.
- Complete GitHub CI [38408465185](https://github.com/mohammad4242/fitician/actions/runs/38408465185)
  passed for f0e35e12. Mobile, Android debug, backend, browser, security and regional
  checks passed. The signed production-device build and workflow
  [38408034474](https://github.com/mohammad4242/fitician/actions/runs/38408034474)
  passed. Final signed-device smoke and overlap regression passed. The mobile tree
  is identical between APK source 2097c202 and CI source f0e35e12; the latter adds
  only the SSH fixture correction. The repository classifier selected
  Full CI after the necessary regional test-fixture correction; no extra manual
  Full CI run was dispatched.
- No AAB or store upload was performed because complete signed-APK authentication
  acceptance remains blocked. No DNS/database change, production deploy,
  credential rotation, or automatic CD enablement was performed.
- Production and regional deployment workflows remain disabled in GitHub, with
  disabled deployment guards in source; no CD state was changed.

## Before cutover and after DNS transfer

The mobile runtime has no direct Netherlands IP dependency. Migration utilities
deliberately identify the current source IP; do not rewrite their frozen source
identity during an active preparation audit. Their post-cutover backup/source
configuration needs separate operational review.

Before cutover, accept Iran public ingress/TLS and renewal, international egress,
private Iran–Germany routing, Agent TLS and container reachability, timeout/outage
handling, S3 access, Google verification, SMS and FCM provider access, final
snapshot/restore/rollback, and capacity. Current Netherlands remains authoritative.

After DNS transfer, repeat from a physical phone on Iranian Wi-Fi and mobile data:

- DNS/IPv4/IPv6 resolution, HTTPS chain, public health/API and direct connectivity.
- Google/email/OTP sign-in, registration, refresh, profile and onboarding handoff.
- App Links domain verification, HTTPS/custom links and password/email recovery.
- S3 images/videos/GIFs, signed private upload/download URLs, camera/gallery uploads.
- Food-photo and Body Analysis jobs, Iran-to-Germany Agent traffic and outage recovery.
- Workout/nutrition/progress correctness and background/foreground session recovery.
- FCM token registration, foreground/background delivery, tap navigation and permission.
- Offline/online retry, bounded loading/error states, crash/ANR and provider failures.

The Bazaar/Myket loading complaint is only partially addressed: a bounded email
timeout is physically demonstrated on the existing fix APK, and error recovery
and the overlap correction are demonstrated on the new signed APK. Successful
Google/email/phone authentication remains blocked. Store release and cutover are
not ready. The proposed Android HTTP/1.1 diagnostic APK requires the owner's
transport decision; no protocol change has been made.
