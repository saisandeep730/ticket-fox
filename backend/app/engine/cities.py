"""Canonical city catalog shared by the add flow and the worker.

The bot only needs to offer a fixed set of cities in V1 (the same set the
BookMyShow adapter knows offline, plus District slugs). Keeping the catalog in
one place means the city screen, the search screen, and region reconstruction
in the worker never drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Region, Source


@dataclass(frozen=True, slots=True)
class City:
    key: str    # stable callback token, e.g. "hyderabad"
    name: str   # display name, e.g. "Hyderabad"


def _key(name: str) -> str:
    return name.lower().replace(" ", "-").strip()


CITY_NAMES: list[str] = [
    "Hyderabad",
    "Mumbai",
    "Delhi-NCR",
    "Bengaluru",
    "Chennai",
    "Kolkata",
    "Pune",
    "Kochi",
    "Ahmedabad",
    "Chandigarh",
]

CITIES: list[City] = [City(_key(name), name) for name in CITY_NAMES]
_BY_KEY: dict[str, City] = {c.key: c for c in CITIES}

# URL slugs and satellite hubs that map to canonical city keys.
_ALIASES: dict[str, str] = {
    # Delhi-NCR
    "delhi": "delhi-ncr",
    "new-delhi": "delhi-ncr",
    "ncr": "delhi-ncr",
    "gurugram": "delhi-ncr",
    "gurgaon": "delhi-ncr",
    "noida": "delhi-ncr",
    "greater-noida": "delhi-ncr",
    "ghaziabad": "delhi-ncr",
    "faridabad": "delhi-ncr",
    # Bengaluru
    "bangalore": "bengaluru",
    # Mumbai & MMR
    "bombay": "mumbai",
    "navi-mumbai": "mumbai",
    "thane": "mumbai",
    "kalyan": "mumbai",
    "ulhasnagar": "mumbai",
    # Hyderabad
    "secunderabad": "hyderabad",
    # Chennai
    "madras": "chennai",
    # Kolkata
    "calcutta": "kolkata",
    "howrah": "kolkata",
    # Pune
    "pcmc": "pune",
    "pimpri": "pune",
    "chinchwad": "pune",
    # Kochi
    "cochin": "kochi",
    "ernakulam": "kochi",
    # Ahmedabad
    "gandhinagar": "ahmedabad",
}


def default_city() -> City:
    return CITIES[0]


def get_city(key: str) -> City | None:
    key = (key or "").lower().strip()
    if key in _BY_KEY:
        return _BY_KEY[key]
    alias = _ALIASES.get(key)
    return _BY_KEY.get(alias) if alias else None


def city_key_from_slug(slug: str) -> str | None:
    """Map a URL region slug ("hyderabad", "bengaluru") to a catalog key."""
    slug = (slug or "").lower().strip()
    if not slug:
        return None
    if slug in _BY_KEY:
        return slug
    return _ALIASES.get(slug)


def city_key_from_name(name: str) -> str | None:
    name = (name or "").strip()
    if not name:
        return None
    key = _key(name)
    if key in _BY_KEY:
        return key
    return _ALIASES.get(key)


def search(query: str) -> list[City]:
    """Case-insensitive substring match over names, keys, and aliases."""
    q = (query or "").lower().strip()
    if not q:
        return list(CITIES)
    matches: list[City] = []
    for city in CITIES:
        haystack = {city.name.lower(), city.key}
        haystack |= {alias for alias, target in _ALIASES.items() if target == city.key}
        if any(q in term for term in haystack):
            matches.append(city)
    return matches


def region_for(source: Source, city: City) -> Region:
    """Build a source region for a catalog city.

    BookMyShow codes come from the offline ``REGION_MAP`` when known; District
    uses the lower-case slug directly. Both are pure (no network).

    ``source`` may be a ``Source`` or a raw string (watches store it as text).
    """
    source = Source(source)
    if source is Source.BOOKMYSHOW:
        from .sources.bookmyshow import REGION_MAP

        entry = REGION_MAP.get(city.key) or REGION_MAP.get(city.name.lower())
        if entry:
            code, slug, lat, lon, geohash = entry
            return Region(source, code, city.name, slug, lat, lon, geohash)
        return Region(source, city.name.upper(), city.name, city.key)
    slug = _key(city.name)
    return Region(source, slug, city.name, slug)
