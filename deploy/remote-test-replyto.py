"""Prove the per-purpose senders and Reply-To header reach Resend.

Run inside the backend container:
    docker compose cp deploy/remote-test-replyto.py backend:/tmp/r.py
    docker compose exec -T -e PYTHONPATH=/app backend python /tmp/r.py <email>
"""

import json
import sys
import urllib.request

from app import notifications
from app.config import settings

email = sys.argv[1]

# Capture the exact JSON body notifications.send_email would POST to Resend,
# without actually sending, so we can assert on the headers we set.
captured: dict = {}
real_urlopen = urllib.request.urlopen


class _FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _fake_urlopen(request, *args, **kwargs):
    captured["body"] = json.loads(request.data.decode("utf-8"))
    return _FakeResponse()


urllib.request.urlopen = _fake_urlopen
try:
    ok, detail = notifications.send_email(
        email,
        "Reply-To probe",
        "<p>probe</p>",
        sender=settings.RESEND_ALERTS_FROM,
        reply_to=settings.SUPPORT_EMAIL,
    )
finally:
    urllib.request.urlopen = real_urlopen

body = captured.get("body", {})
print(f"send_email -> ok={ok} detail={detail}")
print(f"  from     = {body.get('from')}")
print(f"  reply_to = {body.get('reply_to')}")

assert body.get("from") == settings.RESEND_ALERTS_FROM, "wrong From"
assert body.get("reply_to") == settings.SUPPORT_EMAIL, "Reply-To missing"
print("OK — alerts send from alerts@ with Reply-To support@")

# And the auth path: noreply@ From, support@ Reply-To.
captured.clear()
urllib.request.urlopen = _fake_urlopen
try:
    from app import auth_emails

    auth_emails._send(email, "Auth probe", "<p>probe</p>")
finally:
    urllib.request.urlopen = real_urlopen

body = captured.get("body", {})
print(f"  auth from     = {body.get('from')}")
print(f"  auth reply_to = {body.get('reply_to')}")
assert body.get("from") == settings.AUTH_EMAIL_FROM, "wrong auth From"
assert body.get("reply_to") == settings.SUPPORT_EMAIL, "auth Reply-To missing"
print("OK — auth mail sends from noreply@ with Reply-To support@")
