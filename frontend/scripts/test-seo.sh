#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
seo_run="fitician-seo-$$"
seo_image="fitician-frontend:seo-check"
cleanup() {
  docker rm -f "$seo_run-frontend" "$seo_run-backend" >/dev/null 2>&1 || true
  docker network rm "$seo_run" >/dev/null 2>&1 || true
}
trap cleanup EXIT
if [[ -z "${SEO_SKIP_IMAGE_BUILD:-}" ]]; then docker build -f frontend/Dockerfile -t "$seo_image" .; fi
docker network create "$seo_run" >/dev/null
docker run -d --name "$seo_run-backend" --network "$seo_run" --network-alias backend -v "$PWD/frontend/scripts/seo-backend.conf:/etc/nginx/conf.d/default.conf:ro" nginx:1.27-alpine >/dev/null
docker run -d --name "$seo_run-frontend" --network "$seo_run" -p 127.0.0.1:4180:80 "$seo_image" >/dev/null
docker exec "$seo_run-frontend" nginx -t
for seo_attempt in $(seq 1 30); do
  if curl --fail --silent http://127.0.0.1:4180/healthz >/dev/null; then break; fi
  sleep 1
done
npm exec --workspace frontend -- playwright test --config playwright.seo.config.ts
