import pytest

from app.database.models import init_db
from app.database.repository import Repository
from app.engine.models import Source
from app.engine.sources.catalog import MovieSearchResult
from app.worker import is_watch_expired


@pytest.mark.asyncio
async def test_district_cinema_upsert_and_retrieval():
    await init_db()
    repo = Repository()
    cinemas = [
        {"cinema_id": "DIST-101", "cinema_name": "AMB Cinemas Gachibowli", "city_key": "hyderabad", "address": "Gachibowli"},
        {"cinema_id": "DIST-102", "cinema_name": "Prasads Multiplex", "city_key": "hyderabad", "address": "Necklace Road"},
    ]
    await repo.upsert_district_cinemas(cinemas)

    cached = await repo.list_district_cinemas("hyderabad")
    names = [c["name"] for c in cached]
    assert "AMB Cinemas Gachibowli" in names
    assert "Prasads Multiplex" in names


@pytest.mark.asyncio
async def test_poll_state_failure_escalation_and_recovery():
    await init_db()
    repo = Repository()
    key = "test_source:EV123:HYD"

    # The escalation contract: one admin alert at the first failure, silence
    # until the 20th, then the users are told the outage is sustained.
    fail_count, alert_admin, alert_users = await repo.record_poll_failure(key, "bookmyshow", "EV123", "HYD", "Cloudflare 403")
    assert fail_count == 1
    assert alert_admin is True
    assert alert_users is False

    for _ in range(18):
        fail_count, alert_admin, alert_users = await repo.record_poll_failure(key, "bookmyshow", "EV123", "HYD", "Cloudflare 403")
        assert alert_admin is False
        assert alert_users is False
    assert fail_count == 19

    fail_count, alert_admin, alert_users = await repo.record_poll_failure(key, "bookmyshow", "EV123", "HYD", "Cloudflare 403")
    assert fail_count == 20
    assert alert_admin is False
    assert alert_users is True

    was_alerted, prev_fails = await repo.record_poll_success(key)
    assert was_alerted is True
    assert prev_fails == 20


@pytest.mark.asyncio
async def test_batch_delete_watches():
    await init_db()
    repo = Repository()
    user_uid = "batch_test_user"

    w1 = await repo.create_watch(user_uid=user_uid, movie_title="Movie 1", movie_id="M1")
    w2 = await repo.create_watch(user_uid=user_uid, movie_title="Movie 2", movie_id="M2")
    w3 = await repo.create_watch(user_uid=user_uid, movie_title="Movie 3", movie_id="M3")

    deleted = await repo.batch_delete_watches(user_uid, [int(w1["id"]), int(w2["id"])])
    assert deleted == 2

    remaining = await repo.get_user_watches(user_uid)
    remaining_ids = [w["id"] for w in remaining]
    assert w1["id"] not in remaining_ids
    assert w2["id"] not in remaining_ids
    assert w3["id"] in remaining_ids


def test_watch_date_filter_expiry():
    # Dynamic tokens never expire
    assert is_watch_expired(["today"]) is False
    assert is_watch_expired(["weekend"]) is False
    assert is_watch_expired([]) is False
    assert is_watch_expired(["all"]) is False

    # Past explicit date expires
    past_date = "2020-01-01"
    assert is_watch_expired([past_date]) is True

    # Future explicit date does not expire
    future_date = "2099-12-31"
    assert is_watch_expired([future_date]) is False


@pytest.mark.asyncio
async def test_admin_stats_and_broadcast():
    await init_db()
    repo = Repository()
    stats = await repo.admin_stats()
    assert "total_users" in stats
    assert "total_watches" in stats
    assert "active_watches" in stats
    assert "failing_poll_keys" in stats

    campaign = await repo.create_broadcast(
        title="Server Maintenance Completed",
        message="All monitors running at full speed.",
        channels=["email"],
        cta_text="View Dashboard",
        cta_url="https://ticketfox.com",
    )
    assert campaign["id"] > 0
    assert campaign["title"] == "Server Maintenance Completed"

    broadcasts = await repo.get_broadcasts()
    assert any(b["id"] == campaign["id"] for b in broadcasts)


@pytest.mark.asyncio
async def test_create_dual_platform_watch(monkeypatch):
    """A "both platforms" request stores a District watch plus its BMS companion."""
    import app.main as main

    await init_db()
    companion = MovieSearchResult(
        source=Source.BOOKMYSHOW,
        movie_id="ET00427910",
        movie_slug="ranabaali",
        movie_name="Ranabaali",
    )
    monkeypatch.setattr(main.catalog, "search", lambda query="": [companion])

    result = await main._create_dual_watch(
        main.WatchCreate(
            movie_title="Ranabaali",
            movie_id="214106",
            source="both",
            city="Hyderabad",
        ),
        "dual_platform_test_user",
    )

    assert result["dual_source"] is True
    assert result["watch"]["source"] == Source.DISTRICT.value
    assert result["watch"]["movie_id"] == "214106"
    assert result["secondary_watch"] is not None
    assert result["secondary_watch"]["source"] == Source.BOOKMYSHOW.value
    assert result["secondary_watch"]["movie_id"] == "ET00427910"


