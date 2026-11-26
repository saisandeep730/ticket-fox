#!/usr/bin/env bash
# TicketFox — one-shot remote env setup.
# Run on the EC2 host from the project root: bash deploy/remote-setup.sh
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
SA_NAME="ticketfox-web-firebase-adminsdk-fbsvc-a0fa60b1fd.json"

echo "==> project root: $ROOT"

# ---------------------------------------------------------------- compose env
if [ ! -f .env ]; then
  cp deploy/env.compose.template .env
  echo "    created .env from template"
else
  echo "    .env already exists — leaving it alone"
fi

# ---------------------------------------------------------------- backend env
if [ ! -f backend/.env ]; then
  cp deploy/env.backend.template backend/.env
  echo "    created backend/.env from template"
else
  echo "    backend/.env already exists — leaving it alone"
fi

# ------------------------------------------------------------------- secrets
W="$(openssl rand -hex 24)"
S="$(openssl rand -hex 32)"

if grep -q 'REPLACE_WITH_openssl_rand_hex_24' .env; then
  sed -i "s|REPLACE_WITH_openssl_rand_hex_24|${W}|" .env
  echo "    generated WHATSAPP_SECRET_KEY"
else
  echo "    WHATSAPP_SECRET_KEY already set"
fi

if grep -q 'REPLACE_WITH_openssl_rand_hex_32' backend/.env; then
  sed -i "s|REPLACE_WITH_openssl_rand_hex_32|${S}|" backend/.env
  echo "    generated SECRET_KEY"
else
  echo "    SECRET_KEY already set"
fi

# ------------------------------------------------------- firebase SA json
if [ -f "$HOME/firebase-service-account.json" ]; then
  mv "$HOME/firebase-service-account.json" "backend/${SA_NAME}"
  echo "    moved service account into backend/"
fi

if [ ! -s "backend/${SA_NAME}" ]; then
  echo "ERROR: backend/${SA_NAME} is missing or empty" >&2
  exit 1
fi

chmod 600 .env backend/.env "backend/${SA_NAME}"

# ------------------------------------------------------------------ validate
echo
echo "==> service account"
python3 - "backend/${SA_NAME}" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print("    project_id  :", d.get("project_id"))
print("    client_email:", d.get("client_email"))
print("    private_key :", "present" if d.get("private_key") else "MISSING")
PY

echo
echo "==> leftover placeholders"
if grep -rn 'REPLACE_WITH' .env backend/.env; then
  echo "ERROR: placeholders remain" >&2
  exit 1
else
  echo "    none"
fi

echo
echo "==> key values"
grep -E '^(DOMAIN|NEXT_PUBLIC_ADMIN_EMAIL|NEXT_PUBLIC_FIREBASE_PROJECT_ID)=' .env | sed 's/^/    /'
grep -E '^(ADMIN_EMAIL|ADMIN_UID|FIREBASE_CREDENTIALS_PATH|FIREBASE_PROJECT_ID|WHATSAPP_API_URL|WHATSAPP_SESSION|RESEND_FROM|PUBLIC_APP_URL)=' backend/.env | sed 's/^/    /'

echo
echo "==> permissions"
ls -l .env backend/.env "backend/${SA_NAME}" | sed 's/^/    /'

echo
echo "==> compose mount check"
if grep -q "${SA_NAME}" docker-compose.yml; then
  echo "    mount present in docker-compose.yml"
else
  echo "ERROR: ${SA_NAME} is not bind-mounted in docker-compose.yml" >&2
  exit 1
fi

echo
echo "---ENV_SETUP_OK---"
