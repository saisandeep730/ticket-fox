#!/usr/bin/env bash
# Rebuild the WhatsApp gateway with the QR page, restart it, reload Caddy,
# then print the secret so the operator can open the pairing URL.
set -uo pipefail
cd "$HOME/ticket-fox-web" || exit 1

echo "=== BUILD ==="
docker compose build wppconnect 2>&1 | tail -8

echo
echo "=== RESTART GATEWAY ==="
docker compose up -d --no-deps wppconnect 2>&1 | tail -5

echo
echo "=== RELOAD CADDY ==="
docker compose exec -T caddy caddy reload --config /etc/caddy/Caddyfile 2>&1 || \
  docker compose restart caddy 2>&1 | tail -3

echo
echo "=== WAIT FOR QR ==="
for i in $(seq 1 20); do
  sleep 3
  H=$(docker compose exec -T wppconnect wget -q -O - http://127.0.0.1:21465/health 2>/dev/null || true)
  echo "  [$i] $H"
  case "$H" in
    *QRCODE*|*CONNECTED*) break ;;
  esac
done

echo
echo "=== SECRET (for the pairing URL) ==="
grep -E '^WHATSAPP_SECRET_KEY=' .env | cut -d= -f2-

echo
echo "=== DISK ==="
df -h / | tail -1
