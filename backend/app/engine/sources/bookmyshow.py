"""BookMyShow adapter.

Verified endpoints (2026-09, India egress / curl_cffi impersonation):

* Regions:      ``GET /api/explore/v1/discover/regions``
* Venues:       ``GET /api/v2/mobile/venues?regionCode=..&eventType=MT``
* Showtimes:    ``GET /api/movies-data/v4/showtimes-by-event/primary-dynamic``

The old ``/pwa/api/de/venues`` and ``/pwa/api/de/showtimes/byevent`` endpoints
now return HTTP 400 ("blocked through send") and are not used.
"""

from __future__ import annotations

import logging
from datetime import datetime

from ..http import BMS_WEB_HEADERS
from ..models import Region, Show, Source, Theatre
from ..showtime import IST, format_bms_show_time
from .base import SourceAdapter

logger = logging.getLogger(__name__)

REGIONS_URL = "https://in.bookmyshow.com/api/explore/v1/discover/regions"
VENUES_URL = "https://in.bookmyshow.com/api/v2/mobile/venues"
SHOWTIMES_URL = "https://in.bookmyshow.com/api/movies-data/v5/showtimes-by-event/primary-dynamic"
SHOWTIMES_FALLBACK_URL = "https://in.bookmyshow.com/api/movies-data/v4/showtimes-by-event/primary-dynamic"

# Offline fallback for the most common cities: (region_code, slug, lat, lon, geohash).
REGION_MAP: dict[str, tuple[str, str, str, str, str]] = {
    "mumbai": ("MUMBAI", "mumbai", "19.076", "72.878", "te7"),
    "delhi-ncr": ("NCR", "delhi-ncr", "28.613", "77.209", "ttn"),
    "delhi": ("NCR", "delhi-ncr", "28.613", "77.209", "ttn"),
    "bengaluru": ("BANG", "bengaluru", "12.972", "77.594", "tdr"),
    "bangalore": ("BANG", "bengaluru", "12.972", "77.594", "tdr"),
    "hyderabad": ("HYD", "hyderabad", "17.385", "78.487", "tep"),
    "chennai": ("CHEN", "chennai", "13.056", "80.206", "tf3"),
    "kolkata": ("KOLK", "kolkata", "22.573", "88.364", "tun"),
    "pune": ("PUNE", "pune", "18.520", "73.856", "te2"),
    "kochi": ("KOCH", "kochi", "9.932", "76.267", "t9z"),
    "ahmedabad": ("AHD", "ahmedabad", "23.022", "72.571", "t9d"),
    "chandigarh": ("CHD", "chandigarh", "30.733", "76.779", "tth"),
}

# Category availability codes: 0 = sold out, 1/2/3 = open in increasing degree.
_AVAIL_OPEN = {"1", "2", "3"}


class BookMyShowAdapter(SourceAdapter):
    source = Source.BOOKMYSHOW

    # -- regions -----------------------------------------------------------

    def resolve_region(self, city: str) -> Region:
        key = (city or "").lower().strip()
        if key in REGION_MAP:
            code, slug, lat, lon, gh = REGION_MAP[key]
            return Region(Source.BOOKMYSHOW, code, city.strip(), slug, lat, lon, gh)

        region = self._lookup_region_from_api(key)
        if region:
            return region
        raise LookupError(f"BookMyShow region not found for city: {city}")

    def _lookup_region_from_api(self, key: str) -> Region | None:
        """Find a region by slug or alias in the discover/regions payload."""
        payload = self.http.get_json(
            REGIONS_URL, headers={**BMS_WEB_HEADERS, "Accept": "application/json"}
        )
        cities = (
            payload.get("BookMyShow", {}).get("TopCities", [])
            + payload.get("BookMyShow", {}).get("OtherCities", [])
        )
        for item in cities:
            names = {item.get("RegionSlug", "").lower(), item.get("RegionName", "").lower()}
            names.update((a or "").lower() for a in item.get("Alias", []) or [])
            if key in names:
                return Region(
                    Source.BOOKMYSHOW,
                    item.get("RegionCode", ""),
                    item.get("RegionName", ""),
                    item.get("RegionSlug", ""),
                    str(item.get("Lat", "0")),
                    str(item.get("Long", "0")),
                    str(item.get("GeoHash", "")),
                )
        return None

    # -- theatres ----------------------------------------------------------

    def list_theatres(self, region: Region) -> list[Theatre]:
        payload = self.http.get_json(
            VENUES_URL,
            params={"regionCode": region.code, "eventType": "MT"},
            headers={"Accept": "application/json", "x-platform": "AND", "x-app-code": "MOBAND2"},
        )
        theatres: list[Theatre] = []
        for v in payload.get("venues", []) or []:
            code = v.get("VenueCode", "")
            name = v.get("VenueName", "").strip()
            if not code or not name:
                continue
            theatres.append(
                Theatre(Source.BOOKMYSHOW, code, name, v.get("VenueAddress", ""))
            )
        theatres.sort(key=lambda t: t.theatre_name)
        return theatres

    # -- shows -------------------------------------------------------------

    def fetch_shows(
        self,
        movie_id: str,
        region: Region,
        theatres: list[Theatre] | None = None,
        movie_slug: str = "",
    ) -> list[Show]:
        params = {
            "eventCode": movie_id,
            "etCodes": movie_id,
            "dateCode": "",
            "isDesktop": "true",
            "regionCode": region.code,
            "xLocationShared": "false",
            "memberId": "",
            "lsId": "",
            "subCode": "",
            "lat": region.latitude,
            "lon": region.longitude,
            "appCode": "WEB",
        }
        headers = {
            **BMS_WEB_HEADERS,
            "x-region-code": region.code,
            "x-region-slug": region.slug or region.code.lower(),
            "x-latitude": region.latitude,
            "x-longitude": region.longitude,
            "x-geohash": region.geohash,
            "Referer": f"https://in.bookmyshow.com/movies/{region.slug}/buytickets/{movie_id}/",
        }
        try:
            payload = self.http.get_json(SHOWTIMES_URL, params=params, headers=headers)
        except Exception as exc:
            logger.debug("v5 showtimes failed for %s, trying fallback v4: %s", movie_id, exc)
            payload = self.http.get_json(SHOWTIMES_FALLBACK_URL, params=params, headers=headers)

        shows = self._parse_shows(payload, movie_id, region)
        if theatres:
            wanted = {t.theatre_id for t in theatres}
            shows = [s for s in shows if s.theatre_id in wanted]
        return shows

    def _parse_shows(
        self, payload: dict, movie_id: str, region: Region, now: datetime | None = None
    ) -> list[Show]:
        data = payload.get("data", {})
        movie_name = (data.get("header", {}).get("title", {}).get("text") or "").strip()
        # "Today" must be the IST day: BookMyShow's dateCodes are Indian local dates, and
        # a UTC host's naive now() is a day behind between 18:30 and 24:00 UTC, which let
        # yesterday's shows past the stale-date filter below.
        now = now or datetime.now(IST)
        today_code = now.strftime("%Y%m%d")

        shows: list[Show] = []
        for widget in data.get("showtimeWidgets", []) or []:
            if widget.get("type") != "groupList":
                continue
            for group in widget.get("data", []) or []:
                for card in group.get("data", []) or []:
                    if card.get("type") != "venue-card":
                        continue
                    extra = card.get("additionalData", {})
                    venue_code = extra.get("venueCode", "")
                    venue_name = extra.get("venueName", "").strip()

                    # v5 puts showtimes in showtimesSections; v4 puts them directly in showtimes
                    showtime_items: list[dict] = []
                    sections = card.get("showtimesSections", [])
                    if sections and isinstance(sections, list):
                        for sec in sections:
                            if isinstance(sec, dict):
                                showtime_items.extend(sec.get("showtimes", []) or [])
                    if not showtime_items:
                        showtime_items = card.get("showtimes", []) or []

                    for st in showtime_items:
                        sa = st.get("additionalData", {})
                        show = self._parse_show(
                            sa, st, movie_id, movie_name, venue_code, venue_name, region, today_code, now
                        )
                        if show:
                            shows.append(show)
        return shows

    def _parse_show(
        self, sa: dict, st: dict, movie_id: str, movie_name: str,
        venue_code: str, venue_name: str, region: Region, today_code: str, now: datetime,
    ) -> Show | None:
        date_code = str(sa.get("showDateCode") or sa.get("dateCode") or "").strip()
        if not date_code:
            raw = str(sa.get("cutOffDateTime", ""))
            if len(raw) >= 8 and raw[:8].isdigit():
                date_code = raw[:8]
        if not date_code:
            return None

        raw_show_time = str(sa.get("showTime") or st.get("title") or "").strip()
        show_time = format_bms_show_time(date_code, raw_show_time)
        show_id = str(sa.get("sessionId") or "").strip()

        categories = sa.get("categories", []) or []
        available = any(
            str(c.get("availStatus", "")) in _AVAIL_OPEN for c in categories
        ) if categories else True

        # Only future shows count as bookable; a date in the past is stale data.
        if date_code < today_code:
            return None

        screen_format = str(sa.get("attributes") or st.get("screenAttr") or "").strip()
        booking_url = f"https://in.bookmyshow.com/movies/{region.slug or region.code.lower()}/buytickets/{movie_id}/{date_code}"

        return Show(
            source=Source.BOOKMYSHOW,
            movie_id=movie_id,
            movie_name=movie_name,
            theatre_id=venue_code,
            theatre_name=venue_name,
            show_id=show_id,
            show_time=show_time,
            booking_url=booking_url,
            screen_format=screen_format,
            available=available,
        )