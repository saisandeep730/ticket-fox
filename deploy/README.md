# deploy/

Scripts and templates for the EC2 + DuckDNS deployment. Full walkthrough: [`docs/DEPLOY-EC2.md`](../docs/DEPLOY-EC2.md).

| File | Purpose |
|---|---|
| [`bootstrap.sh`](bootstrap.sh) | Installs Docker + Compose, adds 2 GB swap, caps Docker logs, extracts the archive, prints a preflight summary. Idempotent. |
| [`env.compose.template`](env.compose.template) | Copy to `./.env`. `DOMAIN`, `WHATSAPP_SECRET_KEY`, Firebase web config, admin identity. |
| [`env.backend.template`](env.backend.template) | Copy to `./backend/.env`. Auth, secrets, TMDB, Resend, WhatsApp, worker settings. |
| [`start.sh`](start.sh) | Validates config (env files, placeholders, service-account JSON, mount), then builds and starts the stack. |
| [`whatsapp-link.sh`](whatsapp-link.sh) | Mints the bearer token, persists it, starts the session, writes the QR to `/tmp/ticketfox-qr.png`. |
| [`verify.sh`](verify.sh) | Post-deploy checks: DNS, containers, health, `auth_mode`, channels, TLS, WhatsApp, worker. Exits non-zero on failure. |

## Order

```bash
bash deploy/bootstrap.sh        # host prep + extract
cp deploy/env.compose.template .env
cp deploy/env.backend.template backend/.env
# fill in the two REPLACE_WITH secrets, place the Firebase JSON
bash deploy/start.sh            # build + up
bash deploy/verify.sh           # confirm
bash deploy/whatsapp-link.sh    # link WhatsApp
docker compose restart backend
bash deploy/verify.sh           # confirm again
```

## Conventions

- Every script is idempotent and safe to re-run.
- Every script falls back to `sudo docker` when the user is not yet in the `docker` group.
- `verify.sh` is the gate: it exits non-zero if any hard check fails.
- Secrets are never written into the repo. `.env` and `backend/.env` are gitignored and `chmod 600`.
