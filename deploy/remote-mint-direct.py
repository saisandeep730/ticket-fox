"""Mint a fresh action link and print the rewritten (our-domain) version.

Run inside the backend container:
    docker compose cp deploy/remote-mint-direct.py backend:/tmp/md.py
    docker compose exec -T -e PYTHONPATH=/app backend python /tmp/md.py <email> <reset|verify>
"""

import sys

from firebase_admin import auth as fb_auth

from app import auth as app_auth  # noqa: F401  (initialises the Firebase app)
from app.auth_emails import _action_settings, _direct_link

email = sys.argv[1]
kind = sys.argv[2] if len(sys.argv) > 2 else "verify"

if kind == "reset":
    link = fb_auth.generate_password_reset_link(email, action_code_settings=_action_settings())
else:
    link = fb_auth.generate_email_verification_link(email, action_code_settings=_action_settings())

print(_direct_link(link))
