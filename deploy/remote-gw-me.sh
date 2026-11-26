#!/usr/bin/env bash
# Rebuild the gateway with the new /me endpoint, then self-send a WhatsApp
# message to the linked account's own number to prove the send path works.
# NOTE: the gateway port is not published to the host, so every call is made
# from inside the container via `docker compose exec`.
set -uo pipefail
cd "$HOME/ticket-fox-web" || exit 1

SECRET=$(grep -E '^WHATSAPP_SECRET_KEY=' backend/.env | cut -d= -f2- | tr -d '\r')
TOKEN=$(grep -E '^WHATSAPP_API_TOKEN=' backend/.env | cut -d= -f2- | tr -d '\r')
SESSION=ticketfox
BASE="http://127.0.0.1:21465"

gw() { docker compose exec -T wppconnect "$@"; }

echo "=== waiting for session to reconnect ==="
for i in $(seq 1 30); do
  STATE=$(gw node -e "
    fetch('${BASE}/api/${SESSION}/status-session',{headers:{Authorization:'Bearer ${TOKEN}'}})
      .then(r=>r.json()).then(j=>console.log(j.status||'')).catch(()=>console.log(''))
  " 2>/dev/null | tr -d '\r')
  echo "[$i] state=${STATE}"
  [ "$STATE" = "CONNECTED" ] && break
  sleep 4
done

echo
echo "=== /me ==="
ME=$(gw node -e "
  fetch('${BASE}/api/${SESSION}/me',{headers:{Authorization:'Bearer ${TOKEN}'}})
    .then(r=>r.text()).then(t=>console.log(t)).catch(e=>console.log('ERR '+e.message))
" 2>/dev/null | tr -d '\r')
echo "$ME"

PHONE=$(echo "$ME" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("phone",""))' 2>/dev/null)
if [ -z "$PHONE" ]; then
  echo "no phone from /me — aborting self-send"
  exit 1
fi

echo
echo "=== self-send to ${PHONE} ==="
gw node -e "
  fetch('${BASE}/api/${SESSION}/send-message',{
    method:'POST',
    headers:{Authorization:'Bearer ${TOKEN}','Content-Type':'application/json'},
    body: JSON.stringify({phone:['${PHONE}'],message:'TicketFox channel test — WhatsApp delivery is working.'})
  }).then(r=>r.text()).then(t=>console.log(t)).catch(e=>console.log('ERR '+e.message))
" 2>/dev/null | tr -d '\r'
echo
