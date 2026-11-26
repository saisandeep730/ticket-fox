import datetime
import logging

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, inspect, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings

logger = logging.getLogger("ticket_fox_web.database")

Base = declarative_base()

def _utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


class User(Base):
    __tablename__ = "web_users"

    uid = Column(String, primary_key=True, index=True)
    email = Column(String, nullable=True)
    name = Column(String, nullable=True)
    picture = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    telegram_chat_id = Column(String, nullable=True)
    whatsapp_number = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utc_now)
    last_login = Column(DateTime, default=_utc_now)

class Watch(Base):
    __tablename__ = "web_watches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_uid = Column(String, index=True, nullable=False)
    movie_id = Column(String, nullable=False)
    movie_title = Column(String, nullable=False)
    # District addresses movies by slug ("the-paradise"); without it a stored
    # District watch can never be polled (the adapter raises "requires movie_slug").
    movie_slug = Column(String, default="")
    poster_url = Column(String, nullable=True)
    source = Column(String, nullable=False)
    city = Column(String, nullable=False)
    region_code = Column(String, default="")
    region_name = Column(String, default="")
    theatre_ids = Column(JSON, default=list)
    date_filter = Column(JSON, default=list)
    after_time = Column(String, default="")
    before_time = Column(String, default="")
    formats = Column(JSON, default=list)
    max_price = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    status = Column(String, default="UNKNOWN")
    release_date = Column(String, default="")
    last_shows = Column(JSON, default=list)
    notify_new_shows = Column(Boolean, default=True)
    notify_back = Column(Boolean, default=True)
    notified_at = Column(DateTime, nullable=True)
    expired_at = Column(DateTime, nullable=True)
    last_checked_at = Column(DateTime, nullable=True)
    notify_attempts = Column(Integer, default=0)
    notify_last_error = Column(String, nullable=True)
    created_at = Column(DateTime, default=_utc_now)

class AlertLog(Base):
    __tablename__ = "web_alert_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    watch_id = Column(Integer, index=True)
    user_uid = Column(String, index=True)
    channel = Column(String)
    message = Column(Text)
    status = Column(String)
    created_at = Column(DateTime, default=_utc_now)

class DistrictCinema(Base):
    __tablename__ = "district_cinemas"

    cinema_id = Column(String, primary_key=True)
    city_key = Column(String, index=True, nullable=False)
    cinema_name = Column(String, nullable=False)
    address = Column(String, default="")
    discovered_at = Column(DateTime, default=_utc_now)
    last_seen_at = Column(DateTime, default=_utc_now)

class PollState(Base):
    __tablename__ = "web_poll_state"

    poll_key = Column(String, primary_key=True)  # source:movie_id:region_code
    source = Column(String, nullable=False)
    movie_id = Column(String, nullable=False)
    region_code = Column(String, default="")
    fail_count = Column(Integer, default=0)
    admin_alerted = Column(Boolean, default=False)
    users_alerted = Column(Boolean, default=False)
    last_error = Column(Text, nullable=True)
    last_ok_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=_utc_now)

class BroadcastCampaign(Base):
    __tablename__ = "web_broadcast_campaigns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    channels = Column(JSON, default=list)
    cta_text = Column(String, default="")
    cta_url = Column(String, default="")
    status = Column(String, default="draft")
    total_recipients = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utc_now)
    sent_at = Column(DateTime, nullable=True)

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

#: Columns added after the first release. ``create_all`` only creates *missing
#: tables*, so an existing database keeps its old shape. Each one is added with
#: a plain ALTER TABLE when absent.
_ADDED_COLUMNS = (
    ("movie_slug", "VARCHAR"),
    ("region_name", "VARCHAR"),
    ("formats", "TEXT"),
    ("max_price", "INTEGER"),
    ("notify_attempts", "INTEGER DEFAULT 0"),
    ("notify_last_error", "VARCHAR"),
    ("last_shows", "TEXT"),
    ("notify_new_shows", "BOOLEAN DEFAULT TRUE"),
    ("notify_back", "BOOLEAN DEFAULT TRUE"),
    ("expired_at", "TIMESTAMP"),
    ("release_date", "VARCHAR"),
)


def _upgrade_schema(conn) -> None:
    """Bring an existing ``web_watches`` table up to the current column set.

    Failures are not swallowed: a column that cannot be added means the process
    would run against a schema it cannot write to, so startup should stop here.
    """
    inspector = inspect(conn)
    if "web_watches" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("web_watches")}
    for name, ddl_type in _ADDED_COLUMNS:
        if name in existing:
            continue
        logger.info("Adding missing column web_watches.%s", name)
        conn.execute(text(f"ALTER TABLE web_watches ADD COLUMN {name} {ddl_type}"))


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_upgrade_schema)
