@echo off
REM Starts a public Cloudflare quick tunnel to the local Next.js dev server.
REM Requires: backend (python run.py) and frontend (npm run dev) already running.

set CLOUDFLARED="C:\Program Files (x86)\cloudflared\cloudflared.exe"

if not exist %CLOUDFLARED% (
  echo cloudflared not found at %CLOUDFLARED%
  echo Install it with: winget install --id Cloudflare.cloudflared
  pause
  exit /b 1
)

echo Starting tunnel to http://localhost:3000 ...
echo Look for the https://....trycloudflare.com URL below. Keep this window open.
echo.

%CLOUDFLARED% tunnel --url http://localhost:3000 --no-autoupdate

echo.
echo Tunnel stopped.
pause
