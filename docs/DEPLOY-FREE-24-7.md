# Running Ticket Fox 24/7 for free

## Why not a free "web service" host

Ticket Fox is not a request/response website. It is **three always-on processes**:

| Process | Why it must stay awake |
|---|---|
| `backend` (`run.py`) | FastAPI **and** the polling worker in one process. The worker polls BookMyShow/District every 60–180 s and sends alerts. |
| `frontend` (Next.js) | Serves the UI. |
| `wppconnect-server` | Holds a live WhatsApp Web session. If the process dies, the QR link is lost and WhatsApp alerts stop. |

Free tiers on Render, Railway, Koyeb, Fly.io and Heroku **sleep or stop idle services**. A sleeping worker sends no alerts, and a sleeping wppconnect loses its session. So the only genuinely free 24/7 option is a **free-forever VM** that runs all three under Docker Compose.

## The free VM options

| Provider | Free tier | Notes |
|---|---|---|
| **Oracle Cloud Always Free** | 4 ARM cores / 24 GB RAM, forever | Best fit. Ampere A1 shape. Requires a card for verification only. |
| **Google Cloud e2-micro** | 1 shared vCPU / 1 GB, always free in `us-central1` | Tight but workable; add 2 GB swap. |
| **AWS EC2 t2.micro/t3.micro** | 750 h/month for 12 months | **Not** free after 12 months. |
| **Fly.io** | 3 shared-cpu-1x 256 MB VMs | Free allowance, but 256 MB is too small for Next.js + Python + Chromium-based wppconnect. |

**Recommendation: Oracle Cloud Always Free (Ampere A1, 2 OCPU / 12 GB).** It is free forever, has enough RAM for all four containers, and gives a public IPv4.

---

## Step 1 — Create the VM

1. Sign up at <https://cloud.oracle.com> → *Compute → Instances → Create*.
2. Image: **Ubuntu 22.04**. Shape: **VM.Standard.A1.Flex**, 2 OCPU / 12 GB.
3. Download the SSH key. Note the **public IP**.
4. In the VCN security list, open inbound **80** and **443** (TCP). Leave 8000/3000/21465 closed — Caddy is the only public entrypoint.

## Step 2 — Point a hostname at it

You need a real domain for automatic HTTPS. Free options:

- **DuckDuckDNS**: create `ticketfox.duckdns.org`, set its IP to the VM's public IP.
- **Cloudflare** (free plan): add an `A` record `ticketfox` → VM IP, proxy **off** (grey cloud) so Let's Encrypt can validate.

Verify: `ping ticketfox.duckdns.org` resolves to the VM IP.

## Step 3 — Install Docker

```bash
ssh ubuntu@<VM_IP>
sudo apt update && sudo apt install -y git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
```

## Step 4 — Get the code onto the VM

```bash
git clone <your-repo-url> ticket-fox-web
cd ticket-fox-web
```

If the repo is private, use a deploy key or `scp -r` from your machine.

## Step 5 — Fill in the two env files

**`./.env`** (compose-level, from `.env.example`):

```bash
cp .env.example .env
nano .env
```

```ini
DOMAIN=ticketfox.duckdns.org
WHATSAPP_SECRET_KEY=<openssl rand -hex 24>
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
NEXT_PUBLIC_FIREBASE_PROJECT_ID=...
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=...
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=...
NEXT_PUBLIC_FIREBASE_APP_ID=...
NEXT_PUBLIC_ADMIN_EMAIL=you@example.com
NEXT_PUBLIC_ADMIN_UID=<firebase uid>
```

**`./backend/.env`** (from `backend/.env.example`):

```bash
cp backend/.env.example backend/.env
nano backend/.env
```

Set at minimum:

```ini
DEBUG=false
ALLOW_MOCK_AUTH=false
SECRET_KEY=<openssl rand -hex 32>
FIREBASE_CREDENTIALS_PATH=/app/firebase-service-account.json
ADMIN_UID=<same uid as NEXT_PUBLIC_ADMIN_UID>
ADMIN_EMAIL=you@example.com
RESEND_API_KEY=re_...
RESEND_FROM=TicketFox <alerts@yourdomain.com>
WHATSAPP_API_TOKEN=<minted in step 7>
WHATSAPP_SESSION=ticketfox
TMDB_API_KEY=...
```

> `WHATSAPP_SECRET_KEY` (in `./.env`) is the gateway's signing secret. `WHATSAPP_API_TOKEN` (in `backend/.env`) is the bearer token you mint from it in step 7. They are different values.

Copy the Firebase service-account JSON next to the backend so the container can read it:

```bash
cp ~/firebase-service-account.json backend/firebase-service-account.json
```

Then add a read-only mount for it in `docker-compose.yml` under `backend.volumes`:

```yaml
    volumes:
      - backend_data:/data
      - ./backend/firebase-service-account.json:/app/firebase-service-account.json:ro
```

> Docker creates a **directory** at the mount point if the source file is missing, and the backend then fails with `IsADirectoryError`. Create the file before the first `docker compose up`.

## Step 6 — Build and start

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f backend
```

Caddy fetches a certificate on first request. Open `https://ticketfox.duckdns.org` — the site should load, and `https://ticketfox.duckdns.org/health` should return the backend health JSON.

## Step 7 — Mint the WhatsApp token and link the session

The gateway mints a bearer token from `WHATSAPP_SECRET_KEY`. Run these **on the VM** (port 21465 is not public).

```bash
# 1. Mint a token. Copy the returned value into backend/.env as WHATSAPP_API_TOKEN.
curl -X POST "http://127.0.0.1:21465/api/ticketfox/$(grep WHATSAPP_SECRET_KEY .env | cut -d= -f2)/generate-token"
```

```bash
# 2. Start the session (use the token from step 1)
TOKEN=<minted token>
curl -X POST "http://127.0.0.1:21465/api/ticketfox/start-session" \
  -H "Authorization: Bearer $TOKEN"

# 3. Fetch the QR (base64 PNG) and open it
curl "http://127.0.0.1:21465/api/ticketfox/qrcode-session" \
  -H "Authorization: Bearer $TOKEN"
```

Scan the QR with the phone that will send alerts. Confirm:

```bash
curl "http://127.0.0.1:21465/api/ticketfox/status-session" \
  -H "Authorization: Bearer $TOKEN"
```

`"status": "CONNECTED"` means alerts will flow. Then restart the backend so it picks up the token:

```bash
docker compose restart backend
```

## Step 8 — Verify the worker is polling

```bash
docker compose logs -f backend | grep worker
```

You should see `Worker cycle completed in ...s` every 60–180 s. If you see `All N watch(es) ... are resting`, that is normal — watches for unreleased movies are parked until their release tier.

---

## Operating it

| Task | Command |
|---|---|
| Update after a code change | `git pull && docker compose up -d --build` |
| Restart one service | `docker compose restart backend` |
| View logs | `docker compose logs -f backend` |
| Back up the database | `docker compose exec backend cp /data/ticket_fox_web.db /data/backup.db` then `docker cp $(docker compose ps -q backend):/data/backup.db .` |
| Stop everything | `docker compose down` (volumes survive) |

`restart: unless-stopped` on every service means the stack comes back after a VM reboot or a container crash, with no cron or systemd unit needed.

## Things that will bite you

- **`NEXT_PUBLIC_*` are baked in at build time.** Changing them requires `docker compose up -d --build frontend`, not just a restart.
- **SQLite lives in the `backend_data` volume.** `docker compose down -v` deletes every watch and user. Back it up first.
- **The WhatsApp session lives in `wppconnect_tokens`.** Same warning — `down -v` forces a re-scan.
- **Oracle's free ARM instances can be reclaimed** if idle for long periods on some accounts. The worker's constant polling keeps it active, which helps.
- **`CORS_ORIGINS` is set to `https://$DOMAIN` by compose.** If you add a second hostname, add it there.
- **Resend's `onboarding@resend.dev` sender only delivers to your own verified address.** Verify your domain in Resend and set `RESEND_FROM` to an address on it before real users rely on email alerts.
