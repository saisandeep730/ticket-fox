#!/usr/bin/env bash
# Repair the admin profile row: the stored email is the stale 567 default and the
# phone is NULL, so admin email/WhatsApp alerts would go nowhere. Also correct the
# stale 567 default in the server-side env files.
set -uo pipefail
cd "$HOME/ticket-fox-web" || exit 1

ADMIN_UID=$(grep -E '^ADMIN_UID=' backend/.env | cut -d= -f2- | tr -d '\r')
ADMIN_EMAIL=$(grep -E '^ADMIN_EMAIL=' backend/.env | cut -d= -f2- | tr -d '\r')
ADMIN_PHONE="${ADMIN_PHONE:-917305742393}"

echo "admin uid:   ${ADMIN_UID}"
echo "admin email: ${ADMIN_EMAIL}"
echo "admin phone: ${ADMIN_PHONE}"

echo
echo "=== updating the stored admin profile ==="
docker compose exec -T \
  -e ADMIN_UID="$ADMIN_UID" \
  -e ADMIN_EMAIL="$ADMIN_EMAIL" \
  -e ADMIN_PHONE="$ADMIN_PHONE" \
  backend python - <<'PY'
import asyncio
import json
import os

from app.database.repository import Repository

repo = Repository()
uid = os.environ["ADMIN_UID"]
email = os.environ["ADMIN_EMAIL"]
phone = os.environ["ADMIN_PHONE"]

updated = asyncio.run(
    repo.update_user_profile(
        uid,
        {
            "email": email,
            "display_name": email.split("@")[0],
            "phone": phone,
            "whatsapp_number": phone,
        },
    )
)
print(json.dumps(updated, indent=2, default=str))
PY

echo
echo "=== correcting stale 567 defaults in server env files ==="
for f in .env backend/.env frontend/.env.local; do
  if [ -f "$f" ] && grep -q 'saisandeepy567@gmail.com' "$f"; then
    sed -i 's/saisandeepy567@gmail\.com/saisandeepy456@gmail.com/g' "$f"
    echo "patched $f"
  else
    echo "no change: $f"
  fi
done

echo
echo "=== remaining 567 references ==="
grep -rn 'saisandeepy567' .env backend/.env frontend/.env.local 2>/dev/null || echo "none"
