"""Render the real alert email HTML to a file for visual inspection.

Usage (from the ``backend`` directory):

    python scripts/render_email.py

Writes ``email_preview.html`` next to this script.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import notifications  # noqa: E402
from app.engine.models import Show, Source  # noqa: E402

WATCH = {
    "id": 0,
    "movie_id": "",
    "movie_title": "TicketFox Test Alert",
    "source": "bookmyshow",
    "city": "Hyderabad",
}

SHOWS = [
    Show(
        source=Source.BOOKMYSHOW,
        movie_id="et00000000",
        movie_name="TicketFox Test Alert",
        theatre_id="t1",
        theatre_name="Sample Cinema — Nexus Mall",
        show_id="s1",
        show_time="2026-11-13T19:30",
        booking_url="https://in.bookmyshow.com",
        screen_format="2D",
    ),
    Show(
        source=Source.BOOKMYSHOW,
        movie_id="et00000000",
        movie_name="TicketFox Test Alert",
        theatre_id="t1",
        theatre_name="Sample Cinema — Nexus Mall",
        show_id="s2",
        show_time="2026-11-13T22:15",
        booking_url="https://in.bookmyshow.com",
        screen_format="IMAX",
    ),
]


def main() -> int:
    html = notifications.render_alert_html(WATCH, SHOWS, test=True)
    text = notifications.render_alert_text(WATCH, SHOWS, test=True)

    out = Path(__file__).with_name("email_preview.html")
    out.write_text(html, encoding="utf-8")

    txt = Path(__file__).with_name("email_preview.txt")
    txt.write_text(text, encoding="utf-8")

    print(f"html bytes : {len(html)}")
    print(f"text bytes : {len(text)}")
    print(f"wrote      : {out}")
    print(f"wrote      : {txt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
