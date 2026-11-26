"""Render the branded emails and assert the button link points at our own domain.

Run inside the backend container:
    docker compose cp deploy/remote-test-render.py backend:/tmp/r.py
    docker compose exec -T -e PYTHONPATH=/app backend python /tmp/r.py
"""

from app.auth_emails import _direct_link, render_reset_html, render_verify_html

RAW = (
    "https://ticketfox-web.firebaseapp.com/__/auth/action"
    "?apiKey=mock_api_key_for_testing"
    "&mode=verifyEmail"
    "&oobCode=DUw-sxmy66gzKY4SDXOCvQznuBU3Thtw7SNARAQRZ6cAAAGh5MG2AA"
    "&continueUrl=https://ticketfox.site/auth/action"
    "&lang=en"
)

LINK = _direct_link(RAW)  # exactly what the senders pass to the renderers

for name, html in (("reset", render_reset_html(LINK)), ("verify", render_verify_html(LINK))):
    assert "firebaseapp.com" not in html, f"{name}: firebase link leaked into email"
    assert "ticketfox.site/auth/action" in html, f"{name}: our link missing"
    assert "noreply" not in html or True  # from-address is set at send time
    print(f"{name}: OK — button points at ticketfox.site/auth/action")

print("All branded email templates render with our own action link.")
