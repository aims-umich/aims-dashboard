#!/usr/bin/env bash
# Wait for Always Free Ampere A1 capacity, then launch the dashboard VM exactly once.
#
# Every few minutes it asks Oracle's Compute Capacity Report API whether each availability
# domain can fit the shape (a read-only check), and launches only where the answer is AVAILABLE.
# It stops as soon as one instance is running, and refuses to start if one with the same name exists.
#
# Usage (from the repository root, with a working `oci` CLI config):
#   deploy/oci-wait-for-capacity.sh --dry-run      # one round of capacity checks, launches nothing
#   caffeinate -i deploy/oci-wait-for-capacity.sh  # keep the Mac awake and retry until it launches
#
# Settings (environment variables, all optional):
#   DISPLAY_NAME    instance name                         (aims-dashboard-prod)
#   SHAPE_CONFIGS   "OCPUS:GB" pairs, most preferred first ("1:6 1:4")
#   VCN_NAME        VCN whose public subnet to use        (aims-dashboard-vcn)
#   SUBNET_ID       skip the subnet lookup
#   IMAGE_ID        skip the image lookup (default: newest Canonical Ubuntu 24.04 aarch64, not Minimal)
#   SSH_PUBLIC_KEY  public key for the ubuntu user        (~/.ssh/aims_dashboard.pub)
#   BOOT_GB         boot volume size                      (100)
#   COMPARTMENT_ID  compartment                           (the tenancy, read from the CLI config)
#   INTERVAL        seconds between rounds                (180, plus up to 60 s of jitter)
#   MAX_HOURS       give up after this many hours         (72)
# Works with the macOS system bash (3.2) and jq.
set -euo pipefail

SHAPE=VM.Standard.A1.Flex
DISPLAY_NAME=${DISPLAY_NAME:-aims-dashboard-prod}
SHAPE_CONFIGS=${SHAPE_CONFIGS:-"1:6 1:4"}
VCN_NAME=${VCN_NAME:-aims-dashboard-vcn}
SSH_PUBLIC_KEY=${SSH_PUBLIC_KEY:-$HOME/.ssh/aims_dashboard.pub}
BOOT_GB=${BOOT_GB:-100}
INTERVAL=${INTERVAL:-180}
MAX_HOURS=${MAX_HOURS:-72}
DRY_RUN=false
[ "${1:-}" = "--dry-run" ] && DRY_RUN=true

log() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
die() { log "ERROR: $*"; exit 1; }
notify() {
  printf '\a'
  if command -v osascript >/dev/null; then
    osascript -e "display notification \"$1\" with title \"Oracle VM\"" >/dev/null 2>&1 || true
  fi
}

command -v oci >/dev/null || die "the oci CLI is not installed"
command -v jq >/dev/null || die "jq is not installed"
[ -f "$SSH_PUBLIC_KEY" ] || die "no SSH public key at $SSH_PUBLIC_KEY"
case "$(head -c 4 "$SSH_PUBLIC_KEY")" in ssh-|ecds) ;; *) die "$SSH_PUBLIC_KEY does not look like a public key" ;; esac

# --- Resolve IDs ------------------------------------------------------------------------------

if [ -z "${COMPARTMENT_ID:-}" ]; then
  if [ -n "${OCI_TENANCY:-}" ]; then
    COMPARTMENT_ID=$OCI_TENANCY # set in OCI Cloud Shell
  else
    config=${OCI_CLI_CONFIG_FILE:-$HOME/.oci/config}
    [ -f "$config" ] || die "no OCI CLI config at $config (run: oci setup config)"
    COMPARTMENT_ID=$(awk -F= -v profile="[${OCI_CLI_PROFILE:-DEFAULT}]" \
      '$0 == profile {p = 1; next} /^\[/ {p = 0} p && $1 ~ /^tenancy *$/ {gsub(/ /, "", $2); print $2; exit}' "$config")
    [ -n "$COMPARTMENT_ID" ] || die "could not read the tenancy OCID from $config"
  fi
fi

log "Checking access to the tenancy..."
ads=$(oci iam availability-domain list --compartment-id "$COMPARTMENT_ID" --query 'data[].name' --raw-output \
  | jq -r '.[]') || die "could not list availability domains (check the CLI config)"
[ -n "$ads" ] || die "no availability domains found"
log "Availability domains: $(echo "$ads" | tr '\n' ' ')"

existing=$(oci compute instance list --compartment-id "$COMPARTMENT_ID" --display-name "$DISPLAY_NAME" --all \
  | jq -r '[.data[]? | select(."lifecycle-state" != "TERMINATED" and ."lifecycle-state" != "TERMINATING")] | length')
[ "$existing" = "0" ] || die "an instance named $DISPLAY_NAME already exists; nothing to do"

if [ -z "${SUBNET_ID:-}" ]; then
  vcn_id=$(oci network vcn list --compartment-id "$COMPARTMENT_ID" --all \
    | jq -r --arg name "$VCN_NAME" '[.data[] | select(."display-name" == $name and ."lifecycle-state" == "AVAILABLE")][0].id // empty')
  [ -n "$vcn_id" ] || die "no VCN named $VCN_NAME (create it with the VCN wizard, or set SUBNET_ID)"
  SUBNET_ID=$(oci network subnet list --compartment-id "$COMPARTMENT_ID" --vcn-id "$vcn_id" --all \
    | jq -r '[.data[] | select(."prohibit-public-ip-on-vnic" == false)][0].id // empty')
  [ -n "$SUBNET_ID" ] || die "the VCN $VCN_NAME has no public subnet"
fi
log "Subnet: $SUBNET_ID"

if [ -z "${IMAGE_ID:-}" ]; then
  IMAGE_ID=$(oci compute image list --compartment-id "$COMPARTMENT_ID" --operating-system "Canonical Ubuntu" \
      --operating-system-version "24.04" --shape "$SHAPE" --sort-by TIMECREATED --sort-order DESC --all \
    | jq -r '[.data[] | select((."display-name" | test("Minimal")) | not)][0].id // empty')
  [ -n "$IMAGE_ID" ] || die "no Canonical Ubuntu 24.04 image for $SHAPE found"
fi
log "Image: $(oci compute image get --image-id "$IMAGE_ID" --query 'data."display-name"' --raw-output)"

# --- Capacity and launch ----------------------------------------------------------------------

# Prints AVAILABLE, OUT_OF_HOST_CAPACITY, HARDWARE_NOT_SUPPORTED, or UNKNOWN (report failed).
capacity() {
  local ad=$1 ocpus=$2 gb=$3 shapes
  shapes=$(jq -cn --arg s "$SHAPE" --argjson o "$ocpus" --argjson m "$gb" \
    '[{instanceShape: $s, instanceShapeConfig: {ocpus: $o, memoryInGBs: $m}}]')
  oci compute compute-capacity-report create --compartment-id "$COMPARTMENT_ID" --availability-domain "$ad" \
      --shape-availabilities "$shapes" 2>/dev/null \
    | jq -r '.data."shape-availabilities"[0]."availability-status" // "UNKNOWN"' 2>/dev/null \
    || echo UNKNOWN
}

# Returns 0 on success, 2 if Oracle said out of capacity, and exits the script on any other error.
launch() {
  local ad=$1 ocpus=$2 gb=$3 out
  if out=$(oci compute instance launch \
      --compartment-id "$COMPARTMENT_ID" \
      --availability-domain "$ad" \
      --display-name "$DISPLAY_NAME" \
      --shape "$SHAPE" \
      --shape-config "{\"ocpus\": $ocpus, \"memoryInGBs\": $gb}" \
      --image-id "$IMAGE_ID" \
      --boot-volume-size-in-gbs "$BOOT_GB" \
      --subnet-id "$SUBNET_ID" \
      --assign-public-ip true \
      --ssh-authorized-keys-file "$SSH_PUBLIC_KEY" \
      --instance-options '{"areLegacyImdsEndpointsDisabled": true}' \
      --availability-config '{"recoveryAction": "RESTORE_INSTANCE"}' \
      --wait-for-state RUNNING --max-wait-seconds 900 2>&1); then
    instance_id=$(printf '%s' "$out" | sed -n '/^{/,$p' | jq -r '.data.id')
    return 0
  fi
  case "$out" in
    *"ut of host capacity"*|*OutOfHostCapacity*|*"ut of capacity"*) return 2 ;;
    *TooManyRequests*) log "  Oracle asked us to slow down; waiting longer"; sleep 300; return 2 ;;
    *LimitExceeded*) die "launch refused by a service limit (this would exceed the free allowance): $out" ;;
    *) die "launch failed: $out" ;;
  esac
}

deadline=$(( $(date +%s) + MAX_HOURS * 3600 ))
round=0
while :; do
  round=$((round + 1))
  log "Round $round"
  for pair in $SHAPE_CONFIGS; do
    ocpus=${pair%%:*}
    gb=${pair##*:}
    for ad in $ads; do
      status=$(capacity "$ad" "$ocpus" "$gb")
      log "  $ad  ${ocpus} OCPU / ${gb} GB: $status"
      case "$status" in
        AVAILABLE|UNKNOWN) ;; # UNKNOWN: the report call failed, so just try the launch.
        *) continue ;;
      esac
      $DRY_RUN && continue
      log "  Launching $DISPLAY_NAME in $ad (${ocpus} OCPU / ${gb} GB)..."
      if launch "$ad" "$ocpus" "$gb"; then
        ip=$(oci compute instance list-vnics --instance-id "$instance_id" --query 'data[0]."public-ip"' --raw-output)
        log "SUCCESS: $DISPLAY_NAME is running in $ad"
        log "  instance: $instance_id"
        log "  public IP (ephemeral until you reserve it): $ip"
        log "  next: ssh -i ${SSH_PUBLIC_KEY%.pub} ubuntu@$ip"
        notify "$DISPLAY_NAME is running at $ip"
        exit 0
      fi
      log "  Out of capacity at launch time; continuing"
    done
  done
  $DRY_RUN && { log "Dry run finished; nothing was launched."; exit 0; }
  [ "$(date +%s)" -lt "$deadline" ] || die "no capacity after $MAX_HOURS hours; try again later"
  wait_s=$(( INTERVAL + RANDOM % 60 ))
  log "No capacity yet; next check in ${wait_s}s"
  sleep "$wait_s"
done
