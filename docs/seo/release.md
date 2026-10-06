# Public SEO release safety

This release requires Full CI because it changes production delivery, root dependencies,
and release tooling. Classification remains fail-closed; the frontend-only deployment
scope does not reduce validation requirements.

A successful trusted main SHA must publish immutable images and pass Public SEO delivery
for that same SHA. The release gate selects `frontend-full` only for bounded frontend,
documentation, dependency, and release-tooling paths. Backend, native, schema, shared
core, and agent changes cannot use this path. Full-stack deployment rejects this path.
The existing component deployer verifies the actual running frontend SHA, cumulative
image inputs, latest main identity, production health, and unchanged unrelated services.
It preserves backend, worker, agent, database, and original fallback image tags and
rolls the frontend back on verification failure.

The running frontend was released from divergent commit
`61416f1f56b87d66cd4a5095a1d56864280c9fc8`. Its existing Web appearance behavior is
retained in this release; native changes from that branch are excluded. A divergent
baseline is permitted only after exact-main-SHA Full CI proof and cumulative image-input
scope validation. Ordinary component releases retain strict ancestor checks.

Vite preview serves prerendered public documents and the member app shell separately,
matching production nginx. This prevents prerendered landing video requests on `/install`
during browser regression checks. Production API/media prefix routing remains authoritative.

Local release verification: 151 frontend Vitest files / 1,245 tests; 42 SEO Playwright
checks; 87 operations tests. Production deployment and live checks are separate gates.
