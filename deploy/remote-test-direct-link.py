"""Verify _direct_link rewrites a Firebase hosted action link onto our own domain.

Run inside the backend container:
    docker compose cp deploy/remote-test-direct-link.py backend:/tmp/t.py
    docker compose exec -T -e PYTHONPATH=/app backend python /tmp/t.py
"""

from app.auth_emails import _direct_link

RAW = (
    "https://ticketfox-web.firebaseapp.com/__/auth/action"
    "?apiKey=mock_api_key_for_testing"
    "&mode=verifyEmail"
    "&oobCode=DUw-sxmy66gzKY4SDXOCvQznuBU3Thtw7SNARAQRZ6cAAAGh5MG2AA"
    "&continueUrl=https://ticketfox.site/auth/action"
    "&lang=en"
)

out = _direct_link(RAW)
print("RAW :", RAW)
print("OUT :", out)
assert out.startswith("https://ticketfox.site/auth/action?"), out
assert "oobCode=DUw-sxmy66gzKY4SDXOCvQznuBU3Thtw7SNARAQRZ6cAAAGh5MG2AA" in out, out
assert "mode=verifyEmail" in out, out
assert "firebaseapp.com" not in out, out
print("OK: link rewritten onto our own domain")
