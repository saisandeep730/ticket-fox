# Deploying TicketFox to EC2 + a custom domain

Live target: **https://ticketfox.site** on EC2 `13.53.172.114` (Ubuntu, user `ubuntu`).
The original DuckDNS hostname `ticketfox.duckdns.org` is still served as
`DOMAIN_ALT`; see §9 of [`docs/LIVE-DEPLOYMENT.md`](LIVE-DEPLOYMENT.md) for the
migration. The DuckDNS-specific steps below remain valid for any hostname — just
substitute your own domain.

Four containers under Docker Compose:

| Service | Role | Public? |
|---|---|---|
| `caddy` | TLS termination + reverse proxy | 80, 443 |
| `frontend` | Next.js standalone server | no (3000) |
| `backend` | FastAPI + polling worker (one process) | no (8000) |
| `wppconnect` | WhatsApp Web session gateway | no (21465) |

Caddy routes `/api/*` and `/health` to the backend and everything else to the frontend, so the browser only ever talks to one origin.

---

## Prerequisites

- EC2 instance running Ubuntu 22.04/24.04, reachable at `13.53.172.114`
- SSH key at `D:\Ticketfox.pem`
- DuckDNS subdomain `ticketfox.duckdns.org` pointed at the instance IP
- Security group inbound: **22** (your IP), **80** (0.0.0.0/0), **443** (0.0.0.0/0). Nothing else.

> The stack needs ~1.5–2 GB idle because wppconnect runs Chromium. On a 1 GB instance the build itself will OOM — `bootstrap.sh` adds 2 GB swap to cover it.

---

## Step 1 — Point DNS at the instance

In the DuckDNS dashboard set `ticketfox` → `13.53.172.114` and save. Verify from your machine:

```powershell
nslookup ticketfox.duckdns.org
```

It must return `13.53.172.114`. Caddy cannot issue a certificate until this resolves and port 80 is reachable.

---

## Step 2 — Ship the code

There is no Git remote configured for this repo, so the code travels as an archive.

From the project root on Windows:

```powershell
tar --exclude=node_modules --exclude=.next --exclude=__pycache__ --exclude=.pytest_cache --exclude=*.db --exclude=.env --exclude=.env.local -czf ticket-fox-web-deploy.tar.gz .

scp -i "D:\Ticketfox.pem" ticket-fox-web-deploy.tar.gz ubuntu@13.53.172.114:~/
scp -i "D:\Ticketfox.pem" backend\ticketfox-web-firebase-adminsdk-fbsvc-a0fa60b1fd.json ubuntu@13.53.172.114:~/firebase-service-account.json
```

> The archive excludes `.env` and `.env.local` on purpose — secrets are created on the server in step 4.

---

## Step 3 — Bootstrap the host

```bash
ssh -i "D:\Ticketfox.pem" ubuntu@13.53.172.114
bash ~/ticket-fox-web/deploy/bootstrap.sh
```

If the archive has not been extracted yet, extract it first:

```bash
mkdir -p ~/ticket-fox-web
tar -xzf ~/ticket-fox-web-deploy.tar.gz -C ~/ticket-fox-web --strip-components=1
cd ~/ticket-fox-web
bash deploy/bootstrap.sh
```

`bootstrap.sh` installs Docker + the Compose plugin, adds 2 GB swap when RAM is under 7 GB, caps Docker logs at 10 MB × 3 per container, extracts the archive, and prints a preflight summary. It is idempotent.

---

## Step 4 — Create the two env files

```bash
cd ~/ticket-fox-web

cp deploy/env.compose.template .env
cp deploy/env.backend.template backend/.env

# Generate the two secrets and write them in place
sed -i "s|REPLACE_WITH_openssl_rand_hex_24|$(openssl rand -hex 24)|" .env
sed -i "s|REPLACE_WITH_openssl_rand_hex_32|$(openssl rand -hex 32)|" backend/.env

chmod 600 .env backend/.env
```

Both templates are pre-filled with the real Firebase web config, TMDB key, Resend key and admin identity (`saisandeepy456@gmail.com` / uid `1tXP1wmqmgXhVZvOiIgDL5L8sm03`). Review them, then confirm no placeholders remain:

```bash
grep -n REPLACE_WITH .env backend/.env || echo "clean"
```

Place the Firebase service account where the compose mount expects it:

```bash
cp ~/firebase-service-account.json backend/ticketfox-web-firebase-adminsdk-fbsvc-a0fa60b1fd.json
chmod 600 backend/ticketfox-web-firebase-adminsdk-fbsvc-a0fa60b1fd.json
```

> The filename must match `FIREBASE_CREDENTIALS_PATH` in `backend/.env` and the bind-mount target in `docker-compose.yml`. If the file is missing, Docker creates a **directory** at the mount point and the backend dies with `IsADirectoryError`.

---

## Step 5 — Build and start

```bash
cd ~/ticket-fox-web
bash deploy/start.sh
```

`start.sh` refuses to run if either env file is missing, still contains `REPLACE_WITH`, or the service-account JSON is absent or not mounted. It then builds and starts the stack.

First build takes several minutes (Next.js production build + Python dependencies). Watch the backend come up:

```bash
docker compose logs -f backend
```

Look for:

- `Firebase Admin SDK initialized successfully`
- `Uvicorn running on http://0.0.0.0:8000`
- `Starting Ticket Fox Web Unified Runner (API + Worker)`

---

## Step 6 — Verify

```bash
bash deploy/verify.sh
```

Checks DNS, all four containers, the healthcheck, `/health` (including `auth_mode`), `/api/health`, `/api/channels`, the frontend, the TLS issuer, the WhatsApp session, and the worker.

**The critical check is `auth_mode: firebase_admin`.** If it reports `mock` or `unconfigured`, the service-account JSON is not readable inside the container:

```bash
docker compose exec backend ls -l /app/*.json
```

---

## Step 7 — Link WhatsApp

```bash
bash deploy/whatsapp-link.sh
```

This mints a bearer token from `WHATSAPP_SECRET_KEY`, writes it into `backend/.env` as `WHATSAPP_API_TOKEN`, starts the session, and saves the QR to `/tmp/ticketfox-qr.png`.

Copy the QR down and scan it with WhatsApp → Linked devices:

```powershell
scp -i "D:\Ticketfox.pem" ubuntu@13.53.172.114:/tmp/ticketfox-qr.png .
```

Then restart the backend so it picks up the token, and re-verify:

```bash
docker compose restart backend
bash deploy/verify.sh
```

`status-session` must report `CONNECTED`.

---

## Step 8 — Firebase authorized domains

Firebase console → Authentication → Settings → **Authorized domains** → add `ticketfox.duckdns.org`.

Without this, Google sign-in fails with `auth/unauthorized-domain` and password-reset links break.

Then in the browser at `https://ticketfox.duckdns.org`:

- Google sign-in completes and the avatar appears
- Email/password sign-up and sign-in work
- Password reset email arrives and `/auth/action` completes
- `/admin` loads for `saisandeepy456@gmail.com`

---

## Step 9 — Email

`RESEND_FROM` is `TicketFox <onboarding@resend.dev>`, Resend's shared sender. It **only delivers to the Resend account owner's own verified address**.

DuckDNS cannot host the TXT records Resend needs for domain verification, so verifying `ticketfox.duckdns.org` is not possible. To email arbitrary users you need a real domain (or a free subdomain provider that supports TXT records). Until then, email alerts are owner-only.

Test delivery:

```bash
docker compose exec backend python -c "
import asyncio
from app.notifications import send_email
print(asyncio.run(send_email('saisandeepy456@gmail.com','TicketFox test','<b>It works</b>')))
"
```

---

## Step 10 — End-to-end

| Check | Expected |
|---|---|
| `https://ticketfox.duckdns.org` | Loads, valid padlock, no mixed content |
| `/health` | `status: ok`, `auth_mode: firebase_admin` |
| `/api/channels` | email and whatsapp both available |
| Create a watch | Persists and appears in the Watches tab |
| Test alert button | Email and/or WhatsApp arrives |
| `docker compose logs -f backend \| grep -i worker` | `Worker cycle completed` every ~180 s |
| `docker compose ps` | All four `Up`, backend `healthy` |
| Reboot the instance | Stack returns automatically |

---

## Operations

| Task | Command |
|---|---|
| Update code | re-`scp` the archive, re-extract, `docker compose up -d --build` |
| Restart one service | `docker compose restart backend` |
| Logs | `docker compose logs -f backend` |
| Back up SQLite | `docker compose exec backend cp /data/ticket_fox_web.db /data/backup.db` then `docker cp $(docker compose ps -q backend):/data/backup.db .` |
| Stop | `docker compose down` (volumes survive) |
| **Never** | `docker compose down -v` — deletes the database and the WhatsApp session |

---

## Traps

- `NEXT_PUBLIC_*` are baked in at **build** time. Changing them needs `docker compose up -d --build frontend`, not a restart.
- SQLite lives in the `backend_data` volume; the WhatsApp session lives in `wppconnect_tokens`.
- Caddy needs DNS and port 80 before it can issue a certificate. A wrong DuckDNS IP shows up as a TLS handshake failure, not a 404.
- `wppconnect:latest` can change behaviour between pulls. Pin the tag once it works.
- `ADMIN_EMAIL` in `backend/.env` and `NEXT_PUBLIC_ADMIN_EMAIL` in `.env` must be the same address, or the admin dashboard locks the account out.
