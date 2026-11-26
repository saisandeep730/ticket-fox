#!/usr/bin/env bash
# Persist the gateway bearer token into backend/.env and restart the backend.
set -uo pipefail
cd "$HOME/ticket-fox-web" || exit 1

SECRET=$(grep -E '^WHATSAPP_SECRET_KEY=' .env | cut -d= -f2- | tr -d '\r')
SESSION=$(grep -E '^WHATSAPP_SESSION=' .env | cut -d= -f2- | tr -d '\r')
SESSION=${SESSION:-ticketfox}

RESP=$(docker compose exec -T wppconnect wget -q -O - --post-data='' \
  "http://127.0.0.1:21465/api/${SESSION}/${SECRET}/generate-token" 2>/dev/null)
TOKEN=$(printf '%s' "$RESP" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')
if [ -z "$TOKEN" ]; then echo "!! token parse failed: $RESP"; exit 1; fi
echo "token: ${TOKEN:0:12}... (len ${#TOKEN})"

if grep -q '^WHATSAPP_API_TOKEN=' backend/.env; then
  sed -i "s|^WHATSAPP_API_TOKEN=.*|WHATSAPP_API_TOKEN=${TOKEN}|" backend/.env
else
  printf '\nWHATSAPP_API_TOKEN=%s\n' "$TOKEN" >> backend/.env
fi

echo
echo "=== backend/.env whatsapp keys ==="
grep -E '^WHATSAPP_' backend/.env | sed 's/\(API_TOKEN=.\{10\}\).*/\1.../'

echo
echo "=== RESTART BACKEND ==="
docker compose up -d --no-deps --force-recreate backend 2>&1 | tail -4

echo
echo "=== WAIT FOR HEALTH ==="
for i in $(seq 1 25); do
  sleep 3
  H=$(docker compose exec -T backend python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=3).read().decode())" 2>/dev/null || true)
  if [ -n "$H" ]; then echo "  [$i] $H"; break; fi
  echo "  [$i] waiting..."
done

echo
echo "=== /api/channels ==="
docker compose exec -T backend python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/api/channels',timeout=8).read().decode())" 2>&1

echo
echo "=== GATEWAY SESSION STATE ==="
docker compose exec -T wppconnect wget -q -O - http://127.0.0.1:21465/health 2>&1
