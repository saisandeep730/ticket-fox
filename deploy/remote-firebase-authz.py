#!/usr/bin/env python3
"""Add an authorized domain to the Firebase project (Identity Toolkit Admin API).

Runs *inside* the backend container, where firebase-admin / google-auth are
already installed and the service-account JSON is mounted.

Usage (inside the container):
    python3 /tmp/remote-firebase-authz.py ticketfox.site [more.domains ...]

Exit codes:
    0  the domain list now contains every requested domain
    2  the API rejected the call (usually a missing IAM permission) — the
       domain has to be added in the Firebase console instead
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

SA_PATH = "/app/ticketfox-web-firebase-adminsdk-fbsvc-a0fa60b1fd.json"
PROJECT_ID = "ticketfox-web"
CONFIG_URL = (
    f"https://identitytoolkit.googleapis.com/admin/v2/projects/{PROJECT_ID}/config"
)
SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/identitytoolkit",
]


def access_token() -> str:
    import google.auth.transport.requests
    from google.oauth2 import service_account

    creds = service_account.Credentials.from_service_account_file(
        SA_PATH, scopes=SCOPES
    )
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def call(method: str, url: str, token: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        try:
            return exc.code, json.loads(raw)
        except Exception:
            return exc.code, {"raw": raw}


def main() -> int:
    wanted = [d.strip() for d in sys.argv[1:] if d.strip()]
    if not wanted:
        print("no domains given", file=sys.stderr)
        return 2

    token = access_token()

    status, config = call("GET", CONFIG_URL, token)
    if status != 200:
        print(f"GET config failed: {status} {config}", file=sys.stderr)
        return 2

    current = list(config.get("authorizedDomains") or [])
    print(f"current authorizedDomains: {current}")

    merged = list(current)
    for domain in wanted:
        if domain not in merged:
            merged.append(domain)

    if merged == current:
        print("nothing to do — all domains already authorized")
        return 0

    status, updated = call(
        "PATCH",
        CONFIG_URL + "?updateMask=authorizedDomains",
        token,
        {"authorizedDomains": merged},
    )
    if status != 200:
        print(f"PATCH config failed: {status} {updated}", file=sys.stderr)
        return 2

    final = list(updated.get("authorizedDomains") or [])
    print(f"updated authorizedDomains: {final}")
    missing = [d for d in wanted if d not in final]
    if missing:
        print(f"still missing: {missing}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
