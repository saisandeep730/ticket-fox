import pytest
from app.config import _normalize_db_url, _flag, _csv, Settings


def test_normalize_db_url_postgres():
    # Render and Supabase format postgres://
    url1 = "postgres://user:password@host.render.com:5432/ticket_fox_db"
    assert _normalize_db_url(url1, "default.db") == "postgresql+asyncpg://user:password@host.render.com:5432/ticket_fox_db"

    # Standard postgresql://
    url2 = "postgresql://user:password@ep-cool-fog-123.us-east-2.aws.neon.tech/neondb?sslmode=require"
    assert _normalize_db_url(url2, "default.db") == "postgresql+asyncpg://user:password@ep-cool-fog-123.us-east-2.aws.neon.tech/neondb?sslmode=require"


def test_normalize_db_url_sqlite():
    # Standard sqlite:// without aiosqlite
    url = "sqlite:///custom_path.db"
    assert _normalize_db_url(url, "default.db") == "sqlite+aiosqlite:///custom_path.db"

    # Empty URL uses default file
    assert _normalize_db_url("", "default.db") == "sqlite+aiosqlite:///default.db"

    # Already formatted asyncpg URL is preserved
    url_async = "postgresql+asyncpg://user:pass@host/db"
    assert _normalize_db_url(url_async, "default.db") == url_async


def test_flag_parser():
    assert _flag("NONEXISTENT_FLAG", "false") is False
    assert _flag("NONEXISTENT_FLAG", "true") is True


def test_csv_parser(monkeypatch):
    monkeypatch.setenv("TEST_CSV_ORIGINS", "http://localhost:3000, https://ticketfox.app , http://127.0.0.1:3000")
    origins = _csv("TEST_CSV_ORIGINS")
    assert origins == ["http://localhost:3000", "https://ticketfox.app", "http://127.0.0.1:3000"]
