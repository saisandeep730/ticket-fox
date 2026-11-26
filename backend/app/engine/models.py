"""Shared domain models normalized across BookMyShow and District."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Source(str, Enum):
    BOOKMYSHOW = "bookmyshow"
    DISTRICT = "district"


class AvailabilityState(str, Enum):
    """Availability of a watch: three states, transitions drive notifications."""

    UNKNOWN = "UNKNOWN"
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class Region:
    """A city/region in a source's own coordinate system."""

    source: Source
    code: str
    name: str
    slug: str = ""
    latitude: str = "0"
    longitude: str = "0"
    geohash: str = ""


@dataclass(frozen=True, slots=True)
class Theatre:
    """A cinema/venue a user can select to watch."""

    source: Source
    theatre_id: str
    theatre_name: str
    address: str = ""


@dataclass(frozen=True, slots=True)
class Show:
    """A single showtime, normalized across sources.

    The rest of the application never cares whether this came from BMS or
    District: it only looks at ``source`` and the availability fields.
    """

    source: Source
    movie_id: str
    movie_name: str
    theatre_id: str
    theatre_name: str
    show_id: str
    show_time: str  # ISO-ish local string, e.g. "2026-09-16T15:45"
    booking_url: str = ""
    screen_format: str = ""
    available: bool = True


@dataclass(slots=True)
class WatchResult:
    """The availability snapshot for one movie+region+theatre set."""

    movie_name: str
    shows: list[Show] = field(default_factory=list)
    state: AvailabilityState = AvailabilityState.UNAVAILABLE

    @property
    def available_shows(self) -> list[Show]:
        return [s for s in self.shows if s.available]

    @property
    def has_availability(self) -> bool:
        return any(s.available for s in self.shows)