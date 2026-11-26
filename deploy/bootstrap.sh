#!/usr/bin/env bash
# TicketFox — one-shot host bootstrap for a fresh Ubuntu EC2 instance.
#
# Installs Docker + Compose, adds swap, caps Docker log growth, and extracts the
# deployment archive. Idempotent: safe to re-run.
#
# Usage (on the instance, as the `ubuntu` user):
#   bash deploy/bootstrap.sh
#
# Expects the archive at ~/ticket-fox-web-deploy.tar.gz (scp it up first).

set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/ticket-fox-web}"
ARCHIVE="${ARCHIVE:-$HOME/ticket-fox-web-deploy.tar.gz}"
SWAP_SIZE="${SWAP_SIZE:-2G}"
SWAP_FILE="/swapfile"

log() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[fail]\033[0m %s\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] && die "Run as the normal user (ubuntu), not root. The script uses sudo where needed."

# ---------------------------------------------------------------- 1. packages
log "Installing base packages"
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  ca-certificates curl git tar gzip openssl python3

# ------------------------------------------------------------------ 2. docker
if command -v docker >/dev/null 2>&1; then
  log "Docker already installed: $(docker --version)"
else
  log "Installing Docker"
  curl -fsSL https://get.docker.com | sudo sh
fi

if ! docker compose version >/dev/null 2>&1; then
  log "Installing the Compose plugin"
  sudo apt-get install -y -qq docker-compose-plugin
fi

if ! id -nG "$USER" | grep -qw docker; then
  log "Adding $USER to the docker group"
  sudo usermod -aG docker "$USER"
  warn "Group change applies to NEW shells. This script uses sudo docker as a fallback."
fi

DOCKER="docker"
docker info >/dev/null 2>&1 || DOCKER="sudo docker"

# -------------------------------------------------------------------- 3. swap
if swapon --show | grep -q "$SWAP_FILE"; then
  log "Swap already active at $SWAP_FILE"
else
  MEM_MB=$(awk '/MemTotal/ {printf "%d", $2/1024}' /proc/meminfo)
  if [[ "$MEM_MB" -lt 7000 ]]; then
    log "RAM is ${MEM_MB}MB — creating ${SWAP_SIZE} swap"
    sudo fallocate -l "$SWAP_SIZE" "$SWAP_FILE" 2>/dev/null \
      || sudo dd if=/dev/zero of="$SWAP_FILE" bs=1M count=2048 status=none
    sudo chmod 600 "$SWAP_FILE"
    sudo mkswap "$SWAP_FILE" >/dev/null
    sudo swapon "$SWAP_FILE"
    grep -q "^$SWAP_FILE" /etc/fstab || echo "$SWAP_FILE none swap sw 0 0" | sudo tee -a /etc/fstab >/dev/null
  else
    log "RAM is ${MEM_MB}MB — swap not required"
  fi
fi

# ------------------------------------------------------------ 4. docker logs
if [[ ! -f /etc/docker/daemon.json ]] || ! grep -q max-size /etc/docker/daemon.json; then
  log "Capping Docker log size (10m x 3 per container)"
  sudo mkdir -p /etc/docker
  sudo tee /etc/docker/daemon.json >/dev/null <<'JSON'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
JSON
  sudo systemctl restart docker
  sleep 2
else
  log "Docker log rotation already configured"
fi

# ------------------------------------------------------------------ 5. code
if [[ -f "$APP_DIR/docker-compose.yml" ]]; then
  log "Code already present at $APP_DIR"
else
  [[ -f "$ARCHIVE" ]] || die "Archive not found at $ARCHIVE. scp it up first:
  scp -i \"D:\\Ticketfox.pem\" ticket-fox-web-deploy.tar.gz ubuntu@<IP>:~/"
  log "Extracting $ARCHIVE -> $APP_DIR"
  mkdir -p "$APP_DIR"
  tar -xzf "$ARCHIVE" -C "$APP_DIR" --strip-components=1 2>/dev/null \
    || tar -xzf "$ARCHIVE" -C "$APP_DIR"
fi

cd "$APP_DIR"
[[ -f docker-compose.yml ]] || die "docker-compose.yml missing in $APP_DIR — the archive layout is wrong."
[[ -f Caddyfile ]] || die "Caddyfile missing in $APP_DIR."

# --------------------------------------------------------------- 6. preflight
log "Preflight summary"
printf '  host      : %s\n' "$(hostname)"
printf '  ubuntu    : %s\n' "$(lsb_release -ds 2>/dev/null || echo unknown)"
printf '  kernel    : %s\n' "$(uname -r)"
printf '  cpus      : %s\n' "$(nproc)"
printf '  memory    : %s\n' "$(free -h | awk '/^Mem:/ {print $2}')"
printf '  swap      : %s\n' "$(free -h | awk '/^Swap:/ {print $2}')"
printf '  disk /    : %s free\n' "$(df -h / | awk 'NR==2 {print $4}')"
printf '  docker    : %s\n' "$("$DOCKER" --version)"
printf '  compose   : %s\n' "$("$DOCKER" compose version --short 2>/dev/null || echo unknown)"
printf '  app dir   : %s\n' "$APP_DIR"

# --------------------------------------------------------------- 7. env gate
MISSING=0
[[ -f .env ]] || { warn "Missing $APP_DIR/.env (compose-level)"; MISSING=1; }
[[ -f backend/.env ]] || { warn "Missing $APP_DIR/backend/.env"; MISSING=1; }
if ! ls backend/*firebase-adminsdk*.json >/dev/null 2>&1; then
  warn "Missing the Firebase service-account JSON in backend/"
  MISSING=1
fi

if [[ "$MISSING" -eq 1 ]]; then
  cat <<'NEXT'

Next steps:
  1. cp deploy/env.compose.template .env            && edit it
  2. cp deploy/env.backend.template backend/.env    && edit it
  3. scp the Firebase service-account JSON into backend/
  4. bash deploy/start.sh
NEXT
  exit 0
fi

log "Bootstrap complete. Run: bash deploy/start.sh"
