"""Branded transactional auth emails (password reset + email verification).

Firebase Auth can send these itself, but its templates are plain and the sender
is ``noreply@<project>.firebaseapp.com``. Instead we mint the action link with
the Firebase Admin SDK and deliver our own HTML through Resend, so the mail
matches the TicketFox brand and comes from a verified domain.

The link points at our own ``/auth/action`` page (via ``ActionCodeSettings``
with ``handle_code_in_app``), which already knows how to verify the ``oobCode``
and let the user set a new password.
"""

from __future__ import annotations

import html
import logging
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

from app import notifications
from app.config import settings

logger = logging.getLogger("ticket_fox_web.auth_emails")

#: How long the emailed link stays valid (Firebase caps this at 1 hour).
LINK_TTL_MINUTES = 60


def _direct_link(link: str) -> str:
    """Rewrite Firebase's hosted action link onto our own ``/auth/action`` page.

    firebase-admin always mints a link on the project's ``*.firebaseapp.com``
    handler. Opening it there runs Firebase's own interstitial, which consumes
    the one-time code and only *then* redirects — so our page receives no
    ``oobCode`` and reports the link as already used. Rebuilding the identical
    query string on our own domain sidesteps that: the client SDK on
    ``/auth/action`` consumes the code itself, exactly as it does for in-app
    links. Returns the link unchanged if it cannot be parsed.
    """
    try:
        parts = urlparse(link)
        params = parse_qs(parts.query)
    except Exception:  # noqa: BLE001
        return link
    code = params.get("oobCode")
    if not code:
        return link
    query = {
        "mode": (params.get("mode") or ["resetPassword"])[0],
        "oobCode": code[0],
        "apiKey": (params.get("apiKey") or [""])[0],
        "lang": (params.get("lang") or ["en"])[0],
        "continueUrl": f"{settings.PUBLIC_APP_URL}/auth/action",
    }
    query = {key: value for key, value in query.items() if value}
    return f"{settings.PUBLIC_APP_URL}/auth/action?{urlencode(query)}"


def _action_settings() -> Any:
    """Where Firebase should send the user after they click the emailed link."""
    from firebase_admin import auth as fb_auth

    return fb_auth.ActionCodeSettings(
        url=f"{settings.PUBLIC_APP_URL}/auth/action",
        handle_code_in_app=True,
    )


def _from_address() -> str:
    return settings.AUTH_EMAIL_FROM or settings.RESEND_FROM


def _shell(
    *,
    heading: str,
    intro: str,
    button_label: str,
    link: str,
    outro: str,
    fallback_hint: str,
) -> str:
    """One shared dark-branded layout for every auth email."""
    safe_link = html.escape(link, quote=True)
    return f"""<!doctype html>
<html><body style="margin:0;background:#08090d;padding:24px;font-family:Segoe UI,Helvetica,Arial,sans-serif;">
  <div style="max-width:560px;margin:0 auto;background:#11131a;border:1px solid #1f2430;border-radius:16px;padding:28px;">
    <p style="margin:0 0 18px;font-size:12px;letter-spacing:1px;color:#fb923c;font-weight:700;">🦊 TICKETFOX</p>
    <h1 style="margin:0 0 10px;font-size:22px;color:#f8fafc;">{heading}</h1>
    <p style="margin:0 0 22px;color:#cbd5e1;font-size:14px;line-height:1.7;">{intro}</p>
    <a href="{safe_link}" style="display:inline-block;padding:13px 22px;border-radius:10px;background:#f97316;color:#ffffff;font-weight:700;text-decoration:none;font-size:14px;">{button_label}</a>
    <p style="margin:22px 0 0;color:#94a3b8;font-size:13px;line-height:1.7;">{outro}</p>
    <p style="margin:18px 0 0;color:#64748b;font-size:12px;line-height:1.7;">
      {fallback_hint}<br />
      <a href="{safe_link}" style="color:#fb923c;word-break:break-all;">{safe_link}</a>
    </p>
    <p style="margin:24px 0 0;padding-top:18px;border-top:1px solid #1f2430;color:#64748b;font-size:12px;">
      🦊 TicketFox · Real-time Ticket Alerts<br />
      <a href="{settings.PUBLIC_APP_URL}/" style="color:#fb923c;">{settings.PUBLIC_APP_URL}</a>
    </p>
  </div>
</body></html>"""


def render_reset_html(link: str) -> str:
    return _shell(
        heading="Reset your password",
        intro=(
            "We received a request to reset the password for your TicketFox account. "
            f"This link is valid for {LINK_TTL_MINUTES} minutes and can be used once."
        ),
        button_label="Set a new password",
        link=link,
        outro=(
            "If you didn't request this, you can safely ignore this email — "
            "your password won't change."
        ),
        fallback_hint=(
            "Some mail apps hide the button — open the link below to set your new password:"
        ),
    )


def render_verify_html(link: str) -> str:
    return _shell(
        heading="Confirm your email",
        intro=(
            "Welcome to TicketFox! Confirm this email address to finish setting up "
            "your account and start receiving real-time ticket alerts."
        ),
        button_label="Verify my email",
        link=link,
        outro="If you didn't create a TicketFox account, you can ignore this email.",
        fallback_hint=(
            "Some mail apps hide the button — open the link below to confirm your email:"
        ),
    )


def _send(to_email: str, subject: str, html: str) -> tuple[bool, str]:
    """Deliver through Resend using the auth sender (falls back to the alert sender).

    ``noreply@`` is send-only, so Reply-To is set to the monitored support inbox:
    a user who replies to a reset email reaches a human instead of bouncing.
    """
    if not settings.RESEND_API_KEY:
        return False, "RESEND_API_KEY is not configured on the server"
    return notifications.send_email(
        to_email,
        subject,
        html,
        sender=_from_address(),
        reply_to=settings.SUPPORT_EMAIL,
    )


def _account_missing(email: str) -> bool:
    """True when Firebase has no account for this address.

    We look the account up first because ``generate_*_link`` does not reliably
    raise ``UserNotFoundError``: depending on the firebase-admin version it can
    surface an ``UnexpectedResponseError`` carrying ``EMAIL_NOT_FOUND`` instead.
    """
    from firebase_admin import auth as fb_auth

    try:
        fb_auth.get_user_by_email(email)
        return False
    except fb_auth.UserNotFoundError:
        return True
    except Exception as exc:  # noqa: BLE001
        # A lookup problem (transient/network) is not proof the account is
        # absent, so let link generation surface the real error.
        logger.debug("get_user_by_email(%s) failed: %s", email, exc)
        return False


def _is_missing_account_error(exc: Exception) -> bool:
    """Detect the not-found signal across firebase-admin's exception shapes."""
    text = str(exc).lower()
    return "email_not_found" in text or "user not found" in text


def send_password_reset(email: str) -> tuple[bool, str]:
    """Mint a Firebase reset link and email it, branded, via Resend.

    Returns ``(ok, detail)``. ``detail == "user-not-found"`` lets the caller
    answer identically for unknown addresses (no account enumeration).
    """
    from firebase_admin import auth as fb_auth

    email = (email or "").strip()
    if not email:
        return False, "no email address"
    if _account_missing(email):
        return False, "user-not-found"
    try:
        link = fb_auth.generate_password_reset_link(email, action_code_settings=_action_settings())
    except fb_auth.UserNotFoundError:
        return False, "user-not-found"
    except Exception as exc:  # noqa: BLE001
        if _is_missing_account_error(exc):
            return False, "user-not-found"
        logger.warning("generate_password_reset_link failed for %s: %s", email, exc)
        return False, f"link error: {type(exc).__name__}"
    return _send(email, "Reset your TicketFox password", render_reset_html(_direct_link(link)))


def send_email_verification(email: str) -> tuple[bool, str]:
    """Mint a Firebase email-verification link and email it, branded, via Resend."""
    from firebase_admin import auth as fb_auth

    email = (email or "").strip()
    if not email:
        return False, "no email address"
    if _account_missing(email):
        return False, "user-not-found"
    try:
        link = fb_auth.generate_email_verification_link(
            email, action_code_settings=_action_settings()
        )
    except fb_auth.UserNotFoundError:
        return False, "user-not-found"
    except Exception as exc:  # noqa: BLE001
        if _is_missing_account_error(exc):
            return False, "user-not-found"
        logger.warning("generate_email_verification_link failed for %s: %s", email, exc)
        return False, f"link error: {type(exc).__name__}"
    return _send(email, "Confirm your TicketFox email", render_verify_html(_direct_link(link)))
