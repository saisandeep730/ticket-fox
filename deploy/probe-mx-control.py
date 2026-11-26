"""Control test: is the 450 from Private Email meaningful, or generic?

RFC 5321 requires every mail domain to accept ``postmaster@``. So:
  * postmaster@ticketfox.site -> 250  => the domain IS provisioned; the 450 on
    support@ means that specific mailbox has not been created.
  * postmaster@ticketfox.site -> 450  => the domain is NOT provisioned at
    Private Email at all; the MX records point at a server that has never heard
    of ticketfox.site, so every address bounces.

Run locally:  python deploy/probe-mx-control.py
"""

import smtplib
import socket
import sys

MX_HOSTS = ["mx1.privateemail.com", "mx2.privateemail.com"]
SENDER = "probe.test.9f3a@gmail.com"
ADDRESSES = [
    "postmaster@ticketfox.site",   # must exist if the domain is provisioned
    "abuse@ticketfox.site",        # also conventionally required
    "support@ticketfox.site",      # the address we actually care about
]


def probe(mx: str, address: str) -> str:
    try:
        with smtplib.SMTP(mx, 25, timeout=25) as s:
            s.ehlo("probe.local")
            code, msg = s.mail(SENDER)
            if code >= 400:
                return f"MAIL FROM rejected: {code}"
            code, msg = s.rcpt(address)
            text = msg.decode("utf-8", "replace") if isinstance(msg, bytes) else str(msg)
            return f"{code} {text}"
    except (socket.timeout, OSError, smtplib.SMTPException) as exc:
        return f"ERROR {type(exc).__name__}: {exc}"


def main() -> int:
    for mx in MX_HOSTS:
        print(f"== {mx} ==")
        for addr in ADDRESSES:
            print(f"  {addr:34s} -> {probe(mx, addr)}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
