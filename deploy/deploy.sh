#!/usr/bin/env bash
# Pull the given image tag and (re)start the stack. Run on the VM from /opt/dashboard.
#   deploy/deploy.sh [IMAGE_TAG]
# Migrations run first (the `migrate` service); services restart only if their image changed.
set -euo pipefail
cd "$(dirname "$0")/.."

tag="${1:-}"
if [ -n "$tag" ]; then
  # Record the deployed tag in .env so restarts and reboots keep running the same version.
  if grep -q '^IMAGE_TAG=' .env; then sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=${tag}/" .env; else echo "IMAGE_TAG=${tag}" >> .env; fi
fi

docker compose --profile public pull --quiet
docker compose --profile public up -d --remove-orphans --wait --wait-timeout 300
docker image prune -f >/dev/null
docker compose --profile public ps
