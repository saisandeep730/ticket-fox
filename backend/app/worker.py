"""Polling worker: one source request per poll key, then evaluate + alert.

Every watch in the web app is a ``(source, movie, city)`` triple. Watches that
share a triple are served by a *single* source request per cycle (the same
de-duplication the bot worker uses), and each watch is then filtered by its own
theatre / date / time preferences.

Features:
- N1: Tickets open initial notification.
- N3: New show detection (alerts on midnight/extra screens added later).
- N4: Back in stock alert (re-openings after being sold out).
- N5/N6/N7: Failure escalation (tracks failing poll keys, notifies users on sustained outages).
- N8: Stale watch auto-expiry (retires passed calendar dates with a courtesy notice).
- District cinema harvesting (caches discovered venues in district_cinemas).
- Dynamic surge polling (60s surge for active/opening shows, 180s standard).
"""

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Dict, List, Sequence, Optional, Tuple, Any

from app import notifications
from app.config import settings
from app.database.repository import Repository
from app.engine.availability.detector import (
    filter_shows_by_date,
    filter_shows_by_time,
    infer_state,
    should_notify,
)
from app.engine.models import AvailabilityState, Show, Source
from app.engine.showtime import IST
from app.engine.sources.resolver import (
    LiveMovieResolver,
    TemporaryIssue,
    resolved_movie_for_watch,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ticket_fox_web.worker")

DEFAULT_INTERVAL_SECONDS = 180
SURGE_INTERVAL_SECONDS = 60
DEFAULT_CONCURRENCY = 3

ANY_THEATRE_TOKENS = {"", "ANY", "ALL"}


def is_watch_expired(date_filter: list[str]) -> bool:
    """True when every date in the filter is an explicit date that has passed in IST (N8)."""
    values = [d for d in (date_filter or []) if d and d != "all"]
    if not values:
        return False
    today = datetime.now(timezone.utc).astimezone(IST).date()
    for value in values:
        try:
            dt = datetime.fromisoformat(value).date()
            if dt >= today:
                return False
        except ValueError:
            return False  # dynamic tokens like 'today', 'weekend' do not expire
    return True


def shows_snapshot(shows: List[Show]) -> List[Dict[str, str]]:
    return [
        {
            "theatre_id": str(s.theatre_id),
            "show_id": str(s.show_id or s.show_time),
            "show_time": str(s.show_time),
        }
        for s in shows
    ]


def get_watch_polling_tier(watch) -> str:
    """Classify watch into adaptive frequency tier based on release date proximity.

    Tiers:
    - FAR_FUTURE (> 14 days away): Movie releases in weeks/months/next year.
      Skip rapid polling; check once every 24h.
    - APPROACHING (3 < days <= 14): Releasing within next 2 weeks.
      Poll on a 15-minute (900s) schedule.
    - IMMINENT (<= 3 days away, or open, or unknown release date):
      Poll on high-frequency real-time schedule (60s surge / 180s standard).
    """
    if getattr(watch, "status", "") == "AVAILABLE":
        return "IMMINENT"

    rel_str = (getattr(watch, "release_date", None) or "").strip()
    if not rel_str:
        for d in (getattr(watch, "date_filter", None) or []):
            if isinstance(d, str) and len(d) >= 10 and d[:10].replace("-", "").isdigit():
                rel_str = d[:10]
                break

    if not rel_str:
        return "IMMINENT"

    try:
        rel_date = datetime.strptime(rel_str[:10], "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).astimezone(IST).date()
        days_diff = (rel_date - today).days

        if days_diff > 14:
            return "FAR_FUTURE"
        elif days_diff > 3:
            return "APPROACHING"
        else:
            return "IMMINENT"
    except Exception:
        return "IMMINENT"


def is_watch_due_for_poll(watch, now_utc: datetime) -> bool:
    """Evaluate whether this watch needs a live poll in this cycle."""
    last_checked = getattr(watch, "last_checked_at", None)
    if not last_checked:
        return True

    if last_checked.tzinfo is None:
        last_checked = last_checked.replace(tzinfo=timezone.utc)

    elapsed = (now_utc - last_checked).total_seconds()
    tier = get_watch_polling_tier(watch)

    # Distant releases are polled daily, approaching ones every 15 minutes, and
    # imminent ones on every cycle.
    if tier == "FAR_FUTURE":
        return elapsed >= 86400
    elif tier == "APPROACHING":
        return elapsed >= 900
    return True


class WebWorker:
    last_cycle_at: Optional[float] = None
    last_cycle_duration: Optional[float] = None
    last_cycle_keys_count: int = 0
    surge_active: bool = False

    def __init__(self, resolver=None, repo=None, concurrency: int | None = None):
        self.resolver = resolver or LiveMovieResolver()
        self.repo = repo or Repository()
        self.concurrency = max(
            1, int(concurrency or settings.WORKER_CONCURRENCY or DEFAULT_CONCURRENCY)
        )

    # -- grouping ----------------------------------------------------------

    @staticmethod
    def poll_key(watch) -> str:
        return f"{watch.source}:{watch.movie_id}:{watch.region_code or ''}"

    def group_watches(self, watches: Sequence) -> Dict[str, List]:
        grouped: Dict[str, List] = {}
        for watch in watches:
            grouped.setdefault(self.poll_key(watch), []).append(watch)
        return grouped

    @staticmethod
    def previous_state(value) -> AvailabilityState:
        """Parse a stored state, tolerating legacy/unknown values."""
        try:
            return AvailabilityState(str(value or "").upper())
        except ValueError:
            return AvailabilityState.UNKNOWN

    @staticmethod
    def scoped_shows(watch, shows: List[Show]) -> List[Show]:
        """Apply one watch's theatre / date / time preferences to the source response."""
        raw_theatres = getattr(watch, "theatre_ids", None) or getattr(watch, "theatres", None) or []
        selected = [
            t
            for t in raw_theatres
            if str(t or "").strip().upper() not in ANY_THEATRE_TOKENS
        ]
        scoped = list(shows)
        if selected:
            wanted = set(selected)
            scoped = [s for s in scoped if s.theatre_id in wanted or s.theatre_name in wanted]
        date_filter = getattr(watch, "date_filter", None) or ["all"]
        scoped = filter_shows_by_date(scoped, list(date_filter))
        after_time = getattr(watch, "after_time", "") or ""
        before_time = getattr(watch, "before_time", "") or ""
        scoped = filter_shows_by_time(scoped, after_time, before_time)

        # Format filter
        wanted_formats = [str(f).strip().lower() for f in (getattr(watch, "formats", None) or []) if str(f).strip()]
        if wanted_formats and "any" not in wanted_formats:
            scoped = [
                s for s in scoped
                if any(wf in (s.screen_format or "").lower() for wf in wanted_formats)
            ]
        return scoped

    # -- cycle -------------------------------------------------------------

    async def run_cycle(self) -> int:
        """Poll every active watch once using adaptive scheduling tiers."""
        start_time = time.time()
        now_utc = datetime.now(timezone.utc)
        active_watches = await self.repo.get_active_watches()
        if not active_watches:
            logger.info("No active watches to poll.")
            WebWorker.last_cycle_at = time.time()
            WebWorker.last_cycle_duration = round(time.time() - start_time, 2)
            WebWorker.last_cycle_keys_count = 0
            WebWorker.surge_active = False
            return 0

        # Retire watches whose explicit date filter has passed (N8).
        unexpired_watches = []
        for w in active_watches:
            df = getattr(w, "date_filter", None) or []
            if is_watch_expired(df):
                await self.expire_stale_watch(w)
            else:
                unexpired_watches.append(w)

        if not unexpired_watches:
            logger.info("All active watches were stale/expired and retired.")
            WebWorker.last_cycle_at = time.time()
            WebWorker.last_cycle_duration = round(time.time() - start_time, 2)
            WebWorker.last_cycle_keys_count = 0
            WebWorker.surge_active = False
            return 0

        grouped = self.group_watches(unexpired_watches)

        # Adaptive Smart Polling Filter:
        # Only poll source if at least one watch in the group is due for checking
        due_groups: Dict[str, List] = {}
        for key, watches in grouped.items():
            if any(is_watch_due_for_poll(w, now_utc) for w in watches):
                due_groups[key] = watches

        if not due_groups:
            logger.info(
                "Adaptive scheduler: All %d watch(es) in future release tiers are resting. Skipping cycle.",
                len(unexpired_watches),
            )
            WebWorker.last_cycle_at = time.time()
            WebWorker.last_cycle_duration = round(time.time() - start_time, 2)
            WebWorker.last_cycle_keys_count = 0
            WebWorker.surge_active = False
            return 0

        logger.info(
            "Adaptive scheduler: Polling %d due group(s) (%d total active watches)...",
            len(due_groups),
            len(unexpired_watches),
        )

        semaphore = asyncio.Semaphore(self.concurrency)

        async def guarded(key: str, watches: List) -> None:
            async with semaphore:
                await self.poll_group(key, watches)

        results = await asyncio.gather(
            *(guarded(key, watches) for key, watches in due_groups.items()),
            return_exceptions=True,
        )
        for key, result in zip(due_groups, results):
            if isinstance(result, Exception):
                logger.error("Poll key %s crashed: %s: %s", key, type(result).__name__, result)

        duration = round(time.time() - start_time, 2)
        WebWorker.last_cycle_at = time.time()
        WebWorker.last_cycle_duration = duration
        WebWorker.last_cycle_keys_count = len(due_groups)

        # Dynamic surge detection: if any watch is now AVAILABLE, speed up next cycle
        WebWorker.surge_active = any(getattr(w, "status", "") == "AVAILABLE" for w in unexpired_watches)
        logger.info(
            "Worker cycle completed in %.2fs (%d poll keys polled). Surge active: %s",
            duration,
            len(due_groups),
            WebWorker.surge_active,
        )
        return len(due_groups)

    async def _log_system(self, watch: Any, message: str, status_str: str) -> None:
        """Record a system-level event (expiry, outage) against a watch."""
        await self.repo.log_alert(
            watch_id=getattr(watch, "id", 0),
            user_uid=getattr(watch, "user_uid", ""),
            channel="system",
            message=message,
            status_str=status_str,
        )

    async def expire_stale_watch(self, watch: Any) -> None:
        """Deactivate a watch whose chosen calendar date has passed and notify user (N8)."""
        wid = getattr(watch, "id", 0)
        title = getattr(watch, "movie_title", "Movie")
        city = getattr(watch, "city", "")
        logger.info("Retiring expired watch #%s (%s in %s) due to passed date filter.", wid, title, city)
        await self.repo.expire_watch(wid)

        user = await self.repo.get_user(getattr(watch, "user_uid", ""))
        text = notifications.render_expired_text(watch)
        html = notifications.render_expired_html(watch)
        await notifications.deliver_custom_async(user, f"⌛ Watch ended: {title}", text, html)
        await self._log_system(watch, text, "EXPIRED")

    async def poll_group(self, key: str, watches: List) -> None:
        """Fetch once for the poll key and evaluate every watch under it."""
        lead = watches[0]
        movie = resolved_movie_for_watch(lead)
        source_val = lead.source or "bookmyshow"
        movie_id_val = lead.movie_id or ""
        region_code_val = lead.region_code or ""

        try:
            shows = await asyncio.to_thread(self.resolver.fetch_shows, movie, movie.region)
        except TemporaryIssue as exc:
            # Cloudflare or anti-bot challenge (N5/N6 failure escalation)
            logger.warning("SOURCE ISSUE for %s: %s", key, exc)
            await self._handle_poll_failure(key, source_val, movie_id_val, region_code_val, str(exc), watches)
            return
        except Exception as exc:
            logger.error("Failed to fetch shows for %s: %s: %s", key, type(exc).__name__, exc)
            await self._handle_poll_failure(key, source_val, movie_id_val, region_code_val, str(exc), watches)
            return

        # On successful fetch, reset failure counter (N7) and record healthy status
        was_alerted, prev_fails = await self.repo.record_poll_success(
            key, source_val, movie_id_val, region_code_val
        )
        if was_alerted:
            logger.info("N7 RECOVERY: Poll key %s recovered after %d failed cycles!", key, prev_fails)

        # District cinema harvesting: cache any seen cinema into district_cinemas
        if movie.source is Source.DISTRICT and shows:
            discovered = [
                {
                    "cinema_id": s.theatre_id,
                    "cinema_name": s.theatre_name,
                    "address": getattr(s, "address", "") or "",
                    "city_key": movie.region.slug or lead.city,
                }
                for s in shows
                if s.theatre_id and s.theatre_name
            ]
            if discovered:
                await self.repo.upsert_district_cinemas(discovered)

        logger.info(
            "Fetched %d show(s) for %s (%s / %s).",
            len(shows),
            key,
            movie.source.value,
            movie.region.code or movie.region.slug,
        )
        for watch in watches:
            await self.evaluate(watch, shows)

    async def _handle_poll_failure(
        self, key: str, source: str, movie_id: str, region_code: str, error: str, watches: List
    ) -> None:
        fail_count, should_alert_admin, should_alert_users = await self.repo.record_poll_failure(
            key, source, movie_id, region_code, error
        )
        if should_alert_admin:
            logger.warning("N5 ADMIN ALERT: 1st failure for poll key %s: %s", key, error)

        if should_alert_users:
            logger.warning("N6 USER OUTAGE: Poll key %s failed sustained %d times. Notifying users...", key, fail_count)
            for watch in watches:
                user = await self.repo.get_user(getattr(watch, "user_uid", ""))
                text = notifications.render_outage_text(watch)
                html = notifications.render_outage_html(watch)
                await notifications.deliver_custom_async(user, f"⚠️ Monitoring issue: {watch.movie_title}", text, html)
                await self._log_system(watch, text, "OUTAGE_NOTICE")

    async def evaluate(self, watch, shows: List[Show]) -> AvailabilityState:
        """Update one watch from an observation and alert on transitions (N1, N3, N4)."""
        scoped = self.scoped_shows(watch, shows)
        available = [s for s in scoped if s.available]

        previous = self.previous_state(getattr(watch, "status", None) or getattr(watch, "state", None))
        current = infer_state(bool(available))

        notified = False
        notify_error = None
        state_to_save = current.value

        wid = getattr(watch, "id", "?")
        movie_title = getattr(watch, "movie_title", "Movie")
        city = getattr(watch, "city", "")
        notified_at = getattr(watch, "notified_at", None)

        current_attempts = getattr(watch, "notify_attempts", 0) or 0
        is_retry = (
            current == AvailabilityState.AVAILABLE
            and current_attempts > 0
            and current_attempts < 5
            and not notified_at
        )

        should_fire_n1 = should_notify(previous, current) or is_retry

        # N4: Back in Stock detection (was UNAVAILABLE, now AVAILABLE, was already alerted in past)
        should_fire_n4 = (
            previous == AvailabilityState.UNAVAILABLE
            and current == AvailabilityState.AVAILABLE
            and notified_at is not None
            and getattr(watch, "notify_back", True)
        )

        # N3: New Show detection (already AVAILABLE or notified, watch wants new show alerts)
        should_fire_n3 = False
        new_shows: List[Show] = []
        if (
            current == AvailabilityState.AVAILABLE
            and not should_fire_n1
            and not should_fire_n4
            and getattr(watch, "notify_new_shows", True)
        ):
            last_shows_raw = getattr(watch, "last_shows", []) or []
            known_identities = {
                (str(item.get("theatre_id", "")), str(item.get("show_id") or item.get("show_time", "")))
                for item in last_shows_raw
                if isinstance(item, dict)
            }
            if known_identities:
                new_shows = [
                    s for s in available
                    if (str(s.theatre_id), str(s.show_id or s.show_time)) not in known_identities
                ]
                if new_shows:
                    should_fire_n3 = True

        # Process alerts based on priority: N1 > N4 > N3
        current_snapshot = shows_snapshot(available)

        if should_fire_n1:
            logger.info(
                "WATCH FIRED (N1)! %s in %s is AVAILABLE (%d show(s)); watch #%s",
                movie_title, city, len(available), wid
            )
            notified, notify_error = await self.notify(watch, available)
        elif should_fire_n4:
            logger.info(
                "WATCH FIRED (N4 - BACK IN STOCK)! %s in %s; watch #%s",
                movie_title, city, wid
            )
            notified, notify_error = await self.notify_back_in_stock(watch, available)
        elif should_fire_n3:
            logger.info(
                "WATCH FIRED (N3 - NEW SHOWS)! %s in %s (%d new screening(s)); watch #%s",
                movie_title, city, len(new_shows), wid
            )
            notified, notify_error = await self.notify_new_shows(watch, new_shows)

        await self.repo.mark_watch_checked(
            wid,
            state_to_save,
            notified=notified,
            notify_error=notify_error if (not notified and (should_fire_n1 or should_fire_n4)) else None,
            reset_attempts=current != AvailabilityState.AVAILABLE,
            last_shows=current_snapshot if available else getattr(watch, "last_shows", []),
        )
        return current

    async def _dispatch(
        self,
        watch,
        *,
        subject: str,
        text: str,
        html: str,
        log_status: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Deliver one rendered alert to the watch owner and record each attempt.

        ``log_status`` overrides the recorded status; when omitted the actual
        delivery status (SENT/FAILED) is logged.
        """
        user_uid = getattr(watch, "user_uid", None) or getattr(watch, "uid", "")
        wid = getattr(watch, "id", 0)
        user = await self.repo.get_user(user_uid)
        results = await notifications.deliver_custom_async(user, subject, text, html)

        for result in results:
            if result["status"] == notifications.SKIPPED:
                continue
            await self.repo.log_alert(
                watch_id=wid,
                user_uid=user_uid,
                channel=result["channel"],
                message=text,
                status_str=log_status or result["status"].upper(),
            )

        delivered = any(r["status"] == notifications.SENT for r in results)
        summary = notifications.summarize(results)
        return delivered, summary if not delivered else None

    async def notify(self, watch, available: List[Show]) -> Tuple[bool, Optional[str]]:
        """Dispatch N1 alert on configured channels."""
        title = getattr(watch, "movie_title", "Movie")
        return await self._dispatch(
            watch,
            subject=f"🚨 Tickets open: {title}",
            text=notifications.render_alert_text(watch, available),
            html=notifications.render_alert_html(watch, available),
        )

    async def notify_new_shows(self, watch, new_shows: List[Show]) -> Tuple[bool, Optional[str]]:
        """Dispatch N3 alert for newly spotted screenings."""
        title = getattr(watch, "movie_title", "Movie")
        return await self._dispatch(
            watch,
            subject=f"🆕 New screening spotted: {title}",
            text=notifications.render_new_shows_text(watch, new_shows),
            html=notifications.render_new_shows_html(watch, new_shows),
            log_status="NEW_SHOWS",
        )

    async def notify_back_in_stock(self, watch, shows: List[Show]) -> Tuple[bool, Optional[str]]:
        """Dispatch N4 alert for tickets returning to availability."""
        title = getattr(watch, "movie_title", "Movie")
        return await self._dispatch(
            watch,
            subject=f"🔁 Tickets back in stock: {title}",
            text=notifications.render_back_text(watch, shows),
            html=notifications.render_back_html(watch, shows),
            log_status="BACK_IN_STOCK",
        )

    # -- loop with dynamic surge -------------------------------------------

    async def start(self) -> None:
        logger.info(
            "Worker started. Base interval: %ds, Surge interval: %ds, Concurrency: %d.",
            DEFAULT_INTERVAL_SECONDS,
            SURGE_INTERVAL_SECONDS,
            self.concurrency,
        )
        while True:
            try:
                await self.run_cycle()
            except asyncio.CancelledError:
                logger.info("Worker stopped.")
                raise
            except Exception as exc:
                logger.error("Worker cycle error: %s: %s", type(exc).__name__, exc)

            # Adaptive surge sleep: 60s if any watch is active and available, else 180s
            sleep_duration = SURGE_INTERVAL_SECONDS if WebWorker.surge_active else (settings.POLL_INTERVAL_SECONDS or DEFAULT_INTERVAL_SECONDS)
            logger.debug("Sleeping for %d seconds before next cycle (Surge: %s)...", sleep_duration, WebWorker.surge_active)
            await asyncio.sleep(sleep_duration)


if __name__ == "__main__":
    worker = WebWorker()
    asyncio.run(worker.start())


