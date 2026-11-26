"""Ask the domain's MX host whether a mailbox actually exists.

An SMTP RCPT TO probe is the only reliable way to tell "MX is configured" apart
from "the mailbox has been created". A 250/251 means the address is deliverable;
a 550/551/553 means the server is authoritative for the domain but has no such
mailbox (so mail to it would bounce).

Run locally:  python deploy/probe-mx-rcpt.py
"""

import smtplib
import socket
import sys

DOMAIN = "ticketfox.site"
MX_HOSTS = ["mx1.privateemail.com", "mx2.privateemail.com"]
SENDER = "probe.test.9f3a@gmail.com"
ADDRESSES = [
    "support@ticketfox.site",
    "alerts@ticketfox.site",
    "noreply@ticketfox.site",
    "hello@ticketfox.site",
    "definitely-not-a-real-mailbox-xyz@ticketfox.site",
]


def probe(mx: str, address: str) -> str:
    try:
        with smtplib.SMTP(mx, 25, timeout=20) as s:
            s.ehlo("probe.local")
            code, msg = s.mail(SENDER)
            if code >= 400:
                return f"MAIL FROM rejected: {code} {msg!r}"
            code, msg = s.rcpt(address)
            text = msg.decode("utf-8", "replace") if isinstance(msg, bytes) else str(msg)
            return f"{code} {text}"
    except (socket.timeout, OSError, smtplib.SMTPException) as exc:
        return f"ERROR {type(exc).__name__}: {exc}"


def main() -> int:
    for mx in MX_HOSTS:
        print(f"== {mx} ==")
        for addr in ADDRESSES:
            print(f"  {addr:52s} -> {probe(mx, addr)}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
