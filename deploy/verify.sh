#!/usr/bin/env bash
# TicketFox — post-deploy verification.
#
# Usage (on the instance, from the repo root):
#   bash deploy/verify.sh
#
# Exits non-zero if any hard check fails, so it can gate a deploy.

set -uo pipefail

cd "$(dirname "$0")/.."

PASS=0
FAIL=0
WARN=0

ok()   { printf '  \033[1;32mPASS\033[0m  %s\n' "$*"; PASS=$((PASS+1)); }
bad()  { printf '  \033[1;31mFAIL\033[0m  %s\n' "$*"; FAIL=$((FAIL+1)); }
warn() { printf '  \033[1;33mWARN\033[0m  %s\n' "$*"; WARN=$((WARN+1)); }
head_() { printf '\n\033[1;36m%s\033[0m\n' "$*"; }

DOCKER="docker"
docker info >/dev/null 2>&1 || DOCKER="sudo docker"

DOMAIN=$(grep '^DOMAIN=' .env 2>/dev/null | cut -d= -f2 | tr -d '"' || true)
[[ -n "$DOMAIN" ]] || { echo "DOMAIN not set in .env"; exit 1; }

# ------------------------------------------------------------------ 1. DNS
head_ "1. DNS"
RESOLVED=$(getent hosts "$DOMAIN" | awk '{print $1}' | head -n1 || true)
PUBLIC_IP=$(curl -s --max-time 5 https://api.ipify.org || true)
if [[ -z "$RESOLVED" ]]; then
  bad "$DOMAIN does not resolve"
elif [[ "$RESOLVED" == "$PUBLIC_IP" ]]; then
  ok "$DOMAIN -> $RESOLVED (this host)"
else
  warn "$DOMAIN -> $RESOLVED but this host is $PUBLIC_IP (proxy or stale record?)"
fi

# ------------------------------------------------------------ 2. containers
head_ "2. Containers"
for svc in caddy frontend backend wppconnect; do
  STATE=$("$DOCKER" compose ps --format '{{.Service}} {{.State}}' 2>/dev/null | awk -v s="$svc" '$1==s {print $2}')
  if [[ "$STATE" == "running" ]]; then ok "$svc running"; else bad "$svc is '${STATE:-absent}'"; fi
done

HEALTH=$("$DOCKER" inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
  "$("$DOCKER" compose ps -q backend)" 2>/dev/null || echo unknown)
[[ "$HEALTH" == "healthy" ]] && ok "backend healthcheck: healthy" || warn "backend healthcheck: $HEALTH"

# --------------------------------------------------------------- 3. backend
head_ "3. Backend API"
BODY=$(curl -s --max-time 15 "https://$DOMAIN/health" || true)
if [[ -z "$BODY" ]]; then
  bad "https://$DOMAIN/health returned nothing (TLS or Caddy problem)"
else
  echo "  $BODY"
  echo "$BODY" | grep -q '"status":"ok"' && ok "health status ok" || bad "health status not ok"
  if echo "$BODY" | grep -q 'firebase_admin'; then
    ok "auth_mode: firebase_admin (real token verification)"
  elif echo "$BODY" | grep -q 'mock'; then
    bad "auth_mode: mock — ALLOW_MOCK_AUTH is on or Firebase failed to init"
  else
    bad "auth_mode: unconfigured — the service-account JSON is not readable in the container"
  fi
fi

curl -s --max-time 15 "https://$DOMAIN/api/health" >/dev/null \
  && ok "/api/health reachable" || bad "/api/health unreachable"

CHANNELS=$(curl -s --max-time 15 "https://$DOMAIN/api/channels" || true)
if [[ -n "$CHANNELS" ]]; then
  echo "  $CHANNELS"
  echo "$CHANNELS" | grep -qi 'email' && ok "email channel reported" || warn "email channel not reported"
  echo "$CHANNELS" | grep -qi 'whatsapp' && ok "whatsapp channel reported" || warn "whatsapp channel not reported"
else
  warn "/api/channels returned nothing"
fi

# -------------------------------------------------------------- 4. frontend
head_ "4. Frontend"
CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "https://$DOMAIN/" || echo 000)
[[ "$CODE" == "200" ]] && ok "GET / -> 200" || bad "GET / -> $CODE"

CERT=$(echo | openssl s_client -servername "$DOMAIN" -connect "$DOMAIN:443" 2>/dev/null \
  | openssl x509 -noout -issuer 2>/dev/null || true)
if echo "$CERT" | grep -qi "let's encrypt"; then
  ok "TLS certificate issued by Let's Encrypt"
elif [[ -n "$CERT" ]]; then
  warn "TLS certificate issuer: $CERT"
else
  bad "Could not read the TLS certificate"
fi

# -------------------------------------------------------------- 5. whatsapp
head_ "5. WhatsApp gateway"
SESSION=$(grep '^WHATSAPP_SESSION=' backend/.env | cut -d= -f2 | tr -d '"' || true)
SESSION=${SESSION:-ticketfox}
TOKEN=$(grep '^WHATSAPP_API_TOKEN=' backend/.env | cut -d= -f2 | tr -d '"' || true)
NETWORK=$("$DOCKER" inspect "$("$DOCKER" compose ps -q wppconnect)" \
  --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}' 2>/dev/null || true)

if [[ -z "$TOKEN" ]]; then
  warn "WHATSAPP_API_TOKEN is empty — run: bash deploy/whatsapp-link.sh"
elif [[ -z "$NETWORK" ]]; then
  bad "wppconnect is not running"
else
  STATUS=$("$DOCKER" run --rm --network "$NETWORK" curlimages/curl:latest -s \
    "http://wppconnect:21465/api/$SESSION/status-session" \
    -H "Authorization: Bearer $TOKEN" 2>/dev/null || true)
  echo "  $STATUS"
  echo "$STATUS" | grep -qi 'CONNECTED' && ok "WhatsApp session CONNECTED" \
    || bad "WhatsApp session not connected — scan the QR from deploy/whatsapp-link.sh"
fi

# ---------------------------------------------------------------- 6. worker
head_ "6. Polling worker"
if "$DOCKER" compose logs --tail 200 backend 2>/dev/null | grep -qi 'Worker cycle completed'; then
  ok "worker has completed at least one cycle"
elif "$DOCKER" compose logs --tail 200 backend 2>/dev/null | grep -qi 'resting'; then
  ok "worker is running (all watches parked until release)"
else
  warn "no worker cycle in the last 200 log lines — check: docker compose logs -f backend"
fi

"$DOCKER" compose logs --tail 200 backend 2>/dev/null | grep -qi 'Firebase Admin SDK initialized' \
  && ok "Firebase Admin SDK initialized" || bad "Firebase Admin SDK did not initialize"

# ------------------------------------------------------------------ summary
head_ "Summary"
printf '  %d passed, %d failed, %d warnings\n' "$PASS" "$FAIL" "$WARN"
[[ "$FAIL" -eq 0 ]] || exit 1
