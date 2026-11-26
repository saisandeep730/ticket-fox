#!/usr/bin/env bash
# Verify the admin key path (X-Admin-Key == SECRET_KEY) and inspect the stored
# admin profile row, which currently shows the wrong email (567 vs 456).
set -uo pipefail
cd "$HOME/ticket-fox-web" || exit 1

SECRET=$(grep -E '^SECRET_KEY=' backend/.env | cut -d= -f2- | tr -d '\r')
ADMIN_UID=$(grep -E '^ADMIN_UID=' backend/.env | cut -d= -f2- | tr -d '\r')

echo "secret key: ${SECRET:0:8}... (len ${#SECRET})"
echo "admin uid:  ${ADMIN_UID}"

echo
echo "=== GET /api/admin/stats with X-Admin-Key ==="
docker compose exec -T -e SECRET="$SECRET" backend python - <<'PY'
import json
import os
import urllib.error
import urllib.request

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/admin/stats",
    headers={"X-Admin-Key": os.environ["SECRET"]},
)
try:
    with urllib.request.urlopen(req, timeout=25) as r:
        print("status:", r.status)
        print(json.dumps(json.load(r), indent=2)[:1500])
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode()[:400])
PY

echo
echo "=== stored admin profile row ==="
docker compose exec -T -e ADMIN_UID="$ADMIN_UID" backend python - <<'PY'
import asyncio
import json
import os

from app.database.repository import Repository

repo = Repository()
user = asyncio.run(repo.get_user(os.environ["ADMIN_UID"]))
print(json.dumps(user, indent=2, default=str))
PY
