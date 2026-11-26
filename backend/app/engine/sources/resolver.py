"""Resolve a parsed movie URL to a display name + region, and list theatres.

The add flow needs three things the source adapters provide in different shapes:
a human movie name (to render the "movie found" screen), the source region for
the city screen, and the theatre list for the selection screen. This module is
the single seam between the Telegram layer and the adapters, and it is
deliberately synchronous (the bot runs it in a thread pool) with errors mapped
to two coarse cases the UI can act on:

* :class:`TemporaryIssue` — blocked / network failure (S13, retryable)
* :class:`MovieNotFound` — the source has no such movie (S12)
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from dataclasses import dataclass, replace
from typing import Protocol

from .. import cities
from ..http import BMS_WEB_HEADERS, BlockedError, FetchError, HttpClient
from ..models import Region, Show, Source, Theatre
from ..titles import names_match as _names_match
from ..urls import ParsedMovieURL
from .bookmyshow import BookMyShowAdapter
from .catalog import (
    MovieCatalog,
    MovieSearchResult,
    _parse_release_date,
    canonical_movie_id,
    extract_poster_from_html,
)
from .district import DistrictAdapter

logger = logging.getLogger(__name__)


class MovieError(Exception):
    """Base class for add-flow resolution failures."""


class MovieNotFound(MovieError):
    """The source does not know this movie (E4)."""


class TemporaryIssue(MovieError):
    """The source is blocked or unreachable (E3) — safe to retry."""


@dataclass(frozen=True, slots=True)
class ResolvedMovie:
    source: Source
    movie_id: str
    movie_slug: str
    movie_name: str
    region: Region | None
    city_from_url: bool
    poster_url: str = ""
    alt_source: Source | None = None
    alt_movie_id: str = ""
    release_date: str = ""


# ---------------------------------------------------------------------------
# Venue cache
#
# Venue lists change rarely but every fetch is a full API/page request. Caching
# them briefly makes the add flow feel instant when a user moves between the
# city/theatre screens, and stops companion matching from re-fetching.
# ---------------------------------------------------------------------------
VENUE_CACHE_TTL_SECONDS = float(os.getenv("VENUE_CACHE_TTL_SECONDS", "900"))
_venue_cache: dict[tuple[str, str, str], tuple[float, list[Theatre]]] = {}
_venue_lock = threading.Lock()


def _venue_cache_key(movie: ResolvedMovie, region: Region) -> tuple[str, str, str]:
    """BookMyShow lists every venue in a region; District lists the cinemas that
    actually have shows *for that movie*, so the movie id is part of its key."""
    movie_part = movie.movie_id if movie.source is Source.DISTRICT else ""
    return (movie.source.value, region.code or region.slug or region.name, movie_part)


def _venue_cache_get(key: tuple[str, str, str]) -> list[Theatre] | None:
    with _venue_lock:
        entry = _venue_cache.get(key)
        if entry is None:
            return None
        stored_at, theatres = entry
        if (time.monotonic() - stored_at) >= VENUE_CACHE_TTL_SECONDS:
            _venue_cache.pop(key, None)
            return None
        return list(theatres)


def _venue_cache_put(key: tuple[str, str, str], theatres: list[Theatre]) -> None:
    if not theatres:
        return
    with _venue_lock:
        _venue_cache[key] = (time.monotonic(), list(theatres))


def clear_venue_cache() -> None:
    """Drop cached venue lists (used by tests and after a manual refresh)."""
    with _venue_lock:
        _venue_cache.clear()


def title_from_slug(slug: str) -> str:
    return " ".join(part.capitalize() for part in (slug or "").replace("_", "-").split("-") if part)


def slug_from_title(title: str) -> str:
    """``"The Paradise (Telugu)"`` -> ``"the-paradise-telugu"``.

    Used to rebuild a District page URL for legacy watch rows stored before the
    movie slug was persisted (District addresses movies by slug, so a watch
    without one can never be polled).
    """
    cleaned = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    return re.sub(r"-{2,}", "-", cleaned) or "movie"


class MovieResolver(Protocol):
    """Interface the add flow depends on (faked in tests)."""

    def resolve(self, parsed: ParsedMovieURL) -> ResolvedMovie: ...

    def list_theatres(self, movie: ResolvedMovie, region: Region) -> list[Theatre]: ...

    def search_movies(self, query: str) -> list[MovieSearchResult]: ...

    def upcoming_movies(self, city_key: str = "hyderabad", sort_by: str = "date") -> list[MovieSearchResult]: ...

    def find_companion_movie(self, movie_name: str, target_source: Source) -> MovieSearchResult | None: ...

    def fetch_shows(
        self,
        movie: ResolvedMovie,
        region: Region,
        theatres: list[Theatre] | None = None,
    ) -> list[Show]: ...

    def region_for(self, watch) -> Region: ...


class LiveMovieResolver:
    """Adapter-backed resolver with error mapping. Runs in a worker thread."""

    def __init__(
        self,
        http: HttpClient | None = None,
        adapters: dict[Source, object] | None = None,
        catalog: MovieCatalog | None = None,
    ) -> None:
        shared = http or HttpClient()
        self._adapters: dict[Source, object] = adapters or {
            Source.BOOKMYSHOW: BookMyShowAdapter(shared),
            Source.DISTRICT: DistrictAdapter(shared),
        }
        self.catalog = catalog or MovieCatalog(shared)

    def search_movies(self, query: str) -> list[MovieSearchResult]:
        return self.catalog.search(query)

    def upcoming_movies(self, city_key: str = "hyderabad", sort_by: str = "date") -> list[MovieSearchResult]:
        return self.catalog.upcoming(city_key, sort_by=sort_by)

    def find_companion_movie(self, movie_name: str, target_source: Source) -> MovieSearchResult | None:
        """Find matching movie on the other source across catalog, search, and dynamic live search."""
        try:
            # 1. In cached catalog
            for m in self.catalog.refresh(force=False):
                if m.source == target_source and _names_match(m.movie_name, movie_name):
                    return m
            # 2. Token search
            for m in self.catalog.search(movie_name):
                if m.source == target_source and _names_match(m.movie_name, movie_name):
                    return m
            # 3. Dynamic search
            if target_source == Source.BOOKMYSHOW and hasattr(self.catalog, "_search_bms_dynamic"):
                for m in self.catalog._search_bms_dynamic(movie_name):
                    if _names_match(m.movie_name, movie_name):
                        return m
            elif target_source == Source.DISTRICT:
                # Full District catalog (sitemap index) is cheaper and more complete
                # than the live /movies page subset.
                for m in self.catalog.district_movies(force=False):
                    if _names_match(m.movie_name, movie_name):
                        return m
                for m in self.catalog.refresh(force=True):
                    if m.source == Source.DISTRICT and _names_match(m.movie_name, movie_name):
                        return m
        except Exception as exc:
            logger.debug("find_companion_movie error for %s (%s): %s", movie_name, target_source.value, exc)
        return None

    # -- live showtimes (used by the watch-detail "Test Alert" action) -------

    def region_for(self, watch) -> Region:
        """Source region for a stored watch (no network for catalog cities)."""
        adapter = self._adapters.get(Source(str(watch.source)))
        return region_for_watch(adapter, watch)

    def fetch_shows(
        self,
        movie: ResolvedMovie,
        region: Region,
        theatres: list[Theatre] | None = None,
    ) -> list[Show]:
        """Live showtimes for a resolved movie.

        Raises :class:`TemporaryIssue` when the source blocks us, so callers can
        say "couldn't check right now" instead of pretending there are no shows.
        """
        adapter = self._adapters.get(movie.source)
        if adapter is None:
            return []
        try:
            return adapter.fetch_shows(  # type: ignore[attr-defined]
                movie.movie_id,
                region,
                theatres=theatres,
                movie_slug=movie.movie_slug,
            )
        except ValueError as exc:
            # District requires a slug; treat as "nothing to show" instead of failing.
            logger.debug("fetch_shows unavailable for %s: %s", movie.movie_id, exc)
            return []
        except (BlockedError, FetchError) as exc:
            raise TemporaryIssue(str(exc)) from exc

    # -- resolve -----------------------------------------------------------

    def resolve(self, parsed: ParsedMovieURL) -> ResolvedMovie:
        if parsed.source is Source.BOOKMYSHOW:
            return self._resolve_bms(parsed)
        return self._resolve_district(parsed)

    def _resolve_bms(self, parsed: ParsedMovieURL) -> ResolvedMovie:
        adapter: BookMyShowAdapter = self._adapters[Source.BOOKMYSHOW]  # type: ignore[assignment]
        region = self._bms_region(adapter, parsed)
        name = ""
        poster_url = ""
        if region is not None:
            try:
                shows = adapter.fetch_shows(parsed.movie_id, region)
            except (BlockedError, FetchError) as exc:
                raise TemporaryIssue(str(exc)) from exc
            if shows:
                name = shows[0].movie_name

        release_date = ""
        if parsed.original_url:
            try:
                html = adapter.http.get_text(parsed.original_url, headers=BMS_WEB_HEADERS)
                poster_url = extract_poster_from_html(html)
                release_date = _parse_release_date(html)
            except Exception as exc:
                logger.debug("Failed extracting BMS poster: %s", exc)

        if not name.strip() or not poster_url or not release_date:
            item = self.catalog.get_by_id(parsed.source, parsed.movie_id)
            if not item:
                for _, items in getattr(self.catalog, "_upcoming_cache", {}).values():
                    match = next((x for x in items if x.movie_id == parsed.movie_id and x.source == parsed.source), None)
                    if match:
                        item = match
                        break
            if item:
                if not name.strip():
                    name = item.movie_name
                if not poster_url and item.poster_url:
                    poster_url = item.poster_url
                if not release_date and item.release_date:
                    release_date = item.release_date

        final_name = name.strip() or title_from_slug(parsed.movie_slug) or parsed.movie_id
        companion = self.find_companion_movie(final_name, Source.DISTRICT)
        alt_source = Source.DISTRICT if companion else None
        alt_movie_id = companion.movie_id if companion else ""

        return ResolvedMovie(
            source=parsed.source,
            movie_id=parsed.movie_id,
            movie_slug=parsed.movie_slug,
            movie_name=final_name,
            region=region,
            city_from_url=region is not None,
            poster_url=poster_url,
            alt_source=alt_source,
            alt_movie_id=alt_movie_id,
            release_date=release_date,
        )

    def _resolve_district(self, parsed: ParsedMovieURL) -> ResolvedMovie:
        adapter: DistrictAdapter = self._adapters[Source.DISTRICT]  # type: ignore[assignment]
        region = self._district_region(parsed)
        try:
            name = adapter.resolve_movie_name(parsed.movie_id, parsed.movie_slug, parsed.city_slug)
        except (BlockedError, FetchError) as exc:
            raise TemporaryIssue(str(exc)) from exc
        except (RuntimeError, ValueError) as exc:
            raise TemporaryIssue(str(exc)) from exc

        poster_url = ""
        release_date = ""
        if parsed.original_url:
            try:
                html = adapter.http.get_text(parsed.original_url)
                poster_url = extract_poster_from_html(html)
                release_date = _parse_release_date(html)
            except Exception as exc:
                logger.debug("Failed extracting District poster: %s", exc)

        if not poster_url or not release_date:
            item = self.catalog.get_by_id(parsed.source, parsed.movie_id)
            if item:
                if not poster_url and item.poster_url:
                    poster_url = item.poster_url
                if not release_date and item.release_date:
                    release_date = item.release_date

        final_name = name.strip() or title_from_slug(parsed.movie_slug) or parsed.movie_id
        companion = self.find_companion_movie(final_name, Source.BOOKMYSHOW)
        alt_source = Source.BOOKMYSHOW if companion else None
        alt_movie_id = companion.movie_id if companion else ""

        return ResolvedMovie(
            source=parsed.source,
            movie_id=parsed.movie_id,
            movie_slug=parsed.movie_slug,
            movie_name=final_name,
            region=region,
            city_from_url=region is not None,
            poster_url=poster_url,
            alt_source=alt_source,
            alt_movie_id=alt_movie_id,
            release_date=release_date,
        )

    def _bms_region(self, adapter: BookMyShowAdapter, parsed: ParsedMovieURL) -> Region | None:
        key = cities.city_key_from_slug(parsed.region_slug)
        if key:
            city = cities.get_city(key)
            if city is not None:
                return cities.region_for(Source.BOOKMYSHOW, city)
        if not parsed.region_slug:
            return None
        try:
            return adapter.resolve_region(parsed.region_slug)
        except (LookupError, BlockedError, FetchError):
            return None

    @staticmethod
    def _district_region(parsed: ParsedMovieURL) -> Region | None:
        key = cities.city_key_from_slug(parsed.city_slug)
        city = cities.get_city(key) if key else None
        if city is None:
            return None
        return cities.region_for(Source.DISTRICT, city)

    # -- theatres ----------------------------------------------------------

    def list_theatres(self, movie: ResolvedMovie, region: Region) -> list[Theatre]:
        cache_key = _venue_cache_key(movie, region)
        cached = _venue_cache_get(cache_key)
        if cached is not None:
            return cached
        try:
            if movie.source is Source.BOOKMYSHOW:
                adapter: BookMyShowAdapter = self._adapters[Source.BOOKMYSHOW]  # type: ignore[assignment]
                theatres = adapter.list_theatres(region)
            else:
                district: DistrictAdapter = self._adapters[Source.DISTRICT]  # type: ignore[assignment]
                theatres = district.list_theatres_for_movie(movie.movie_id, movie.movie_slug, region)
        except (BlockedError, FetchError) as exc:
            raise TemporaryIssue(str(exc)) from exc
        except (RuntimeError, ValueError) as exc:
            raise TemporaryIssue(str(exc)) from exc
        _venue_cache_put(cache_key, theatres)
        return theatres


def region_for_watch(adapter: object, watch) -> Region:
    """Rebuild a full source region from a stored watch (no network for catalog cities)."""
    source = Source(watch.source)
    city = cities.get_city(cities.city_key_from_name(watch.region_name) or "")
    if city is not None:
        return cities.region_for(source, city)
    if getattr(adapter, "source", None) is Source.BOOKMYSHOW:
        try:
            return adapter.resolve_region(watch.region_name)  # type: ignore[attr-defined]
        except (LookupError, BlockedError, FetchError):
            pass
    slug = (watch.region_code or watch.region_name or "").lower()
    return Region(source, watch.region_code or slug, watch.region_name, slug)


def region_for_city(source: Source | str, city_name: str, region_code: str = "") -> Region:
    """Resolve the *city name* the web UI stores into a full source region.

    Catalog cities are resolved offline (``cities.region_for``); an unknown
    BookMyShow city is looked up in the regions API; anything else falls back to
    a slug region. ``region_code`` wins when it is already known (e.g. a watch
    created for BMS "HYD"), so a poll keeps hitting the region it was set up in.
    """
    src = source if isinstance(source, Source) else Source(str(source).lower())
    key = cities.city_key_from_name(city_name)
    catalog_city = cities.get_city(key) if key else None

    region: Region | None = None
    if catalog_city is not None:
        region = cities.region_for(src, catalog_city)
    elif city_name and src is Source.BOOKMYSHOW:
        try:
            region = BookMyShowAdapter().resolve_region(city_name)
        except (LookupError, BlockedError, FetchError):
            region = None
    elif city_name:
        slug = (city_name or "").strip().lower().replace(" ", "-")
        region = Region(src, slug, city_name.strip(), slug)

    if region is None:
        region = Region(src, region_code or "hyderabad", city_name or "", "hyderabad")

    if region_code and region_code != region.code:
        region = replace(region, code=region_code)
    return region


def resolved_movie_for_watch(watch) -> ResolvedMovie:
    """Build the :class:`ResolvedMovie` the worker/Test-Alert need from a stored watch.

    The web app stores a city name (not a source region) and, for District, the
    movie slug — both are rebuilt here so the worker never has to know how the
    adapters address their sources.
    """
    source = Source(str(getattr(watch, "source", "") or "").lower())
    city_name = getattr(watch, "city", "") or getattr(watch, "region_name", "") or ""
    region = region_for_city(source, city_name, getattr(watch, "region_code", "") or "")

    movie_id = canonical_movie_id(source, getattr(watch, "movie_id", "") or "")
    movie_slug = (getattr(watch, "movie_slug", "") or "").strip()
    if not movie_slug and source is Source.DISTRICT:
        movie_slug = slug_from_title(getattr(watch, "movie_title", "") or "")

    return ResolvedMovie(
        source=source,
        movie_id=movie_id,
        movie_slug=movie_slug,
        movie_name=(getattr(watch, "movie_title", "") or movie_id),
        region=region,
        city_from_url=False,
        poster_url=getattr(watch, "poster_url", "") or "",
    )

