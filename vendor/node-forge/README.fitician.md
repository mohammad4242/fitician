# Temporary Fitician node-forge backport

Private, unreleased artifact `1.4.1-fitician.1`, based on official `node-forge@1.4.0`.
Only lib/rsa.js incorporates the exact patch from digitalbazaar/forge PR #1152,
commit ceba34402e329f0365134f23fe19898756527d65, fixing GHSA-86w9-cpqp-85rv / CVE-2026-85393.
The upstream PR is not merged and no official patched npm release exists at review time.
Original license is retained in LICENSE. integrity.json records all source hashes.
See docs/mobile-dependency-security.md for review, tests and removal condition.
TODO: replace with official fixed release once both Expo signing paths support it.
