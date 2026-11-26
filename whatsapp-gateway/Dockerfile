# TicketFox WhatsApp gateway — Baileys-based, no Chromium.
#
# Deliberately tiny: the official wppconnect-server image unpacks to >4 GB and
# cannot fit on an 8 GB root volume. This image is ~250 MB.
FROM node:20-alpine

WORKDIR /app

# Baileys depends on `libsignal` straight from a git URL
# ("github:whiskeysockets/libsignal-node"), and node:20-alpine ships no git
# binary — without this the install dies with `npm error syscall spawn git`.
# python3/make/g++ are here in case any transitive addon has to compile.
RUN apk add --no-cache git python3 make g++ \
    && rm -rf /var/cache/apk/*

# Install dependencies first so the layer caches across source edits.
COPY package.json ./
RUN npm install --omit=dev --no-audit --no-fund \
    && npm cache clean --force

# The toolchain is only needed while installing; drop it so the final image
# stays small (this box has very little disk headroom).
RUN apk del git python3 make g++ 2>/dev/null || true

COPY server.js ./

# Baileys writes credentials here; mount a volume so the link survives restarts.
ENV AUTH_DIR=/data/auth
RUN mkdir -p /data/auth

EXPOSE 21465

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD node -e "require('http').get('http://127.0.0.1:21465/health',r=>process.exit(r.statusCode===200?0:1)).on('error',()=>process.exit(1))"

CMD ["node", "server.js"]
