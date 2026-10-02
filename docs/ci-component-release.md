# CI and component releases

`ci.yml` is the only automatic push/PR router. Its first job logs the selected
path, flags, and whole backend test suites. Reusable component workflows do not
have push triggers. Successful main push runs pass exact-SHA release evidence to
`deploy-production.yml`; a successful validation alone does not authorize release.

| Change | Validation | Production |
|---|---|---|
| Web src/public, isolated UI/tests | Frontend tests, lint, core build, production build | Frontend image only, `--no-deps frontend` |
| Allowed backend domain business code | Whole domain/coupled suites, auth/entitlement/safety/API regressions, quality and current typing checks, contracts | Backend image only, both API replicas |
| Mobile only | Vitest, native tests, foundation checks, typecheck, validation, core build | None; Android/iOS releases remain manual |
| Multiple safe components | Union of affected validations | Only affected deployable images/components |
| Safe core presentation helpers/i18n | Core/contracts plus Web and Mobile consumers | Frontend if runtime code changed |
| High-risk or unknown files | Full repository gates | Existing full immutable-image release |

Backend scopes currently cover workouts, workout cycles/reviews, nutrition,
exercises, training templates, profile, athlete state, program timeline, and
conversations. Workout changes include cycles/reviews/templates/exercises and
related consumer suites; nutrition changes include its entire suite and coupled
athlete/timeline/conversation suites. All fast backend scopes include entitlement,
auth, health, error, medical-safety, time, and mobile API contract regressions.

Full fallback includes migrations, models/schemas/enums/routers, authentication,
security/access/billing, database/cache/Redis/jobs, providers, worker/scheduler
transitive runtime dependencies, dependency manifests/locks, generated/shared API
contracts, Web auth/payment infrastructure and routing/bootstrap, Docker/nginx/Caddy/Compose, production config, ops, and workflows.
Only an explicit core helper allowlist and i18n are medium-risk shared changes;
unknown shared changes require full validation. Worker imports of `app.main` only
register ORM/API modules; actual worker business imports remain full-risk.

Existing domain quality debt is reported against the exact base SHA. Ruff,
format, and mypy run on whole changed domains and prohibit new diagnostic counts;
existing critical backend lint/typing checks remain strict. This avoids unrelated
application cleanup. Full CI retains all existing comprehensive gates.

## Operations

- Full validation: dispatch **Fitician CI**, `mode=full` (no image push/deploy).
- Full release: push a high-risk change to main, or dispatch `mode=release`, then
  dispatch **Deploy Fitician production** with that verified SHA.
- Frontend/backend manual release: dispatch the respective **Only CI** workflow
  on main with `deploy_production=true`. Validation/image checks run first.
  `previous_image_tag` is optional and, when supplied, must match the running SHA.
  Manual component dispatch rejects a high-risk or mixed HEAD diff.
- Nightly: **00:23 UTC**, current main, all full gates and image builds, no push or
  deployment. Existing weekly heavy load/failure drills remain unchanged.
- PRs validate only; they never publish production images or deploy.

npm, uv lockfile, and Docker BuildKit caches remain enabled. Core build artifacts
are reused by Web/Mobile/browser checks within the same exact-SHA CI run. No
node_modules or cross-SHA build-output cache is used.

Production deployments share a non-cancellable serialized queue. Obsolete
component candidates are skipped. Before rollout, cumulative changes since the
running component must be safe and covered by this exact run's suites/shared
checks; cancelled or failed predecessors cannot smuggle an unvalidated change.
If this refuses a release, use a new Full CI release rather than bypassing it.

Component deployment snapshots unrelated IDs, restart counts, and start times,
checks target SHA/readiness and HTTPS ingress, and rolls back only the component
on failure. Backend compares image Alembic heads to the DB without running any
migration. Frontend rollback restores the prior frontend; backend rollback
restores both API replicas. DB/Redis/agent/workers are preserved.

Successful component tags persist as `FRONTEND_IMAGE_TAG` and
`BACKEND_API_IMAGE_TAG`; worker/agent tags keep the full-release baseline.
Full releases reset all component overrides, retain backup/schema approval and
scalability acceptance, and restore actual previous component versions on a
schema-compatible rollback. Schema-changing failures retain the existing manual
backup recovery rule. Do not use mutable `main`/`latest` tags for deployment.

Release-plan artifacts expire after 30 days; old manual full deployments require
fresh successful full release evidence. Medium deployments use separate component
rollouts; each retains its own rollback rather than a cross-component transaction.
