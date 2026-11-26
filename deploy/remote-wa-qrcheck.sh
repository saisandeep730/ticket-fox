#!/usr/bin/env bash
# Confirm qrcode-session returns a real base64 PNG when called with the token.
set -uo pipefail
cd "$HOME/ticket-fox-web" || exit 1

SECRET=$(grep -E '^WHATSAPP_SECRET_KEY=' .env | cut -d= -f2- | tr -d '\r')
SESSION=$(grep -E '^WHATSAPP_SESSION=' .env | cut -d= -f2- | tr -d '\r')
SESSION=${SESSION:-ticketfox}

TOKEN=$(docker compose exec -T wppconnect wget -q -O - --post-data='' \
  "http://127.0.0.1:21465/api/${SESSION}/${SECRET}/generate-token" 2>/dev/null \
  | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')
echo "token: ${TOKEN:0:12}..."

echo
echo "=== status-session (with token) ==="
docker compose exec -T wppconnect wget -q -O - \
  --header="Authorization: Bearer ${TOKEN}" \
  "http://127.0.0.1:21465/api/${SESSION}/status-session" 2>&1

echo
echo "=== qrcode-session (with token) ==="
QR=$(docker compose exec -T wppconnect wget -q -O - \
  --header="Authorization: Bearer ${TOKEN}" \
  "http://127.0.0.1:21465/api/${SESSION}/qrcode-session" 2>&1)
echo "response length: ${#QR}"
echo "first 120 chars: ${QR:0:120}"

echo
echo "=== /qr page served through Caddy ==="
curl -s -o /dev/null -w "qr_page=%{http_code}\n" "https://ticketfox.site/qr/${SECRET}"
