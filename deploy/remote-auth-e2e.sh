#!/usr/bin/env bash
# End-to-end auth proof: mint a real Firebase ID token for the admin UID using the
# service account, exchange it via the Identity Toolkit REST API with the web API
# key, then call the protected backend endpoints with that token.
#
# This exercises exactly the same path a browser sign-in takes:
#   browser -> Firebase ID token -> Authorization: Bearer -> verify_id_token()
#
# Everything runs in ONE container invocation so the token never has to cross the
# container/host boundary.
set -uo pipefail
cd "$HOME/ticket-fox-web" || exit 1

ADMIN_UID=$(grep -E '^ADMIN_UID=' backend/.env | cut -d= -f2- | tr -d '\r')
ADMIN_EMAIL=$(grep -E '^ADMIN_EMAIL=' backend/.env | cut -d= -f2- | tr -d '\r')
WEB_API_KEY=$(grep -E '^NEXT_PUBLIC_FIREBASE_API_KEY=' .env | cut -d= -f2- | tr -d '\r')

echo "admin uid:   ${ADMIN_UID}"
echo "admin email: ${ADMIN_EMAIL}"
echo "web api key: ${WEB_API_KEY:0:12}..."

docker compose exec -T \
  -e ADMIN_UID="$ADMIN_UID" \
  -e ADMIN_EMAIL="$ADMIN_EMAIL" \
  -e WEB_API_KEY="$WEB_API_KEY" \
  backend python - <<'PY'
import json
import os
import urllib.error
import urllib.request

# Importing app.auth initializes the Firebase Admin SDK (it reads the service
# account from settings), so firebase_admin.auth has a default app to use.
from app import auth as _app_auth  # noqa: F401
from firebase_admin import auth

uid = os.environ["ADMIN_UID"]
email = os.environ["ADMIN_EMAIL"]
key = os.environ["WEB_API_KEY"]

print("\n=== minting custom token + exchanging for an ID token ===")
custom = auth.create_custom_token(uid, {"email": email})
if isinstance(custom, bytes):
    custom = custom.decode()

req = urllib.request.Request(
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={key}",
    data=json.dumps({"token": custom, "returnSecureToken": True}).encode(),
    headers={"Content-Type": "application/json"},
)
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        payload = json.load(r)
except urllib.error.HTTPError as e:
    print("token exchange failed:", e.code, e.read().decode()[:600])
    raise SystemExit(1)

id_token = payload.get("idToken")
if not id_token:
    print("no idToken in response:", json.dumps(payload)[:600])
    raise SystemExit(1)

print("id token minted, length:", len(id_token))
print("localId:", payload.get("localId"))
print("email:", payload.get("email"))


def call(path, label):
    print(f"\n=== GET {path} ({label}) ===")
    req = urllib.request.Request(
        f"http://127.0.0.1:8000{path}",
        headers={"Authorization": f"Bearer {id_token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read().decode()
            print("status:", r.status)
            try:
                print(json.dumps(json.loads(body), indent=2)[:1200])
            except Exception:
                print(body[:600])
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode()[:600])
    except Exception as e:
        print("ERR", type(e).__name__, e)


call("/api/user/me", "protected, syncs the local profile")
call("/api/admin/stats", "admin-only")
call("/api/watches", "protected, user's watches")
PY
