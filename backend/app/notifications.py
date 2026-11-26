"""Out-of-band alert delivery: Email (Resend) and WhatsApp (wppconnect-server).

Channels:
* **Email** — the Resend HTTP API (``RESEND_API_KEY``).
* **WhatsApp** — the wppconnect-server gateway (see :mod:`app.whatsapp`).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any, Iterable

from app import whatsapp
from app.config import settings
from app.engine.models import Show
from app.engine.showtime import parse_show_time, show_day_label, spans_multiple_days

logger = logging.getLogger("ticket_fox_web.notifications")

RESEND_API = "https://api.resend.com/emails"
MAX_SHOWS_PER_CINEMA = 8

SENT = "sent"
FAILED = "failed"
SKIPPED = "skipped"          # the user has no target configured for this channel
UNAVAILABLE = "unavailable"  # the server has no transport configured


def channel_available(channel: str) -> bool:
    """Whether the *server* can deliver on ``channel`` at all."""
    if channel == "email":
        return bool(settings.RESEND_API_KEY or (settings.SMTP_HOST and settings.SMTP_USER)) or settings.DEBUG
    if channel == "whatsapp":
        return bool(settings.WHATSAPP_API_URL and settings.WHATSAPP_SESSION)
    return False


def channel_ready(channel: str) -> bool:
    """Whether ``channel`` is configured *and* actually usable right now.

    For WhatsApp this probes the gateway's session status (cached), so an
    unlinked session no longer reports "Ready" in Settings. Email has no
    equivalent probe, so it falls back to :func:`channel_available`.
    """
    if channel == "whatsapp":
        return channel_available("whatsapp") and whatsapp.is_connected()
    return channel_available(channel)


def channel_status() -> dict[str, bool]:
    return {name: channel_available(name) for name in ("email", "whatsapp")}


def user_targets(user: dict[str, Any] | None) -> dict[str, str]:
    """The per-user delivery targets saved on the profile."""
    user = user or {}
    whatsapp_target = (
        user.get("whatsapp_number")
        or user.get("phone")
        or user.get("mobile")
        or ""
    )
    return {
        "email": (user.get("email") or "").strip(),
        "whatsapp": str(whatsapp_target).strip(),
    }


def configured_channels(user: dict[str, Any] | None) -> list[str]:
    """Channels this user can actually be reached on right now."""
    targets = user_targets(user)
    return [name for name, target in targets.items() if target and channel_available(name)]


def _pretty_time(show: Show) -> str:
    parsed = parse_show_time(show.show_time)
    if parsed is None:
        return show.show_time
    return parsed.strftime("%I:%M %p").lstrip("0")


def _grouped(shows: Iterable[Show]) -> dict[str, list[Show]]:
    grouped: dict[str, list[Show]] = {}
    for show in shows:
        grouped.setdefault(show.theatre_name or "Cinema", []).append(show)
    for group in grouped.values():
        group.sort(key=lambda s: s.show_time)
    return grouped


def _booking_url(shows: list[Show]) -> str:
    for show in shows:
        if show.booking_url:
            return show.booking_url
    return ""


def _watch_city(watch: Any) -> str:
    return (getattr(watch, "city", "") or getattr(watch, "region_name", "") or "").strip()


def _render_cinema_block(
    header_lines: list[str],
    grouped: dict[str, list[Show]],
    *,
    multi_day: bool,
    footer_text: str,
    limit: int,
) -> str:
    """Fit as many cinemas/shows as possible under ``limit``, degrading gracefully."""
    cinema_items = list(grouped.items())
    for max_c, max_s in ((min(len(cinema_items), 8), 3), (5, 2), (3, 2), (1, 2)):
        c_lines: list[str] = []
        for cinema, group in cinema_items[:max_c]:
            c_lines.append(f"🏢 {cinema}")
            for show in group[:max_s]:
                day = show_day_label(show.show_time, weekday=True) if multi_day else ""
                when = f"{day} {_pretty_time(show)}".strip()
                fmt = f" · {show.screen_format}" if show.screen_format else ""
                c_lines.append(f"   • {when}{fmt}")
            if len(group) > max_s:
                c_lines.append(f"   … +{len(group) - max_s} more")
            c_lines.append("")

        if len(cinema_items) > max_c:
            c_lines.append(f"… and {len(cinema_items) - max_c} more cinemas!")
            c_lines.append("")

        candidate = "\n".join(header_lines) + "\n" + "\n".join(c_lines) + footer_text
        if len(candidate) <= limit:
            return candidate.strip()

    base = "\n".join(header_lines)
    cut_size = max(100, limit - len(footer_text) - 50)
    return f"{base[:cut_size]}\n…\n\n{footer_text}".strip()


def render_alert_text(watch: Any, shows: list[Show], *, test: bool = False, limit: int = 3500) -> str:
    """Plain-text alert (WhatsApp), strictly budgeted to fit within WhatsApp limits."""
    title = (getattr(watch, "movie_title", "") or getattr(watch, "movie_id", "") or "Your movie").strip()
    city = _watch_city(watch)
    source = str(getattr(watch, "source", "") or "").upper()
    grouped = _grouped(shows)
    multi_day = spans_multiple_days(shows)

    lines: list[str] = []
    lines.append("🧪 TICKETFOX TEST ALERT" if test else "🚨 TICKETS ARE OPEN! 🎟️")
    lines.append("")
    lines.append(f"🍿 {title}")
    meta = " · ".join(
        part for part in (f"📍 {city}" if city else "", f"🎬 {source}" if source else "") if part
    )
    if meta:
        lines.append(meta)
    lines.append(f"🟢 {len(shows)} showtime(s) across {len(grouped)} cinema(s)")
    lines.append("")

    booking = _booking_url(shows)
    footer_lines = [""]
    if booking:
        footer_lines.append(f"🎟️ Book now: {booking}")
        footer_lines.append("")
    footer_lines.append("🦊 TicketFox · Real-time Ticket Alerts")
    footer_lines.append(f"Manage your watches: {settings.PUBLIC_APP_URL}/")
    footer_text = "\n".join(footer_lines)

    return _render_cinema_block(
        lines, grouped, multi_day=multi_day, footer_text=footer_text, limit=limit
    )


def render_alert_html(watch: Any, shows: list[Show], *, test: bool = False) -> str:
    """HTML alert (email)."""
    title = (getattr(watch, "movie_title", "") or getattr(watch, "movie_id", "") or "Your movie").strip()
    city = _watch_city(watch)
    source = str(getattr(watch, "source", "") or "").upper()
    poster = (getattr(watch, "poster_url", "") or "").strip()
    grouped = _grouped(shows)
    multi_day = spans_multiple_days(shows)
    booking = _booking_url(shows)

    rows: list[str] = []
    for cinema, group in grouped.items():
        rows.append(
            f'<h3 style="margin:18px 0 6px;font-size:15px;color:#f8fafc;">🏢 {cinema}</h3>'
            '<ul style="margin:0;padding-left:18px;color:#cbd5e1;font-size:13px;line-height:1.7;">'
        )
        for show in group[:MAX_SHOWS_PER_CINEMA]:
            day = show_day_label(show.show_time, weekday=True) if multi_day else ""
            when = f"{day} {_pretty_time(show)}".strip()
            fmt = f" · {show.screen_format}" if show.screen_format else ""
            rows.append(f"<li>{when}{fmt}</li>")
        if len(group) > MAX_SHOWS_PER_CINEMA:
            rows.append(f"<li>… +{len(group) - MAX_SHOWS_PER_CINEMA} more</li>")
        rows.append("</ul>")

    poster_html = (
        f'<img src="{poster}" alt="{title}" width="140" '
        'style="border-radius:12px;display:block;margin-bottom:12px;" />'
        if poster
        else ""
    )
    button = (
        f'<a href="{booking}" style="display:inline-block;margin-top:16px;padding:12px 20px;'
        'border-radius:10px;background:#f97316;color:#fff;font-weight:700;text-decoration:none;">'
        "🎟️ Book now</a>"
        if booking
        else ""
    )
    banner = "🧪 TICKETFOX TEST ALERT" if test else "🚨 TICKETFOX — TICKETS ARE OPEN"
    source_meta = f" · {source}" if source else ""
    # Only emit the meta line when there is something to say, otherwise the
    # empty <p> still contributes its margin and leaves a visible gap.
    meta_html = (
        f'<p style="margin:0;color:#94a3b8;font-size:13px;">{city}{source_meta}</p>'
        if (city or source_meta)
        else ""
    )

    return f"""<!doctype html>
<html><body style="margin:0;background:#08090d;padding:24px;font-family:Segoe UI,Helvetica,Arial,sans-serif;">
  <div style="max-width:560px;margin:0 auto;background:#11131a;border:1px solid #1f2430;border-radius:16px;padding:24px;">
    <p style="margin:0 0 12px;font-size:12px;letter-spacing:1px;color:#fb923c;font-weight:700;">{banner}</p>
    {poster_html}
    <h1 style="margin:0 0 4px;font-size:20px;color:#f8fafc;">{title}</h1>
    {meta_html}
    <p style="margin:8px 0 0;color:#34d399;font-size:13px;font-weight:700;">
      🟢 {len(shows)} showtime(s) across {len(grouped)} cinema(s)
    </p>
    {''.join(rows)}
    {button}
    <p style="margin:24px 0 0;color:#64748b;font-size:12px;">
      🦊 TicketFox · Real-time Ticket Alerts<br />
      <a href="{settings.PUBLIC_APP_URL}/" style="color:#fb923c;">Manage your watches</a>
    </p>
  </div>
</body></html>"""


def render_new_shows_text(watch: Any, new_shows: list[Show], *, limit: int = 3500) -> str:
    """N3 — new show added later (plain-text, WhatsApp)."""
    title = (getattr(watch, "movie_title", "") or getattr(watch, "movie_id", "") or "Your movie").strip()
    city = _watch_city(watch)
    grouped = _grouped(new_shows)
    multi_day = spans_multiple_days(new_shows)

    lines: list[str] = [
        "🆕 NEW SHOW SPOTTED! 🎟️",
        "🦊 TicketFox found extra screenings added for your watch.",
        "",
        f"🍿 {title}",
    ]
    if city:
        lines.append(f"📍 {city}")
    lines.append(f"✨ {len(new_shows)} newly added showtime(s)")
    lines.append("")

    booking = _booking_url(new_shows)
    footer_lines = [""]
    if booking:
        footer_lines.append(f"🎟️ Book now: {booking}")
        footer_lines.append("")
    footer_lines.append("🦊 TicketFox · Real-time Ticket Alerts")
    footer_lines.append(f"Manage your watches: {settings.PUBLIC_APP_URL}/")
    footer_text = "\n".join(footer_lines)

    return _render_cinema_block(
        lines, grouped, multi_day=multi_day, footer_text=footer_text, limit=limit
    )


def render_new_shows_html(watch: Any, new_shows: list[Show]) -> str:
    """N3 — new show added later (HTML email)."""
    title = (getattr(watch, "movie_title", "") or getattr(watch, "movie_id", "") or "Your movie").strip()
    city = _watch_city(watch)
    poster = (getattr(watch, "poster_url", "") or "").strip()
    grouped = _grouped(new_shows)
    multi_day = spans_multiple_days(new_shows)
    booking = _booking_url(new_shows)

    rows: list[str] = []
    for cinema, group in grouped.items():
        rows.append(f'<h3 style="margin:16px 0 6px;font-size:15px;color:#f8fafc;">🏢 {cinema}</h3><ul style="margin:0;padding-left:18px;color:#cbd5e1;font-size:13px;line-height:1.7;">')
        for show in group[:MAX_SHOWS_PER_CINEMA]:
            day = show_day_label(show.show_time, weekday=True) if multi_day else ""
            when = f"{day} {_pretty_time(show)}".strip()
            fmt = f" · {show.screen_format}" if show.screen_format else ""
            rows.append(f"<li>{when}{fmt}</li>")
        rows.append("</ul>")

    poster_html = f'<img src="{poster}" alt="{title}" width="140" style="border-radius:12px;display:block;margin-bottom:12px;" />' if poster else ""
    btn = f'<a href="{booking}" style="display:inline-block;margin-top:16px;padding:12px 20px;border-radius:10px;background:#3b82f6;color:#fff;font-weight:700;text-decoration:none;">🎟️ Book new show</a>' if booking else ""

    return f"""<!doctype html>
<html><body style="margin:0;background:#08090d;padding:24px;font-family:Segoe UI,Helvetica,Arial,sans-serif;">
  <div style="max-width:560px;margin:0 auto;background:#11131a;border:1px solid #1f2430;border-radius:16px;padding:24px;">
    <p style="margin:0 0 12px;font-size:12px;letter-spacing:1px;color:#60a5fa;font-weight:700;">🆕 NEW SHOWTIME SPOTTED</p>
    {poster_html}
    <h1 style="margin:0 0 4px;font-size:20px;color:#f8fafc;">{title}</h1>
    <p style="margin:0;color:#94a3b8;font-size:13px;">{city}</p>
    <p style="margin:8px 0 0;color:#60a5fa;font-size:13px;font-weight:700;">✨ {len(new_shows)} newly added screening(s)</p>
    {''.join(rows)}
    {btn}
    <p style="margin:24px 0 0;color:#64748b;font-size:12px;">🦊 TicketFox · <a href="{settings.PUBLIC_APP_URL}/" style="color:#fb923c;">Manage watches</a></p>
  </div>
</body></html>"""


def render_back_text(watch: Any, shows: list[Show]) -> str:
    """N4 — tickets available again / re-stock (plain-text)."""
    title = (getattr(watch, "movie_title", "") or getattr(watch, "movie_id", "") or "Your movie").strip()
    city = _watch_city(watch)
    grouped = _grouped(shows)
    lines = [
        "🔔 TICKETS ARE BACK IN STOCK! 🎟️",
        "🦊 TicketFox spotted availability again for your sold-out watch.",
        "",
        f"🍿 {title}",
    ]
    if city:
        lines.append(f"📍 {city}")
    lines.append(f"🟢 {len(shows)} seat/showtime(s) returned!")
    lines.append("")
    booking = _booking_url(shows)
    if booking:
        lines.append(f"🎟️ Book before they sell out again: {booking}")
    lines.append(f"🦊 TicketFox: {settings.PUBLIC_APP_URL}/")
    return "\n".join(lines).rstrip()


def render_back_html(watch: Any, shows: list[Show]) -> str:
    """N4 — tickets available again (HTML email)."""
    title = (getattr(watch, "movie_title", "") or getattr(watch, "movie_id", "") or "Your movie").strip()
    city = _watch_city(watch)
    poster = (getattr(watch, "poster_url", "") or "").strip()
    booking = _booking_url(shows)
    poster_html = f'<img src="{poster}" alt="{title}" width="140" style="border-radius:12px;display:block;margin-bottom:12px;" />' if poster else ""
    btn = f'<a href="{booking}" style="display:inline-block;margin-top:16px;padding:12px 20px;border-radius:10px;background:#10b981;color:#fff;font-weight:700;text-decoration:none;">🎟️ Grab returned seats</a>' if booking else ""

    return f"""<!doctype html>
<html><body style="margin:0;background:#08090d;padding:24px;font-family:Segoe UI,Helvetica,Arial,sans-serif;">
  <div style="max-width:560px;margin:0 auto;background:#11131a;border:1px solid #1f2430;border-radius:16px;padding:24px;">
    <p style="margin:0 0 12px;font-size:12px;letter-spacing:1px;color:#34d399;font-weight:700;">🔁 TICKETS BACK IN STOCK</p>
    {poster_html}
    <h1 style="margin:0 0 4px;font-size:20px;color:#f8fafc;">{title}</h1>
    <p style="margin:0;color:#94a3b8;font-size:13px;">{city}</p>
    <p style="margin:8px 0 0;color:#34d399;font-size:13px;font-weight:700;">Seats just reopened! Move fast before they sell out again.</p>
    {btn}
    <p style="margin:24px 0 0;color:#64748b;font-size:12px;">🦊 TicketFox · <a href="{settings.PUBLIC_APP_URL}/" style="color:#fb923c;">Manage watches</a></p>
  </div>
</body></html>"""


def render_expired_text(watch: Any) -> str:
    """N8 — watch expired notice (plain-text)."""
    title = (getattr(watch, "movie_title", "") or getattr(watch, "movie_id", "") or "Your movie").strip()
    city = _watch_city(watch)
    return (
        f"⌛ WATCH ENDED\n\n"
        f"🎬 {title} (📍 {city})\n\n"
        "The calendar date you chose has passed, so there are no upcoming screenings left to monitor. "
        "TicketFox has automatically retired this watch. You can set up a new watch anytime!"
    )


def render_expired_html(watch: Any) -> str:
    """N8 — watch expired notice (HTML email)."""
    title = (getattr(watch, "movie_title", "") or getattr(watch, "movie_id", "") or "Your movie").strip()
    city = _watch_city(watch)
    return f"""<!doctype html>
<html><body style="margin:0;background:#08090d;padding:24px;font-family:Segoe UI,Helvetica,Arial,sans-serif;">
  <div style="max-width:560px;margin:0 auto;background:#11131a;border:1px solid #1f2430;border-radius:16px;padding:24px;">
    <p style="margin:0 0 12px;font-size:12px;letter-spacing:1px;color:#94a3b8;font-weight:700;">⌛ WATCH ENDED</p>
    <h1 style="margin:0 0 4px;font-size:20px;color:#f8fafc;">{title}</h1>
    <p style="margin:0;color:#94a3b8;font-size:13px;">{city}</p>
    <p style="margin:16px 0 0;color:#cbd5e1;font-size:14px;line-height:1.6;">
      The calendar date you chose for this movie has passed, so there are no upcoming screenings left to monitor.
      TicketFox has retired this watch to keep your dashboard clean.
    </p>
    <p style="margin:24px 0 0;color:#64748b;font-size:12px;">🦊 TicketFox · <a href="{settings.PUBLIC_APP_URL}/" style="color:#fb923c;">Visit dashboard</a></p>
  </div>
</body></html>"""


def render_outage_text(watch: Any) -> str:
    """N6 — sustained outage notice (plain-text)."""
    title = (getattr(watch, "movie_title", "") or getattr(watch, "movie_id", "") or "Your movie").strip()
    city = _watch_city(watch)
    return (
        f"⚠️ MONITORING ISSUE\n\n"
        f"We've encountered temporary provider blocks checking:\n"
        f"🎬 {title} (📍 {city})\n\n"
        "Your watch remains active. Our engine is automatically retrying with exponential backoff."
    )


def render_outage_html(watch: Any) -> str:
    """N6 — sustained outage notice (HTML email)."""
    title = (getattr(watch, "movie_title", "") or getattr(watch, "movie_id", "") or "Your movie").strip()
    city = _watch_city(watch)
    return f"""<!doctype html>
<html><body style="margin:0;background:#08090d;padding:24px;font-family:Segoe UI,Helvetica,Arial,sans-serif;">
  <div style="max-width:560px;margin:0 auto;background:#11131a;border:1px solid #1f2430;border-radius:16px;padding:24px;">
    <p style="margin:0 0 12px;font-size:12px;letter-spacing:1px;color:#f59e0b;font-weight:700;">⚠️ TEMPORARY MONITORING ISSUE</p>
    <h1 style="margin:0 0 4px;font-size:20px;color:#f8fafc;">{title}</h1>
    <p style="margin:0;color:#94a3b8;font-size:13px;">{city}</p>
    <p style="margin:16px 0 0;color:#cbd5e1;font-size:14px;line-height:1.6;">
      TicketFox has had trouble reaching the ticketing provider for this title recently due to anti-bot challenges.
      Your watch remains active and we are continuing to cycle and retry.
    </p>
    <p style="margin:24px 0 0;color:#64748b;font-size:12px;">🦊 TicketFox · <a href="{settings.PUBLIC_APP_URL}/" style="color:#fb923c;">Dashboard</a></p>
  </div>
</body></html>"""



def send_smtp_email(
    to_email: str,
    subject: str,
    html_body: str,
    sender: str | None = None,
    reply_to: str | None = None,
) -> tuple[bool, str]:
    """Deliver one HTML email using standard SMTP (Gmail App Password, Outlook, etc.)."""
    if not (settings.SMTP_HOST and settings.SMTP_USER):
        return False, "SMTP not configured"
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    sender = sender or settings.SMTP_FROM or settings.SMTP_USER
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.attach(MIMEText(html_body, "html"))
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.starttls()
            if settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(sender, [to_email], msg.as_string())
        logger.info("SMTP email successfully delivered to %s", to_email)
        return True, "delivered via SMTP"
    except Exception as exc:
        logger.warning("SMTP email to %s failed: %s: %s", to_email, type(exc).__name__, exc)
        return False, f"SMTP error: {exc}"


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    sender: str | None = None,
    reply_to: str | None = None,
) -> tuple[bool, str]:
    """Deliver one HTML email through SMTP or Resend API.

    ``sender`` overrides the configured From address (used by the branded auth
    emails, which send from a dedicated address on the verified domain).
    ``reply_to`` points replies at a monitored inbox — the From address is a
    send-only mailbox, so without this a user's reply would vanish.
    """
    to_email = (to_email or "").strip()
    if not to_email:
        return False, "no email address"

    # 1. Use real SMTP if configured (can send to ANY email address without domain verification)
    if settings.SMTP_HOST and settings.SMTP_USER:
        return send_smtp_email(to_email, subject, html_body, sender, reply_to)

    # 2. Resend API
    if not settings.RESEND_API_KEY:
        if settings.DEBUG:
            logger.info("RESEND_API_KEY is unset — simulated email delivery to %s", to_email)
            return True, "simulated delivery (set RESEND_API_KEY or SMTP in backend/.env for live emails)"
        return False, "RESEND_API_KEY is not configured on the server"

    body: dict[str, Any] = {
        "from": sender or settings.RESEND_FROM,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    }
    if reply_to:
        body["reply_to"] = reply_to
    payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        RESEND_API,
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "TicketFox/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if int(getattr(response, "status", 200) or 200) in (200, 201):
                return True, "delivered"
            return False, f"HTTP {getattr(response, 'status', 0)}"
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:
            detail = ""
        logger.warning("Resend delivery to %s failed: HTTP %s %s", to_email, exc.code, detail)
        # Resend free tier restriction: onboarding@resend.dev can only send to account owner's email
        if exc.code == 403 and "only send testing emails to your own email address" in detail:
            if settings.DEBUG:
                logger.info("DEBUG mode: Simulated email to %s (Resend sandbox: domain not verified)", to_email)
                return True, "simulated delivery (Resend sandbox: domain unverified for non-owner)"
            return False, "Resend sandbox: verify domain at resend.com to send to all users"
        return False, f"HTTP {exc.code}"
    except Exception as exc:
        logger.warning("Resend delivery to %s failed: %s: %s", to_email, type(exc).__name__, exc)
        return False, type(exc).__name__


def send_whatsapp(phone_number: str, text: str) -> tuple[bool, str]:
    """Deliver one WhatsApp text through the wppconnect-server gateway."""
    if not channel_available("whatsapp"):
        return False, "whatsapp gateway is not configured"
    recipient = whatsapp.phone_number(phone_number)
    if recipient is None:
        return False, "phone number is incomplete"
    ok = whatsapp.send_text(recipient, text)
    return (True, "delivered") if ok else (False, "gateway rejected the message")


def _send(
    channel: str, target: str, *, subject: str, text_body: str, html_body: str
) -> tuple[bool, str]:
    """Dispatch one message to one channel. Returns ``(ok, detail)``."""
    if channel == "email":
        # Alerts go out from the alerts@ mailbox, but replies must land in the
        # monitored support inbox — alerts@ is send-only.
        return send_email(
            target,
            subject,
            html_body,
            sender=settings.RESEND_ALERTS_FROM,
            reply_to=settings.SUPPORT_EMAIL,
        )
    if channel == "whatsapp":
        return send_whatsapp(target, text_body)
    return False, "unknown channel"


def _deliver_one(channel: str, target: str, watch: Any, shows: list[Show], test: bool) -> dict[str, Any]:
    title = getattr(watch, "movie_title", "") or "TicketFox"
    subject = f"🧪 TicketFox test alert — {title}" if test else f"🚨 Tickets open: {title}"
    ok, detail = _send(
        channel,
        target,
        subject=subject,
        text_body=render_alert_text(watch, shows, test=test),
        html_body=render_alert_html(watch, shows, test=test),
    )

    logger.info(
        "%s %s for watch #%s -> %s (%s)",
        channel.upper(),
        "DELIVERED" if ok else "FAILED",
        getattr(watch, "id", "?"),
        target,
        detail,
    )
    return {
        "channel": channel,
        "target": target,
        "status": SENT if ok else FAILED,
        "detail": detail,
    }


def deliver(
    user: dict[str, Any] | None,
    watch: Any,
    shows: list[Show],
    *,
    test: bool = False,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for channel, target in user_targets(user).items():
        if not target:
            results.append(
                {"channel": channel, "target": "", "status": SKIPPED, "detail": "not configured"}
            )
            continue
        if not channel_available(channel):
            results.append(
                {
                    "channel": channel,
                    "target": target,
                    "status": UNAVAILABLE,
                    "detail": f"{channel} transport is not configured on the server",
                }
            )
            continue
        results.append(_deliver_one(channel, target, watch, shows, test))
    return results


async def deliver_async(
    user: dict[str, Any] | None,
    watch: Any,
    shows: list[Show],
    *,
    test: bool = False,
) -> list[dict[str, Any]]:
    return await asyncio.to_thread(deliver, user, watch, shows, test=test)


def render_broadcast_text(title: str, message: str, cta_text: str = "", cta_url: str = "") -> str:
    """Rich plain-text announcement formatted for WhatsApp with prominent title and button link."""
    lines: list[str] = [
        "📢 *TICKETFOX ANNOUNCEMENT*",
        "",
        f"🎬 *{title.strip()}*",
        "",
        message.strip(),
    ]
    if cta_url.strip():
        btn_label = (cta_text or "Book Tickets").strip().upper()
        lines.append("")
        lines.append("─────────────────────────")
        lines.append(f"🎟️ *[ {btn_label} ]*")
        lines.append(f"👉 {cta_url.strip()}")
        lines.append("─────────────────────────")

    lines.append("")
    lines.append(f"🦊 _TicketFox_ · {settings.PUBLIC_APP_URL}/")
    return "\n".join(lines).rstrip()


def render_broadcast_html(title: str, message: str, cta_text: str = "", cta_url: str = "") -> str:
    """Rich responsive HTML email for promotional broadcasts."""
    btn_html = (
        f'<a href="{cta_url.strip()}" style="display:inline-block;margin-top:16px;padding:12px 24px;border-radius:10px;background:#f97316;color:#ffffff;font-weight:700;text-decoration:none;font-size:14px;box-shadow:0 4px 14px rgba(249,115,22,0.4);">{cta_text.strip() or "Book Tickets"}</a>'
        if cta_url.strip()
        else ""
    )
    return f"""<!doctype html>
<html><body style="margin:0;background:#08090d;padding:24px;font-family:Segoe UI,Helvetica,Arial,sans-serif;">
  <div style="max-width:560px;margin:0 auto;background:#11131a;border:1px solid #1f2430;border-radius:16px;padding:28px;">
    <p style="margin:0 0 12px;font-size:12px;letter-spacing:1px;color:#fb923c;font-weight:700;">📢 TICKETFOX ANNOUNCEMENT</p>
    <h1 style="margin:0 0 10px;font-size:22px;color:#f8fafc;line-height:1.3;">{title.strip()}</h1>
    <p style="margin:0 0 18px;color:#cbd5e1;font-size:14px;line-height:1.6;white-space:pre-line;">{message.strip()}</p>
    {btn_html}
    <div style="margin-top:28px;padding-top:16px;border-top:1px solid #1f2430;">
      <p style="margin:0;color:#64748b;font-size:12px;">🦊 TicketFox · <a href="{settings.PUBLIC_APP_URL}/" style="color:#fb923c;text-decoration:none;">Visit Dashboard</a></p>
    </div>
  </div>
</body></html>"""


def deliver_custom(
    user: dict[str, Any] | None,
    subject: str,
    text_body: str,
    html_body: str,
    *,
    channels: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Deliver a custom notice/alert (N3, N4, N6, N8, or Broadcast) to requested user channels."""
    results: list[dict[str, Any]] = []
    targets = user_targets(user)

    if channels:
        active_channels = [c.lower() for c in channels if c.lower() in ("email", "whatsapp")]
    else:
        active_channels = list(targets.keys())

    for channel in active_channels:
        target = targets.get(channel, "")
        if not target:
            results.append({"channel": channel, "target": "", "status": SKIPPED, "detail": "not configured on profile"})
            continue
        if not channel_available(channel):
            results.append({"channel": channel, "target": target, "status": UNAVAILABLE, "detail": f"{channel} transport is not configured on server"})
            continue

        ok, detail = _send(
            channel, target, subject=subject, text_body=text_body, html_body=html_body
        )

        results.append({
            "channel": channel,
            "target": target,
            "status": SENT if ok else FAILED,
            "detail": detail,
        })
    return results


async def deliver_custom_async(
    user: dict[str, Any] | None,
    subject: str,
    text_body: str,
    html_body: str,
    *,
    channels: list[str] | None = None,
) -> list[dict[str, Any]]:
    return await asyncio.to_thread(deliver_custom, user, subject, text_body, html_body, channels=channels)



def summarize(results: list[dict[str, Any]]) -> str:
    sent = [r["channel"] for r in results if r["status"] == SENT]
    failed = [f"{r['channel']} ({r['detail']})" for r in results if r["status"] == FAILED]
    unavailable = [r["channel"] for r in results if r["status"] == UNAVAILABLE]

    if sent and not failed:
        return f"Alert delivered via {', '.join(sent)}."
    if sent and failed:
        return f"Delivered via {', '.join(sent)}; failed on {', '.join(failed)}."
    if failed:
        return f"Delivery failed on {', '.join(failed)}."
    if unavailable:
        return f"No transport configured on the server for {', '.join(unavailable)}."
    return "No notification channel is configured for your account yet."
