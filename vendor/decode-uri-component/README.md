# decode-uri-component CommonJS compatibility package

Upstream: https://github.com/SamVerschueren/decode-uri-component
Source: npm `decode-uri-component@0.5.1`, MIT license included in the archive.

The decoder implementation is unchanged from the upstream security-fixed 0.5.1.
Only `export default` becomes `module.exports`, and package metadata declares CommonJS,
so Expo 57/query-string 7 can consume the fix without a framework major upgrade.
This addresses GHSA-vcc3-ghjq-m6fr and GHSA-qr28-fpjm-wq7f; no audit exclusion is added.

Verification: `node --test mobile/scripts/verify-decode-backport.test.mjs`.
Remove this package when the Expo-compatible dependency chain consumes the upstream fixed
decoder natively. Expo CLI and Zod were refreshed within existing compatible ranges.

Archive SHA-256: `e6a07727c1d46749d4ad28447729d404aeb4ea591982ac681613d0bdba79f6f7`.
