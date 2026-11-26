#!/usr/bin/env bash
# Poll the gateway until the session leaves QRCODE, or time out.
set -uo pipefail
cd "$HOME/ticket-fox-web" || exit 1

for i in $(seq 1 40); do
  H=$(docker compose exec -T wppconnect wget -q -O - http://127.0.0.1:21465/health 2>/dev/null || true)
  echo "[$i] $H"
  case "$H" in
    *CONNECTED*) echo ">>> LINKED"; break ;;
  esac
  sleep 5
done

echo
echo "=== GATEWAY LOGS ==="
docker compose logs --tail=30 wppconnect 2>&1

echo
echo "=== /api/channels ==="
docker compose exec -T backend python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/api/channels',timeout=8).read().decode())" 2>&1
