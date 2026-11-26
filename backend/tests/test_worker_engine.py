from app.engine.availability.detector import (
    filter_shows_by_time,
    should_notify,
)
from app.engine.models import AvailabilityState, Show, Source
from app.engine.showtime import parse_show_time


def test_should_notify_transitions():
    assert should_notify(AvailabilityState.UNKNOWN, AvailabilityState.AVAILABLE) is True
    assert should_notify(AvailabilityState.UNAVAILABLE, AvailabilityState.AVAILABLE) is True

    # Staying AVAILABLE must not re-notify on every poll.
    assert should_notify(AvailabilityState.AVAILABLE, AvailabilityState.AVAILABLE) is False

    assert should_notify(AvailabilityState.AVAILABLE, AvailabilityState.UNAVAILABLE) is False
    assert should_notify(AvailabilityState.UNKNOWN, AvailabilityState.UNAVAILABLE) is False


def test_filter_shows_by_time():
    shows = [
        Show(Source.BOOKMYSHOW, "M1", "Movie", "T1", "Cinema A", "S1", "2026-10-15T11:00", "", "2D", True),
        Show(Source.BOOKMYSHOW, "M1", "Movie", "T1", "Cinema A", "S2", "2026-10-15T16:30", "", "2D", True),
        Show(Source.BOOKMYSHOW, "M1", "Movie", "T1", "Cinema A", "S3", "2026-10-15T21:15", "", "IMAX", True),
    ]

    after_filtered = filter_shows_by_time(shows, after="15:00", before="")
    assert [s.show_id for s in after_filtered] == ["S2", "S3"]

    window_filtered = filter_shows_by_time(shows, after="12:00", before="20:00")
    assert [s.show_id for s in window_filtered] == ["S2"]


def test_parse_show_time():
    parsed = parse_show_time("2026-10-15T19:30")
    assert parsed is not None and (parsed.hour, parsed.minute) == (19, 30)

    time_only = parse_show_time("21:45")
    assert time_only is not None and (time_only.hour, time_only.minute) == (21, 45)
