"""District adapter.

District is a Next.js app. A movie page URL (optionally pinned to a city) is
fetched once and the showtime data lives in the ``__NEXT_DATA__`` JSON blob:

    props.pageProps.data.serverState.movieSessions.<key>.pageData.nearbyCinemas[]
        cinema.id / cinema.cinemaInfo{name, address, cityKey}
        cinema.sessions[]  {sid, showTime, avail, total, seatStatus,
                            statusColor, scrnFmt, encSessionId, areas[]}

For upcoming movies with no showtimes yet the ``movieSessions`` node is absent
and ``fetch_shows`` returns an empty list (the "UNAVAILABLE" state the notifier
watches for).
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from ..http import HttpClient
from ..models import Region, Show, Source, Theatre
from .base import SourceAdapter
from ..showtime import parse_show_time
from ..urls import build_district_url, normalise_district_id

logger = logging.getLogger(__name__)

NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)

# Seat statuses that indicate a session is genuinely bookable.
_AVAILABLE_STATUSES = {"available", "few seats left", "filling fast"}


class DistrictAdapter(SourceAdapter):
    source = Source.DISTRICT

    def __init__(self, http: HttpClient | None = None) -> None:
        super().__init__(http)
        self._http: HttpClient = self.http

    def _fetch_page(self, movie_slug: str, movie_id: str, city_slug: str = "") -> dict[str, Any]:
        url = build_district_url(movie_slug, movie_id, city_slug)
        html = self._http.get_text(url, headers={"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"})
        match = NEXT_DATA_RE.search(html)
        if not match:
            raise RuntimeError(f"No __NEXT_DATA__ found on District page: {url}")
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid __NEXT_DATA__ JSON on {url}") from exc

    # -- regions -----------------------------------------------------------

    def resolve_region(self, city: str) -> Region:
        # District identifies cities by a lowercase slug (cityKey), e.g. "hyderabad".
        slug = (city or "").strip().lower().replace(" ", "-")
        if not slug:
            raise LookupError("District requires a city name")
        return Region(Source.DISTRICT, code=slug, name=city.strip(), slug=slug)

    # -- theatres ----------------------------------------------------------

    def list_theatres(self, region: Region) -> list[Theatre]:
        # Theatres are enumerated from a movie page in that city. We need a
        # movie that has sessions; the caller passes it via fetch_shows-style
        # context. See ``list_theatres_for_movie``.
        raise NotImplementedError("Use list_theatres_for_movie(movie_id, movie_slug, region)")

    def list_theatres_for_movie(
        self, movie_id: str, movie_slug: str, region: Region
    ) -> list[Theatre]:
        page = self._fetch_page(movie_slug, movie_id, region.slug)
        theatres = self._extract_theatres(page)
        theatres.sort(key=lambda t: t.theatre_name)
        return theatres

    def resolve_movie_name(self, movie_id: str, movie_slug: str, city_slug: str = "") -> str:
        """Fetch the movie page once and return its display name."""
        page = self._fetch_page(movie_slug, movie_id, city_slug)
        return self._movie_name(page, movie_id)

    # -- shows -------------------------------------------------------------

    def fetch_shows(
        self,
        movie_id: str,
        region: Region,
        theatres: list[Theatre] | None = None,
        movie_slug: str = "",
    ) -> list[Show]:
        if not movie_slug:
            raise ValueError("DistrictAdapter.fetch_shows requires movie_slug")
        # Canonicalise here too: a legacy watch row may still store "MV185027", and
        # every comparison below (and the returned Show ids) assumes the bare digits.
        movie_id = normalise_district_id(movie_id)
        page = self._fetch_page(movie_slug, movie_id, region.slug)
        shows = self._parse_shows(page, movie_id, movie_slug)
        if theatres:
            wanted = {t.theatre_id for t in theatres}
            shows = [s for s in shows if s.theatre_id in wanted]
        return shows

    # -- parsing -----------------------------------------------------------

    def _extract_theatres(self, page: dict[str, Any]) -> list[Theatre]:
        cinemas = self._cinemas(page)
        theatres: list[Theatre] = []
        for cinema in cinemas:
            cid = str(cinema.get("id", ""))
            info = cinema.get("cinemaInfo", {})
            name = (info.get("name") or info.get("label") or "").strip()
            if not cid or not name:
                continue
            theatres.append(
                Theatre(Source.DISTRICT, cid, name, info.get("address", ""))
            )
        return theatres

    def _parse_shows(self, page: dict[str, Any], movie_id: str, movie_slug: str) -> list[Show]:
        movie_name = self._movie_name(page, movie_id)
        now = datetime.now(timezone.utc)
        base_url = build_district_url(movie_slug, movie_id)
        shows: list[Show] = []

        for cinema in self._cinemas(page):
            cid = str(cinema.get("id", ""))
            info = cinema.get("cinemaInfo", {})
            theatre_name = (info.get("name") or info.get("label") or "").strip()
            for session in cinema.get("sessions", []) or []:
                show_time = session.get("showTime", "")
                if not show_time:
                    continue
                starts_at = parse_show_time(show_time)
                if starts_at is None or starts_at <= now:
                    continue  # ignore stale / already-started shows
                avail = int(session.get("avail", 0) or 0)
                seat_status = (session.get("seatStatus", "") or "").strip().lower()
                status_color = session.get("statusColor", "")
                available = (
                    avail > 0
                    or seat_status in _AVAILABLE_STATUSES
                    or status_color == "G"
                )
                shows.append(
                    Show(
                        source=Source.DISTRICT,
                        movie_id=movie_id,
                        movie_name=movie_name,
                        theatre_id=cid,
                        theatre_name=theatre_name,
                        show_id=str(session.get("sid", "")),
                        show_time=show_time,
                        booking_url=base_url,
                        screen_format=session.get("scrnFmt", ""),
                        available=available,
                    )
                )
        return shows

    def _cinemas(self, page: dict[str, Any]) -> list[dict[str, Any]]:
        sessions = page.get("props", {}).get("pageProps", {}).get("data", {}).get(
            "serverState", {}
        ).get("movieSessions", {})
        for group in sessions.values():
            page_data = group.get("pageData", {}) or {}
            for key in ("nearbyCinemas", "farCinemas"):
                cinemas = page_data.get(key, []) or []
                if cinemas:
                    return cinemas
        return []

    def extract_cinemas_from_page(self, page: dict[str, Any]) -> list[dict[str, str]]:
        out = []
        for cinema in self._cinemas(page):
            cid = str(cinema.get("id", ""))
            info = cinema.get("cinemaInfo", {}) or {}
            cname = str(info.get("name", ""))
            caddr = str(info.get("address", ""))
            city = str(info.get("cityKey", ""))
            if cid and cname:
                out.append({"cinema_id": cid, "cinema_name": cname, "address": caddr, "city_key": city})
        return out

    def _movie_name(self, page: dict[str, Any], movie_id: str) -> str:
        groups = page.get("props", {}).get("pageProps", {}).get("data", {}).get(
            "serverState", {}
        ).get("movieSessions", {})
        for group in groups.values():
            name = group.get("meta", {}).get("movie", {}).get("name")
            if name:
                return str(name)
        # Fall back to the movie-data node. Compare as strings: `int(movie_id)` used
        # to raise ValueError on a legacy "MV185027" id, which aborted the whole poll
        # (and reported a generic ValueError instead of a usable message).
        wanted = normalise_district_id(movie_id)
        mdp = page.get("props", {}).get("pageProps", {}).get("initialState", {}).get(
            "mdpV2", {}
        ).get("movieData", {})
        for key, value in mdp.items():
            content_id = value.get("movie", {}).get("content_id")
            if str(key) == wanted or (content_id is not None and str(content_id) == wanted):
                name = value.get("movie", {}).get("name")
                if name:
                    return str(name)
        return ""