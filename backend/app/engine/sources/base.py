"""Common interface for showtime sources (BookMyShow, District)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..http import HttpClient
from ..models import Region, Show, Source, Theatre


class SourceAdapter(ABC):
    """A source knows how to resolve a region, list its theatres, and fetch shows.

    Adapters are synchronous: the polling worker runs them in a thread pool so
    the async Telegram bot is never blocked. This keeps the HTTP layer simple
    (``curl_cffi`` is synchronous) while still supporting concurrency.
    """

    source: Source

    def __init__(self, http: HttpClient | None = None) -> None:
        self.http = http or HttpClient()

    @abstractmethod
    def resolve_region(self, city: str) -> Region:
        """Resolve a human city name (or slug) to a source region."""

    @abstractmethod
    def list_theatres(self, region: Region) -> list[Theatre]:
        """List selectable theatres in a region."""

    @abstractmethod
    def fetch_shows(
        self,
        movie_id: str,
        region: Region,
        theatres: list[Theatre] | None = None,
        movie_slug: str = "",
    ) -> list[Show]:
        """Fetch normalized showtimes for a movie in a region.

        ``theatres`` filters the result to the selected theatres; when omitted,
        all theatres in the source response are returned. ``movie_slug`` is used
        by District (which addresses movies by slug); BookMyShow ignores it.
        """


def filter_shows_by_theatres(shows: list[Show], theatres: list[Theatre]) -> list[Show]:
    """Keep only shows whose theatre_id is in the selected set."""
    wanted = {t.theatre_id for t in theatres}
    if not wanted:
        return list(shows)
    return [s for s in shows if s.theatre_id in wanted]