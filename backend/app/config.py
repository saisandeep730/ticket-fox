import os
from pathlib import Path

from dotenv import load_dotenv

# The README tells operators to `cp .env.example .env`, but nothing ever loaded
# that file: every documented setting (DATABASE_URL, FIREBASE_SERVICE_ACCOUNT_JSON,
# CORS_ORIGINS, ...) was silently ignored and the app ran on the defaults below.
# Load it here, before any os.getenv() call in this module runs.
BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env.local", override=True)


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _csv(name: str, default: str = "") -> list:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


def _normalize_db_url(url: str, default_file: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return f"sqlite+aiosqlite:///{default_file}"
    if raw.startswith("postgres://"):
        return raw.replace("postgres://", "postgresql+asyncpg://", 1)
    if raw.startswith("postgresql://") and not raw.startswith("postgresql+asyncpg://"):
        return raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    if raw.startswith("sqlite://") and not raw.startswith("sqlite+aiosqlite://"):
        return raw.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return raw


class Settings:
    APP_NAME: str = "Ticket Fox Web"
    DEBUG: bool = _flag("DEBUG", "true")

    # API server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    BACKEND_DIR: Path = BACKEND_DIR
    DEFAULT_DB_FILE: str = (BACKEND_DIR / "ticket_fox_web.db").as_posix()
    DATABASE_URL: str = _normalize_db_url(os.getenv("DATABASE_URL", ""), DEFAULT_DB_FILE)

    # Auth (Firebase Admin). Either an inline service-account JSON blob or a path
    # to the downloaded key file is accepted.
    FIREBASE_CREDENTIALS_PATH: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
    FIREBASE_SERVICE_ACCOUNT_JSON: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "ticket-fox-demo")
    # Security: In production (DEBUG=false), mock auth defaults to false.
    ALLOW_MOCK_AUTH: bool = _flag("ALLOW_MOCK_AUTH", "true" if _flag("DEBUG", "true") else "false")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")

    # CORS: the Next.js dev server by default. "*" is only used when an operator
    # asks for it explicitly (a wildcard origin plus credentials is rejected by
    # browsers anyway).
    CORS_ORIGINS: list = _csv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    )

    # Polling worker
    WORKER_ENABLED: bool = _flag("WORKER_ENABLED", "true")
    POLL_INTERVAL_SECONDS: int = int(os.getenv("POLL_INTERVAL_SECONDS", "180"))
    WORKER_CONCURRENCY: int = int(os.getenv("WORKER_CONCURRENCY", "3"))
    ADMIN_UID: str = os.getenv("ADMIN_UID", "1tXP1wmqmgXhVZvOiIgDL5L8sm03")
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "saisandeepy456@gmail.com")

    # Scraping engine
    IMPERSONATE: str = os.getenv("IMPERSONATE", "safari18_0")

    # Alert channels (Email / WhatsApp)
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    RESEND_FROM: str = os.getenv("RESEND_FROM", "TicketFox <onboarding@resend.dev>")

    # Per-purpose senders. Resend authorises the *domain*, not individual
    # mailboxes, so every address below works off the same API key and the same
    # DKIM record — no extra DNS verification is needed to add one. Each falls
    # back to RESEND_FROM when unset, so a single-sender deployment still works.
    RESEND_ALERTS_FROM: str = os.getenv("RESEND_ALERTS_FROM", "") or os.getenv(
        "RESEND_FROM", "TicketFox <onboarding@resend.dev>"
    )
    RESEND_SUPPORT_FROM: str = os.getenv("RESEND_SUPPORT_FROM", "") or os.getenv(
        "RESEND_FROM", "TicketFox <onboarding@resend.dev>"
    )
    RESEND_GENERAL_FROM: str = os.getenv("RESEND_GENERAL_FROM", "") or os.getenv(
        "RESEND_FROM", "TicketFox <onboarding@resend.dev>"
    )

    # Transactional auth emails (password reset / email verification) are sent by
    # the backend through Resend so they are fully branded instead of Firebase's
    # default template. AUTH_EMAIL_FROM must be an address on a Resend-verified
    # domain; it falls back to RESEND_FROM when unset.
    AUTH_EMAIL_FROM: str = os.getenv("AUTH_EMAIL_FROM", "") or os.getenv(
        "RESEND_FROM", "TicketFox <onboarding@resend.dev>"
    )
    AUTH_EMAIL_ENABLED: bool = _flag("AUTH_EMAIL_ENABLED", "true")

    # The human-monitored inbox. Alert and broadcast mail sets this as Reply-To so
    # a user who hits "Reply" reaches a person instead of a black hole. This is a
    # *receiving* address: it needs a real mailbox (MX + IMAP/webmail), which
    # Resend does not provide.
    SUPPORT_EMAIL: str = os.getenv("SUPPORT_EMAIL", "support@ticketfox.site")
    # SMTP Email (Alternative to Resend, works with Gmail / Outlook to send to ANY email)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "")

    WHATSAPP_API_URL: str = os.getenv("WHATSAPP_API_URL", "http://localhost:21465")
    WHATSAPP_API_TOKEN: str = os.getenv("WHATSAPP_API_TOKEN", "")
    WHATSAPP_SESSION: str = os.getenv("WHATSAPP_SESSION", "ticketfox")
    # wppconnect-server's send-message iterates the `phone` field, so it must be
    # an array on current builds; older builds expect a bare string.
    WHATSAPP_PHONE_FORMAT: str = os.getenv("WHATSAPP_PHONE_FORMAT", "array").strip().lower()
    TMDB_API_KEY: str = os.getenv("TMDB_API_KEY", "")
    PUBLIC_APP_URL: str = os.getenv("PUBLIC_APP_URL", "http://localhost:3000").rstrip("/")


settings = Settings()
