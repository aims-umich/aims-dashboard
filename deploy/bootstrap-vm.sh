#!/usr/bin/env bash
# One-time setup of a fresh Oracle Cloud Always Free Ampere VM (Ubuntu 24.04, arm64).
# Run as the default "ubuntu" user:  curl -fsSL <raw url> | bash   (or scp this file and run it)
# Safe to re-run: every step checks what is already done.
set -euo pipefail

APP_DIR=/opt/dashboard
BACKUP_DIR=/var/backups/dashboard

log() { printf '\n==> %s\n' "$*"; }

log "System updates and automatic security patches"
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates curl gnupg unattended-upgrades iptables-persistent age rclone jq
sudo dpkg-reconfigure -f noninteractive unattended-upgrades

log "Docker Engine and the compose plugin"
if ! command -v docker >/dev/null; then
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  codename=$(grep -oP '^VERSION_CODENAME=\K.*' /etc/os-release)
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu ${codename} stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
sudo usermod -aG docker "$USER"
sudo tee /etc/docker/daemon.json >/dev/null <<'JSON'
{ "log-driver": "json-file", "log-opts": { "max-size": "10m", "max-file": "5" } }
JSON
sudo systemctl enable --now docker
sudo systemctl restart docker

log "Firewall: Oracle's Ubuntu image rejects everything but SSH in iptables; open HTTP(S)"
for rule in "-p tcp --dport 80" "-p tcp --dport 443" "-p udp --dport 443"; do
  # shellcheck disable=SC2086
  if ! sudo iptables -C INPUT -m state --state NEW $rule -j ACCEPT 2>/dev/null; then
    # Insert before the image's catch-all REJECT rule (or append if there is none).
    reject=$(sudo iptables -L INPUT --line-numbers | awk '/REJECT/ {print $1; exit}')
    # shellcheck disable=SC2086
    sudo iptables -I INPUT "${reject:-$(( $(sudo iptables -L INPUT --line-numbers | tail -n +3 | wc -l) + 1 ))}" \
      -m state --state NEW $rule -j ACCEPT
  fi
done
sudo netfilter-persistent save

log "2 GB swap as a safety margin for model loading"
if ! swapon --show | grep -q /swapfile; then
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

log "App and backup folders"
sudo mkdir -p "$APP_DIR/deploy" "$BACKUP_DIR"
sudo chown -R "$USER:$USER" "$APP_DIR" "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
if [ ! -f "$APP_DIR/.env" ]; then
  install -m 600 /dev/null "$APP_DIR/.env"
  echo "Created an empty $APP_DIR/.env (mode 600). Fill it in from deploy/env.example."
fi

log "Nightly encrypted backups (systemd timer)"
if [ -f "$APP_DIR/deploy/systemd/dashboard-backup.service" ]; then
  sudo cp "$APP_DIR"/deploy/systemd/dashboard-backup.{service,timer} /etc/systemd/system/
  sudo sed -i "s/__USER__/$USER/" /etc/systemd/system/dashboard-backup.service
  sudo systemctl daemon-reload
  sudo systemctl enable --now dashboard-backup.timer
else
  echo "Skipped: deploy files are not in $APP_DIR yet. Re-run this script after the first deploy."
fi

log "Done. Log out and back in so the docker group applies, then run deploy/deploy.sh."
