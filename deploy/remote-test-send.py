"""Call the real senders and print their (ok, detail) result.

Run inside the backend container:
    docker compose cp deploy/remote-test-send.py backend:/tmp/s.py
    docker compose exec -T -e PYTHONPATH=/app backend python /tmp/s.py <email>
"""

import sys

from app import auth as app_auth  # noqa: F401  (initialises the Firebase app)
from app.auth_emails import send_email_verification, send_password_reset

email = sys.argv[1]

ok, detail = send_password_reset(email)
print(f"password_reset -> ok={ok} detail={detail}")

ok, detail = send_email_verification(email)
print(f"email_verification -> ok={ok} detail={detail}")
