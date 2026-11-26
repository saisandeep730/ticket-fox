#!/usr/bin/env bash
# Exercise both delivery channels from inside the backend container, bypassing
# Firebase auth (which needs a real browser ID token we cannot mint here).
set -uo pipefail
cd "$HOME/ticket-fox-web" || exit 1

ADMIN_EMAIL=$(grep -E '^ADMIN_EMAIL=' backend/.env | cut -d= -f2- | tr -d '\r')
ADMIN_UID=$(grep -E '^ADMIN_UID=' backend/.env | cut -d= -f2- | tr -d '\r')
echo "admin email: ${ADMIN_EMAIL}"
echo "admin uid:   ${ADMIN_UID}"

echo
echo "=== email (Resend) ==="
docker compose exec -T backend python - <<'PY'
from app import notifications
from app.config import settings

to = settings.ADMIN_EMAIL
ok, detail = notifications.send_email(
    to,
    "TicketFox — channel test",
    "<h2>TicketFox email channel is live</h2>"
    "<p>This is a delivery test from the production EC2 deployment.</p>",
)
print("email ok=%s detail=%s" % (ok, detail))
PY

echo
echo "=== whatsapp (gateway) ==="
docker compose exec -T backend python - <<'PY'
import asyncio

from app import notifications, whatsapp
from app.config import settings
from app.database.repository import Repository

print("gateway status:", whatsapp.status())

repo = Repository()
user = asyncio.run(repo.get_user(settings.ADMIN_UID)) if settings.ADMIN_UID else None
phone = (user or {}).get("phone")
print("admin phone on file:", phone)

if not phone:
    print("whatsapp skipped: no phone number saved on the admin profile")
else:
    ok, detail = notifications.send_whatsapp(
        phone,
        "TicketFox channel test — if you see this, WhatsApp delivery works.",
    )
    print("whatsapp ok=%s detail=%s" % (ok, detail))
PY
