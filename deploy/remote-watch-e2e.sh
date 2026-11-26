#!/usr/bin/env bash
# Item 37: create a real watch for the admin, run a worker cycle, and read back
# the alert log. Proves the full poll -> detect -> deliver -> log pipeline.
set -uo pipefail
cd "$HOME/ticket-fox-web" || exit 1

ADMIN_UID=$(grep -E '^ADMIN_UID=' backend/.env | cut -d= -f2- | tr -d '\r')
ADMIN_EMAIL=$(grep -E '^ADMIN_EMAIL=' backend/.env | cut -d= -f2- | tr -d '\r')
WEB_API_KEY=$(grep -E '^NEXT_PUBLIC_FIREBASE_API_KEY=' .env | cut -d= -f2- | tr -d '\r')
SECRET=$(grep -E '^SECRET_KEY=' backend/.env | cut -d= -f2- | tr -d '\r')

docker compose exec -T \
  -e ADMIN_UID="$ADMIN_UID" \
  -e ADMIN_EMAIL="$ADMIN_EMAIL" \
  -e WEB_API_KEY="$WEB_API_KEY" \
  -e SECRET="$SECRET" \
  backend python - <<'PY'
import json
import os
import time
import urllib.error
import urllib.request

from app import auth as _app_auth  # noqa: F401  (initializes Firebase Admin)
from firebase_admin import auth

BASE = "http://127.0.0.1:8000"
uid = os.environ["ADMIN_UID"]
email = os.environ["ADMIN_EMAIL"]
key = os.environ["WEB_API_KEY"]
secret = os.environ["SECRET"]

custom = auth.create_custom_token(uid, {"email": email})
if isinstance(custom, bytes):
    custom = custom.decode()
req = urllib.request.Request(
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={key}",
    data=json.dumps({"token": custom, "returnSecureToken": True}).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=20) as r:
    token = json.load(r)["idToken"]


def call(method, path, body=None, headers=None, auth=True):
    hdrs = {}
    if auth:
        hdrs["Authorization"] = f"Bearer {token}"
    if headers:
        hdrs.update(headers)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]


print("=== existing watches ===")
print(call("GET", "/api/watches"))

print("\n=== creating a watch (G.O.A.T / ET00476213 / Hyderabad) ===")
status, body = call(
    "POST",
    "/api/watches",
    {
        "movie_title": "G.O.A.T",
        "movie_id": "ET00476213",
        "source": "bookmyshow",
        "city": "Hyderabad",
        "whatsapp_number": "917305742393",
    },
)
print("status:", status)
print(json.dumps(body, indent=2)[:900] if isinstance(body, dict) else body)

print("\n=== triggering a worker cycle (X-Admin-Key only) ===")
# NOTE: verify_admin prefers the Bearer value over X-Admin-Key, so the Firebase
# token must NOT be sent on this call or the admin key is ignored.
status, body = call("POST", "/api/worker/cycle", headers={"X-Admin-Key": secret}, auth=False)
print("status:", status)
print(json.dumps(body, indent=2)[:1500] if isinstance(body, dict) else body)

print("\n=== alert log ===")
status, body = call("GET", "/api/alerts")
print("status:", status)
print(json.dumps(body, indent=2)[:1500] if isinstance(body, dict) else body)

print("\n=== watches after cycle (state/timestamps) ===")
status, body = call("GET", "/api/watches")
print("status:", status)
print(json.dumps(body, indent=2)[:2000] if isinstance(body, dict) else body)
PY
