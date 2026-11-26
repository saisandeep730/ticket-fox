#!/usr/bin/env bash
# Debug the generate-token call: show the exact URL, the raw response and the
# gateway's own log lines for the request.
set -uo pipefail
cd "$HOME/ticket-fox-web" || exit 1

SECRET=$(grep -E '^WHATSAPP_SECRET_KEY=' .env | cut -d= -f2- | tr -d '\r')
SESSION=$(grep -E '^WHATSAPP_SESSION=' .env | cut -d= -f2- | tr -d '\r')
SESSION=${SESSION:-ticketfox}

echo "secret=[$SECRET] len=${#SECRET}"
echo "session=[$SESSION]"
echo

URL="http://127.0.0.1:21465/api/${SESSION}/${SECRET}/generate-token"
echo "URL=$URL"
echo

echo "=== POST with -S (show headers) ==="
docker compose exec -T wppconnect wget -S -O - --post-data='' "$URL" 2>&1 | head -30

echo
echo "=== POST with JSON content-type ==="
docker compose exec -T wppconnect wget -S -O - \
  --header='Content-Type: application/json' \
  --post-data='{}' "$URL" 2>&1 | head -30

echo
echo "=== GATEWAY LOGS ==="
docker compose logs --tail=25 wppconnect 2>&1
