#!/usr/bin/env bash
# TicketFox — validate config, build, and start the stack.
#
# Usage (on the instance, from the repo root):
#   bash deploy/start.sh
#
# Refuses to start if the env files or the Firebase service-account JSON are
# missing, because Docker would otherwise create a *directory* at the mount
# point and the backend would die with IsADirectoryError.

set -euo pipefail

cd "$(dirname "$0")/.."

log() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\033[1;31m[fail]\033[0m %s\n' "$*" >&2; exit 1; }

DOCKER="docker"
docker info >/dev/null 2>&1 || DOCKER="sudo docker"

# ------------------------------------------------------------------ preflight
[[ -f .env ]] || die ".env missing. cp deploy/env.compose.template .env and fill it in."
[[ -f backend/.env ]] || die "backend/.env missing. cp deploy/env.backend.template backend/.env and fill it in."

grep -q '^DOMAIN=.\+' .env || die "DOMAIN is empty in .env"
grep -q 'REPLACE_WITH' .env && die ".env still contains REPLACE_WITH placeholders"
grep -q 'REPLACE_WITH' backend/.env && die "backend/.env still contains REPLACE_WITH placeholders"

SA_JSON=$(ls backend/*firebase-adminsdk*.json 2>/dev/null | head -n1 || true)
[[ -n "$SA_JSON" ]] || die "Firebase service-account JSON not found in backend/.
  scp -i \"D:\\Ticketfox.pem\" backend/ticketfox-web-firebase-adminsdk-fbsvc-a0fa60b1fd.json ubuntu@<IP>:~/ticket-fox-web/backend/"
[[ -s "$SA_JSON" ]] || die "$SA_JSON is empty"

# The mount target in docker-compose.yml must match FIREBASE_CREDENTIALS_PATH.
SA_NAME=$(basename "$SA_JSON")
grep -q "$SA_NAME" docker-compose.yml \
  || die "docker-compose.yml has no bind mount for $SA_NAME. Add under backend.volumes:
      - ./backend/$SA_NAME:/app/$SA_NAME:ro"

grep -q '^WHATSAPP_SECRET_KEY=.\+' .env || die "WHATSAPP_SECRET_KEY is empty in .env"

# --------------------------------------------------------------------- build
log "Validating compose config"
"$DOCKER" compose config >/dev/null || die "docker compose config failed"

log "Building images (this takes several minutes on first run)"
"$DOCKER" compose build

log "Starting the stack"
"$DOCKER" compose up -d

log "Container status"
"$DOCKER" compose ps

cat <<'NEXT'

Next steps:
  1. Wait ~30s, then: bash deploy/verify.sh
  2. Link WhatsApp:   bash deploy/whatsapp-link.sh
  3. Add ticketfox.site to Firebase -> Authentication -> Settings -> Authorized domains
NEXT
