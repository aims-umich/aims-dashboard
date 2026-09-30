#!/usr/bin/env bash
# Set one value in /opt/dashboard/.env without an editor, and without the value touching the
# terminal history or the process list. Run it from your laptop:
#   ssh -t -i ~/.ssh/aims_dashboard ubuntu@<vm> /opt/dashboard/deploy/set-secret.sh GUARDIAN_API_KEY
set -euo pipefail
cd "$(dirname "$0")/.."

name="${1:?usage: set-secret.sh NAME   (for example GUARDIAN_API_KEY)}"
grep -q "^${name}=" .env || { echo "Unknown setting ${name}. Known ones:"; grep -oE '^[A-Z_]+' .env; exit 1; }

read -r -s -p "Paste the value for ${name} (input is hidden), then press Enter: " value
echo
[ -n "$value" ] || { echo "Nothing entered; .env unchanged."; exit 1; }
case "$value" in *[[:space:]]*) echo "The value contains spaces or line breaks; check what you copied."; exit 1 ;; esac
case "$value" in *"'"*) echo "The value contains a single quote; set it by hand."; exit 1 ;; esac
# Docker Compose expands $ and treats # as a comment in unquoted .env values; single quotes keep them literal.
case "$value" in *'$'*|*'#'*) value="'${value}'" ;; esac

# Rewrite through a temp file with awk, so no character in the value is treated as special.
tmp=$(mktemp .env.XXXXXX)
chmod 600 "$tmp"
NAME="$name" VALUE="$value" awk -F= '
  $1 == ENVIRON["NAME"] { print ENVIRON["NAME"] "=" ENVIRON["VALUE"]; next } { print }
' .env > "$tmp"
mv "$tmp" .env
chmod 600 .env
echo "Saved ${name} (${#value} characters). Restarting the collectors..."
docker compose up -d --no-deps ingest >/dev/null
echo "Done. Check it with: curl -s localhost:8000/api/v1/status | jq '.platforms[] | {platform, state}'"
