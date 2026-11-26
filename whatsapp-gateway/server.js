/**
 * TicketFox WhatsApp gateway — a minimal, wppconnect-compatible REST server.
 *
 * Why this exists
 * ---------------
 * `wppconnect/wppconnect-server` ships a multi-gigabyte `node_modules` tree and
 * cannot be unpacked on an 8 GB root volume. This server implements the exact
 * subset of the wppconnect REST contract that `backend/app/whatsapp.py` calls,
 * on top of Baileys (a pure-WebSocket WhatsApp Web client with no Chromium).
 *
 * Contract implemented (see backend/app/whatsapp.py for the client side):
 *   POST /api/:session/:secret/generate-token  -> { token }
 *   GET  /api/:session/status-session          -> { status: "CONNECTED" | ... }
 *   POST /api/:session/start-session           -> { status: true }
 *   GET  /api/:session/qrcode-session          -> { qrcode: "<base64 png>" }
 *   POST /api/:session/send-message            -> { status: true }
 *   POST /api/:session/close-session
 *   GET  /health
 *
 * Auth: every route except generate-token and /health requires
 * `Authorization: Bearer <token>`, where <token> is the value returned by
 * generate-token (derived from SECRET_KEY, so it survives restarts).
 */

'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const express = require('express');
const pino = require('pino');
const QRCode = require('qrcode');
const {
    default: makeWASocket,
    useMultiFileAuthState,
    DisconnectReason,
    fetchLatestBaileysVersion,
    Browsers,
} = require('@whiskeysockets/baileys');

const PORT = Number(process.env.PORT || 21465);
const SECRET_KEY = process.env.SECRET_KEY || '';
const AUTH_DIR = process.env.AUTH_DIR || '/data/auth';
const LOG_LEVEL = process.env.LOG_LEVEL || 'warn';

if (!SECRET_KEY) {
    console.error('[fatal] SECRET_KEY is not set');
    process.exit(1);
}

const logger = pino({ level: LOG_LEVEL });

/**
 * The bearer token is a deterministic HMAC of the secret, so the same token is
 * produced on every boot and the backend's stored WHATSAPP_API_TOKEN keeps
 * working across container restarts.
 */
const TOKEN = crypto
    .createHmac('sha256', SECRET_KEY)
    .update('ticketfox-whatsapp-token')
    .digest('hex');

/** @type {Map<string, Session>} */
const sessions = new Map();

class Session {
    constructor(name) {
        this.name = name;
        this.sock = null;
        this.status = 'CLOSED';
        this.qr = null;
        this.qrUpdatedAt = 0;
        this.starting = false;
        this.dir = path.join(AUTH_DIR, name);
    }

    async start() {
        if (this.starting) return;
        if (this.sock && ['CONNECTED', 'ISLOGGED', 'INCHAT', 'MAIN'].includes(this.status)) {
            return;
        }
        this.starting = true;
        try {
            fs.mkdirSync(this.dir, { recursive: true });
            const { state, saveCreds } = await useMultiFileAuthState(this.dir);
            const { version } = await fetchLatestBaileysVersion();

            const sock = makeWASocket({
                version,
                auth: state,
                logger,
                printQRInTerminal: false,
                browser: Browsers.ubuntu('Chrome'),
                syncFullHistory: false,
                markOnlineOnConnect: false,
                generateHighQualityLinkPreview: false,
            });
            this.sock = sock;

            sock.ev.on('creds.update', saveCreds);

            sock.ev.on('connection.update', async (update) => {
                const { connection, lastDisconnect, qr } = update;

                if (qr) {
                    try {
                        this.qr = await QRCode.toDataURL(qr, { margin: 1, width: 512 });
                        this.qrUpdatedAt = Date.now();
                        this.status = 'QRCODE';
                        console.log('[session:%s] QR ready — scan it', this.name);
                    } catch (err) {
                        console.error('[session:%s] QR render failed: %s', this.name, err.message);
                    }
                }

                if (connection === 'open') {
                    this.status = 'CONNECTED';
                    this.qr = null;
                    console.log('[session:%s] CONNECTED', this.name);
                }

                if (connection === 'close') {
                    const code = lastDisconnect?.error?.output?.statusCode;
                    const loggedOut = code === DisconnectReason.loggedOut;
                    this.status = loggedOut ? 'CLOSED' : 'DISCONNECTED';
                    this.sock = null;
                    console.log('[session:%s] closed (code=%s loggedOut=%s)', this.name, code, loggedOut);

                    if (loggedOut) {
                        // Credentials are dead — wipe them so a fresh QR can be issued.
                        try {
                            fs.rmSync(this.dir, { recursive: true, force: true });
                        } catch (_) {
                            /* ignore */
                        }
                    } else {
                        // Transient drop: reconnect with a small backoff.
                        setTimeout(() => {
                            this.start().catch((err) =>
                                console.error('[session:%s] reconnect failed: %s', this.name, err.message)
                            );
                        }, 3000);
                    }
                }
            });
        } catch (err) {
            this.status = 'CLOSED';
            console.error('[session:%s] start failed: %s', this.name, err.message);
            throw err;
        } finally {
            this.starting = false;
        }
    }

    async close() {
        try {
            if (this.sock) await this.sock.logout();
        } catch (_) {
            /* ignore */
        }
        this.sock = null;
        this.status = 'CLOSED';
        this.qr = null;
    }

    isConnected() {
        return ['CONNECTED', 'ISLOGGED', 'INCHAT', 'MAIN'].includes(this.status);
    }

    async sendText(phone, message) {
        if (!this.sock || !this.isConnected()) {
            throw new Error('session is not connected');
        }
        const jid = `${String(phone).replace(/\D/g, '')}@s.whatsapp.net`;
        await this.sock.sendMessage(jid, { text: message });
    }
}

function getSession(name) {
    let session = sessions.get(name);
    if (!session) {
        session = new Session(name);
        sessions.set(name, session);
    }
    return session;
}

// ---------------------------------------------------------------------------
// HTTP layer
// ---------------------------------------------------------------------------

const app = express();
app.use(express.json({ limit: '1mb' }));

app.get('/health', (_req, res) => {
    const states = {};
    for (const [name, session] of sessions) states[name] = session.status;
    res.json({ status: 'ok', sessions: states });
});

// ---------------------------------------------------------------------------
// Human-facing QR page
// ---------------------------------------------------------------------------
// Baileys rotates the pairing QR roughly every 20 seconds, so a one-shot PNG is
// useless. This page polls the gateway and repaints the code in place, which
// lets the operator scan it straight from a browser. It is gated by SECRET_KEY
// in the path so it is not publicly reachable.

app.get('/qr/:secret', (req, res) => {
    if (req.params.secret !== SECRET_KEY) {
        return res.status(401).type('text/plain').send('invalid secret');
    }
    res.type('html').send(`<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TicketFox — Link WhatsApp</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; min-height: 100vh; display: grid; place-items: center;
    background: #0b0d12; color: #e8ecf4;
    font: 15px/1.5 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  .card {
    width: min(92vw, 420px); padding: 28px 24px 24px; text-align: center;
    background: #12151d; border: 1px solid #232838; border-radius: 18px;
    box-shadow: 0 24px 60px -20px rgba(0,0,0,.8);
  }
  h1 { margin: 0 0 4px; font-size: 19px; letter-spacing: -.01em; }
  p  { margin: 0 0 20px; font-size: 13px; color: #8b93a7; }
  .frame {
    display: grid; place-items: center; width: 100%; aspect-ratio: 1;
    background: #fff; border-radius: 12px; padding: 12px; overflow: hidden;
  }
  .frame img { width: 100%; height: 100%; object-fit: contain; image-rendering: pixelated; }
  .frame .msg { color: #4a5163; font-size: 13px; padding: 0 16px; }
  .state {
    margin-top: 16px; font-size: 12px; letter-spacing: .08em;
    text-transform: uppercase; color: #6f7891;
  }
  .state b { color: #4ade80; font-weight: 600; }
  .state.warn b { color: #fbbf24; }
  .bar { margin-top: 14px; height: 3px; border-radius: 2px; background: #1d2230; overflow: hidden; }
  .bar i { display: block; height: 100%; width: 0; background: #4ade80; transition: width .25s linear; }
</style>
</head>
<body>
  <div class="card">
    <h1>Link your WhatsApp</h1>
    <p>Open WhatsApp &rarr; Linked devices &rarr; Link a device, then scan.</p>
    <div class="frame" id="frame"><div class="msg">Waiting for a QR code&hellip;</div></div>
    <div class="state" id="state">connecting</div>
    <div class="bar"><i id="bar"></i></div>
  </div>
<script>
(function () {
  var SESSION = ${JSON.stringify(process.env.DEFAULT_SESSION || 'ticketfox')};
  // The API guard expects the derived bearer token, not the raw secret.
  var SECRET  = ${JSON.stringify(TOKEN)};
  var frame = document.getElementById('frame');
  var state = document.getElementById('state');
  var bar   = document.getElementById('bar');
  var last  = null;
  var t0    = Date.now();

  function setState(text, warn) {
    state.innerHTML = text;
    state.className = 'state' + (warn ? ' warn' : '');
  }

  function tick() {
    var pct = Math.min(100, ((Date.now() - t0) / 20000) * 100);
    bar.style.width = pct + '%';
  }
  setInterval(tick, 200);

  function poll() {
    // NOTE: this page is served through Caddy, where /api/* belongs to the
    // backend. The gateway's own API is exposed under /qr-api/* instead.
    fetch('/qr-api/' + SESSION + '/status-session', {
      headers: { Authorization: 'Bearer ' + SECRET }
    })
      .then(function (r) { return r.json(); })
      .then(function (s) {
        if (s.status === 'CONNECTED') {
          setState('connected &mdash; you can close this tab');
          frame.innerHTML = '<div class="msg" style="color:#16a34a;font-size:15px">&#10003; WhatsApp linked</div>';
          bar.style.width = '100%';
          return true;
        }
        return fetch('/qr-api/' + SESSION + '/qrcode-session', {
          headers: { Authorization: 'Bearer ' + SECRET }
        })
          .then(function (r) { return r.json(); })
          .then(function (q) {
            if (q && q.qrcode) {
              if (q.qrcode !== last) {
                last = q.qrcode;
                t0 = Date.now();
                frame.innerHTML = '<img alt="WhatsApp pairing QR" src="data:image/png;base64,' + q.qrcode + '">';
              }
              setState('waiting for scan &mdash; code refreshes every 20s', true);
            } else {
              setState('starting session&hellip;', true);
            }
            return false;
          });
      })
      .catch(function () { setState('gateway unreachable', true); return false; })
      .then(function (done) { if (!done) setTimeout(poll, 2000); });
  }
  poll();
})();
</script>
</body>
</html>`);
});

// The pairing page is served from the site's own origin, where Caddy sends
// /api/* to the backend. Mirror the gateway API under /qr-api/* so the page can
// reach it, then rewrite the prefix and let the normal routes below handle it.
// NOTE: this must be a *global* middleware — Express restores req.url after a
// path-mounted middleware returns, which would undo the rewrite.
app.use((req, _res, next) => {
    if (req.url.startsWith('/qr-api/')) {
        req.url = '/api' + req.url.slice('/qr-api'.length);
    }
    next();
});

/** Bearer-token guard for everything under /api. */
app.use('/api', (req, res, next) => {
    // generate-token is the bootstrap call and is guarded by the secret in the path.
    if (/^\/[^/]+\/[^/]+\/generate-token$/.test(req.path)) return next();

    const header = req.get('authorization') || '';
    const presented = header.startsWith('Bearer ') ? header.slice(7).trim() : '';
    if (!presented || presented !== TOKEN) {
        return res.status(401).json({ status: false, message: 'invalid token' });
    }
    return next();
});

app.post('/api/:session/:secret/generate-token', (req, res) => {
    if (req.params.secret !== SECRET_KEY) {
        return res.status(401).json({ status: false, message: 'invalid secret key' });
    }
    return res.json({ status: true, token: TOKEN });
});

app.get('/api/:session/status-session', (req, res) => {
    const session = getSession(req.params.session);
    res.json({ status: session.status, session: session.name });
});

// The linked account's own identity. Useful for a delivery self-test: WhatsApp
// lets you message your own number, so this proves the send path end to end
// without needing a second phone.
app.get('/api/:session/me', (req, res) => {
    const session = getSession(req.params.session);
    const user = session.sock && session.sock.user;
    if (!user) {
        return res.status(404).json({
            status: false,
            message: 'session is not connected',
            state: session.status,
        });
    }
    const jid = user.id || '';
    return res.json({
        status: true,
        session: session.name,
        jid,
        phone: jid.split('@')[0].split(':')[0],
        name: user.name || null,
    });
});

app.post('/api/:session/start-session', async (req, res) => {
    const session = getSession(req.params.session);
    try {
        await session.start();
        res.json({ status: true, session: session.name, state: session.status });
    } catch (err) {
        res.status(500).json({ status: false, message: err.message });
    }
});

app.get('/api/:session/qrcode-session', (req, res) => {
    const session = getSession(req.params.session);
    if (!session.qr) {
        return res.status(404).json({
            status: false,
            message: session.isConnected() ? 'session already connected' : 'no QR available yet',
            state: session.status,
        });
    }
    // wppconnect returns a bare base64 PNG string (no data: prefix).
    const base64 = session.qr.replace(/^data:image\/png;base64,/, '');
    return res.json({ status: true, qrcode: base64, state: session.status });
});

app.post('/api/:session/send-message', async (req, res) => {
    const session = getSession(req.params.session);
    const { phone, message } = req.body || {};

    if (!message) {
        return res.status(400).json({ status: false, message: 'message is required' });
    }

    // The backend sends either a bare string or a one-element array.
    const raw = Array.isArray(phone) ? phone[0] : phone;
    if (!raw) {
        return res.status(400).json({ status: false, message: 'phone is required' });
    }

    try {
        await session.sendText(raw, message);
        return res.json({ status: true, message: 'sent' });
    } catch (err) {
        console.error('[session:%s] send failed: %s', session.name, err.message);
        return res.status(500).json({ status: false, message: err.message });
    }
});

app.post('/api/:session/close-session', async (req, res) => {
    const session = getSession(req.params.session);
    await session.close();
    res.json({ status: true, session: session.name });
});

app.listen(PORT, '0.0.0.0', () => {
    console.log('[gateway] listening on 0.0.0.0:%d', PORT);
    console.log('[gateway] auth dir: %s', AUTH_DIR);

    // START_ALL_SESSIONS mirrors the wppconnect env var: boot the default session
    // immediately so a QR is available without an explicit start-session call.
    if (String(process.env.START_ALL_SESSIONS || '').toLowerCase() === 'true') {
        const name = process.env.DEFAULT_SESSION || 'ticketfox';
        console.log('[gateway] auto-starting session "%s"', name);
        getSession(name)
            .start()
            .catch((err) => console.error('[gateway] auto-start failed: %s', err.message));
    }
});
