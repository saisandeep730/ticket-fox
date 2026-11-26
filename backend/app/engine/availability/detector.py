"""Availability detection: state machine over watch snapshots.

We track three states per watch: UNKNOWN, AVAILABLE, UNAVAILABLE. The worker
compares the freshly observed state with the stored previous state and decides
whether to notify. Only the transition to AVAILABLE triggers a notification,
so we never spam on repeated checks.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum

from ..models import AvailabilityState, Show
from ..showtime import IST, parse_hhmm, parse_show_time


class NotifyAction(Enum):
    NOTIFY = "notify"
    UPDATE = "update"   # persist state, no notification
    NOTHING = "nothing"


# previous x current -> action
_TRANSITIONS: dict[tuple[AvailabilityState, AvailabilityState], NotifyAction] = {
    (AvailabilityState.UNKNOWN, AvailabilityState.UNKNOWN): NotifyAction.NOTHING,
    (AvailabilityState.UNKNOWN, AvailabilityState.UNAVAILABLE): NotifyAction.UPDATE,
    (AvailabilityState.UNKNOWN, AvailabilityState.AVAILABLE): NotifyAction.NOTIFY,
    (AvailabilityState.UNAVAILABLE, AvailabilityState.UNKNOWN): NotifyAction.UPDATE,
    (AvailabilityState.UNAVAILABLE, AvailabilityState.UNAVAILABLE): NotifyAction.NOTHING,
    (AvailabilityState.UNAVAILABLE, AvailabilityState.AVAILABLE): NotifyAction.NOTIFY,
    (AvailabilityState.AVAILABLE, AvailabilityState.UNKNOWN): NotifyAction.UPDATE,
    (AvailabilityState.AVAILABLE, AvailabilityState.UNAVAILABLE): NotifyAction.UPDATE,
    (AvailabilityState.AVAILABLE, AvailabilityState.AVAILABLE): NotifyAction.NOTHING,
}


def transition(previous: AvailabilityState, current: AvailabilityState) -> NotifyAction:
    return _TRANSITIONS[(previous, current)]


def should_notify(previous: AvailabilityState, current: AvailabilityState) -> bool:
    return transition(previous, current) is NotifyAction.NOTIFY


def infer_state(has_available_shows: bool) -> AvailabilityState:
    """Turn an observation into a concrete state.

    Transient fetch/parse failures are handled by the caller (they should be
    passed through as UNKNOWN, not as UNAVAILABLE) -- a network error must
    never look like "no tickets".
    """
    return AvailabilityState.AVAILABLE if has_available_shows else AvailabilityState.UNAVAILABLE


def filter_shows_by_date(shows: list[Show], date_filter: list[str]) -> list[Show]:
    """Filter shows according to the user's date preferences.

    Show dates are India-local, so "today"/"tomorrow" are resolved in IST —
    otherwise a worker running in UTC would bucket the wrong day around
    midnight IST. Also supports "premier", "first_day", and exact YYYY-MM-DD dates.
    """
    if not date_filter or "all" in date_filter:
        return shows

    now = datetime.now(IST)
    today_str = now.strftime("%Y-%m-%d")
    tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    matched: list[Show] = []
    for s in shows:
        show_date = (
            s.show_time[:10]
            if len(s.show_time) >= 10 and s.show_time[4] == "-" and s.show_time[7] == "-"
            else ""
        )
        is_match = False
        if "weekend" in date_filter and show_date:
            try:
                dt = datetime.fromisoformat(show_date)
                if dt.weekday() in (5, 6):  # Saturday or Sunday
                    is_match = True
            except ValueError:
                pass
        if "today" in date_filter and show_date == today_str:
            is_match = True
        if "tomorrow" in date_filter and show_date == tomorrow_str:
            is_match = True
        if ("premier" in date_filter or "premier_2days" in date_filter) and show_date:
            # Premier option searches for both 2 days before & 1 day before release date
            is_match = True
        if "first_day" in date_filter and show_date:
            is_match = True
        if show_date and show_date in date_filter:
            is_match = True

        if is_match:
            matched.append(s)
    return matched


def filter_shows_by_time(shows: list[Show], after: str = "", before: str = "") -> list[Show]:
    """Keep only shows whose start time falls in ``[after, before)`` in IST.

    Bounds are 24-hour ``HH:MM`` strings; an empty or unparseable bound is
    ignored. ``after`` is inclusive, ``before`` exclusive (so ``17:00``–``21:00``
    is an evening window). Shows whose time cannot be parsed are kept, matching
    ``is_future``: a parse failure must never hide availability.
    """
    after_minutes = parse_hhmm(after) if after else None
    before_minutes = parse_hhmm(before) if before else None
    if after_minutes is None and before_minutes is None:
        return list(shows)

    kept: list[Show] = []
    for show in shows:
        parsed = parse_show_time(show.show_time)
        if parsed is None:
            kept.append(show)
            continue
        minutes = parsed.hour * 60 + parsed.minute
        if after_minutes is not None and minutes < after_minutes:
            continue
        if before_minutes is not None and minutes >= before_minutes:
            continue
        kept.append(show)
    return kept