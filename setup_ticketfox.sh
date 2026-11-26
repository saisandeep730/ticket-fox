#!/usr/bin/env bash
set -e

echo "=== 1. Setting up Backend ==="
cd /home/ubuntu/ticket-fox-web/backend

cat << 'EOF' > /home/ubuntu/ticket-fox-web/backend/.env
HOST=127.0.0.1
PORT=8000
DEBUG=false
DATABASE_URL=
ALLOW_MOCK_AUTH=true
FIREBASE_SERVICE_ACCOUNT_JSON=
FIREBASE_CREDENTIALS_PATH=ticketfox-web-firebase-adminsdk-fbsvc-a0fa60b1fd.json
SECRET_KEY=change_me_production_secret_key_32_chars
CORS_ORIGINS=*
WORKER_ENABLED=true
POLL_INTERVAL_SECONDS=180
WORKER_CONCURRENCY=3
ADMIN_UID=
IMPERSONATE=safari18_0
RESEND_API_KEY=re_your_resend_api_key
RESEND_FROM=TicketFox <onboarding@resend.dev>
WHATSAPP_API_URL=http://127.0.0.1:2785
WHATSAPP_API_TOKEN=your_whatsapp_token
WHATSAPP_SESSION=ticketfox
TMDB_API_KEY=your_tmdb_api_key
PUBLIC_APP_URL=https://ticketfox.site
EOF

echo "Backend env configured."

echo "=== 2. Setting up Frontend ==="
cd /home/ubuntu/ticket-fox-web/frontend

cat << 'EOF' > /home/ubuntu/ticket-fox-web/frontend/.env.local
NEXT_PUBLIC_API_URL=
NEXT_PUBLIC_FIREBASE_API_KEY=your_firebase_api_key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=ticketfox-web.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=ticketfox-web
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=ticketfox-web.firebasestorage.app
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=595371367509
NEXT_PUBLIC_FIREBASE_APP_ID=1:595371367509:web:145077a5f7f134f76fc8dc
EOF

echo "Installing frontend dependencies..."
npm install

echo "Building Next.js frontend..."
npm run build

echo "Frontend built successfully!"
