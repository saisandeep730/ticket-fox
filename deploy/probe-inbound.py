"""Send a real message to support@ticketfox.site and read back what happened to it.

Resend reports a per-email ``last_event`` (queued / sent / delivered / bounced /
complained). That is the only authoritative answer to "does this mailbox exist?" —
an SMTP RCPT probe only gets a greylist 450 from Private Email's callout verifier.

Run locally:  python deploy/probe-inbound.py
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

API_KEY = os.getenv("RESEND_API_KEY", "")
if not API_KEY:
    print("Error: RESEND_API_KEY environment variable is required", file=sys.stderr)
    sys.exit(1)
TARGET = "support@ticketfox.site"
SENDER = "TicketFox Alerts <alerts@ticketfox.site>"
BASE = "https://api.resend.com"


def call(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            # Resend sits behind Cloudflare, which rejects the default
            # "Python-urllib/x.y" agent with error 1010. The app sends this UA.
            "User-Agent": "TicketFox/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {"raw": body}


def main() -> int:
    status, body = call(
        "POST",
        "/emails",
        {
            "from": SENDER,
            "to": [TARGET],
            "subject": "TicketFox inbound mailbox check",
            "html": "<p>If you can read this, support@ticketfox.site is a live mailbox.</p>",
            "reply_to": TARGET,
        },
    )
    print(f"POST /emails -> {status} {body}")
    email_id = body.get("id")
    if not email_id:
        print("No email id returned — cannot poll status.")
        return 1

    for attempt in range(1, 13):
        time.sleep(5)
        st, info = call("GET", f"/emails/{email_id}")
        event = info.get("last_event")
        print(f"  poll {attempt:2d}: {st} last_event={event!r}")
        if event in {"delivered", "bounced", "complained", "failed", "canceled"}:
            print()
            print(f"FINAL: {event}")
            if event == "delivered":
                print("=> support@ticketfox.site ACCEPTS mail. The mailbox is live.")
            elif event == "bounced":
                print("=> support@ticketfox.site REJECTED mail. No mailbox exists yet.")
            return 0
    print("Timed out waiting for a terminal event.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
