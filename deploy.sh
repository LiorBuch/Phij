#!/usr/bin/env bash
set -euo pipefail

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

APP_VERSION="${APP_VERSION:-0.1.0}"
IMAGE_PREFIX="${IMAGE_PREFIX:-ghcr.io/liorbuch/phij}"

export APP_VERSION IMAGE_PREFIX

for service in web server camera; do
  image="${IMAGE_PREFIX}-${service}:${APP_VERSION}"
  echo "Pulling ${image}"
  docker pull "${image}"
done

echo "Starting Phij ${APP_VERSION}"
docker compose up -d --no-build --remove-orphans
