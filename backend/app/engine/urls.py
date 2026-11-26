"""Parse movie URLs from BookMyShow and District into structured movie IDs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from .models import Source

# https://in.bookmyshow.com/movies/<city-slug>/<movie-name>/<ET-code>
# e.g. /movies/hyderabad/the-paradise/ET00436621
BMS_EVENT_RE = re.compile(r"^ET\d{8,}$")

# https://www.district.in/movies/<slug>-movie-tickets[-in-<city>]-MV<id>
# e.g. /movies/the-paradise-movie-tickets-in-hyderabad-MV185027
DISTRICT_MV_RE = re.compile(r"^(?P<slug>.*?)-movie-tickets(?:-in-(?P<city>[a-z0-9\-]+))?-MV(?P<id>\d+)$")
DISTRICT_FALLBACK_RE = re.compile(r"^(?:(?P<slug>.*?)(?:-movie-tickets)?(?:-in-(?P<city>[a-z0-9\-]+))?[-_])?(?:MV)?(?P<id>\d+)$")


class URLParseError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ParsedMovieURL:
    source: Source
    movie_id: str
    region_slug: str = ""      # BMS: city slug from the path (e.g. "hyderabad")
    movie_slug: str = ""       # District: base slug without "-movie-tickets-..."
    city_slug: str = ""        # District: city from URL, if present
    original_url: str = ""


def parse_movie_url(url: str) -> ParsedMovieURL:
    """Parse a supported movie URL. Raises :class:`URLParseError` otherwise."""
    url = url.strip()
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    if "bookmyshow.com" in host:
        return _parse_bms(parsed, url)
    if "district.in" in host:
        return _parse_district(parsed, url)
    raise URLParseError(f"Unsupported site: {host or url}")


def _parse_bms(parsed, url: str) -> ParsedMovieURL:
    parts = [p for p in parsed.path.split("/") if p]
    event_code = next((p for p in parts if BMS_EVENT_RE.match(p)), None)
    if not event_code:
        raise URLParseError(f"No BookMyShow event code in URL: {url}")

    region_slug = ""
    movie_slug = ""
    if "movies" in parts:
        idx = parts.index("movies")
        # BookMyShow serves two shapes:
        #   /movies/<city>/<movie-slug>/<code>        (the shape the docs describe)
        #   /<city>/movies/<movie-slug>/<code>        (what the discovery CDN returns)
        # Reading only ``parts[idx + 1]`` treated the *movie slug* as the region in
        # the second shape ("the-paradise" as a city) and left ``movie_slug`` empty,
        # which broke region resolution and poster lookups for those URLs.
        if idx == 0:
            candidate_region = parts[1] if len(parts) > 1 else ""
            slug_candidates = parts[2:]
        else:
            candidate_region = parts[idx - 1]
            slug_candidates = parts[idx + 1:]
        if candidate_region and not BMS_EVENT_RE.match(candidate_region):
            region_slug = candidate_region

        for candidate in slug_candidates:
            if BMS_EVENT_RE.match(candidate) or candidate == "buytickets":
                break
            movie_slug = candidate
            break

    return ParsedMovieURL(
        source=Source.BOOKMYSHOW,
        movie_id=event_code,
        region_slug=region_slug,
        movie_slug=movie_slug,
        original_url=url,
    )


def _parse_district(parsed, url: str) -> ParsedMovieURL:
    parts = [p for p in parsed.path.split("/") if p]
    if not parts or parts[0] != "movies" or len(parts) < 2:
        raise URLParseError(f"Not a District movie URL: {url}")
    leaf = parts[-1]
    match = DISTRICT_MV_RE.match(leaf) or DISTRICT_FALLBACK_RE.match(leaf)
    if not match or not match.group("id"):
        raise URLParseError(f"Could not parse District movie id from: {url}")

    return ParsedMovieURL(
        source=Source.DISTRICT,
        movie_id=match.group("id"),
        movie_slug=match.group("slug") or "movie",
        city_slug=match.group("city") or "",
        original_url=url,
    )


def normalise_district_id(movie_id: str) -> str:
    """Return the bare numeric District id (``MV185027`` -> ``185027``).

    District exposes the *same* movie as both ``...-MV185027`` and ``...-185027``,
    but only the ``MV`` form is a real page. ``parse_movie_url`` always yields the
    bare digits, so anything that stores or rebuilds an id must pass through here:
    a stored ``MV185027`` would otherwise be prefixed a second time by
    :func:`build_district_url` and 404 on every poll.
    """
    value = (movie_id or "").strip()
    if value[:2].upper() == "MV" and value[2:].isdigit():
        return value[2:]
    return value


def build_district_url(movie_slug: str, movie_id: str, city_slug: str = "") -> str:
    """Build a District movie URL, optionally pinned to a city.

    Idempotent in ``movie_id``: both ``"185027"`` and ``"MV185027"`` produce a
    single ``-MV185027`` leaf, so a legacy watch row heals without a DB write.
    """
    leaf = f"{movie_slug}-movie-tickets"
    if city_slug:
        leaf += f"-in-{city_slug}"
    leaf += f"-MV{normalise_district_id(movie_id)}"
    return f"https://www.district.in/movies/{leaf}"


def build_bms_url(movie_id: str, movie_slug: str = "", city_slug: str = "hyderabad") -> str:
    """Build a canonical BookMyShow movie URL."""
    slug = movie_slug or "movie"
    city = city_slug or "hyderabad"
    return f"https://in.bookmyshow.com/movies/{city}/{slug}/{movie_id}"


def build_app_deep_link(source: Source | str, movie_id: str, movie_slug: str = "", city_slug: str = "") -> str:
    """Build a direct mobile app deep link scheme for native apps."""
    src = Source(source) if isinstance(source, str) else source
    if src is Source.BOOKMYSHOW:
        return f"bms://movie/{movie_id}"
    return f"district://movies/{movie_id}"