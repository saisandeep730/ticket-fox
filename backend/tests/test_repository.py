import uuid

import pytest

from app.database.models import init_db
from app.database.repository import Repository


@pytest.mark.asyncio
async def test_repository_user_lifecycle():
    await init_db()
    repo = Repository()
    test_uid = f"test_user_{uuid.uuid4().hex[:8]}"

    created = await repo.get_or_create_user(test_uid, email="test@ticketfox.app", name="QA Tester")
    assert created["uid"] == test_uid
    assert created["email"] == "test@ticketfox.app"

    updated = await repo.update_user_profile(test_uid, {
        "whatsapp_number": "+919999988888",
        "email": "updated@ticketfox.app"
    })
    assert updated["whatsapp_number"] == "+919999988888"
    assert updated["email"] == "updated@ticketfox.app"

    fetched = await repo.get_user(test_uid)
    assert fetched is not None
    assert fetched["uid"] == test_uid


@pytest.mark.asyncio
async def test_repository_watch_isolation_and_lifecycle():
    await init_db()
    repo = Repository()
    suffix = uuid.uuid4().hex[:6]
    user_a = f"user_alpha_{suffix}"
    user_b = f"user_beta_{suffix}"

    watch_a = await repo.create_watch(
        user_uid=user_a,
        movie_title="Test Movie 1",
        movie_id="ET_TEST_001",
        source="bookmyshow",
        city="Hyderabad",
        theatres=["PVR Nexus"],
        date_filter=["today"],
        after_time="18:00",
        before_time="22:00",
        movie_slug="test-movie-1",
        region_code="HYD",
    )
    assert watch_a["user_uid"] == user_a
    watch_a_id = watch_a["id"]

    existing = await repo.find_existing_watch(user_a, "bookmyshow", "ET_TEST_001", "Hyderabad")
    assert existing is not None
    assert existing["id"] == watch_a_id

    # Tenant isolation: another user's watch is invisible and untouchable.
    b_watches = await repo.get_user_watches(user_b)
    assert all(w["id"] != watch_a_id for w in b_watches)

    assert await repo.update_watch(user_b, watch_a_id, {"is_active": False}) is None
    assert await repo.delete_watch(user_b, watch_a_id) is False

    updated_a = await repo.update_watch(user_a, watch_a_id, {"is_active": False})
    assert updated_a is not None
    assert updated_a["is_active"] is False

    deleted_a = await repo.delete_watch(user_a, watch_a_id)
    assert deleted_a is True


@pytest.mark.asyncio
async def test_repository_alert_logging_and_retry_state():
    await init_db()
    repo = Repository()
    uid = f"user_alert_{uuid.uuid4().hex[:8]}"

    w = await repo.create_watch(
        user_uid=uid,
        movie_title="Alert Test Movie",
        movie_id="ALERT_001",
        source="bookmyshow",
        city="Hyderabad",
    )
    wid = w["id"]

    # A failed send records the error and the attempt count so the worker retries.
    await repo.mark_watch_checked(wid, "AVAILABLE", notified=False, notify_error="Resend network timeout")
    watches = await repo.get_user_watches(uid)
    target = next(item for item in watches if item["id"] == wid)
    assert target["notify_attempts"] == 1
    assert "Resend network timeout" in target["notify_last_error"]

    await repo.mark_watch_checked(wid, "AVAILABLE", notified=True)
    watches2 = await repo.get_user_watches(uid)
    target2 = next(item for item in watches2 if item["id"] == wid)
    assert target2["notify_attempts"] == 0
    assert target2["notified_at"] is not None

    await repo.log_alert(wid, uid, "email", "Tickets Open Alert", "SENT")
    alerts = await repo.get_recent_alerts(uid, limit=10)
    assert alerts[0]["channel"] == "email"
    assert alerts[0]["status"] == "SENT"

    await repo.delete_watch(uid, wid)
