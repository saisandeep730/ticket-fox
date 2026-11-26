#!/usr/bin/env bash
# Inspect the WhatsApp gateway container: state, logs, health, disk.
set -uo pipefail
cd "$HOME/ticket-fox-web" || exit 1

echo "=== COMPOSE PS ==="
docker compose ps

echo
echo "=== GATEWAY LOGS (last 60) ==="
docker compose logs --tail=60 wppconnect 2>&1

echo
echo "=== HEALTH (from inside container) ==="
docker compose exec -T wppconnect wget -q -O - http://127.0.0.1:21465/health 2>&1 || echo "wget failed"

echo
echo "=== STATUS-SESSION ==="
docker compose exec -T wppconnect wget -q -O - http://127.0.0.1:21465/api/ticketfox/status-session 2>&1 || echo "wget failed"

echo
echo "=== DISK ==="
df -h / | tail -1
