# Sharing Ticket Fox with a friend who is NOT on your network

Your app is two processes:

| Process | Port | Who needs to reach it |
| --- | --- | --- |
| Next.js frontend (`npm run dev`) | 3000 | **your friend's browser** |
| FastAPI backend (`python run.py`) | 8000 | only the Next.js server, on your machine |

The frontend proxies `/api/*` to the backend (see [`next.config.js`](../frontend/next.config.js:11)),
so **you only expose port 3000**. The backend stays on `127.0.0.1:8000`.

> [`frontend/.env.local`](../frontend/.env.local:1) now leaves `NEXT_PUBLIC_API_URL` empty on purpose.
> If it were `http://localhost:8000`, your friend's browser would try to reach *their own* machine.

---

## Manual steps (Cloudflare Tunnel)

`cloudflared` is already installed at:
`C:\Program Files (x86)\cloudflared\cloudflared.exe`

### 1. Keep the two servers running

- Terminal A: `cd backend` then `python run.py`
- Terminal B: `cd frontend` then `npm run dev`

### 2. Open a NEW terminal and start the tunnel

Easiest: double-click [`share.bat`](../share.bat:1) in the project root.

Or type the full command. Note the program name `cloudflared.exe` comes **before** `tunnel` —
typing only `tunnel` gives `'tunnel' is not recognized`:

```cmd
"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:3000
```

If you `cd` into the install folder first, you still need the exe name:

```cmd
cd "C:\Program Files (x86)\cloudflared"
cloudflared.exe tunnel --url http://localhost:3000
```

Wait ~10 seconds. It prints a box like:

```
+--------------------------------------------------------------------------------------------+
|  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |
|  https://random-words-1234.trycloudflare.com                                               |
+--------------------------------------------------------------------------------------------+
```

That `https://....trycloudflare.com` URL is what you send your friend.

### 3. Point alert links at the tunnel

Edit [`backend/.env`](../backend/.env:1):

```env
PUBLIC_APP_URL=https://random-words-1234.trycloudflare.com
```

Restart the backend (Ctrl+C in Terminal A, then `python run.py`). Without this, links
inside email/WhatsApp alerts point at your localhost and won't open for your friend.

### 4. Allow Google Sign-In (only if you use it)

Firebase Console → Authentication → Settings → **Authorized domains** → add
`random-words-1234.trycloudflare.com`.

### 5. Send the link

Your friend opens the URL from anywhere. Keep all three terminals open — closing the
tunnel terminal kills the link, and the URL changes each time you restart it.

---

## If the tunnel errors

| Error | Fix |
| --- | --- |
| `'cloudflared' is not recognized` | Use the full path above, or open a brand-new terminal. |
| `failed to request quick Tunnel: ... no such host` | DNS/network blocked. Try `nslookup api.trycloudflare.com`; if it fails, switch networks or use ngrok. |
| `Failed to dial a quic connection ... timeout` | Corporate/ISP blocks UDP 7844. Retry with `--protocol http2`. |
| Window closes instantly | Run it from an already-open terminal (not by double-clicking) so you can read the error. |

Retry with HTTP/2 if QUIC is blocked:

```cmd
"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:3000 --protocol http2
```

### Alternative: ngrok

```cmd
winget install --id Ngrok.Ngrok
ngrok config add-authtoken <your-token-from-dashboard.ngrok.com>
ngrok http 3000
```

Share the `https://....ngrok-free.app` URL. Same `PUBLIC_APP_URL` and Firebase steps apply.

---

## Before your friend tests it

1. **They share your data.** Everyone uses the same SQLite DB
   (`backend/ticket_fox_web.db`), so they see your watches and alerts and can delete them.
   Back it up first:
   ```cmd
   copy backend\ticket_fox_web.db backend\ticket_fox_web.backup.db
   ```
2. **Auth is open.** `ALLOW_MOCK_AUTH=true` lets anyone use the one-click demo sign-in.
   Fine for a friend, not for a public link.
3. **Secrets.** [`backend/.env`](../backend/.env:1) holds live Resend, WhatsApp and TMDB keys.
   It is git-ignored — never commit or paste it.
4. **Your laptop must stay awake** with all terminals running.

---

## Checklist

- [ ] Backend running on 8000
- [ ] Frontend running on 3000
- [ ] Tunnel running, URL copied
- [ ] `PUBLIC_APP_URL` set to the tunnel URL, backend restarted
- [ ] Tunnel host added to Firebase authorized domains (only for Google Sign-In)
- [ ] Link sent
