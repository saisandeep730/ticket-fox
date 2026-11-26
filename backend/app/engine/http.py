"""HTTP client with browser impersonation, retries, backoff and block detection.

BookMyShow and District sit behind Cloudflare-style anti-bot checks that are
*intermittent*: the same URL can return 200 on one attempt and a challenge on
the next. We use ``curl_cffi`` with browser TLS impersonation (the default
``requests``/``httpx`` TLS fingerprints get blocked), retry with exponential
backoff, and *never* treat a block or a transient error as "no shows".
"""

from __future__ import annotations

import logging
import threading
import time
import urllib.parse
from typing import Any

from curl_cffi import requests as cffi_requests

from .config import Config

logger = logging.getLogger(__name__)

CHALLENGE_MARKERS = (
    "Just a moment",
    "Attention Required",
    "attention required",
    "cf-chl",
    "cf-challenge",
    "cf-browser-verification",
    "cdn-cgi/challenge-platform",
    "Checking your browser",
    "Verifying you are human",
    "Enable JavaScript and cookies to continue",
    "challenge-form",
)

# BookMyShow sends 403 challenges to Chrome TLS fingerprints while letting
# Safari/Firefox/Edge through (measured 2026-09, and independently by SeatSniper).
# The default profile in Config is Safari; this list exists only to surface a
# clearer error when an operator overrides IMPERSONATE back to a Chrome profile.
CHROME_IMPERSONATIONS = (
    "chrome",
    "chrome99",
    "chrome100",
    "chrome101",
    "chrome104",
    "chrome107",
    "chrome110",
    "chrome116",
    "chrome119",
    "chrome120",
    "chrome123",
    "chrome124",
    "chrome131",
    "chrome133a",
    "chrome136",
    "chrome142",
    "chrome145",
    "chrome146",
    "chrome150",
    "chrome_android",
    "chrome99_android",
    "chrome131_android",
)

# Domain-specific headers used for BMS web API calls.
BMS_WEB_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8",
    "x-app-code": "WEB",
    "x-location-selection": "manual",
}


class FetchError(Exception):
    """A request failed in a way that should NOT be treated as availability data."""


class BlockedError(FetchError):
    """The site returned an anti-bot challenge / block page."""


class HTTPError(FetchError):
    """The site returned a non-200 status for a genuine (non-block) reason."""

    def __init__(self, status: int, body: str = "", url: str = "") -> None:
        super().__init__(f"HTTP {status}")
        self.status = status
        self.body = body
        # Kept so the poll log can name the URL that failed: a malformed URL built
        # by the app itself (e.g. District "…-MVMV185027") is otherwise
        # indistinguishable from a source outage in the SOURCE FAILURE line.
        self.url = url


class HttpClient:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()
        self._local = threading.local()
        if self.config.impersonate in CHROME_IMPERSONATIONS:
            logger.warning(
                "IMPERSONATE=%s is a Chrome profile; BookMyShow challenges Chrome "
                "TLS fingerprints. Use a safari*/edge*/firefox* profile instead.",
                self.config.impersonate,
            )

    # -- sessions ------------------------------------------------------------

    @property
    def _session(self) -> cffi_requests.Session:
        """One ``curl_cffi`` session per thread.

        The worker fans poll keys out through ``asyncio.to_thread`` while the bot
        shares the same client, so a single shared session would be used from
        several threads at once (curl handles are not thread-safe). Per-thread
        sessions keep the cookie jar and warm TLS connection, which makes repeat
        requests noticeably faster.
        """
        session = getattr(self._local, "session", None)
        if session is None:
            session = cffi_requests.Session()
            self._local.session = session
        return session

    # -- public API ----------------------------------------------------------

    def get_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        text = self._get(url, params=params, headers=headers)
        import json

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise FetchError(f"Invalid JSON from {url}") from exc

    def get_text(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        return self._get(url, params=params, headers=headers)

    # -- internals -----------------------------------------------------------

    def _build_headers(self, headers: dict[str, str] | None) -> dict[str, str]:
        merged: dict[str, str] = {"Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8"}
        # An empty User-Agent lets curl_cffi supply the impersonated browser's own
        # UA, which is the only way to guarantee the header set stays coherent.
        if self.config.user_agent:
            merged["User-Agent"] = self.config.user_agent
        if headers:
            merged.update(headers)
        return merged

    def _get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        final_url = self._apply_egress(url, params)
        request_headers = self._build_headers(headers)
        proxies = self._proxies()

        last_exc: Exception | None = None
        for attempt in range(1, self.config.max_retries + 1):
            try:
                resp = self._session.get(
                    final_url,
                    headers=request_headers,
                    impersonate=self.config.impersonate,
                    timeout=self.config.request_timeout,
                    proxies=proxies,
                )
            except Exception as exc:  # network-level failure
                last_exc = exc
                self._backoff(attempt, f"network error: {exc}")
                continue

            text = resp.text
            if self._is_challenge(resp.status_code, text):
                pool = [p.strip() for p in (self.config.proxy_urls or self.config.proxy_url).split(",") if p.strip()]
                if not proxies and (pool or self.config.scraperapi_key):
                    logger.warning("Challenge detected on direct egress; attempting proxy fallback pool for %s", url)
                    for px in (pool or [self.config.proxy_url]):
                        if not px and not self.config.scraperapi_key:
                            continue
                        try:
                            fb_url = (
                                "https://api.scraperapi.com/?" + urllib.parse.urlencode(
                                    {"api_key": self.config.scraperapi_key, "country_code": "in", "url": final_url}
                                )
                                if self.config.scraperapi_key
                                else final_url
                            )
                            fb_proxies = (
                                {"http": px, "https": px}
                                if px
                                else None
                            )
                            fb_resp = self._session.get(
                                fb_url,
                                headers=request_headers,
                                impersonate=self.config.impersonate,
                                timeout=self.config.request_timeout,
                                proxies=fb_proxies,
                            )
                            if fb_resp.status_code == 200 and not self._is_challenge(fb_resp.status_code, fb_resp.text):
                                return fb_resp.text
                        except Exception as fb_exc:
                            logger.debug("Proxy fallback %s failed: %s", px, fb_exc)
                raise BlockedError(f"Blocked by anti-bot (HTTP {resp.status_code}): {url}")

            if resp.status_code == 200:
                return text

            if resp.status_code in (429, 500, 502, 503, 504):
                self._backoff(attempt, f"HTTP {resp.status_code}")
                continue

            raise HTTPError(resp.status_code, text[:500], url=url)

        raise FetchError(f"Request failed after {self.config.max_retries} attempts: {url}") from last_exc

    def _apply_egress(
        self, url: str, params: dict[str, Any] | None
    ) -> str:
        """Wrap the target URL in ScraperAPI when configured (India egress)."""
        if not self.config.scraperapi_key:
            return url + ("?" + urllib.parse.urlencode(params) if params else "")
        full = url + ("?" + urllib.parse.urlencode(params) if params else "")
        return "https://api.scraperapi.com/?" + urllib.parse.urlencode(
            {"api_key": self.config.scraperapi_key, "country_code": "in", "url": full}
        )

    def _proxies(self) -> dict[str, str] | None:
        if not self.config.proxy_url:
            return None
        return {"http": self.config.proxy_url, "https": self.config.proxy_url}

    def _backoff(self, attempt: int, reason: str) -> None:
        delay = self.config.retry_backoff * (2 ** (attempt - 1))
        logger.warning("Retrying in %.1fs (%s), attempt %d/%d", delay, reason, attempt, self.config.max_retries)
        time.sleep(delay)

    @staticmethod
    def _is_challenge(status: int, text: str) -> bool:
        if status == 403 and any(m in text for m in CHALLENGE_MARKERS):
            return True
        if status == 200 and any(m in text[:1500] for m in CHALLENGE_MARKERS):
            return True
        return False