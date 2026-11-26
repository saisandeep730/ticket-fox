"""Tests for the wppconnect-server WhatsApp client."""

import pytest

from app import whatsapp
from app.config import settings


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_API_URL", "http://localhost:21465")
    monkeypatch.setattr(settings, "WHATSAPP_API_TOKEN", "secret-token")
    monkeypatch.setattr(settings, "WHATSAPP_SESSION", "ticketfox")
    monkeypatch.setattr(settings, "WHATSAPP_PHONE_FORMAT", "array")
    whatsapp.clear_status_cache()
    yield
    whatsapp.clear_status_cache()


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("9876543210", "+919876543210"),
        ("09876543210", "+919876543210"),
        ("0091 98765 43210", "+919876543210"),
        ("+91 98765 43210", "+919876543210"),
        ("12345", None),
        ("", None),
    ],
)
def test_normalize_phone(raw, expected):
    assert whatsapp.normalize_phone(raw) == expected


def test_phone_number_is_bare_digits():
    assert whatsapp.phone_number("+91 98765 43210") == "919876543210"
    assert whatsapp.phone_number("9876543210") == "919876543210"
    assert whatsapp.phone_number("123") is None


def test_headers_use_bearer_token():
    assert whatsapp.headers()["Authorization"] == "Bearer secret-token"


def test_headers_omit_authorization_without_token(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_API_TOKEN", "")
    assert "Authorization" not in whatsapp.headers()


def test_send_text_builds_wppconnect_request(monkeypatch):
    captured = {}

    def fake_request(method, path, payload=None, *, timeout=15.0):
        captured.update(method=method, path=path, payload=payload)
        return whatsapp.Response(True, 200, {"status": "success"})

    monkeypatch.setattr(whatsapp, "_request", fake_request)

    assert whatsapp.send_text("919876543210", "hello") is True
    assert captured["method"] == "POST"
    assert captured["path"] == "/api/ticketfox/send-message"
    assert captured["payload"] == {"phone": ["919876543210"], "message": "hello"}


def test_send_text_string_phone_format(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_PHONE_FORMAT", "string")
    captured = {}

    def fake_request(method, path, payload=None, *, timeout=15.0):
        captured.update(payload=payload)
        return whatsapp.Response(True, 200, None)

    monkeypatch.setattr(whatsapp, "_request", fake_request)

    assert whatsapp.send_text("919876543210", "hi") is True
    assert captured["payload"]["phone"] == "919876543210"


def test_send_text_truncates_long_messages(monkeypatch):
    captured = {}

    def fake_request(method, path, payload=None, *, timeout=15.0):
        captured.update(payload=payload)
        return whatsapp.Response(True, 200, None)

    monkeypatch.setattr(whatsapp, "_request", fake_request)

    whatsapp.send_text("919876543210", "x" * 5000)
    assert len(captured["payload"]["message"]) <= 4000


def test_send_text_returns_false_without_base_url(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_API_URL", "")
    assert whatsapp.send_text("919876543210", "hi") is False


def test_send_text_returns_false_without_session(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_SESSION", "")
    assert whatsapp.send_text("919876543210", "hi") is False


def test_send_text_returns_false_when_gateway_rejects(monkeypatch):
    monkeypatch.setattr(
        whatsapp, "_request", lambda *a, **k: whatsapp.Response(False, 500)
    )
    assert whatsapp.send_text("919876543210", "hi") is False


def test_is_connected_true_when_session_connected(monkeypatch):
    monkeypatch.setattr(
        whatsapp,
        "_request",
        lambda *a, **k: whatsapp.Response(True, 200, {"status": "CONNECTED"}),
    )
    assert whatsapp.is_connected() is True


def test_is_connected_false_when_session_closed(monkeypatch):
    monkeypatch.setattr(
        whatsapp,
        "_request",
        lambda *a, **k: whatsapp.Response(True, 200, {"status": "CLOSED"}),
    )
    assert whatsapp.is_connected() is False


def test_is_connected_caches_result(monkeypatch):
    calls = {"n": 0}

    def fake_request(*a, **k):
        calls["n"] += 1
        return whatsapp.Response(True, 200, {"status": "CONNECTED"})

    monkeypatch.setattr(whatsapp, "_request", fake_request)

    assert whatsapp.is_connected() is True
    assert whatsapp.is_connected() is True
    assert calls["n"] == 1


def test_is_connected_false_without_config(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_SESSION", "")
    assert whatsapp.is_connected() is False
