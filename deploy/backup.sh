#!/usr/bin/env bash
# Nightly: dump Postgres, encrypt it with age (public key only on this machine), keep 14 local copies,
# and copy it to every rclone remote in BACKUP_REMOTES (for example OCI Object Storage and a lab drive).
# The age *private* key never lives on the VM, so a compromised VM cannot read old backups.
set -euo pipefail
cd /opt/dashboard

# Read single keys instead of sourcing .env, which may contain characters the shell would interpret.
env_get() { grep -E "^$1=" .env | tail -n 1 | cut -d= -f2- | sed -e "s/^[\"']//" -e "s/[\"']\$//"; }
BACKUP_AGE_RECIPIENT=$(env_get BACKUP_AGE_RECIPIENT)
BACKUP_REMOTES=$(env_get BACKUP_REMOTES)
HEALTHCHECKS_PING_KEY=$(env_get HEALTHCHECKS_PING_KEY)

: "${BACKUP_AGE_RECIPIENT:?set BACKUP_AGE_RECIPIENT (an age public key) in .env}"
dir=/var/backups/dashboard
stamp=$(date -u +%Y%m%dT%H%M%SZ)
file="$dir/dashboard-$stamp.dump.age"

ping() {
  [ -n "${HEALTHCHECKS_PING_KEY:-}" ] || return 0
  curl -fsS -m 10 --retry 3 "https://hc-ping.com/${HEALTHCHECKS_PING_KEY}/dashboard-backup$1?create=1" >/dev/null || true
}
trap 'ping /fail' ERR

ping /start
docker compose exec -T postgres pg_dump -U dashboard -d dashboard --format=custom --compress=9 \
  | age --encrypt --recipient "$BACKUP_AGE_RECIPIENT" > "$file.partial"
mv "$file.partial" "$file"
find "$dir" -name 'dashboard-*.dump.age' -mtime +14 -delete

for remote in ${BACKUP_REMOTES:-}; do
  rclone copy --quiet "$file" "$remote"
  rclone delete --quiet --min-age 60d --include 'dashboard-*.dump.age' "$remote"
done
echo "backup ok: $file ($(du -h "$file" | cut -f1))"
ping ""
