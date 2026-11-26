"""Showtime parsing shared by the adapters and the worker.

Both BookMyShow and District return *India-local* showtimes. BMS gives a
time-only string (``15:45`` or ``03:45 PM``) with the date implied by a
``dateCode``; District gives an ISO string without a timezone (``2026-09-16T15:45``).
The worker compares these against ``utcnow()``, so every parsed showtime is
normalised to India Standard Time (UTC+5:30) and returned timezone-aware.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .models import Show

IST = timezone(timedelta(hours=5, minutes=30))

# "15:45", "3:45 PM", "03:45 pm"
_TIME_ONLY_RE = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*([APap][Mm])?\s*$")

# "18:00", "9:30" — a 24-hour wall-clock bound used by per-watch time filters.
_HHMM_RE = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*$")


def parse_hhmm(raw: str) -> int | None:
    """Parse a 24-hour ``HH:MM`` string into minutes past midnight, or ``None``.

    Used for per-watch showtime bounds (e.g. "no alerts before 18:00"). Invalid
    or unset values return ``None`` so the caller can treat the bound as absent.
    """
    match = _HHMM_RE.match(raw or "")
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        return None
    return hour * 60 + minute


def parse_show_time(raw: str) -> datetime | None:
    """Parse a showtime into an IST-aware datetime, or ``None`` if unrecognised.

    * ISO strings without a timezone are assumed to be India-local.
    * ``HH:MM`` / ``HH:MM AM|PM`` are resolved against *today* in IST.
    """
    raw = (raw or "").strip()
    if not raw:
        return None

    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        parsed = None

    if parsed is not None:
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=IST)
        return parsed.astimezone(IST)

    match = _TIME_ONLY_RE.match(raw)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        meridiem = (match.group(3) or "").upper()
        if meridiem == "PM" and hour < 12:
            hour += 12
        elif meridiem == "AM" and hour == 12:
            hour = 0
        today = datetime.now(IST).date()
        return datetime.combine(today, time(hour, minute), tzinfo=IST)

    return None


def format_bms_show_time(date_code: str, raw_time: str) -> str:
    """Combine a BookMyShow dateCode ('YYYYMMDD') and time string into an ISO string.

    For example:
        date_code='20260920', raw_time='10:00 AM' -> '2026-09-20T10:00'
        date_code='20260920', raw_time='15:45'    -> '2026-09-20T15:45'

    If date_code is missing or invalid, or raw_time is already ISO-ish or unparseable,
    returns raw_time unchanged so downstream error handling / fallbacks work cleanly.
    """
    raw_time = (raw_time or "").strip()
    date_code = (date_code or "").strip().replace("-", "")
    if "T" in raw_time:
        return raw_time
    if len(date_code) == 8 and date_code.isdigit():
        match = _TIME_ONLY_RE.match(raw_time)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            meridiem = (match.group(3) or "").upper()
            if meridiem == "PM" and hour < 12:
                hour += 12
            elif meridiem == "AM" and hour == 12:
                hour = 0
            return f"{date_code[:4]}-{date_code[4:6]}-{date_code[6:8]}T{hour:02d}:{minute:02d}"
    return raw_time


# ---------------------------------------------------------------------------
# Displaying showtimes (shared by the Telegram, email and WhatsApp renderers)
#
# A showtime string may or may not carry a date: the adapters produce ISO strings
# ("2026-09-20T18:00"), while a bare "10:00 AM" is a legacy/sample shape. "Does
# this showtime have a date?" is answered here by looking for a genuine
# ``YYYY-MM-DD`` prefix rather than by calling :func:`parse_show_time` — that one
# resolves a bare time against *today*, which is right for the availability
# comparison but would stamp a made-up date onto a show that has none.
# ---------------------------------------------------------------------------

_DATE_ONLY_RE = re.compile(r"^\s*(\d{4})-(\d{2})-(\d{2})")

#: "Sat, 20 Sep" — weekday included, because "is that Saturday?" is the question
#: a ticket alert has to answer.
_WEEKDAY_DAY_FMT = "%a, %d %b"


def show_date(raw: str) -> date | None:
    """The calendar date a showtime carries, or ``None`` when it has none."""
    match = _DATE_ONLY_RE.match(raw or "")
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def show_day_label(raw: str, *, weekday: bool = False) -> str:
    """``'2026-09-20T18:00'`` -> ``'Sat, 20 Sep'`` (``'20 Sep'`` without weekday).

    Returns ``''`` for an undated showtime so callers can leave it untouched.
    """
    day = show_date(raw)
    if day is None:
        return ""
    if weekday:
        return day.strftime(_WEEKDAY_DAY_FMT)
    return f"{day.day} {day.strftime('%b')}"


def show_days(shows: "Iterable[Show]") -> list[date]:
    """Sorted distinct dates across ``shows``; undated showtimes contribute nothing."""
    return sorted({d for d in (show_date(s.show_time) for s in shows) if d is not None})


def single_day_label(shows: "Iterable[Show]") -> str:
    """``'Sat, 20 Sep'`` when every dated showtime lands on one day, else ``''``.

    A one-day list gets a single date header (it covers every time printed under
    it); a multi-day list must label each showtime instead — see
    :func:`spans_multiple_days`.
    """
    days = show_days(shows)
    if len(days) != 1:
        return ""
    return days[0].strftime(_WEEKDAY_DAY_FMT)


def spans_multiple_days(shows: "Iterable[Show]") -> bool:
    """True when ``shows`` covers more than one calendar day."""
    return len(show_days(shows)) > 1