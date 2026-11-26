#!/usr/bin/env bash
# TicketFox — mint the WhatsApp bearer token, start the session, and fetch the QR.
#
# Usage (on the instance, from the repo root):
#   bash deploy/whatsapp-link.sh
#
# Port 21465 is not published, so this must run on the VM itself.
# The QR is written to /tmp/ticketfox-qr.png — scp it down and scan it.

set -euo pipefail

cd "$(dirname "$0")/.."

log() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\033[1;31m[fail]\033[0m %s\n' "$*" >&2; exit 1; }

DOCKER="docker"
docker info >/dev/null 2>&1 || DOCKER="sudo docker"

[[ -f .env ]] || die ".env missing"
[[ -f backend/.env ]] || die "backend/.env missing"

SESSION=$(grep '^WHATSAPP_SESSION=' backend/.env | cut -d= -f2 | tr -d '"' || true)
SESSION=${SESSION:-ticketfox}
SECRET=$(grep '^WHATSAPP_SECRET_KEY=' .env | cut -d= -f2 | tr -d '"' || true)
[[ -n "$SECRET" ]] || die "WHATSAPP_SECRET_KEY is empty in .env"

BASE="http://127.0.0.1:21465/api/$SESSION"

# The gateway is only reachable from inside the Docker network, so run curl in a
# throwaway container attached to the same network.
NETWORK=$("$DOCKER" inspect "$("$DOCKER" compose ps -q wppconnect)" \
  --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}' 2>/dev/null || true)
[[ -n "$NETWORK" ]] || die "wppconnect container is not running. Start the stack first."

gw() {
  "$DOCKER" run --rm --network "$NETWORK" curlimages/curl:latest -s "$@"
}

log "Waiting for the gateway to answer"
for i in $(seq 1 30); do
  if gw "$BASE/status-session" >/dev/null 2>&1; then break; fi
  sleep 2
  [[ $i -eq 30 ]] && die "Gateway did not respond on $BASE after 60s. Check: $DOCKER compose logs wppconnect"
done

log "Minting a bearer token"
TOKEN=$(gw -X POST "$BASE/$SECRET/generate-token" \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("token") or d.get("data",{}).get("token",""))' 2>/dev/null || true)
[[ -n "$TOKEN" ]] || die "Could not mint a token. Inspect: $DOCKER compose logs wppconnect"
echo "  token: $TOKEN"

log "Persisting the token into backend/.env"
if grep -q '^WHATSAPP_API_TOKEN=' backend/.env; then
  sed -i "s|^WHATSAPP_API_TOKEN=.*|WHATSAPP_API_TOKEN=$TOKEN|" backend/.env
else
  printf '\nWHATSAPP_API_TOKEN=%s\n' "$TOKEN" >> backend/.env
fi
grep '^WHATSAPP_API_TOKEN=' backend/.env | sed 's/=.*/=<set>/'

log "Starting the session"
gw -X POST "$BASE/start-session" -H "Authorization: Bearer $TOKEN" || true

log "Fetching the QR code"
for i in $(seq 1 20); do
  gw "$BASE/qrcode-session" -H "Authorization: Bearer $TOKEN" \
    | python3 -c '
import sys, json, base64
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
qr = d.get("qrcode") or d.get("data", {}).get("qrcode")
if not qr:
    sys.exit(1)
open("/tmp/ticketfox-qr.png", "wb").write(base64.b64decode(qr))
' && break
  sleep 3
  [[ $i -eq 20 ]] && die "No QR produced. The session may already be linked — check status below."
done

log "QR written to /tmp/ticketfox-qr.png"
cat <<'NEXT'
  Copy it to your machine and scan with WhatsApp -> Linked devices:
    scp -i "D:\Ticketfox.pem" ubuntu@13.53.172.114:/tmp/ticketfox-qr.png .

  Then confirm the link and restart the backend so it picks up the token:
    bash deploy/verify.sh
    docker compose restart backend
NEXT
