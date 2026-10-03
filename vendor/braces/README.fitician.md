# Fitician local security patch

This is a local patch, not an upstream release. Source: npm `braces@3.0.3`.
Upstream archive SHA-512 (base64):
`yQbXgO/OSZVD2IsiLlro+7Hf6Q18EJrKSEsdoMzKePKXct3gvD8oLcOQdIzGupr5Fj+EDe8gO/lxc1BzfMpxvA==`.
The downloaded archive was checked against this registry integrity before patching.

Addresses GHSA-vfj7-8cjw-p6xm (CVE-2026-93687):
https://github.com/advisories/GHSA-vfj7-8cjw-p6xm
https://github.com/micromatch/braces/issues/70
No upstream patched version was available when reviewed on 2026-10-03.

Parsing rejects more than 128 nested brace/parenthesis containers with SyntaxError.
An iterative depth check protects compile, expand and stringify from externally
supplied deep or cyclic ASTs before their recursive walkers run. Parent and prev
links are not traversed. The limit cannot be disabled through options. Ordinary
brace expansion semantics and the existing expansion range limit are unchanged.

`3.0.4-fitician.1` distinguishes the actual patched package from vulnerable upstream
3.0.3. The root file dependency and override install the same immutable archive
for glob consumers. The dependency audit first checks the installed source hashes
and runs the advisory reproduction; its existing high/critical gate remains intact.
This version label alone is not evidence that the fix works.

`integrity.json` records SHA-256 for every executable source and package metadata.
Regression tests cover the depth boundary, all four APIs, mixed containers,
external ASTs/cycles, and ordinary glob matching. Keep the original MIT license.
Replace this patch with a verified official fix when available.
