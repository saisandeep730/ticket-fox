"""Single TMDB client.

Every TMDB lookup goes through this module: the movie-info endpoint, the
release-date backfill, and the browser proxy. The API key is read once from
settings and never leaves the server.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from typing import Any, Dict, List, Optional

from app.config import settings
from app.engine.titles import normalize_title

logger = logging.getLogger("ticket_fox_web.tmdb")

BASE_URLS = ("https://api.tmdb.org/3", "https://api.themoviedb.org/3")
IMAGE_BASE = "https://image.tmdb.org/t/p"

_release_date_cache: Dict[str, str] = {}


def _key() -> str:
    return (getattr(settings, "TMDB_API_KEY", "") or "").strip()


def _get(path: str, params: Dict[str, str], *, timeout: int = 6) -> Optional[Dict[str, Any]]:
    """GET a TMDB path, trying each base URL. Returns the JSON body or None."""
    key = _key()
    if not key:
        return None
    from curl_cffi import requests as cffi_requests, CurlHttpVersion

    query = urllib.parse.urlencode({**params, "api_key": key})
    for base in BASE_URLS:
        try:
            resp = cffi_requests.get(
                f"{base}{path}?{query}",
                http_version=CurlHttpVersion.V1_1,
                timeout=timeout,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as exc:
            logger.debug("TMDB %s failed on %s: %s", path, base, exc)
    return None


def search(title: str, *, timeout: int = 6) -> List[Dict[str, Any]]:
    """Raw TMDB search results for a title (empty when unconfigured or offline)."""
    body = _get("/search/movie", {"query": title, "include_adult": "false"}, timeout=timeout)
    return (body or {}).get("results", []) or []


def find_exact(title: str, clean_title: str = "") -> Optional[Dict[str, Any]]:
    """The first search result whose normalized title matches exactly.

    TMDB is only trusted for an exact title match; fuzzy candidates are ignored
    so the UI never shows metadata for a different film.
    """
    targets = {
        normalize_title(t, strip_languages=True)
        for t in (clean_title, title)
        if t
    }
    targets.discard("")
    if not targets:
        return None

    for query in dict.fromkeys(t for t in (clean_title, title) if t):
        for cand in search(query):
            names = {
                normalize_title(cand.get("title") or "", strip_languages=True),
                normalize_title(cand.get("original_title") or "", strip_languages=True),
            }
            names.discard("")
            if names & targets:
                return cand
    return None


def details(tmdb_id: Any) -> Optional[Dict[str, Any]]:
    """Full movie record with credits and videos appended."""
    if not tmdb_id:
        return None
    return _get(f"/movie/{tmdb_id}", {"append_to_response": "credits,videos"})


def movie_info(title: str, clean_title: str = "") -> Optional[Dict[str, Any]]:
    """Exact-match movie metadata, or None when TMDB has no exact match."""
    match = find_exact(title, clean_title)
    if not match:
        return None
    return details(match.get("id")) or match


def image_url(path: str, size: str = "w500") -> str:
    return f"{IMAGE_BASE}/{size}{path}" if path else ""


# Paths the browser proxy is allowed to forward. Anything else is rejected so
# the endpoint cannot be used as a general-purpose TMDB relay.
PROXY_PREFIXES = (
    "/trending/",
    "/movie/",
    "/discover/",
    "/search/",
    "/genre/",
)


def proxy(path: str, params: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Forward a read-only TMDB request for the browser, injecting the key."""
    if not path.startswith("/") or not path.startswith(PROXY_PREFIXES):
        return None
    return _get(path, params)


def release_date(title: str) -> str:
    """Release date for a title, cached. Empty string when unknown."""
    clean = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", title.lower())).strip()
    if not clean:
        return ""
    if clean in _release_date_cache:
        return _release_date_cache[clean]

    for cand in search(title.strip(), timeout=4):
        names = {
            re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", (cand.get("title") or "").lower())).strip(),
            re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", (cand.get("original_title") or "").lower())).strip(),
        }
        if clean in names or any(clean in n or n in clean for n in names if n):
            rd = cand.get("release_date") or ""
            if rd:
                _release_date_cache[clean] = rd
                return rd
    return ""
