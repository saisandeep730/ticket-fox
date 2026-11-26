# TicketFox — Live Deployment Record

Status: **LIVE and verified end-to-end** (2026-11-14). Migrated to the custom
domain **`ticketfox.site`** on 2026-11-16 (see §9).

This document records the actual production instance, the secrets surface, and the
verification evidence for every subsystem. It is the operational reference for the
running deployment — not a plan.

---

## 1. Public endpoints

| What | URL |
| --- | --- |
| Web app | https://ticketfox.site (alias: https://www.ticketfox.site) |
| Admin control plane | https://ticketfox.site/admin |
| Health probe | https://ticketfox.site/health |
| WhatsApp pairing page | https://ticketfox.site/qr/<WHATSAPP_SECRET_KEY> |
| Legacy hostname | https://ticketfox.duckdns.org (kept as `DOMAIN_ALT` during the DNS move) |

TLS is issued and auto-renewed by Caddy (Let's Encrypt) for **both** hostnames.

---

## 2. Infrastructure

| Item | Value |
| --- | --- |
| Cloud | AWS EC2 |
| Instance ID | `i-003a1dedf273db4b5` |
| Type | `t3.small` |
| Region / AZ | `eu-north-1` / `eu-north-1c` |
| Public IP | `13.53.172.114` (Elastic IP recommended — all domain A records point here) |
| SSH | `ssh -i D:\Ticketfox.pem ubuntu@13.53.172.114` |
| App directory | `/home/ubuntu/ticket-fox-web` |
| Primary domain | `ticketfox.site` (Namecheap; A record → `13.53.172.114`) |
| Alt domain | `ticketfox.duckdns.org` (kept serving via `DOMAIN_ALT`) |
| Inbound ports | 22 (SSH, restricted), 80 (HTTP → ACME + redirect), 443 (HTTPS) |
| Swap | 2 GB swapfile (required — `t3.small` has 2 GB RAM and the frontend build is memory-hungry) |

> **Note:** the instance has **no IAM instance profile**, so the EBS volume cannot be
> resized from inside the guest. Enlarge it in the AWS console if disk pressure returns.

---

## 3. Container stack

`docker compose` runs four services:

| Service | Image / build | Role |
| --- | --- | --- |
| `caddy` | `caddy:2-alpine` | TLS termination + reverse proxy |
| `frontend` | `frontend/Dockerfile` (Next.js standalone) | UI on `:3000` |
| `backend` | `backend/Dockerfile` (FastAPI + uvicorn) | API + polling worker on `:8000` |
| `wppconnect` | `whatsapp-gateway/Dockerfile` (Baileys) | WhatsApp Web client on `:21465` (not host-published) |

### Caddy routing

```
/api/*      -> backend:8000
/health     -> backend:8000
/qr/*       -> wppconnect:21465
/qr-api/*   -> wppconnect:21465
everything  -> frontend:3000
```

The `/qr` and `/qr-api` routes exist because the gateway's own `/api/...` paths would
otherwise collide with the backend's `/api/*` prefix.

---

## 4. Secrets surface

All secrets live in `.env` (compose) and `backend/.env` (backend). They are **not** in
the repo. Values below are recorded so the operator can recover the deployment; treat
this file as sensitive.

| Variable | Where | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | `backend/.env` | **Doubles as the admin key** for `/admin` and `X-Admin-Key` |
| `WHATSAPP_SECRET_KEY` | both | Gateway session secret + `/qr/<secret>` path |
| `WHATSAPP_API_TOKEN` | both | Deterministic HMAC bearer token for the gateway |
| `FIREBASE_SERVICE_ACCOUNT_JSON` / mount | `backend/` | Firebase Admin SDK credentials |
| `NEXT_PUBLIC_FIREBASE_*` | `.env` | Baked into the frontend at **build** time |
| `RESEND_API_KEY` | `backend/.env` | Email delivery |
| `TMDB_API_KEY` | `backend/.env` | Movie metadata |
| `ADMIN_EMAIL` | both | `saisandeepy456@gmail.com` |
| `ADMIN_UID` | both | `1tXP1wmqmgXhVZvOiIgDL5L8sm03` |

> `NEXT_PUBLIC_*` values are compiled into the JS bundle. Changing them requires a
> **frontend image rebuild**, not just a restart.

---

## 5. Identity

| Item | Value |
| --- | --- |
| Firebase project | `ticketfox-web` |
| Web API key | `your_firebase_web_api_key` |
| Admin email | `saisandeepy456@gmail.com` |
| Admin UID | `1tXP1wmqmgXhVZvOiIgDL5L8sm03` |
| Authorized domains | `localhost`, `ticketfox-web.firebaseapp.com`, `ticketfox-web.web.app`, `ticketfox.duckdns.org`, `ticketfox.site`, `www.ticketfox.site` |
| WhatsApp linked number | `917305742393` |

### Two independent admin mechanisms

1. **Admin dashboard (`/admin`)** — key-based. The operator pastes `SECRET_KEY`; the page
   sends it as `X-Admin-Key` and stores it in `localStorage["ticketfox_admin_key"]`.
2. **`isAdminUser()`** in the frontend — compares the signed-in Firebase email/uid against
   `NEXT_PUBLIC_ADMIN_EMAIL` / `NEXT_PUBLIC_ADMIN_UID`.

> **Gotcha:** `verify_admin()` in `backend/app/main.py` prefers the `Authorization: Bearer`
> value over `X-Admin-Key`. Never send both on an admin call — the bearer token will
> override the key and the request will 403.

---

## 6. Verification evidence

### 6.1 Authentication (Firebase)

A real ID token was minted server-side (custom token → Identity Toolkit exchange) and
accepted by `verify_id_token`:

| Call | Result |
| --- | --- |
| `GET /api/user/me` | `200` — profile synced |
| `GET /api/watches` | `200` — `{"watches": []}` |
| `GET /api/admin/stats` with a Firebase token | `403` — **by design** (admin is key-based) |

Google sign-in popup opens on the production domain with no `auth/unauthorized-domain`
error, confirming the authorized-domain entry.

### 6.2 Admin control plane

`X-Admin-Key` == `SECRET_KEY` unlocks `/admin`. Live dashboard values:

| Metric | Value |
| --- | --- |
| Total users | 3 |
| Active watches | 2 of 2 |
| Alerts delivered | 6 |
| Worker cadence | 180 s |
| Delivery transports | Email (Resend) ✅ · WhatsApp (OpenWA) ✅ |
| Failing poll keys | 0 |

### 6.3 Poll → detect → deliver → log pipeline

A real watch was created and a worker cycle was triggered:

```
POST /api/watches        -> 201  (G.O.A.T / ET00476213 / Hyderabad / region HYD)
POST /api/worker/cycle   -> 200  {keys_polled: 1, duration_seconds: 0.61}
```

The worker detected 5 showtimes across 5 cinemas and delivered on **both** channels:

| Alert id | Channel | Status |
| --- | --- | --- |
| 5 | email | `SENT` |
| 6 | whatsapp | `SENT` |

The watch transitioned `UNKNOWN → AVAILABLE` with `last_checked_at` and `notified_at`
populated and 5 `last_shows` entries persisted.

### 6.4 Channels

| Channel | Test | Result |
| --- | --- | --- |
| Email (Resend) | test alert | delivered |
| WhatsApp (Baileys gateway) | self-send to `917305742393` | `{"status":true,"message":"sent"}` |

---

## 7. Operational commands

```bash
# On the instance
cd ~/ticket-fox-web

docker compose ps                      # container health
docker compose logs -f backend         # API + worker logs
docker compose logs -f wppconnect      # WhatsApp session logs
docker compose restart backend         # after editing backend/.env
docker compose up -d --build frontend  # after changing NEXT_PUBLIC_* values

# Health + channel state
curl -s https://ticketfox.site/health | python3 -m json.tool
curl -s https://ticketfox.site/api/channels | python3 -m json.tool

# Re-pair WhatsApp (open the printed URL in a browser and scan)
bash deploy/whatsapp-link.sh
```

### Re-running the verification scripts

| Script | Purpose |
| --- | --- |
| `deploy/verify.sh` | DNS, containers, health, auth mode, channels, TLS, worker |
| `deploy/remote-auth-e2e.sh` | Mint a real Firebase ID token and hit protected endpoints |
| `deploy/remote-admin-check.sh` | Prove the `X-Admin-Key` path and dump the admin row |
| `deploy/remote-watch-e2e.sh` | Create a watch, run a worker cycle, read the alert log |

---

## 8. Known limitations

1. **SQLite is ephemeral.** `/health` warns that the database is not durable in
   non-debug mode. Configure a hosted PostgreSQL (`DATABASE_URL`) before relying on
   long-lived watches.
2. **WhatsApp session is device-bound.** The Baileys session lives in `/data/auth` inside
   the container volume. If the phone unlinks the device, re-pair via `/qr/<secret>`.
3. **Resend shared sender.** `onboarding@resend.dev` only delivers to the account owner's
   verified address. The custom domain now makes domain verification possible — add the
   SPF/DKIM records Resend shows for `ticketfox.site` and switch `RESEND_FROM` to
   `TicketFox <alerts@ticketfox.site>` to email arbitrary users.
4. **No IAM instance profile.** EBS resizing must be done from the AWS console.
5. **Single instance.** No horizontal scaling; the worker runs in-process with the API.

---

## 9. Domain migration — DuckDNS → `ticketfox.site`

On 2026-11-16 the deployment moved from `ticketfox.duckdns.org` to the custom
domain `ticketfox.site`. Because the `Caddyfile` and `docker-compose.yml` are
domain-parameterized, the migration is a config-only change — no image rebuild.

### What changed

| Item | Where | Value |
| --- | --- | --- |
| `DOMAIN` | `./.env` | `ticketfox.site` |
| `DOMAIN_ALT` | `./.env` | `ticketfox.duckdns.org` (served by the same site block) |
| `PUBLIC_APP_URL` | `backend/.env` | `https://ticketfox.site` |
| `CORS_ORIGINS` | `backend/.env` | `https://ticketfox.site,https://www.ticketfox.site,https://ticketfox.duckdns.org` |
| Caddy site address | `Caddyfile` | `{$DOMAIN}, www.{$DOMAIN}, {$DOMAIN_ALT}` |
| caddy env | `docker-compose.yml` | `DOMAIN_ALT: ${DOMAIN_ALT:-${DOMAIN}}` (defaults to `DOMAIN`; must never be empty) |
| Authorized domains | Firebase Identity Toolkit config | added `ticketfox.site`, `www.ticketfox.site` |

`PUBLIC_APP_URL` and `CORS_ORIGINS` are also computed from `${DOMAIN}` in
`docker-compose.yml`, so they track `DOMAIN` automatically.

### Required DNS records (Namecheap → Advanced DNS)

Initially the apex resolved to Namecheap's parking page and `www` was a CNAME to
`parkingpage.namecheap.com`; **both had to be repointed** or Caddy's ACME
challenge fails (it validates the apex *and* `www`). This was done on
2026-11-16 and both hostnames now resolve to the instance IP.

| Type | Host | Value | TTL |
| --- | --- | --- | --- |
| A | `@` | `13.53.172.114` | Automatic |
| A | `www` | `13.53.172.114` | Automatic |

Delete the Namecheap parking records for `@` and `www` first. Do **not** leave a
`www` CNAME pointing at the parking page.

### Applying / re-verifying

```bash
# 1. Confirm DNS has propagated to the instance IP
nslookup ticketfox.site 8.8.8.8          # -> 13.53.172.114
nslookup www.ticketfox.site 8.8.8.8      # -> 13.53.172.114

# 2. Reload Caddy (it will request the cert once DNS is correct).
#    `up -d` does NOT recreate a container whose config is unchanged, so use
#    restart (or `up -d --force-recreate caddy`) to pick up a new Caddyfile.
cd ~/ticket-fox-web
docker compose restart caddy

# 3. Watch the ACME orders succeed (one per hostname: apex, www, DOMAIN_ALT)
docker compose logs caddy --tail 40 | grep -i 'certificate obtained\|error'

# 4. Verify every hostname end to end
for h in ticketfox.site www.ticketfox.site ticketfox.duckdns.org; do
  curl -s -o /dev/null -w "$h -> %{http_code} (tls=%{ssl_verify_result})\n" "https://$h/health"
done
curl -s https://ticketfox.site/api/channels
```

Once `https://ticketfox.site` serves with a valid cert and Google sign-in works
on that origin, unset `DOMAIN_ALT` in `./.env` and `docker compose restart caddy`
to stop serving the DuckDNS hostname (it then defaults to `DOMAIN`, so only the
apex and `www` remain).
