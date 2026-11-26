import asyncio
import uuid
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.testclient import TestClient

from app.auth import verify_firebase_token, get_current_user_id
from app.config import settings
from app.database.models import init_db
from app.database.repository import Repository
from app.engine.models import AvailabilityState, Show, Source
from app.main import app
from app.notifications import send_email
from app.worker import WebWorker


@pytest.mark.asyncio
async def test_auth_missing_token_rejected_when_mock_disabled(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_MOCK_AUTH", False)
    with pytest.raises(HTTPException) as exc_info:
        await verify_firebase_token(None)
    assert exc_info.value.status_code == 401
    assert "Missing Authorization header" in exc_info.value.detail


@pytest.mark.asyncio
async def test_auth_invalid_token_rejected_when_mock_disabled(monkeypatch):
    monkeypatch.setattr(settings, "ALLOW_MOCK_AUTH", False)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.jwt.token")
    with pytest.raises(HTTPException) as exc_info:
        await verify_firebase_token(creds)
    assert exc_info.value.status_code == 401


def test_api_tenant_isolation_on_watches():
    """User B must not be able to read, update, or delete User A's watches."""
    client = TestClient(app)
    user_a = f"user_alpha_{uuid.uuid4().hex[:6]}"
    user_b = f"user_beta_{uuid.uuid4().hex[:6]}"

    app.dependency_overrides[get_current_user_id] = lambda: user_a
    create_resp = client.post("/api/watches", json={
        "movie_title": "Tenet Re-release",
        "movie_id": "ET00123456",
        "source": "bookmyshow",
        "city": "Hyderabad",
        "whatsapp_number": "9876543210",
    })
    assert create_resp.status_code == 201
    watch_id = create_resp.json()["watch"]["id"]

    list_a = client.get("/api/watches")
    assert any(w["id"] == watch_id for w in list_a.json()["watches"])

    app.dependency_overrides[get_current_user_id] = lambda: user_b

    list_b = client.get("/api/watches")
    assert all(w["id"] != watch_id for w in list_b.json()["watches"])

    assert client.patch(f"/api/watches/{watch_id}", json={"is_active": False}).status_code == 404
    assert client.delete(f"/api/watches/{watch_id}").status_code == 404

    app.dependency_overrides[get_current_user_id] = lambda: user_a
    client.delete(f"/api/watches/{watch_id}")
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_worker_lifecycle_startup_and_cancellation():
    """Verify that worker starts up, runs cycles, and cancels cleanly without hanging."""
    worker = WebWorker(concurrency=2)
    assert worker.concurrency == 2

    keys_handled = await worker.run_cycle()
    assert isinstance(keys_handled, int)
    assert WebWorker.last_cycle_at is not None

    task = asyncio.create_task(worker.start())
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_worker_duplicate_alert_prevention_on_restart():
    """Verify that a watch already in AVAILABLE state does NOT re-notify when the worker restarts."""
    repo = Repository()
    uid = f"user_dedup_{uuid.uuid4().hex[:6]}"
    watch = await repo.create_watch(
        user_uid=uid,
        movie_title="Interstellar",
        movie_id="DEDUP_001",
        source="bookmyshow",
        city="Hyderabad",
    )
    wid = watch["id"]

    await repo.mark_watch_checked(wid, "AVAILABLE", notified=True)

    stored_watch = type("W", (), (await repo.get_user_watches(uid))[0])()
    worker = WebWorker()

    shows = [
        Show(Source.BOOKMYSHOW, "DEDUP_001", "Interstellar", "T1", "Prasads IMAX",
             "S1", "2026-10-20T19:30", "https://in.bookmyshow.com", "IMAX", True)
    ]

    state = await worker.evaluate(stored_watch, shows)
    assert state == AvailabilityState.AVAILABLE

    # Already-notified AVAILABLE must not produce a second alert.
    alerts = await repo.get_recent_alerts(uid, limit=10)
    assert len(alerts) == 0

    await repo.delete_watch(uid, wid)


@pytest.mark.asyncio
async def test_worker_retry_after_failed_notification():
    """Verify that if a notification failed previously (notify_attempts > 0), the worker retries it."""
    repo = Repository()
    uid = f"user_retry_{uuid.uuid4().hex[:6]}"
    watch = await repo.create_watch(
        user_uid=uid,
        movie_title="Dune 2",
        movie_id="RETRY_001",
        source="bookmyshow",
        city="Hyderabad",
    )
    wid = watch["id"]

    await repo.mark_watch_checked(wid, "AVAILABLE", notified=False, notify_error="Resend rate limit")

    stored_watch = type("W", (), (await repo.get_user_watches(uid))[0])()
    assert stored_watch.notify_attempts == 1
    assert stored_watch.notified_at is None

    worker = WebWorker()
    shows = [
        Show(Source.BOOKMYSHOW, "RETRY_001", "Dune 2", "T1", "PVR",
             "S1", "2026-10-20T21:00", "", "2D", True)
    ]

    async def mock_notify(w, av):
        return True, None

    worker.notify = mock_notify
    state = await worker.evaluate(stored_watch, shows)
    assert state == AvailabilityState.AVAILABLE

    # A successful retry clears the failure counter and stamps notified_at.
    rechecked = (await repo.get_user_watches(uid))[0]
    assert rechecked["notify_attempts"] == 0
    assert rechecked["notified_at"] is not None

    await repo.delete_watch(uid, wid)


def test_production_fails_safely_when_credentials_missing(monkeypatch):
    """Verify that send_email does NOT report fake success when RESEND_API_KEY is empty in production."""
    monkeypatch.setattr(settings, "DEBUG", False)
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")

    ok, detail = send_email("target@example.com", "Test Subject", "<html>Test</html>")
    assert ok is False
    assert "RESEND_API_KEY is not configured on the server" in detail


def test_health_check_handles_database_failure(monkeypatch):
    """Verify that /api/health catches database outages and returns 503 Service Unavailable."""
    client = TestClient(app)

    async def broken_db():
        raise ConnectionRefusedError("Database connection pool exhausted")

    monkeypatch.setattr("app.main.repo.get_active_watches", broken_db)

    resp = client.get("/api/health")
    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "degraded"
    assert "disconnected" in data["database"]["status"]


def test_worker_cycle_endpoint_security(monkeypatch):
    """Verify that POST /api/worker/cycle requires authorization."""
    client = TestClient(app)
    monkeypatch.setattr(settings, "SECRET_KEY", "super_secret_admin_key_123")

    assert client.post("/api/worker/cycle").status_code == 403
    assert client.post("/api/worker/cycle", headers={"X-Admin-Key": "wrong_key"}).status_code == 403

    valid_resp = client.post("/api/worker/cycle", headers={"X-Admin-Key": "super_secret_admin_key_123"})
    assert valid_resp.status_code == 200
    assert valid_resp.json()["status"] == "success"
    assert "poll_keys_handled" in valid_resp.json()
