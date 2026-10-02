# Mobile dependency security remediation

## Reproduced baseline

Branch `feat/support-progress`, implementation SHA `cbe39b19ebff694d4e17adc9f1d02033fcfc8026`. Both CI audit command and raw production audit fail: high **6**, critical **0**, moderate **12**. These are six package findings propagating **one** high advisory, not six distinct GHSAs.

Advisory: [GHSA-86w9-cpqp-85rv](https://github.com/advisories/GHSA-86w9-cpqp-85rv), CVE-2026-85393, high, node-forge RSA nested DigestAlgorithm validation. Published official package `1.4.0` remains affected (`<=1.4.0`); no official patched npm version at review time.

| Package | Installed | npm affected range | Direct | Production graph | Exact path |
|---|---|---|---|---|---|
| @expo/cli | 57.0.24 | `<=0.0.0-canary-20231123-1b19f96-4 || >=0.0.1-canary-20231125-d600e44` | No | Yes | mobile → expo → @expo/cli → node-forge (also code-signing-certificates) |
| @expo/code-signing-certificates | 0.0.6 | `*` | No | Yes | mobile → expo-updates → @expo/code-signing-certificates → node-forge; mobile → expo → @expo/cli → @expo/code-signing-certificates → node-forge |
| expo | 57.0.22 | `40.0.0-alpha.0 - 40.0.0-beta.5 || >=41.0.0-alpha.0` | Yes | Yes | mobile → expo → @expo/cli → node-forge |
| expo-updates | 57.0.22 | `<=0.0.1-canary-20240418-8d74597 || >=0.12.0` | Yes | Yes | mobile → expo-updates → @expo/code-signing-certificates → node-forge |
| node-forge | 1.4.0 | `*` | No | Yes | mobile → expo → @expo/cli → node-forge; mobile → expo-updates → @expo/code-signing-certificates → node-forge |
| react-native-nitro-google-signin | 2.3.0 | `*` | Yes | Yes | mobile → react-native-nitro-google-signin → expo (optional peer) → @expo/cli → node-forge |

All rows carry the same GHSA/CVE through npm's metavulnerability propagation. The broad parent ranges describe dependency exposure, not separate cryptographic flaws. There is no compatible patched parent reported. npm's suggested expo-updates 0.11.7 is incompatible with SDK 57 and is rejected.

`npm explain` and `npm ls --all` confirm production dependency edges. npm considers them reachable because Expo is a direct dependency and CLI is a normal Expo dependency; updates directly loads code-signing-certificates; Google sign-in peers on Expo. This is primarily Node-side Expo CLI/iOS signing and update certificate tooling, not proof that node-forge executes in the mobile JS bundle. Actual imports exist in both Expo signing consumers, so removing it as unused is unsafe. Updates is configured in app.config.ts and required release flows remain intact.

## Official upgrade investigation

Current latest SDK-compatible Expo 57.0.26 requires CLI ^57.0.27; CLI 57.0.27 still requires node-forge ^1.3.3 and code-signing-certificates ^0.0.6. Updates 57.0.24 still requires certificates ^0.0.6. Latest certificates 0.0.7 requires node-forge ^1.4.0. These upgrades do not remove the flaw and unrelated upgrades are avoided.

## Exact backport

Source: https://github.com/digitalbazaar/forge/pull/1152
Commit: `ceba34402e329f0365134f23fe19898756527d65` (open, unmerged, contributor-reviewed; not represented as an official released fix).

Base is the installed official node-forge 1.4.0 source. Only `lib/rsa.js` changes: validate the nested DigestAlgorithm child count against the captured optional NULL, after ASN.1 validation and the outer count check. This rejects unconsumed children that permit the exact CVE; existing OID and optional NULL semantics are retained. No cryptographic algorithm is rewritten.

`vendor/node-forge` contains readable source and original dual license, with explicit private backport version `1.4.1-fitician.1`. A reproducibly packed local npm archive, root file dependency and `$node-forge` override resolve both consumers to that source. The lockfile records its SHA-512 integrity. It is not an official npm 1.4.1 release. Frontend Docker copies the archive and readable vendor source before npm ci; EAS ignore rules retain it. No stale vulnerable precompiled dist is included or used by these Node consumers.

npm's actual production audit inventory includes `node-forge@1.4.1-fitician.1`:
this is an installed archive with the original package name, not an audit-exempt
workspace/directory link or renamed package. Current npm tests advisory ranges
with prereleases included. The unchanged high/critical policy additionally calls
a verifier rejecting directory links, checking the package identity and every
installed source SHA-256 against the reviewed manifest, verifying actual resolution
from CLI, certificates and updates, and running the exact upstream regression
vector. A version-label change alone cannot pass this guard.

Repack after reviewed source changes with `npm pack ./vendor/node-forge
--pack-destination vendor --ignore-scripts`, then update the lockfile and rerun all
security/source/regression checks. Do not edit the archive independently.

Baseline upstream regression: fails with missing expected exception on 1.4.0. Patched full upstream unit/security suite: 829 passing, 4 upstream pending. The upstream branch had a stray describe.only, removed only in the temporary test checkout (matching upstream main's test-only correction) so every suite ran. Project regression also checks normal RSA SHA-256 signing and certificate round-trip.

TODO: remove the vendor, root dependency, override and verifier only when an official released fix for this exact GHSA is available in all compatible Expo dependency paths. Require npm ci, audit high/critical=0, regression and native build validation before removal.

## Release verification

Clean npm ci passes; npm 10 compatibility is checked for production builds. All six affected package paths
now resolve the exact backport; no nested registry node-forge remains. Final audit:
high **0**, critical **0**, moderate **15** (remaining existing/moderate propagation).
Expo Router native screens are deduplicated to existing supported 4.26.2, satisfying
its ^4.26.0 requirement; no Expo SDK or native package upgrade was introduced.

Core 127, Web 1203, mobile logic 619, native rendering 368, foundation 63, browser
8 FA/EN at 320/1440px, focused backend/migration 43 and ops 80 checks pass.
Web build/lint, mobile typecheck/release validation, OpenAPI/contracts and secret
scan pass. Existing backend quality debt is unchanged (Ruff zero; mypy 44, format 7
existing diagnostics in reused domains); new Support/Progress modules pass strict
checks. Full backend fresh-process shards pass: 4312 tests, one existing opt-in live-provider
test skipped. Normal local benchmark database migrations corrected the initial
stale-schema failures; no project test was removed or weakened.

Expo doctor passes 19/21 checks after deduplication. Its schema service returned
HTML instead of JSON; the production Expo config resolves correctly with public
test configuration, and repository release/schema validations pass. The other
check recommends 14 newer SDK 57 patch versions; current pinned versions satisfy
the installed SDK's bundled compatibility map. No exclusions were added. Native
Android CI build remains required.

Full CI, main integration, immutable images and production deployment remain
pending. Production read-only inspection finds schema 20260929_165 and immutable
release 49e90f8823fb3816e63445f109d26b679ab6b252, with backup configuration and
acceptance marker present. The normal deployment contract requires encrypted
backup before migration; reviewed feature heads are 166–169. The prepared rollback API smoke passes locally across Support, notifications,
all four body metrics, missing nutrition and all product modes, with zero persisted
fixture rows. No release claim yet.
