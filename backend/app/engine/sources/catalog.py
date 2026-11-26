"""Harvest and search running and upcoming movies from BookMyShow and District."""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.parse
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from ..http import BMS_WEB_HEADERS, HttpClient
from ..models import Source
from ..showtime import IST
from ..titles import names_match as _names_match
from ..titles import normalize_title as _normalize_title
from ..urls import normalise_district_id, parse_movie_url

logger = logging.getLogger(__name__)

CATALOG_CACHE_TTL_SECONDS = 3600  # 1 hour

# BookMyShow "explore" region slugs (the city key differs for NCR).
BMS_EXPLORE_SLUGS: dict[str, str] = {
    "hyderabad": "hyderabad",
    "mumbai": "mumbai",
    "delhi-ncr": "national-capital-region-ncr",
    "bengaluru": "bengaluru",
    "chennai": "chennai",
    "kolkata": "kolkata",
    "pune": "pune",
    "kochi": "kochi",
    "ahmedabad": "ahmedabad",
    "chandigarh": "chandigarh",
}

# "12.1K+ are interested" — the heart/likes count BookMyShow shows per movie.
_INTEREST_RE = re.compile(r"([\d.]+)\s*([KkLlMm])?\+?\s*are interested")


@dataclass(frozen=True, slots=True)
class MovieSearchResult:
    source: Source
    movie_id: str
    movie_slug: str
    movie_name: str
    poster_url: str = ""
    url: str = ""
    interest: int = 0
    release_date: str = ""
    both_sources: bool = False
    alt_source: Source | None = None
    alt_movie_id: str = ""


def canonical_movie_id(source: Source, movie_id: str) -> str:
    """The id shape each site is stored with.

    District ids are the **bare digits** (``185027``) because the adapter rebuilds
    the page URL as ``…-MV<id>`` — a stored ``MV185027`` would become
    ``…-MVMV185027`` and 404. BookMyShow event codes pass through untouched.
    """
    return normalise_district_id(movie_id) if source is Source.DISTRICT else movie_id


_INTEREST_MULTIPLIERS = {"k": 1_000, "l": 100_000, "m": 1_000_000}


def _parse_interest(html: str) -> int:
    """Parse "12.1K+ are interested" into an integer (0 when absent)."""
    match = _INTEREST_RE.search(html or "")
    if not match:
        return 0
    try:
        value = float(match.group(1))
    except ValueError:
        return 0
    multiplier = _INTEREST_MULTIPLIERS.get((match.group(2) or "").lower(), 1)
    return int(value * multiplier)


def _parse_release_date(html: str) -> str:
    """Extract release date in 'YYYY-MM-DD' from Movie JSON-LD or date string."""
    if not html:
        return ""

    def _extract_from_dict(item: dict) -> str:
        if not isinstance(item, dict):
            return ""
        if item.get("@type") == "Movie":
            date_val = (
                (item.get("releasedEvent") or {}).get("startDate")
                or item.get("datePublished")
                or item.get("releaseDate")
            )
            if date_val:
                date_clean = str(date_val).strip()[:10]
                try:
                    dt = datetime.strptime(date_clean, "%Y-%m-%d").date()
                    return dt.isoformat()
                except ValueError:
                    pass
        return ""

    # 1. Look for Movie schema in JSON-LD
    for script in re.findall(r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>', html, re.DOTALL):
        try:
            data = json.loads(script)
            if isinstance(data, list):
                for obj in data:
                    res = _extract_from_dict(obj)
                    if res:
                        return res
            elif isinstance(data, dict):
                res = _extract_from_dict(data)
                if res:
                    return res
                for obj in data.get("@graph", []):
                    res = _extract_from_dict(obj)
                    if res:
                        return res
        except Exception:
            continue

    # 2. Fallback: regex search in HTML
    # Day Month Year (e.g. 18 Sep 2026, 18 September, 2026)
    date_match = re.search(r'(\d{1,2})\s+([A-Za-z]{3,9}),?\s+(\d{4})', html)
    if date_match:
        day, month_str, year = date_match.groups()
        for fmt in ("%d %b %Y", "%d %B %Y"):
            try:
                dt = datetime.strptime(f"{day} {month_str} {year}", fmt).date()
                return dt.isoformat()
            except ValueError:
                pass

    # Month Day, Year (e.g. Sep 18, 2026, September 18 2026)
    date_match2 = re.search(r'([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})', html)
    if date_match2:
        month_str, day, year = date_match2.groups()
        for fmt in ("%b %d %Y", "%B %d %Y"):
            try:
                dt = datetime.strptime(f"{month_str} {day} {year}", fmt).date()
                return dt.isoformat()
            except ValueError:
                pass

    return ""


# BookMyShow's JSON-LD/og:image points at a *landscape banner*
# (discovery-catalog/events/tr:w-750,h-550/<code>-<hash>-landscape.jpg, 750x550),
# while the real 2:3 poster lives under iedb/movies/images/ and is keyed by the
# same event code. Showing the banner wherever a poster belongs is what made the
# bot look like it was displaying the wrong poster, so upgrade it when possible.
# Preference order is highest-resolution portrait variant first; every URL must
# be one that actually appears on the page (never fabricated) so it cannot 404.
_BMS_LANDSCAPE_RE = re.compile(r"^https://assets-in\.bmscdn\.com/.*landscape\.jpg$", re.IGNORECASE)
_BMS_EVENT_CODE_RE = re.compile(r"et(\d{8,})", re.IGNORECASE)
_BMS_PORTRAIT_PATHS = (
    "iedb/movies/images/mobile/thumbnail/xlarge",
    "iedb/movies/images/website/poster/large",
    "iedb/movies/images/mobile/thumbnail/large",
    "iedb/movies/images/website/poster/medium",
    "iedb/movies/images/mobile/thumbnail/medium",
    "iedb/movies/images/website/poster/small",
    "iedb/movies/images/mobile/thumbnail/small",
)


def _upgrade_bms_banner_to_poster(html: str, image_url: str) -> str:
    """Swap a BookMyShow landscape banner for the same movie's portrait poster.

    The event code is matched so a carousel entry for a *different* movie on the
    same page can never be picked, and the returned URL is always one found in
    ``html`` (so it is known to resolve).
    """
    if not image_url or not _BMS_LANDSCAPE_RE.match(image_url):
        return image_url
    code_match = _BMS_EVENT_CODE_RE.search(image_url)
    if not code_match:
        return image_url
    code = code_match.group(1).lower()

    for path in _BMS_PORTRAIT_PATHS:
        pattern = re.compile(
            r'https://assets-in\.bmscdn\.com/' + re.escape(path) + r'/[^"\'\s]+-et' + code + r'-\d+\.jpg',
            re.IGNORECASE,
        )
        found = pattern.search(html)
        if found:
            return found.group(0)

    # Any portrait asset for this event code, whatever size directory it uses.
    fallback = re.compile(
        r'https://assets-in\.bmscdn\.com/iedb/movies/images/[^"\'\s]+-et' + code + r'-\d+\.jpg',
        re.IGNORECASE,
    )
    found = fallback.search(html)
    return found.group(0) if found else image_url


def extract_poster_from_html(html: str) -> str:
    """Extract the movie's official poster from JSON-LD schema or og:image.

    BookMyShow's own metadata advertises a landscape banner, which is swapped for
    the movie's portrait poster via :func:`_upgrade_bms_banner_to_poster`.
    """
    if not html:
        return ""
    for script in re.findall(r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>', html, re.DOTALL):
        try:
            data = json.loads(script)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and item.get("@type") == "Movie" and item.get("image"):
                    img = item["image"]
                    if isinstance(img, list) and img:
                        return _upgrade_bms_banner_to_poster(html, str(img[0]).strip())
                    if isinstance(img, str) and img.startswith("http"):
                        return _upgrade_bms_banner_to_poster(html, img.strip())
        except Exception:
            continue
    m = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if m and m.group(1).startswith("http"):
        return _upgrade_bms_banner_to_poster(html, m.group(1).strip())
    return ""

BMS_SHORT_CODES: dict[str, str] = {
    "hyderabad": "hyd",
    "mumbai": "mumbai",
    "delhi-ncr": "national-capital-region-ncr",
    "bengaluru": "bang",
    "chennai": "chen",
    "kolkata": "kolk",
    "pune": "pune",
    "kochi": "koch",
    "ahmedabad": "ahd",
    "chandigarh": "chd",
}

# District's full movie catalog (every movie URL with its MV id). The live
# `/movies` page only lists a city's subset, so titles that exist on District but
# are not currently touring that city (e.g. an older run of "The Paradise") never
# reach the harvested catalog and the Dual Radar companion is missed. This sitemap
# (~2.5k entries, ~400 KB) is the complete, cheap source for companion discovery.
DISTRICT_SITEMAP_URL = "https://cdn.district.in/sitemap/movie-detail-generic.xml"


def _slug_to_display_name(slug: str) -> str:
    """``the-paradise`` → ``The Paradise`` (sitemap locs carry no human title)."""
    return " ".join(part.capitalize() for part in (slug or "").split("-") if part)


# Tokens too common to matter for "any token" substring scoring: without this,
# a query like "the paradise" matches almost every title that contains "the".
_SEARCH_STOPWORDS = frozenset(
    {
        "the", "a", "an", "and", "or", "of", "in", "for", "to", "with", "vs",
        "on", "at", "by", "is", "it", "its", "be", "de",
    }
)


class MovieCatalog:
    """In-memory movie catalog refreshed periodically from source explore pages."""

    def __init__(self, http: HttpClient | None = None) -> None:
        self.http = http or HttpClient()
        self._cache: list[MovieSearchResult] = []
        self._all_city_movies: list[MovieSearchResult] = []
        self._last_fetched_at: float = 0.0
        self._upcoming_cache: dict[str, tuple[float, list[MovieSearchResult]]] = {}
        # Full District movie index (slug + MV id) harvested from their sitemap.
        # Kept separate from ``_cache`` so the ~2.5k URLs never pollute search or
        # upcoming lists; it exists purely to find "dual radar" companions.
        self._district_sitemap_cache: list[MovieSearchResult] = []
        self._district_sitemap_at: float = 0.0

    def refresh(self, force: bool = False) -> list[MovieSearchResult]:
        now = time.monotonic()
        if not force and self._cache and (now - self._last_fetched_at) < CATALOG_CACHE_TTL_SECONDS:
            return self._cache

        movies: list[MovieSearchResult] = []

        # 1. Harvest District movies
        try:
            district_html = self.http.get_text("https://www.district.in/movies")
            movies.extend(self._parse_district_catalog(district_html))
        except Exception as exc:
            logger.debug("Failed harvesting District catalog: %s", exc)

        # 2. Harvest BookMyShow movies across top metro regions (home, movies, upcoming)
        for city in ("hyderabad", "mumbai", "national-capital-region-ncr", "bengaluru"):
            for kind in ("home", "movies", "upcoming-movies"):
                bms_url = (
                    f"https://in.bookmyshow.com/explore/home/{city}"
                    if kind == "home"
                    else f"https://in.bookmyshow.com/explore/{kind}-{city}"
                )
                try:
                    bms_html = self.http.get_text(bms_url, headers=BMS_WEB_HEADERS)
                    movies.extend(self._parse_bms_catalog(bms_html))
                except Exception as exc:
                    logger.debug("Failed harvesting BMS %s (%s): %s", kind, city, exc)

        # Deduplicate by (source, movie_id) while preserving poster_url & highest interest
        seen_map: dict[tuple[str, str], MovieSearchResult] = {}
        for m in movies:
            key = (m.source.value, m.movie_id)
            if key not in seen_map:
                seen_map[key] = m
            else:
                existing = seen_map[key]
                new_poster = existing.poster_url or m.poster_url
                new_interest = max(existing.interest, m.interest)
                new_rel_date = existing.release_date or m.release_date
                seen_map[key] = replace(
                    existing,
                    poster_url=new_poster,
                    interest=new_interest,
                    release_date=new_rel_date,
                )
        deduped = list(seen_map.values())

        if deduped or not self._cache:
            self._cache = deduped
            self._last_fetched_at = now
        return self._cache

    def district_movies(self, force: bool = False) -> list[MovieSearchResult]:
        """Full District movie index (slug + MV id) from their sitemap.

        Used only for Dual-Radar companion discovery — never surfaced in search or
        upcoming lists. Cached for :data:`CATALOG_CACHE_TTL_SECONDS`.
        """
        now = time.monotonic()
        if not force and self._district_sitemap_cache and (now - self._district_sitemap_at) < CATALOG_CACHE_TTL_SECONDS:
            return list(self._district_sitemap_cache)
        try:
            xml = self.http.get_text(DISTRICT_SITEMAP_URL)
            entries = self._parse_district_sitemap(xml)
            if entries:
                self._district_sitemap_cache = entries
                self._district_sitemap_at = now
                return list(entries)
        except Exception as exc:
            logger.debug("Failed harvesting District sitemap: %s", exc)
        return list(self._district_sitemap_cache)

    @staticmethod
    def _parse_district_sitemap(xml: str) -> list[MovieSearchResult]:
        """Parse ``<loc>https://www.district.in/movies/<slug>...-MV<id></loc>`` rows."""
        entries: list[MovieSearchResult] = []
        seen: set[str] = set()
        pattern = re.compile(r"<loc>(https://www\.district\.in/movies/[^<]+?-MV(\d+))</loc>")
        for url, movie_id in pattern.findall(xml):
            if movie_id in seen:
                continue
            seen.add(movie_id)
            leaf = url.rstrip("/").split("/")[-1]
            # <slug>-movie-tickets[-in-<city>]-MV<id>
            match = re.match(r"^(.*?)-movie-tickets(?:-in-[a-z0-9\-]+)?-MV\d+$", leaf)
            slug = match.group(1) if match else leaf
            entries.append(
                MovieSearchResult(
                    source=Source.DISTRICT,
                    movie_id=movie_id,
                    movie_slug=slug,
                    movie_name=_slug_to_display_name(slug),
                    url=url,
                )
            )
        return entries

    def _district_companion_pool(self) -> list[MovieSearchResult]:
        """Catalog + full District index, for finding dual-source matches."""
        pool = self.district_movies(force=False)
        if pool:
            return pool
        return self._cache

    def _search_bms_dynamic(self, query: str) -> list[MovieSearchResult]:
        """Query BookMyShow's dynamic live search API for real-time matches across all movies."""
        q = (query or "").strip()
        if len(q) < 2:
            return []
        encoded = urllib.parse.quote(q)
        # Use instant=false to search the entire BookMyShow movie library (both released and upcoming)
        url = f"https://in.bookmyshow.com/api/v1/search/dynamic?q={encoded}&instant=false&firstLoad=false"
        headers = {
            **BMS_WEB_HEADERS,
            "Referer": "https://in.bookmyshow.com/",
        }
        try:
            data = self.http.get_json(url, headers=headers)
        except Exception as exc:
            logger.debug("BMS dynamic search failed for '%s': %s", q, exc)
            return []

        widgets = data.get("data", {}).get("widgets", {})
        search_w = widgets.get("search-vi-v2-results")
        if not search_w:
            for k, v in widgets.items():
                if "search" in k.lower() or (isinstance(v, dict) and v.get("id") == "searchResultsV2"):
                    search_w = v
                    break
        if not search_w:
            return []

        cards_obj = search_w.get("data", {}).get("cards", {})
        cards = cards_obj.get("data", []) if isinstance(cards_obj, dict) else cards_obj
        if not isinstance(cards, list):
            return []

        results: list[MovieSearchResult] = []
        for card in cards:
            if not isinstance(card, dict):
                continue
            c_data = card.get("data", {})
            title = (c_data.get("result-title") or c_data.get("title") or "").strip()
            if not title:
                continue
            cta = c_data.get("cta", {})
            cta_url = cta.get("url", "")
            analytics = cta.get("analytics", {}) or c_data.get("analytics", {})
            ptype = str(analytics.get("type") or analytics.get("product") or "").lower()
            if "movie" not in ptype and "/movies/" not in cta_url.lower():
                continue

            event_code = (c_data.get("identifier") or str(analytics.get("entity_code") or "") or "").strip().upper()
            if not event_code:
                m = re.search(r"(ET\d{8})", cta_url, re.IGNORECASE)
                if m:
                    event_code = m.group(1).upper()
            if not event_code:
                continue

            slug_m = re.search(r"/movies/(?:[^/]+/)?([^/]+)", cta_url)
            slug = slug_m.group(1) if slug_m else event_code.lower()
            poster = c_data.get("result-poster-url") or c_data.get("result-icon") or ""

            # If known in upcoming or cache, reuse release date & interest
            known = next((m for m in self._cache if m.movie_id == event_code), None)
            if not known:
                for up_list in self._upcoming_cache.values():
                    known = next((m for m in up_list[1] if m.movie_id == event_code), None)
                    if known:
                        break
            rel_date = known.release_date if known else ""
            interest = known.interest if known else 0

            results.append(
                MovieSearchResult(
                    source=Source.BOOKMYSHOW,
                    movie_id=event_code,
                    movie_slug=slug,
                    movie_name=title,
                    poster_url=poster,
                    url=cta_url,
                    release_date=rel_date,
                    interest=interest,
                )
            )
        return results

    def search(self, query: str = "") -> list[MovieSearchResult]:
        q = (query or "").strip().lower()
        catalog = list(self.refresh(force=False))
        if not q:
            return catalog[:20]

        # Ensure all harvested city movies and upcoming caches are in the searchable pool
        existing_ids = {(m.source, m.movie_id) for m in catalog}
        for m in self._all_city_movies:
            if (m.source, m.movie_id) not in existing_ids:
                catalog.append(m)
                existing_ids.add((m.source, m.movie_id))

        for up_list in self._upcoming_cache.values():
            for m in up_list[1]:
                if (m.source, m.movie_id) not in existing_ids:
                    catalog.append(m)
                    existing_ids.add((m.source, m.movie_id))

        # Query BookMyShow dynamic live search for instant fresh matches across all of BMS
        dynamic_bms = self._search_bms_dynamic(query)
        if dynamic_bms:
            for dyn in dynamic_bms:
                if (dyn.source, dyn.movie_id) not in existing_ids:
                    catalog.append(dyn)
                    self._cache.append(dyn)
                    existing_ids.add((dyn.source, dyn.movie_id))
                else:
                    idx = next((i for i, c in enumerate(catalog) if (c.source, c.movie_id) == (dyn.source, dyn.movie_id)), None)
                    if idx is not None and not catalog[idx].poster_url and dyn.poster_url:
                        catalog[idx] = replace(catalog[idx], poster_url=dyn.poster_url)

        tokens = [t for t in re.split(r"\W+", q) if t]
        if not tokens:
            return catalog[:20]

        results: list[tuple[int, MovieSearchResult]] = []
        q_dedup = re.sub(r'(.)\1+', r'\1', q)
        for item in catalog:
            name_lower = item.movie_name.lower()
            id_lower = item.movie_id.lower()
            name_dedup = re.sub(r'(.)\1+', r'\1', name_lower)
            score = 0
            if q == id_lower or q == item.movie_slug.lower():
                score = 110
            elif q == name_lower:
                score = 100
            elif q_dedup == name_dedup:
                score = 90
            elif name_lower.startswith(q) or name_dedup.startswith(q_dedup):
                score = 75
            elif all(t in name_lower or re.sub(r'(.)\1+', r'\1', t) in name_dedup for t in tokens):
                score = 50
            elif any((t in name_lower or re.sub(r'(.)\1+', r'\1', t) in name_dedup) for t in tokens if len(t) >= 3 and t not in _SEARCH_STOPWORDS):
                score = 25

            if score > 0:
                results.append((score, item))

        results.sort(key=lambda x: (-x[0], x[1].movie_name))
        scored_items = [item for _, item in results]

        # Merge matching cross-platform movies into unified dual-source cards
        final_results: list[MovieSearchResult] = []
        seen_norms: set[str] = set()

        for item in scored_items:
            norm = _normalize_title(item.movie_name)
            if norm and norm in seen_norms:
                continue

            other_source = Source.DISTRICT if item.source == Source.BOOKMYSHOW else Source.BOOKMYSHOW
            pool = self._district_companion_pool() if other_source is Source.DISTRICT else catalog
            companion = next(
                (m for m in pool if m.source == other_source and _names_match(m.movie_name, item.movie_name)),
                None,
            )
            if companion:
                if norm:
                    seen_norms.add(norm)
                merged = replace(
                    item,
                    both_sources=True,
                    alt_source=companion.source,
                    alt_movie_id=canonical_movie_id(companion.source, companion.movie_id),
                    poster_url=item.poster_url or companion.poster_url,
                    release_date=item.release_date or companion.release_date,
                )
                final_results.append(merged)
            else:
                final_results.append(item)

            if len(final_results) >= 25:
                break

        return final_results

    def get_by_id(self, source: Source, movie_id: str) -> MovieSearchResult | None:
        wanted = canonical_movie_id(source, movie_id)
        for item in self.refresh(force=False):
            if item.source == source and canonical_movie_id(item.source, item.movie_id) == wanted:
                return item
        # District titles that are not touring a harvested city only appear in the
        # sitemap index. Without this second pass a stored District watch could not
        # be re-resolved to its page slug, and District needs the slug to poll.
        if source is Source.DISTRICT:
            for item in self._district_companion_pool():
                if canonical_movie_id(item.source, item.movie_id) == wanted:
                    return item
        return None

    # -- upcoming (ranked by interest / "likes") ---------------------------

    def upcoming(
        self,
        city_key: str = "hyderabad",
        limit: int = 60,
        days_ahead: int | None = 14,
        sort_by: str = "date",
    ) -> list[MovieSearchResult]:
        """Upcoming and now-showing BookMyShow movies for a city, strictly filtered to 2 weeks for display.

        Harvests from:
        - https://in.bookmyshow.com/explore/movies-{slug} (now showing)
        - https://in.bookmyshow.com/explore/upcoming-movies-{slug}?referrerBase=movies (upcoming)
        - https://in-cdn.bmscdn.com/discovery-catalog/response-cache/movies-{short_code}-web.json (CDN now showing)
        - https://in-cdn.bmscdn.com/discovery-catalog/response-cache/upcoming-movies-{short_code}-web.json (CDN upcoming)
        - https://in.bookmyshow.com/explore/home/{slug} (featured)

        All movies (regardless of release date) are added to the global search pool
        `self._all_city_movies`, while the returned website catalog displays ONLY movies
        releasing within 2 weeks (or currently running).
        """
        city_key = (city_key or "hyderabad").strip().lower()
        slug = BMS_EXPLORE_SLUGS.get(city_key, "hyderabad")
        now = time.monotonic()
        cache_key = f"{city_key}:{sort_by}:{days_ahead}"
        cached = self._upcoming_cache.get(cache_key)
        if cached and (now - cached[0]) < CATALOG_CACHE_TTL_SECONDS:
            return list(cached[1][:limit])

        raw_items: list[MovieSearchResult] = []
        now_showing_ids: set[str] = set()

        # 1. BMS movies explore page (Now showing in theatres)
        # e.g. https://in.bookmyshow.com/explore/movies-hyderabad
        movies_url = f"https://in.bookmyshow.com/explore/movies-{slug}"
        try:
            movies_html = self.http.get_text(movies_url, headers=BMS_WEB_HEADERS)
            parsed_now = self._parse_bms_catalog(movies_html)
            for it in parsed_now:
                now_showing_ids.add(it.movie_id)
            raw_items.extend(parsed_now)
        except Exception as exc:
            logger.debug("Failed harvesting now-showing movies for %s: %s", city_key, exc)

        # 2. BMS upcoming explore page
        # e.g. https://in.bookmyshow.com/explore/upcoming-movies-hyderabad?referrerBase=movies
        up_url = f"https://in.bookmyshow.com/explore/upcoming-movies-{slug}?referrerBase=movies"
        try:
            up_html = self.http.get_text(up_url, headers=BMS_WEB_HEADERS)
            raw_items.extend(self._parse_bms_catalog(up_html))
        except Exception as exc:
            logger.debug("Failed harvesting upcoming movies for %s: %s", city_key, exc)

        # 3. BMS CDN discovery cache - Now Showing
        short_code = BMS_SHORT_CODES.get(city_key, city_key[:4])
        cdn_movies_url = f"https://in-cdn.bmscdn.com/discovery-catalog/response-cache/movies-{short_code}-web.json"
        try:
            cdn_data = self.http.get_json(cdn_movies_url, headers=BMS_WEB_HEADERS)
            cdn_now = self._parse_bms_cdn_cards(cdn_data)
            for it in cdn_now:
                now_showing_ids.add(it.movie_id)
            raw_items.extend(cdn_now)
        except Exception as exc:
            logger.debug("Failed harvesting CDN now-showing for %s: %s", city_key, exc)

        # 4. BMS CDN discovery cache - Upcoming
        cdn_up_url = f"https://in-cdn.bmscdn.com/discovery-catalog/response-cache/upcoming-movies-{short_code}-web.json"
        try:
            cdn_data = self.http.get_json(cdn_up_url, headers=BMS_WEB_HEADERS)
            raw_items.extend(self._parse_bms_cdn_cards(cdn_data))
        except Exception as exc:
            logger.debug("Failed harvesting CDN upcoming cache for %s: %s", city_key, exc)

        # 5. BMS home explore page (where blockbusters / trending movies are featured)
        home_url = f"https://in.bookmyshow.com/explore/home/{slug}"
        try:
            home_html = self.http.get_text(home_url, headers=BMS_WEB_HEADERS)
            raw_items.extend(self._parse_bms_catalog(home_html))
        except Exception as exc:
            logger.debug("Failed harvesting home page for %s: %s", city_key, exc)

        # Deduplicate & merge across sources
        seen_items: dict[str, MovieSearchResult] = {}
        for it in raw_items:
            if it.movie_id not in seen_items:
                seen_items[it.movie_id] = it
            else:
                existing = seen_items[it.movie_id]
                new_poster = existing.poster_url or it.poster_url
                new_interest = max(existing.interest, it.interest)
                new_rel_date = existing.release_date or it.release_date
                new_name = existing.movie_name if len(existing.movie_name) >= len(it.movie_name) else it.movie_name
                seen_items[it.movie_id] = replace(
                    existing,
                    poster_url=new_poster,
                    interest=new_interest,
                    release_date=new_rel_date,
                    movie_name=new_name,
                )
        items = list(seen_items.values())

        # Store ALL harvested items into self._all_city_movies so search() can find everything!
        existing_all = {m.movie_id for m in self._all_city_movies}
        for it in items:
            if it.movie_id not in existing_all:
                self._all_city_movies.append(it)
                existing_all.add(it.movie_id)

        today = datetime.now(IST).date()
        three_days_ago = today - timedelta(days=3)
        cutoff = (today + timedelta(days=days_ahead)) if days_ahead else None

        ranked: list[MovieSearchResult] = []
        if items:
            scored: list[MovieSearchResult] = []
            for item in items:
                interest = item.interest
                rel_date = item.release_date
                poster = item.poster_url

                if not rel_date or interest == 0 or not poster:
                    fetched_interest, fetched_date, fetched_poster = self._details_for(item.url)
                    interest = interest or fetched_interest
                    rel_date = rel_date or fetched_date
                    poster = poster or fetched_poster

                # HOMEPAGE ELIGIBILITY RULE:
                # Displays only two categories:
                # A. Recently released movies: released within the last 3 days (rd >= three_days_ago and rd <= today).
                #    A movie released 2 days ago remains eligible.
                #    A movie released exactly 3 days ago remains eligible.
                #    A movie released 4 days ago or more is EXCLUDED.
                # B. Upcoming movies: release dates in the future (rd > today).
                #    Keep upcoming movies eligible regardless of how far away their release date is (unless days_ahead is set).
                # Missing or invalid release date: EXCLUDED (never assume an unknown date means upcoming or eligible).
                if not rel_date:
                    continue

                try:
                    rd = datetime.strptime(rel_date, "%Y-%m-%d").date()
                except ValueError:
                    continue

                # If released in the past, verify it was released at most 3 days ago:
                if rd < three_days_ago:
                    continue

                # If an explicit days_ahead restriction was provided for upcoming movies:
                if cutoff and rd > cutoff:
                    continue

                scored.append(replace(item, interest=interest, release_date=rel_date, poster_url=poster))

            if sort_by == "likes":
                ranked = sorted(scored, key=lambda it: it.interest, reverse=True)
            else:
                # Default BookMyShow order: release date soonest first, then most-liked
                ranked = sorted(scored, key=lambda it: (it.release_date or "9999-99-99", -it.interest))

        # Upcoming lists come from BookMyShow pages only, but TicketFox watches both
        # sites — record each title's companion so the UI can say so.
        ranked = self._annotate_companions(ranked)
        self._upcoming_cache[cache_key] = (now, ranked)
        return list(ranked[:limit])

    def _annotate_companions(self, items: list[MovieSearchResult]) -> list[MovieSearchResult]:
        """Flag titles that also exist on the other site, using the cached catalog.

        Purely in-memory (no extra network): the catalog is already harvested from
        both BookMyShow and District, so a normalized-name match is enough to set
        ``both_sources`` + the companion ``alt_source``/``alt_movie_id``.
        """
        if not items:
            return items
        try:
            catalog = self.refresh(force=False)
        except Exception as exc:
            logger.debug("Companion annotation skipped: %s", exc)
            return items
        if not catalog:
            return items

        annotated: list[MovieSearchResult] = []
        for item in items:
            other = Source.DISTRICT if item.source is Source.BOOKMYSHOW else Source.BOOKMYSHOW
            pool = self._district_companion_pool() if other is Source.DISTRICT else catalog
            companion = next(
                (
                    m
                    for m in pool
                    if m.source is other and _names_match(m.movie_name, item.movie_name)
                ),
                None,
            )
            if companion is None:
                annotated.append(item)
                continue
            annotated.append(
                replace(
                    item,
                    both_sources=True,
                    alt_source=companion.source,
                    alt_movie_id=canonical_movie_id(companion.source, companion.movie_id),
                    poster_url=item.poster_url or companion.poster_url,
                    release_date=item.release_date or companion.release_date,
                )
            )
        return annotated

    def _parse_bms_cdn_cards(self, data: dict) -> list[MovieSearchResult]:
        import base64
        results: list[MovieSearchResult] = []
        if not isinstance(data, dict):
            return results
        for item in data.get("listings", []):
            for card in item.get("cards", []):
                url = card.get("ctaUrl") or ""
                if not url or "/movies/" not in url:
                    continue
                analytics = card.get("analytics") or {}
                title = analytics.get("title") or card.get("seoText") or ""
                interest = 0
                text_list = card.get("text", [])
                if text_list and isinstance(text_list, list):
                    for t_entry in text_list:
                        for comp in t_entry.get("components", []):
                            txt = comp.get("text", "").strip()
                            if not title and "likes" not in txt.lower():
                                title = txt
                            elif "likes" in txt.lower():
                                m = re.search(r"([\d.]+)\s*([KkMm]?)\+?\s*Likes", txt, re.I)
                                if m:
                                    val = float(m.group(1))
                                    unit = m.group(2).lower()
                                    if unit == "k":
                                        val *= 1000
                                    elif unit == "m":
                                        val *= 1000000
                                    interest = int(val)
                img_dict = card.get("image") or {}
                img_url = img_dict.get("url", "")
                rel_date = ""
                m_date = re.search(r"ie-([A-Za-z0-9+/=]+)", img_url)
                if m_date:
                    try:
                        raw_d = base64.b64decode(m_date.group(1)).decode("utf-8")
                        dt = datetime.strptime(raw_d.strip(), "%d, %b %Y")
                        rel_date = dt.strftime("%Y-%m-%d")
                    except Exception:
                        pass
                try:
                    parsed = parse_movie_url(url)
                    results.append(
                        MovieSearchResult(
                            source=Source.BOOKMYSHOW,
                            movie_id=parsed.movie_id,
                            movie_slug=parsed.movie_slug,
                            movie_name=title.strip() or parsed.movie_slug,
                            poster_url=img_url.strip(),
                            url=url,
                            interest=interest,
                            release_date=rel_date,
                        )
                    )
                except Exception:
                    continue
        return results

    def _details_for(self, url: str) -> tuple[int, str, str]:
        if not url:
            return 0, "", ""
        try:
            html = self.http.get_text(url, headers=BMS_WEB_HEADERS)
        except Exception as exc:
            logger.debug("Failed fetching details for %s: %s", url, exc)
            return 0, "", ""
        return _parse_interest(html), _parse_release_date(html), extract_poster_from_html(html)

    def _interest_for(self, url: str) -> int:
        interest, _, _ = self._details_for(url)
        return interest

    def _parse_district_catalog(self, html: str) -> list[MovieSearchResult]:
        results: list[MovieSearchResult] = []
        seen_ids: set[str] = set()
        for script in re.findall(r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>', html, re.DOTALL):
            try:
                data = json.loads(script)
                if data.get("@type") == "ItemList":
                    for el in data.get("itemListElement", []):
                        url = el.get("url", "")
                        name = el.get("name", "")
                        img = el.get("image", "")
                        if url and name:
                            parsed = parse_movie_url(url)
                            if parsed.movie_id not in seen_ids:
                                seen_ids.add(parsed.movie_id)
                                results.append(
                                    MovieSearchResult(
                                        source=Source.DISTRICT,
                                        movie_id=parsed.movie_id,
                                        movie_slug=parsed.movie_slug,
                                        movie_name=name.strip(),
                                        poster_url=img.strip(),
                                        url=url,
                                    )
                                )
            except Exception:
                continue

        # Also extract all movie links rendered in HTML: /movies/...-MV<id>
        # The regex only needs the whole href (for parse_movie_url) and the anchor
        # text — the id is never scraped out of the URL by hand, which is what
        # allowed two id shapes ("185027" and "MV185027") to coexist.
        for m in re.finditer(
            r'<a\s+[^>]*href=["\'](https://www\.district\.in/movies/[^"\'?#]+-MV\d+[^"\'?#]*)["\'][^>]*>(.*?)</a>',
            html,
            re.DOTALL,
        ):
            full_url, inner_text = m.groups()
            parsed = parse_movie_url(full_url)
            movie_id = canonical_movie_id(Source.DISTRICT, parsed.movie_id)
            # The anchor wraps the whole movie card (title | genre · meta … Book now),
            # so the usable title is the text before the first " | " (or Book now).
            clean_name = re.sub(r"<[^>]+>", "", inner_text).strip()
            clean_name = re.split(r"\s*\|\s*", clean_name, maxsplit=1)[0]
            clean_name = re.split(r"\s+Book now\s*", clean_name, flags=re.IGNORECASE, maxsplit=1)[0]
            clean_name = clean_name.strip()
            if movie_id not in seen_ids and clean_name and not clean_name.lower().startswith("view"):
                seen_ids.add(movie_id)
                results.append(
                    MovieSearchResult(
                        source=Source.DISTRICT,
                        movie_id=movie_id,
                        movie_slug=parsed.movie_slug,
                        movie_name=clean_name,
                        poster_url="",
                        url=full_url,
                    )
                )

        return results

    def _parse_bms_catalog(self, html: str) -> list[MovieSearchResult]:
        results: list[MovieSearchResult] = []
        for script in re.findall(r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>', html, re.DOTALL):
            try:
                data = json.loads(script)
                if data.get("@type") == "ItemList":
                    for el in data.get("itemListElement", []):
                        url = el.get("url", "")
                        name = el.get("name", "")
                        img = el.get("image", "")
                        if url and name:
                            parsed = parse_movie_url(url)
                            results.append(
                                MovieSearchResult(
                                    source=Source.BOOKMYSHOW,
                                    movie_id=parsed.movie_id,
                                    movie_slug=parsed.movie_slug,
                                    movie_name=name.strip(),
                                    poster_url=img.strip(),
                                    url=url,
                                )
                            )
            except Exception:
                continue
        return results
