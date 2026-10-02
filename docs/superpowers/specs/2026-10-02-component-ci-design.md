# Component CI and releases

Approved architecture: one CI router calls reusable frontend/backend workflows.
A deterministic Python classifier chooses component, medium, or full validation.
Unknown paths, schema/contracts, infrastructure, dependencies, security, and worker
runtime changes require full validation. Backend scopes include whole domain suites
and coupled regression/entitlement suites. Mobile validation never releases VPS images.

Only successful exact-SHA validation publishes release evidence. Production CD reads
that run's evidence and successful image jobs, then deploys the selected components.
Deployment is serialized separately from cancellable validation. Component deployment
uses --no-deps, both API replicas for backend, no migrations, health/public smoke,
unchanged unrelated container IDs/start times, and component rollback. Persistent
frontend/API/worker/agent tags support mixed releases and full rollback.

Nightly and manual full validation exercise all existing comprehensive gates without
automatic deployment. This workflow redesign itself requires the full push release.
Manual component deployment still validates exact SHA and checks cumulative changes
since the currently running component, refusing unsafe or uncovered changes.

Existing backend quality debt is reported and compared to the exact CI base SHA;
whole-domain Ruff/format/mypy diagnostics may not increase. Existing critical
backend typing checks remain strict. Core artifacts are reused only within one
exact-SHA run. Native-only dependency/config changes never release VPS images.
