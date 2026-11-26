#!/usr/bin/env python3
"""Probe what the Resend key is allowed to send.

Sends to Resend's official test address (delivered@resend.dev) from two
different senders:
  1. onboarding@resend.dev  (the shared sandbox sender)
  2. noreply@ticketfox.site (only works if the domain is verified)

The HTTP status/body tells us whether ticketfox.site is verified, without
delivering anything to a real inbox.
"""
import json
import urllib.error
import urllib.request

ENV = "/home/ubuntu/ticket-fox-web/backend/.env"
TEST_TO = "delivered@resend.dev"


def read_key() -> str:
    with open(ENV, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("RESEND_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def send(key: str, sender: str) -> None:
    payload = json.dumps(
        {
            "from": sender,
            "to": [TEST_TO],
            "subject": "TicketFox Resend probe",
            "html": "<p>probe</p>",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "TicketFox/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            print(f"  from={sender!r:40} -> HTTP {resp.status} {resp.read().decode()[:200]}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:300]
        print(f"  from={sender!r:40} -> HTTP {exc.code} {body}")
    except Exception as exc:  # noqa: BLE001
        print(f"  from={sender!r:40} -> {type(exc).__name__}: {exc}")


def main() -> None:
    key = read_key()
    print(f"key prefix: {key[:6]}...  to={TEST_TO}")
    send(key, "TicketFox <onboarding@resend.dev>")
    send(key, "TicketFox <noreply@ticketfox.site>")
    # Control: an unverified domain must be rejected, proving a 200 above is
    # meaningful (i.e. ticketfox.site really is verified).
    send(key, "TicketFox <noreply@definitely-not-verified-xyz.com>")


if __name__ == "__main__":
    main()
