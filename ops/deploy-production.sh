#!/usr/bin/env sh
set -eu

compose_file=${COMPOSE_FILE:-compose.prod.yaml}
image_tag=${IMAGE_TAG:?IMAGE_TAG is required}
previous_image_tag=${PREVIOUS_IMAGE_TAG:-}

compose() {
  IMAGE_TAG="$image_tag" docker compose -f "$compose_file" "$@"
}

rollback() {
  if [ -z "$previous_image_tag" ]; then
    echo "Deployment failed and PREVIOUS_IMAGE_TAG is not set" >&2
    return 1
  fi
  echo "Rolling back to previous immutable image tag"
  image_tag="$previous_image_tag"
  compose pull
  compose up -d --wait --remove-orphans
}

if ! compose pull; then
  echo "Unable to pull immutable production images" >&2
  exit 1
fi

if ! compose up -d --wait --remove-orphans; then
  rollback
  exit 1
fi

if ! compose exec -T backend curl -fsS http://127.0.0.1:8000/healthz >/dev/null; then
  echo "Backend readiness check failed" >&2
  rollback
  exit 1
fi

if ! compose exec -T frontend wget -qO- http://127.0.0.1/healthz >/dev/null; then
  echo "Frontend readiness check failed" >&2
  rollback
  exit 1
fi

domain=$(compose exec -T caddy sh -c 'printf %s "$FITICIAN_DOMAIN"')
if [ -z "$domain" ] || ! curl --fail --silent --show-error \
  --resolve "$domain:443:127.0.0.1" "https://$domain/healthz" >/dev/null; then
  echo "HTTPS ingress readiness check failed" >&2
  rollback
  exit 1
fi

echo "Production deployment verified for immutable image tag ${image_tag}"
