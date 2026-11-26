#!/usr/bin/env python3
"""Idempotently set the auth-email settings in backend/.env on the instance.

Adds/updates AUTH_EMAIL_FROM and AUTH_EMAIL_ENABLED, and moves RESEND_FROM onto
the Resend-verified domain so alert emails also come from ticketfox.site.
"""
import re

ENV = "/home/ubuntu/ticket-fox-web/backend/.env"

UPDATES = {
    "RESEND_FROM": "TicketFox <alerts@ticketfox.site>",
    "AUTH_EMAIL_FROM": "TicketFox <noreply@ticketfox.site>",
    "AUTH_EMAIL_ENABLED": "true",
}


def main() -> None:
    with open(ENV, "r", encoding="utf-8") as fh:
        lines = fh.readlines()

    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        m = re.match(r"^([A-Z0-9_]+)=", line)
        if m and m.group(1) in UPDATES:
            key = m.group(1)
            out.append(f"{key}={UPDATES[key]}\n")
            seen.add(key)
        else:
            out.append(line)

    missing = [k for k in UPDATES if k not in seen]
    if missing:
        if out and not out[-1].endswith("\n"):
            out.append("\n")
        out.append("\n# Branded auth emails (password reset + email verification)\n")
        for key in missing:
            out.append(f"{key}={UPDATES[key]}\n")

    with open(ENV, "w", encoding="utf-8") as fh:
        fh.writelines(out)

    print("updated keys:", ", ".join(sorted(UPDATES)))
    for line in out:
        if line.startswith(("RESEND_FROM", "AUTH_EMAIL")):
            print("  " + line.rstrip())


if __name__ == "__main__":
    main()
