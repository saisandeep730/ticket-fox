from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.future import select
from sqlalchemy import update, delete, func
import datetime

from app.database.models import AsyncSessionLocal, Watch, User, AlertLog, DistrictCinema, PollState, BroadcastCampaign

class Repository:
    async def get_user_watches(self, user_uid: str) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            stmt = select(Watch).where(Watch.user_uid == user_uid).order_by(Watch.created_at.desc())
            result = await session.execute(stmt)
            watches = result.scalars().all()
            return [self._to_dict(w) for w in watches]

    async def find_existing_watch(self, user_uid: str, source: str, movie_id: str, city: str) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            stmt = select(Watch).where(
                Watch.user_uid == user_uid,
                Watch.source == source,
                Watch.movie_id == movie_id,
                Watch.city == city,
                Watch.is_active == True,
            )
            result = await session.execute(stmt)
            watch = result.scalar_one_or_none()
            return self._to_dict(watch) if watch else None

    async def get_active_watches(self) -> List[Watch]:
        async with AsyncSessionLocal() as session:
            stmt = select(Watch).where(Watch.is_active == True)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def create_watch(
        self,
        user_uid: str,
        movie_title: str,
        movie_id: str,
        source: str = "bookmyshow",
        city: str = "Hyderabad",
        theatres: List[str] = None,
        date_filter: List[str] = None,
        after_time: str = "",
        before_time: str = "",
        poster_url: str = "",
        movie_slug: str = "",
        region_code: str = "",
        region_name: str = "",
        formats: List[str] = None,
        max_price: Optional[int] = None,
        notify_new_shows: bool = True,
        notify_back: bool = True,
        release_date: str = "",
    ) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            watch = Watch(
                user_uid=user_uid,
                movie_title=movie_title,
                movie_id=movie_id,
                movie_slug=movie_slug or "",
                poster_url=poster_url or "",
                source=source,
                city=city,
                region_code=region_code or "",
                region_name=region_name or city,
                theatre_ids=theatres or [],
                date_filter=date_filter or [],
                after_time=after_time,
                before_time=before_time,
                formats=formats or [],
                max_price=max_price,
                is_active=True,
                status="UNKNOWN",
                release_date=release_date or "",
                last_shows=[],
                notify_new_shows=notify_new_shows,
                notify_back=notify_back,
            )
            session.add(watch)
            await session.commit()
            await session.refresh(watch)
            return self._to_dict(watch)

    async def update_watch(self, user_uid: str, watch_id: Any, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            try:
                wid = int(watch_id)
            except ValueError:
                return None

            stmt = select(Watch).where(Watch.id == wid, Watch.user_uid == user_uid)
            result = await session.execute(stmt)
            watch = result.scalar_one_or_none()
            if not watch:
                return None

            for key, val in updates.items():
                if hasattr(watch, key) and val is not None:
                    setattr(watch, key, val)

            await session.commit()
            await session.refresh(watch)
            return self._to_dict(watch)

    async def delete_watch(self, user_uid: str, watch_id: Any) -> bool:
        async with AsyncSessionLocal() as session:
            try:
                wid = int(watch_id)
            except ValueError:
                return False

            stmt = delete(Watch).where(Watch.id == wid, Watch.user_uid == user_uid)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def batch_delete_watches(self, user_uid: str, watch_ids: List[Any]) -> int:
        """Delete multiple watches in a single transaction."""
        parsed_ids = []
        for raw in watch_ids:
            try:
                parsed_ids.append(int(raw))
            except (ValueError, TypeError):
                continue
        if not parsed_ids:
            return 0

        async with AsyncSessionLocal() as session:
            stmt = delete(Watch).where(Watch.id.in_(parsed_ids), Watch.user_uid == user_uid)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount

    async def expire_watch(self, watch_id: Any) -> bool:
        """Deactivate a watch whose explicit calendar date filter has passed (N8)."""
        now = datetime.datetime.now(datetime.timezone.utc)
        async with AsyncSessionLocal() as session:
            try:
                wid = int(watch_id)
            except (ValueError, TypeError):
                return False
            stmt = select(Watch).where(Watch.id == wid)
            result = await session.execute(stmt)
            watch = result.scalar_one_or_none()
            if not watch:
                return False
            watch.is_active = False
            watch.expired_at = now
            await session.commit()
            return True

    async def get_or_create_user(
        self,
        user_uid: str,
        email: str = None,
        name: str = None,
        picture: str = None,
    ) -> Dict[str, Any]:
        """Fetch the local profile, creating it on first login.

        Claim values from the Firebase token fill in what is missing (and
        ``last_login`` is always refreshed), so a Google sign-in populates the
        profile the settings screen reads instead of leaving it blank.
        """
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.uid == user_uid)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                user = User(uid=user_uid, email=email, name=name, picture=picture)
                session.add(user)
            else:
                if email and not user.email:
                    user.email = email
                if name and not user.name:
                    user.name = name
                if picture and not user.picture:
                    user.picture = picture
            user.last_login = datetime.datetime.now(datetime.timezone.utc)
            await session.commit()
            await session.refresh(user)
            return self._user_to_dict(user)

    async def get_user(self, user_uid: str) -> Optional[Dict[str, Any]]:
        """Read-only profile lookup (the worker must not create users)."""
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.uid == user_uid)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            return self._user_to_dict(user) if user else None

    async def update_user_profile(self, user_uid: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.uid == user_uid)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                user = User(uid=user_uid)
                session.add(user)

            for k, v in updates.items():
                if hasattr(user, k) and v is not None:
                    setattr(user, k, v)

            await session.commit()
            await session.refresh(user)
            return self._user_to_dict(user)

    async def get_watch(self, user_uid: str, watch_id: Any) -> Optional[Dict[str, Any]]:
        """One watch, scoped to its owner (used by the Test Alert endpoint)."""
        async with AsyncSessionLocal() as session:
            try:
                wid = int(watch_id)
            except (TypeError, ValueError):
                return None
            stmt = select(Watch).where(Watch.id == wid, Watch.user_uid == user_uid)
            result = await session.execute(stmt)
            watch = result.scalar_one_or_none()
            return self._to_dict(watch) if watch else None

    async def mark_watch_checked(
        self,
        watch_id: Any,
        state: str,
        *,
        notified: bool = False,
        notify_error: Optional[str] = None,
        reset_attempts: bool = False,
        last_shows: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Persist the outcome of one poll for a watch (state + timestamps + retry tracking).

        ``last_checked_at`` moves on every successful poll and ``notified_at``
        only when an alert actually went out, so the UI can tell "never checked"
        apart from "checked, nothing open yet".
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        async with AsyncSessionLocal() as session:
            stmt = select(Watch).where(Watch.id == int(watch_id))
            result = await session.execute(stmt)
            watch = result.scalar_one_or_none()
            if not watch:
                return
            watch.status = state
            watch.last_checked_at = now
            if last_shows is not None:
                watch.last_shows = last_shows
            if notified:
                watch.notified_at = now
                watch.notify_attempts = 0
                watch.notify_last_error = None
            elif notify_error:
                watch.notify_attempts = (getattr(watch, "notify_attempts", 0) or 0) + 1
                watch.notify_last_error = notify_error[:250]
            elif reset_attempts:
                watch.notify_attempts = 0
                watch.notify_last_error = None
            await session.commit()

    async def get_recent_alerts(self, user_uid: str, limit: int = 25) -> List[Dict[str, Any]]:
        """The alert history shown to a signed-in user (newest first)."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(AlertLog)
                .where(AlertLog.user_uid == user_uid)
                .order_by(AlertLog.created_at.desc(), AlertLog.id.desc())
                .limit(max(1, min(limit, 200)))
            )
            result = await session.execute(stmt)
            return [
                {
                    "id": log.id,
                    "watch_id": str(log.watch_id),
                    "channel": log.channel,
                    "message": log.message,
                    "status": log.status,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in result.scalars().all()
            ]

    async def log_alert(self, watch_id: Any, user_uid: str, channel: str, message: str, status_str: str = "SENT"):
        async with AsyncSessionLocal() as session:
            try:
                wid = int(watch_id)
            except Exception:
                wid = 0
            log = AlertLog(watch_id=wid, user_uid=user_uid, channel=channel, message=message, status=status_str)
            session.add(log)
            await session.commit()

    # -- District cinema caching -------------------------------------------

    async def upsert_district_cinemas(self, cinemas: List[Dict[str, str]]) -> None:
        if not cinemas:
            return
        now = datetime.datetime.now(datetime.timezone.utc)
        async with AsyncSessionLocal() as session:
            for c in cinemas:
                cid = str(c.get("cinema_id") or c.get("id") or "").strip()
                ckey = str(c.get("city_key") or "").lower().strip()
                cname = str(c.get("cinema_name") or c.get("name") or "").strip()
                caddr = str(c.get("address") or "").strip()
                if not (cid and cname):
                    continue
                stmt = select(DistrictCinema).where(DistrictCinema.cinema_id == cid)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                if existing:
                    existing.cinema_name = cname
                    if caddr:
                        existing.address = caddr
                    if ckey:
                        existing.city_key = ckey
                    existing.last_seen_at = now
                else:
                    session.add(
                        DistrictCinema(
                            cinema_id=cid,
                            city_key=ckey,
                            cinema_name=cname,
                            address=caddr,
                            discovered_at=now,
                            last_seen_at=now,
                        )
                    )
            await session.commit()

    async def list_district_cinemas(self, city_key: str) -> List[Dict[str, str]]:
        key = (city_key or "").lower().strip()
        async with AsyncSessionLocal() as session:
            stmt = select(DistrictCinema).where(DistrictCinema.city_key == key).order_by(DistrictCinema.cinema_name.asc())
            result = await session.execute(stmt)
            cinemas = result.scalars().all()
            return [
                {
                    "id": c.cinema_id,
                    "name": c.cinema_name,
                    "address": c.address or "",
                }
                for c in cinemas
            ]

    # -- Poll State & Failure Escalation (N5, N6, N7) ----------------------

    async def record_poll_failure(
        self, poll_key: str, source: str, movie_id: str, region_code: str, error: str
    ) -> Tuple[int, bool, bool]:
        """Record a cycle failure. Returns (fail_count, should_alert_admin_n5, should_alert_users_n6)."""
        now = datetime.datetime.now(datetime.timezone.utc)
        async with AsyncSessionLocal() as session:
            stmt = select(PollState).where(PollState.poll_key == poll_key)
            result = await session.execute(stmt)
            ps = result.scalar_one_or_none()
            if not ps:
                ps = PollState(
                    poll_key=poll_key,
                    source=source,
                    movie_id=movie_id,
                    region_code=region_code or "",
                    fail_count=1,
                    admin_alerted=True,
                    users_alerted=False,
                    last_error=error[:500],
                    updated_at=now,
                )
                session.add(ps)
                await session.commit()
                return 1, True, False

            ps.fail_count += 1
            ps.last_error = error[:500]
            ps.updated_at = now

            should_alert_admin = False
            if not ps.admin_alerted:
                ps.admin_alerted = True
                should_alert_admin = True

            should_alert_users = False
            if ps.fail_count >= 20 and not ps.users_alerted:
                ps.users_alerted = True
                should_alert_users = True

            await session.commit()
            return ps.fail_count, should_alert_admin, should_alert_users

    async def record_poll_success(
        self,
        poll_key: str,
        source: str = "",
        movie_id: str = "",
        region_code: str = "",
    ) -> Tuple[bool, int]:
        """Reset failure counter on success and record key as healthy."""
        now = datetime.datetime.now(datetime.timezone.utc)
        async with AsyncSessionLocal() as session:
            stmt = select(PollState).where(PollState.poll_key == poll_key)
            result = await session.execute(stmt)
            ps = result.scalar_one_or_none()
            if not ps:
                ps = PollState(
                    poll_key=poll_key,
                    source=source,
                    movie_id=movie_id,
                    region_code=region_code,
                    fail_count=0,
                    admin_alerted=False,
                    users_alerted=False,
                    last_error=None,
                    last_ok_at=now,
                    updated_at=now,
                )
                session.add(ps)
                await session.commit()
                return False, 0

            prev_fails = ps.fail_count
            was_alerted = ps.admin_alerted
            ps.fail_count = 0
            ps.admin_alerted = False
            ps.users_alerted = False
            ps.last_ok_at = now
            ps.updated_at = now
            if source:
                ps.source = source
            if movie_id:
                ps.movie_id = movie_id
            if region_code:
                ps.region_code = region_code
            await session.commit()
            return was_alerted, prev_fails

    async def get_all_poll_states(self) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            stmt = select(PollState).order_by(PollState.fail_count.desc(), PollState.updated_at.desc())
            result = await session.execute(stmt)
            return [
                {
                    "poll_key": ps.poll_key,
                    "source": ps.source,
                    "movie_id": ps.movie_id,
                    "region_code": ps.region_code,
                    "fail_count": ps.fail_count,
                    "admin_alerted": ps.admin_alerted,
                    "users_alerted": ps.users_alerted,
                    "last_error": ps.last_error,
                    "last_ok_at": ps.last_ok_at.isoformat() if ps.last_ok_at else None,
                    "updated_at": ps.updated_at.isoformat() if ps.updated_at else None,
                }
                for ps in result.scalars().all()
            ]

    # -- Broadcast Campaigns ------------------------------------------------

    async def create_broadcast(
        self, title: str, message: str, channels: List[str] = None, cta_text: str = "", cta_url: str = ""
    ) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            campaign = BroadcastCampaign(
                title=title,
                message=message,
                channels=channels or ["email"],
                cta_text=cta_text,
                cta_url=cta_url,
                status="draft",
            )
            session.add(campaign)
            await session.commit()
            await session.refresh(campaign)
            return {
                "id": campaign.id,
                "title": campaign.title,
                "message": campaign.message,
                "channels": campaign.channels,
                "cta_text": campaign.cta_text,
                "cta_url": campaign.cta_url,
                "status": campaign.status,
                "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
            }

    async def get_broadcasts(self, limit: int = 20) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            stmt = select(BroadcastCampaign).order_by(BroadcastCampaign.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            return [
                {
                    "id": c.id,
                    "title": c.title,
                    "message": c.message,
                    "channels": c.channels,
                    "cta_text": c.cta_text,
                    "cta_url": c.cta_url,
                    "status": c.status,
                    "total_recipients": c.total_recipients,
                    "sent_count": c.sent_count,
                    "failed_count": c.failed_count,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "sent_at": c.sent_at.isoformat() if c.sent_at else None,
                }
                for c in result.scalars().all()
            ]

    async def update_broadcast_status(
        self, campaign_id: int, status: str, sent_count: int, failed_count: int
    ) -> None:
        now = datetime.datetime.now(datetime.timezone.utc)
        async with AsyncSessionLocal() as session:
            stmt = select(BroadcastCampaign).where(BroadcastCampaign.id == campaign_id)
            result = await session.execute(stmt)
            c = result.scalar_one_or_none()
            if c:
                c.status = status
                c.sent_count = sent_count
                c.failed_count = failed_count
                if status == "sent":
                    c.sent_at = now
                await session.commit()

    # -- Admin Dashboard Metrics -------------------------------------------

    async def admin_stats(self) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            user_count = (await session.execute(select(func.count(User.uid)))).scalar() or 0
            watch_count = (await session.execute(select(func.count(Watch.id)))).scalar() or 0
            active_watches = (await session.execute(select(func.count(Watch.id)).where(Watch.is_active == True))).scalar() or 0
            alerts_sent = (await session.execute(select(func.count(AlertLog.id)))).scalar() or 0
            failing_keys = (await session.execute(select(func.count(PollState.poll_key)).where(PollState.fail_count > 0))).scalar() or 0
            cached_cinemas = (await session.execute(select(func.count(DistrictCinema.cinema_id)))).scalar() or 0

            return {
                "total_users": user_count,
                "total_watches": watch_count,
                "active_watches": active_watches,
                "total_alerts_sent": alerts_sent,
                "failing_poll_keys": failing_keys,
                "cached_district_cinemas": cached_cinemas,
            }

    async def admin_list_users(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            stmt = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
            result = await session.execute(stmt)
            users = result.scalars().all()

            user_dicts = []
            for u in users:
                w_count = (await session.execute(select(func.count(Watch.id)).where(Watch.user_uid == u.uid))).scalar() or 0
                ud = self._user_to_dict(u)
                ud["watch_count"] = w_count
                ud["created_at"] = u.created_at.isoformat() if u.created_at else None
                ud["last_login"] = u.last_login.isoformat() if u.last_login else None
                user_dicts.append(ud)
            return user_dicts

    async def admin_list_watches(
        self, limit: int = 50, offset: int = 0, status_filter: str = "all"
    ) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            stmt = select(Watch).order_by(Watch.created_at.desc())
            if status_filter == "active":
                stmt = stmt.where(Watch.is_active == True)
            elif status_filter == "available":
                stmt = stmt.where(Watch.status == "AVAILABLE")
            elif status_filter == "expired":
                stmt = stmt.where(Watch.expired_at.is_not(None))

            result = await session.execute(stmt.limit(limit).offset(offset))
            watches = result.scalars().all()

            user_uids = list({w.user_uid for w in watches if w.user_uid})
            users_map = {}
            if user_uids:
                u_res = await session.execute(select(User).where(User.uid.in_(user_uids)))
                for u in u_res.scalars().all():
                    users_map[u.uid] = {"email": u.email, "name": u.name}

            watch_dicts = []
            for w in watches:
                wd = self._to_dict(w)
                u_info = users_map.get(w.user_uid, {})
                wd["user_email"] = u_info.get("email") or ""
                wd["user_name"] = u_info.get("name") or ""
                watch_dicts.append(wd)
            return watch_dicts

    def _to_dict(self, w: Watch) -> Dict[str, Any]:
        return {
            "id": str(w.id),
            "user_uid": w.user_uid,
            "movie_id": w.movie_id,
            "movie_title": w.movie_title,
            "movie_slug": w.movie_slug or "",
            "poster_url": w.poster_url,
            "source": w.source,
            "city": w.city,
            "region_code": w.region_code or "",
            "region_name": w.region_name or w.city or "",
            "theatres": w.theatre_ids or [],
            "date_filter": w.date_filter or [],
            "after_time": w.after_time or "",
            "before_time": w.before_time or "",
            "formats": w.formats or [],
            "max_price": w.max_price,
            "is_active": w.is_active,
            "state": w.status or "UNKNOWN",
            "release_date": getattr(w, "release_date", "") or "",
            "last_shows": getattr(w, "last_shows", []) or [],
            "notify_new_shows": getattr(w, "notify_new_shows", True),
            "notify_back": getattr(w, "notify_back", True),
            "notify_attempts": getattr(w, "notify_attempts", 0) or 0,
            "notify_last_error": getattr(w, "notify_last_error", None),
            "notified_at": w.notified_at.isoformat() if w.notified_at else None,
            "expired_at": w.expired_at.isoformat() if getattr(w, "expired_at", None) else None,
            "last_checked_at": w.last_checked_at.isoformat() if w.last_checked_at else None,
            "created_at": w.created_at.isoformat() if w.created_at else None
        }

    def _user_to_dict(self, u: User) -> Dict[str, Any]:
        return {
            "id": u.uid,
            "uid": u.uid,
            "email": u.email,
            "name": u.name,
            "display_name": u.name or (u.email.split("@")[0] if u.email else "User"),
            "picture": u.picture,
            "phone": u.phone,
            "telegram_chat_id": u.telegram_chat_id,
            "whatsapp_number": u.whatsapp_number,
        }
