"""wppconnect-server WhatsApp gateway client (the WhatsApp delivery channel).

`wppconnect-server <https://github.com/wppconnect-team/wppconnect-server>`_ is a
REST gateway in front of WhatsApp Web. The contract this module targets:

* the **session name** is part of the URL path — there is no id lookup:
  ``POST /api/<session>/send-message``;
* the token goes in ``Authorization: Bearer <token>`` (the bcrypt hash produced by
  ``POST /api/<session>/<secretkey>/generate-token``);
* the body is ``{"phone": ["919876543210"], "message": "..."}`` — the recipient is
  bare digits, **not** a ``@c.us`` chat id;
* only text is sent: media sends are unreliable and a failed media attempt can
  keep the session's send queue busy, which can lose the text alert that follows.

Every failure is logged at WARNING with the HTTP status and the gateway body: a
4xx here is a configuration fault (wrong token, unknown session, engine not
ready), not a transient network blip.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from app.config import settings

logger = logging.getLogger("ticket_fox_web.whatsapp")

#: How long a connection-status probe is trusted before the gateway is asked again.
STATUS_CACHE_SECONDS = 60

#: ``(base_url, token, session) -> (expiry, connected)``
_status_cache: dict[tuple[str, str, str], tuple[float, bool]] = {}


@dataclass(frozen=True, slots=True)
class Response:
    """Outcome of one gateway call (``status`` is ``0`` when nothing answered)."""

    ok: bool
    status: int
    data: Any = None


def base_url() -> str:
    return (settings.WHATSAPP_API_URL or "").rstrip("/")


def session_name() -> str:
    return (settings.WHATSAPP_SESSION or "").strip()


def headers() -> dict[str, str]:
    result = {"Content-Type": "application/json", "Accept": "application/json"}
    if settings.WHATSAPP_API_TOKEN:
        result["Authorization"] = f"Bearer {settings.WHATSAPP_API_TOKEN}"
    return result


def normalize_phone(phone_number: str) -> str | None:
    """Canonical Indian mobile number as ``+91XXXXXXXXXX``.

    Accepts ``9876543210``, ``09876543210``, ``0091 98765 43210`` and
    ``+91 98765 43210``. Returns ``None`` when there are too few digits.
    """
    digits = "".join(c for c in (phone_number or "") if c.isdigit())
    if digits.startswith("00"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) < 10:
        return None
    if len(digits) == 10:
        digits = f"91{digits}"
    return f"+{digits}"


def phone_number(phone_number: str) -> str | None:
    """Normalise a user-entered number to the bare digits wppconnect expects.

    ``+91 98765 43210`` → ``919876543210`` (no ``@c.us`` suffix).
    """
    canonical = normalize_phone(phone_number)
    if canonical is None:
        return None
    return canonical.lstrip("+")


def _request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout: float = 15.0,
) -> Response:
    """Call the gateway. Never raises — every failure is logged and returned."""
    if not base_url():
        return Response(False, 0)

    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"{base_url()}{path}", data=data, headers=headers(), method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = int(getattr(response, "status", 200) or 200)
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:  # pragma: no cover - body already consumed
            detail = ""
        logger.warning("wppconnect %s %s failed: HTTP %s %s", method, path, exc.code, detail)
        return Response(False, int(getattr(exc, "code", 0) or 0))
    except Exception as exc:  # URLError, timeout, connection reset, ...
        logger.warning(
            "wppconnect %s %s failed: %s: %s (is the gateway running at %s?)",
            method,
            path,
            type(exc).__name__,
            exc,
            base_url(),
        )
        return Response(False, 0)

    if status not in (200, 201, 202):
        logger.warning("wppconnect %s %s failed: unexpected HTTP %s", method, path, status)
        return Response(False, status)
    if not raw:
        return Response(True, status, None)
    try:
        return Response(True, status, json.loads(raw.decode("utf-8")))
    except ValueError:
        logger.debug("wppconnect %s %s returned a non-JSON body", method, path)
        return Response(True, status, None)


def clear_status_cache() -> None:
    _status_cache.clear()


def status(*, force: bool = False) -> Response:
    """``GET /api/<session>/status-session`` — the gateway's connection state."""
    name = session_name()
    if not name:
        logger.warning("wppconnect: no session configured (set WHATSAPP_SESSION)")
        return Response(False, 0)
    return _request("GET", f"/api/{name}/status-session", timeout=10.0)


def is_connected(*, force: bool = False) -> bool:
    """Whether the configured session is actually linked to WhatsApp.

    Cached for :data:`STATUS_CACHE_SECONDS` so the readiness check in
    ``/api/channels`` does not probe the gateway on every request. Never used on
    the send path.
    """
    name = session_name()
    if not name or not base_url():
        return False

    key = (base_url(), settings.WHATSAPP_API_TOKEN, name)
    cached = _status_cache.get(key)
    if cached and not force and time.time() < cached[0]:
        return cached[1]

    response = status(force=force)
    connected = False
    if response.ok and isinstance(response.data, dict):
        state = str(response.data.get("status") or "").strip().upper()
        connected = state in {"CONNECTED", "ISLOGGED", "INCHAT", "MAIN"}
    _status_cache[key] = (time.time() + STATUS_CACHE_SECONDS, connected)
    return connected


def send_text(to: str, text: str) -> bool:
    """Send a plain text message (the only message kind TicketFox uses)."""
    # WhatsApp text limit is 4096 characters. Cap safely to prevent HTTP 400.
    if len(text) > 4000:
        cut = text.rfind("\n", 0, 3980)
        text = (text[:cut] if cut > 2000 else text[:3980]).rstrip() + "\n…"

    name = session_name()
    if not name:
        logger.warning("wppconnect: no session configured (set WHATSAPP_SESSION)")
        return False

    phone: Any = to
    if (settings.WHATSAPP_PHONE_FORMAT or "array").strip().lower() != "string":
        phone = [to]

    response = _request(
        "POST",
        f"/api/{name}/send-message",
        {"phone": phone, "message": text},
    )
    return response.ok
