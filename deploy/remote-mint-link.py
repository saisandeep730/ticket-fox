"""Mint a real Firebase action link inside the backend container (diagnostic).

Usage: docker compose exec -T backend python /tmp/remote-mint-link.py <email> <reset|verify>
Prints the link so it can be opened in a browser for an end-to-end check.
"""
import sys

from firebase_admin import auth as fb_auth

from app import auth as app_auth  # noqa: F401  (initialises the Firebase app)
from app.auth_emails import _action_settings

email = sys.argv[1]
kind = sys.argv[2] if len(sys.argv) > 2 else "verify"

if kind == "reset":
    link = fb_auth.generate_password_reset_link(email, action_code_settings=_action_settings())
else:
    link = fb_auth.generate_email_verification_link(email, action_code_settings=_action_settings())

print(link)
