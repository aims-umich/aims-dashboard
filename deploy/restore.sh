#!/usr/bin/env bash
# Restore an encrypted backup into the stack in this folder (use a staging VM to test restores).
#   deploy/restore.sh path/to/dashboard-XXXX.dump.age path/to/age-identity.txt
# The identity (private key) is kept offline; copy it here only for the restore, then delete it.
set -euo pipefail
cd "$(dirname "$0")/.."
backup="${1:?backup file}"
identity="${2:?age identity file}"

read -r -p "This replaces the database in $(pwd). Type 'restore' to continue: " answer
[ "$answer" = "restore" ] || { echo "Aborted."; exit 1; }

docker compose stop ingest scorer api
age --decrypt --identity "$identity" "$backup" \
  | docker compose exec -T postgres pg_restore -U dashboard -d dashboard --clean --if-exists --no-owner
docker compose up -d
echo "Restored $backup"
