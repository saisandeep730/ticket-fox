from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import asyncio
import logging
import re

from app import auth_emails, notifications, tmdb, whatsapp
from app.auth import get_current_user, get_current_user_id
from app.config import settings
from app.database.models import init_db
from app.database.repository import Repository
from app.engine import cities
from app.engine.models import Region, Source, Show
from app.engine.showtime import parse_show_time
from app.engine.sources.catalog import MovieCatalog
from app.engine.sources.resolver import (
    LiveMovieResolver,
    ResolvedMovie,
    region_for_city,
    slug_from_title,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ticket_fox_web.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info(
        "Alert transports: email=%s whatsapp=%s",
        notifications.channel_available("email"),
        notifications.channel_available("whatsapp"),
    )
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# CORS: `allow_origins=["*"]` together with credentials is rejected by browsers,
# and the documented CORS_ORIGINS setting was never read. Use the configured
# origin list (a literal "*" still works when an operator asks for it).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

repo = Repository()
catalog = MovieCatalog()
resolver = LiveMovieResolver()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class WatchCreate(BaseModel):
    movie_title: str
    movie_id: str
    source: str = "bookmyshow"
    city: str = "Hyderabad"
    theatres: List[str] = []
    date_filter: List[str] = []
    after_time: str = ""
    before_time: str = ""
    poster_url: str = ""
    movie_slug: str = ""
    region_code: str = ""
    formats: List[str] = []
    max_price: Optional[int] = None
    notify_new_shows: bool = True
    notify_back: bool = True
    release_date: Optional[str] = ""
    whatsapp_number: Optional[str] = None


class WatchUpdate(BaseModel):
    is_active: Optional[bool] = None
    date_filter: Optional[List[str]] = None
    after_time: Optional[str] = None
    before_time: Optional[str] = None
    notify_new_shows: Optional[bool] = None
    notify_back: Optional[bool] = None


class BatchDeleteRequest(BaseModel):
    watch_ids: List[int]


class BroadcastCreateRequest(BaseModel):
    title: str
    message: str
    channels: List[str] = ["email"]
    cta_text: str = ""
    cta_url: str = ""


class UserProfileUpdate(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    whatsapp_number: Optional[str] = None


class AuthEmailRequest(BaseModel):
    email: str


# ---------------------------------------------------------------------------
# Branded auth emails (Firebase action link + Resend delivery)
# ---------------------------------------------------------------------------

#: Minimum seconds between two auth emails to the same address. Firebase also
#: rate-limits link minting per address, so this keeps us well inside its budget
#: and stops the endpoint being used to spray a victim's inbox.
AUTH_EMAIL_COOLDOWN_SECONDS = 60

#: address -> monotonic timestamp of the last accepted request.
_auth_email_last_sent: Dict[str, float] = {}


def _auth_email_throttled(email: str) -> bool:
    """True when this address was emailed too recently. Records the attempt."""
    import time

    key = email.lower()
    now = time.monotonic()
    last = _auth_email_last_sent.get(key)
    if last is not None and now - last < AUTH_EMAIL_COOLDOWN_SECONDS:
        return True
    _auth_email_last_sent[key] = now
    # Keep the map from growing without bound on a long-lived process.
    if len(_auth_email_last_sent) > 5000:
        cutoff = now - AUTH_EMAIL_COOLDOWN_SECONDS
        for stale in [k for k, v in _auth_email_last_sent.items() if v < cutoff]:
            _auth_email_last_sent.pop(stale, None)
    return False


@app.post("/api/auth/password-reset")
async def request_password_reset(data: AuthEmailRequest):
    """Email a branded password-reset link (Firebase oobCode, delivered by Resend)."""
    email = (data.email or "").strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email address is required")
    if not settings.AUTH_EMAIL_ENABLED:
        raise HTTPException(status_code=503, detail="Auth emails are disabled on this server")
    if _auth_email_throttled(email):
        # Same shape as success so the response never reveals account existence.
        return {"ok": True, "detail": "sent"}

    ok, detail = await asyncio.to_thread(auth_emails.send_password_reset, email)
    if not ok and detail == "user-not-found":
        # Never reveal whether an account exists for this address.
        return {"ok": True, "detail": "sent"}
    if not ok:
        logger.warning("password reset email to %s failed: %s", email, detail)
        raise HTTPException(
            status_code=502, detail="Could not send the reset email. Please try again."
        )
    return {"ok": True, "detail": "sent"}


@app.post("/api/auth/verify-email")
async def request_email_verification(data: AuthEmailRequest):
    """Email a branded email-verification link (Firebase oobCode, delivered by Resend)."""
    email = (data.email or "").strip()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email address is required")
    if not settings.AUTH_EMAIL_ENABLED:
        raise HTTPException(status_code=503, detail="Auth emails are disabled on this server")
    if _auth_email_throttled(email):
        return {"ok": True, "detail": "sent"}

    ok, detail = await asyncio.to_thread(auth_emails.send_email_verification, email)
    if not ok and detail == "user-not-found":
        return {"ok": True, "detail": "sent"}
    if not ok:
        logger.warning("verification email to %s failed: %s", email, detail)
        raise HTTPException(
            status_code=502, detail="Could not send the verification email. Please try again."
        )
    return {"ok": True, "detail": "sent"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SOURCE_ALIASES = {
    "bookmyshow": Source.BOOKMYSHOW,
    "bms": Source.BOOKMYSHOW,
    "book_my_show": Source.BOOKMYSHOW,
    "district": Source.DISTRICT,
    "district.in": Source.DISTRICT,
}


def normalize_source(value: Any) -> Source:
    """Map any client spelling of a source to the engine enum."""
    key = str(value or "").strip().lower()
    source = SOURCE_ALIASES.get(key)
    if source is None:
        raise HTTPException(status_code=400, detail=f"Unsupported source: {value!r}")
    return source


def movie_to_dict(movie) -> Dict[str, Any]:
    """Serialize an engine ``MovieSearchResult`` for the web client."""
    return {
        "id": movie.movie_id,
        "title": movie.movie_name,
        "movie_slug": movie.movie_slug,
        "source": movie.source.value,
        "poster_url": movie.poster_url,
        "release_date": movie.release_date,
        "likes_count": movie.interest,
        "url": movie.url,
        "both_sources": movie.both_sources,
        "alt_source": movie.alt_source.value if movie.alt_source else None,
        "alt_movie_id": movie.alt_movie_id,
    }


def resolved_from_request(
    movie_id: str,
    movie_slug: str,
    movie_name: str,
    source: Source,
    city: str,
    region_code: str = "",
) -> ResolvedMovie:
    """Build the ``ResolvedMovie`` the theatre lookup needs from query params."""
    if source is Source.DISTRICT and not movie_slug:
        # District addresses movies by slug; fall back to the harvested catalog.
        item = catalog.get_by_id(source, movie_id)
        if item:
            movie_slug = item.movie_slug
            movie_name = movie_name or item.movie_name
    return ResolvedMovie(
        source=source,
        movie_id=movie_id,
        movie_slug=movie_slug or "",
        movie_name=movie_name or movie_id,
        region=region_for_city(source, city, region_code),
        city_from_url=False,
    )


def sample_shows(watch: Dict[str, Any], source: Source) -> List[Show]:
    """A believable show list for the Test Drill.

    The drill proves *delivery*, so it must not depend on the live source (which
    may be blocked at that moment) — the sample mirrors a real alert instead.
    """
    evening = parse_show_time("19:30")
    night = parse_show_time("22:15")
    booking_url = (
        "https://www.district.in/movies"
        if source is Source.DISTRICT
        else "https://in.bookmyshow.com"
    )
    common = {
        "source": source,
        "movie_id": watch.get("movie_id", ""),
        "movie_name": watch.get("movie_title", "Sample Movie"),
        "theatre_id": "TEST-DRILL",
        "theatre_name": "Sample Cinema — Nexus Mall",
        "booking_url": booking_url,
        "available": True,
    }
    shows = [
        {
            "show_id": "TEST-1",
            "show_time": evening.strftime("%Y-%m-%dT%H:%M") if evening else "19:30",
            "screen_format": "2D",
        },
        {
            "show_id": "TEST-2",
            "show_time": night.strftime("%Y-%m-%dT%H:%M") if night else "22:15",
            "screen_format": "IMAX",
        },
    ]
    return [Show(**common, **show) for show in shows]


async def dispatch_test_alert(user_id: str, watch: Dict[str, Any], source: Source) -> Dict[str, Any]:
    """Deliver a drill over the user's channels, log it, and describe the outcome."""
    user = await repo.get_user(user_id)
    shows = sample_shows(watch, source)
    results = await notifications.deliver_async(user, watch, shows, test=True)

    for result in results:
        if result["status"] == notifications.SKIPPED:
            continue
        await repo.log_alert(
            watch_id=watch.get("id", 0),
            user_uid=user_id,
            channel=result["channel"],
            message="[TEST DRILL] " + notifications.render_alert_text(watch, shows, test=True),
            status_str=result["status"].upper(),
        )

    delivered = any(r["status"] == notifications.SENT for r in results)
    return {
        "status": "success" if delivered else "failed",
        "delivered": delivered,
        "results": results,
        "message": notifications.summarize(results),
    }


async def run_test_drill(user_id: str, watch: Dict[str, Any], source: Source) -> Dict[str, Any]:
    """Deliver a drill and turn a non-delivery into a 502 for the caller."""
    outcome = await dispatch_test_alert(user_id, watch, source)
    if not outcome["delivered"]:
        raise HTTPException(status_code=502, detail=outcome["message"])
    return outcome


def _watch_fields(
    data: "WatchCreate",
    *,
    source: Source,
    movie_id: str,
    movie_slug: str,
    region: Region,
    theatres: List[str],
) -> Dict[str, Any]:
    """The repository kwargs for one watch, shared by single- and dual-platform creation."""
    return {
        "movie_title": data.movie_title.strip(),
        "movie_id": movie_id.strip(),
        "source": source.value,
        "city": data.city,
        "theatres": theatres,
        "date_filter": data.date_filter,
        "after_time": data.after_time,
        "before_time": data.before_time,
        "poster_url": data.poster_url,
        "movie_slug": movie_slug,
        "region_code": data.region_code or region.code,
        "region_name": region.name or data.city,
        "formats": data.formats,
        "max_price": data.max_price,
        "notify_new_shows": data.notify_new_shows,
        "notify_back": data.notify_back,
        "release_date": data.release_date or "",
    }


async def _create_dual_watch(data: "WatchCreate", user_id: str) -> Dict[str, Any]:
    """Create a primary watch plus a companion watch on the other platform."""
    is_district_primary = (
        data.movie_id.isdigit()
        or data.movie_id.startswith("MV")
        or "district" in (data.movie_slug or "").lower()
    )
    p_source = Source.DISTRICT if is_district_primary else Source.BOOKMYSHOW
    s_source = Source.BOOKMYSHOW if is_district_primary else Source.DISTRICT

    s_id = ""
    s_slug = ""
    for hit in catalog.search(data.movie_title):
        if hit.source == s_source:
            s_id, s_slug = hit.movie_id, hit.movie_slug
            break
        if hit.both_sources and hit.alt_source == s_source:
            s_id = hit.alt_movie_id
            break

    p_slug = data.movie_slug or (
        slug_from_title(data.movie_title) if p_source is Source.DISTRICT else ""
    )
    watch1 = await repo.create_watch(
        user_uid=user_id,
        **_watch_fields(
            data,
            source=p_source,
            movie_id=data.movie_id,
            movie_slug=p_slug,
            region=region_for_city(p_source, data.city, data.region_code),
            theatres=data.theatres,
        ),
    )

    watch2 = None
    if s_id and not await repo.find_existing_watch(user_id, s_source.value, s_id, data.city):
        watch2 = await repo.create_watch(
            user_uid=user_id,
            **_watch_fields(
                data,
                source=s_source,
                movie_id=s_id,
                movie_slug=s_slug
                or (slug_from_title(data.movie_title) if s_source is Source.DISTRICT else ""),
                region=region_for_city(s_source, data.city),
                theatres=[],
            ),
        )

    return {"watch": watch1, "secondary_watch": watch2, "dual_source": True}


@app.get("/health")
@app.get("/api/health")
async def health():
    from app.worker import WebWorker
    from app.auth import firebase_app
    from fastapi.responses import JSONResponse

    db_status = "connected"
    active_watches_count = 0
    is_healthy = True
    try:
        active_watches = await repo.get_active_watches()
        active_watches_count = len(active_watches)
    except Exception as exc:
        logger.error("Health check database probe failed: %s", exc)
        db_status = f"disconnected: {type(exc).__name__}"
        is_healthy = False

    db_driver = "postgresql" if "postgresql" in settings.DATABASE_URL else "sqlite"
    db_warning = None
    if db_driver == "sqlite" and not settings.DEBUG:
        db_warning = "Using local SQLite in non-debug environment; ephemeral hosting will lose data on restart. Configure hosted PostgreSQL."

    content = {
        "status": "ok" if is_healthy else "degraded",
        "app": settings.APP_NAME,
        "database": {
            "status": db_status,
            "engine": db_driver,
            "warning": db_warning,
        },
        "auth_mode": "firebase_admin" if firebase_app else ("mock" if settings.ALLOW_MOCK_AUTH else "unconfigured"),
        "channels": notifications.channel_status(),
        "worker": {
            "enabled": settings.WORKER_ENABLED,
            "poll_interval_seconds": settings.POLL_INTERVAL_SECONDS,
            "active_watches_count": active_watches_count,
            "last_cycle_at": WebWorker.last_cycle_at,
            "last_cycle_duration_seconds": WebWorker.last_cycle_duration,
            "last_cycle_keys_count": WebWorker.last_cycle_keys_count,
        },
    }
    if not is_healthy:
        return JSONResponse(status_code=503, content=content)
    return content


@app.get("/api/channels")
async def get_channels():
    """Which alert transports this deployment can actually deliver on.

    WhatsApp is probed for a live session (cached for 60s) so an unlinked
    gateway no longer reports "Ready"; the probe runs in a thread because the
    gateway client is synchronous.
    """
    channels = notifications.channel_status()
    if channels.get("whatsapp"):
        channels["whatsapp"] = await asyncio.to_thread(notifications.channel_ready, "whatsapp")
    return {"channels": channels}


@app.get("/api/cities")
async def get_cities():
    """The canonical city catalog, so the frontend never keeps its own copy."""
    return {"cities": [{"key": c.key, "name": c.name} for c in cities.CITIES]}


@app.get("/api/catalog")
async def get_catalog(
    city: str = Query("Hyderabad"),
    sort_by: str = Query("date"),
    limit: int = Query(60, ge=1, le=120),
):
    """Homepage movies for a city: upcoming movies and movies released within the last 3 days."""
    city_key = cities.city_key_from_name(city) or city.strip().lower() or "hyderabad"
    try:
        movies = await asyncio.to_thread(catalog.upcoming, city_key, limit, None, sort_by)
        return {"movies": [movie_to_dict(m) for m in movies], "city": city}
    except Exception as exc:
        logger.warning("Catalog harvest failed for %s: %s: %s", city, type(exc).__name__, exc)
        return {"movies": [], "city": city, "error": str(exc)}


@app.get("/api/tmdb")
async def proxy_tmdb(path: str = Query(...), language: str = Query("en-US")):
    """Read-only TMDB proxy so the API key never reaches the browser."""
    params = {"language": language} if language else {}
    body = await asyncio.to_thread(tmdb.proxy, path, params)
    if body is None:
        return {"results": []}
    return body


@app.get("/api/movie/info")
async def get_movie_info(
    title: str = Query(...),
    movie_id: str = Query(""),
    poster_url: str = Query(""),
):
    """Fetch exact TMDB metadata if and only if the exact movie title matches.

    If the exact movie is not available on TMDB, does NOT use TMDB or pick random alternatives.
    Instead, uses authentic BookMyShow/District data.
    """
    import re

    active_watches = await repo.get_active_watches()
    matching = [
        w for w in active_watches
        if title.lower() in (w.movie_title or "").lower() or (movie_id and w.movie_id == movie_id)
    ]
    real_watch_count = len(matching)

    final_poster = poster_url
    if not final_poster and movie_id:
        cached_m = catalog.get_by_id(Source.BOOKMYSHOW, movie_id) or catalog.get_by_id(Source.DISTRICT, movie_id)
        if cached_m and cached_m.poster_url:
            final_poster = cached_m.poster_url
    if not final_poster:
        for m in getattr(catalog, "_all_city_movies", []):
            if m.movie_id == movie_id or m.movie_name.lower() == title.lower():
                if m.poster_url:
                    final_poster = m.poster_url
                    break

    # Strip a trailing bracket and any format/language tag so "Dune 2 (IMAX 3D)"
    # matches the TMDB title "Dune: Part Two"'s plain form.
    clean_title = re.sub(r"\s*[\(\[\{].*?$", "", title).strip()
    clean_title = re.sub(
        r"\s*\b(3d|2d|imax|4dx|telugu|hindi|tamil|kannada|malayalam)\b.*$",
        "",
        clean_title,
        flags=re.IGNORECASE,
    ).strip()
    if not clean_title:
        clean_title = title

    movie_data = {
        "title": title,
        "clean_title": clean_title,
        "overview": f"Track ticket availability for {title} on BookMyShow & District. Get instant alerts on WhatsApp & Email when bookings open.",
        "release_date": "Upcoming",
        "poster_url": final_poster,
        "backdrop_url": final_poster,
        "rating": None,
        "vote_count": 0,
        "runtime": "",
        "genres": ["Cinema"],
        "director": "",
        "writers": [],
        "cast": [],
        "trailer_key": "",
        "active_watch_count": real_watch_count,
        "demand_level": "⚡ LIVE WATCHING" if real_watch_count > 0 else "ACTIVE TRACKING",
        "is_tmdb_matched": False,
    }

    try:
        res = await asyncio.to_thread(tmdb.movie_info, title, clean_title)
        if res:
            movie_data["is_tmdb_matched"] = True
            if res.get("poster_path"):
                movie_data["poster_url"] = tmdb.image_url(res["poster_path"], "w500")
            if res.get("backdrop_path"):
                movie_data["backdrop_url"] = tmdb.image_url(res["backdrop_path"], "w1280")
            if res.get("overview"):
                movie_data["overview"] = res["overview"]
            if res.get("release_date"):
                movie_data["release_date"] = res["release_date"]
            if res.get("vote_average"):
                movie_data["rating"] = round(res["vote_average"], 1)
            if res.get("vote_count"):
                movie_data["vote_count"] = res["vote_count"]
            if res.get("runtime"):
                r_min = res["runtime"]
                movie_data["runtime"] = f"{r_min // 60}h {r_min % 60}m" if r_min >= 60 else f"{r_min}m"
            if res.get("genres"):
                movie_data["genres"] = [g["name"] for g in res["genres"]]
            if res.get("title"):
                movie_data["title"] = res["title"]

            credits = res.get("credits", {})
            crew = credits.get("crew", [])
            directors = [c["name"] for c in crew if c.get("job") == "Director"]
            writers = [c["name"] for c in crew if c.get("job") in ("Writer", "Screenplay", "Story")][:3]
            if directors:
                movie_data["director"] = ", ".join(directors)
            if writers:
                movie_data["writers"] = writers

            cast_list = credits.get("cast", [])
            if cast_list:
                movie_data["cast"] = [
                    {
                        "name": c["name"],
                        "character": c.get("character", ""),
                        "profile_path": f"https://image.tmdb.org/t/p/w185{c['profile_path']}" if c.get("profile_path") else None,
                    }
                    for c in cast_list[:8]
                ]

            videos = res.get("videos", {}).get("results", [])
            trailers = [v for v in videos if v.get("site") == "YouTube" and v.get("type") in ("Trailer", "Teaser")]
            if trailers:
                movie_data["trailer_key"] = trailers[0].get("key", "")

    except Exception as exc:
        logger.debug("TMDB fetch exception: %s", exc)

    return {"movie": movie_data}


@app.get("/api/search")
async def search_movies(q: str = Query(...), city: str = Query("Hyderabad")):
    """Live movie search across all BookMyShow (released & upcoming) and District."""
    query = (q or "").strip()
    if not query:
        return {"results": [], "query": q}
    try:
        results = await asyncio.to_thread(catalog.search, query)
        serialized = [movie_to_dict(r) for r in results]
        for item in serialized:
            if not item.get("release_date") and item.get("title"):
                rd = await asyncio.to_thread(tmdb.release_date, item["title"])
                if rd:
                    item["release_date"] = rd
        return {"results": serialized, "query": q}
    except Exception as exc:
        logger.warning("Search failed for %r: %s: %s", query, type(exc).__name__, exc)
        return {"results": [], "query": q, "error": "Search is temporarily unavailable."}


@app.get("/api/theatres")
async def get_theatres(
    city: str = Query("Hyderabad"),
    source: str = Query("bookmyshow"),
    movie_id: str = Query("", description="Movie/event id — required for District"),
    movie_slug: str = Query("", description="District movie slug"),
    movie_title: str = Query(""),
    region_code: str = Query(""),
):
    """The cinemas a watch can be limited to.

    BookMyShow lists every venue in a region; District only knows the cinemas
    that have sessions for *this* movie, so ``movie_id``/``movie_slug`` are part
    of the request. The previous implementation called a ``resolver.list_cinemas``
    that does not exist and fell back to a hardcoded, city-specific fake list.
    """
    src = normalize_source(source)
    if src is Source.DISTRICT and not (movie_id or movie_slug):
        return {
            "theatres": [],
            "city": city,
            "source": src.value,
            "error": "District cinema lists need a movie — pass movie_id/movie_slug.",
        }

    movie = resolved_from_request(movie_id, movie_slug, movie_title, src, city, region_code)
    try:
        theatres = await asyncio.to_thread(resolver.list_theatres, movie, movie.region)
        if src is Source.DISTRICT and theatres:
            asyncio.create_task(
                repo.upsert_district_cinemas([
                    {"id": t.theatre_id, "name": t.theatre_name, "address": t.address, "city_key": movie.region.slug or city}
                    for t in theatres
                ])
            )
    except Exception as exc:
        logger.warning(
            "Theatre lookup failed for %s/%s in %s: %s: %s",
            src.value,
            movie_id or movie_slug,
            city,
            type(exc).__name__,
            exc,
        )
        if src is Source.DISTRICT:
            cached = await repo.list_district_cinemas(movie.region.slug or city)
            if cached:
                return {
                    "theatres": cached,
                    "city": city,
                    "source": src.value,
                    "region_code": movie.region.code,
                    "cached": True,
                }
        return {
            "theatres": [],
            "city": city,
            "source": src.value,
            "region_code": movie.region.code,
            "error": "Could not load cinemas right now — you can still watch all theatres.",
        }

    theatres_data = [
        {"id": t.theatre_id, "name": t.theatre_name, "address": t.address}
        for t in theatres
    ]
    if not theatres_data and src is Source.DISTRICT:
        cached = await repo.list_district_cinemas(movie.region.slug or city)
        if cached:
            theatres_data = cached

    return {
        "theatres": theatres_data,
        "city": city,
        "source": src.value,
        # The exact source region the watch should poll (e.g. BMS "HYD"):
        # persisted with the watch so the worker never has to re-resolve it.
        "region_code": movie.region.code,
        "region_name": movie.region.name or city,
    }


# ---------------------------------------------------------------------------
# Watches
# ---------------------------------------------------------------------------


@app.get("/api/watches")
async def get_watches(user_id: str = Depends(get_current_user_id)):
    watches = await repo.get_user_watches(user_id)
    return {"watches": watches}


@app.post("/api/watches", status_code=201)
async def create_watch(data: WatchCreate, user_id: str = Depends(get_current_user_id)):
    """Create a watch.

    The region the source must be polled in (BMS ``HYD``, District ``hyderabad``)
    is resolved here and stored. Rejects duplicates with a 409 Conflict.
    """
    if not (data.movie_title or "").strip() or not (data.movie_id or "").strip():
        raise HTTPException(status_code=400, detail="movie_title and movie_id are required")

    # A phone number is compulsory: without one no channel can reach the user.
    user = await repo.get_user(user_id)
    user_whatsapp = (getattr(user, "whatsapp_number", None) or (user.get("whatsapp_number") if isinstance(user, dict) else "") or "").strip()

    if data.whatsapp_number and data.whatsapp_number.strip():
        formatted = whatsapp.normalize_phone(data.whatsapp_number) or data.whatsapp_number.strip()
        await repo.update_user_profile(user_id, {"whatsapp_number": formatted})
        user_whatsapp = formatted

    if not user_whatsapp:
        raise HTTPException(
            status_code=400,
            detail="WhatsApp number is compulsory before creating a ticket watch in India. Please provide your 10-digit mobile number.",
        )

    if (data.source or "").lower() in ("both", "all"):
        return await _create_dual_watch(data, user_id)

    source = normalize_source(data.source)
    region = region_for_city(source, data.city, data.region_code)
    movie_slug = data.movie_slug
    if source is Source.DISTRICT and not movie_slug:
        item = catalog.get_by_id(source, data.movie_id)
        if item:
            movie_slug = item.movie_slug

    existing = await repo.find_existing_watch(user_id, source.value, data.movie_id, data.city)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"You already have an active watch for '{data.movie_title}' in {data.city} ({source.value.upper()}).",
        )

    watch = await repo.create_watch(
        user_uid=user_id,
        **_watch_fields(
            data,
            source=source,
            movie_id=data.movie_id,
            movie_slug=movie_slug,
            region=region,
            theatres=data.theatres,
        ),
    )
    return {"watch": watch}


@app.patch("/api/watches/{watch_id}")
async def update_watch(watch_id: str, data: WatchUpdate, user_id: str = Depends(get_current_user_id)):
    updated = await repo.update_watch(user_id, watch_id, data.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Watch not found")
    return {"watch": updated}


@app.delete("/api/watches/{watch_id}")
async def delete_watch(watch_id: str, user_id: str = Depends(get_current_user_id)):
    success = await repo.delete_watch(user_id, watch_id)
    if not success:
        raise HTTPException(status_code=404, detail="Watch not found")
    return {"status": "deleted"}


@app.post("/api/watches/batch-delete")
async def batch_delete_watches_endpoint(data: BatchDeleteRequest, user_id: str = Depends(get_current_user_id)):
    count = await repo.batch_delete_watches(user_id, data.watch_ids)
    return {"status": "deleted", "count": count}


@app.post("/api/watches/{watch_id}/test")
async def test_watch_alert(watch_id: str, user_id: str = Depends(get_current_user_id)):
    """Send a real drill over the user's configured channels.

    This used to write a "SENT" row into the alert log without sending anything,
    so the UI reported success even when no channel was configured.
    """
    watch = await repo.get_watch(user_id, watch_id)
    if not watch:
        raise HTTPException(status_code=404, detail="Watch not found")

    return await run_test_drill(user_id, watch, normalize_source(watch["source"]))


@app.get("/api/alerts")
async def get_alerts(
    limit: int = Query(25, ge=1, le=200),
    user_id: str = Depends(get_current_user_id),
):
    alerts = await repo.get_recent_alerts(user_id, limit)
    return {"alerts": alerts}


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


@app.get("/api/user/me")
async def get_user_me(user: Dict[str, Any] = Depends(get_current_user)):
    """The local profile, kept in sync with the Firebase/Google account."""
    profile = await repo.get_or_create_user(
        user["uid"], email=user["email"], name=user["name"], picture=user["picture"]
    )
    return {"profile": profile, "channels": notifications.channel_status()}


@app.patch("/api/user/me")
async def update_user_me(data: UserProfileUpdate, user_id: str = Depends(get_current_user_id)):
    profile = await repo.update_user_profile(user_id, data.model_dump(exclude_unset=True))
    return {"profile": profile}


@app.post("/api/user/me/test-alert")
async def test_user_alert(user: Dict[str, Any] = Depends(get_current_user)):
    """Prove the saved notification channels work, straight from the settings screen."""
    profile = await repo.get_or_create_user(
        user["uid"], email=user["email"], name=user["name"], picture=user["picture"]
    )
    if not notifications.configured_channels(profile):
        raise HTTPException(
            status_code=400,
            detail=(
                "No usable channel yet. Save an Email address or WhatsApp number in Settings "
                "— and make sure the matching transport is configured on the server."
            ),
        )

    return await run_test_drill(
        user["uid"],
        {
            "id": 0,
            "movie_id": "",
            "movie_title": "TicketFox Test Alert",
            "source": Source.BOOKMYSHOW.value,
            "city": "Hyderabad",
        },
        Source.BOOKMYSHOW,
    )


# ---------------------------------------------------------------------------
# Admin API
# ---------------------------------------------------------------------------


def verify_admin(
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    authorization: Optional[str] = Header(None),
) -> bool:
    expected = (settings.SECRET_KEY or settings.ADMIN_UID or "").strip()
    provided = (x_admin_key or "").strip()
    if authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:].strip()
    if not expected or provided != expected:
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required")
    return True


@app.get("/api/admin/stats")
async def get_admin_stats(is_admin: bool = Depends(verify_admin)):
    from app.worker import WebWorker

    stats = await repo.admin_stats()
    stats["worker"] = {
        "enabled": settings.WORKER_ENABLED,
        "last_cycle_at": WebWorker.last_cycle_at,
        "last_cycle_duration_seconds": WebWorker.last_cycle_duration,
        "last_cycle_keys_count": WebWorker.last_cycle_keys_count,
        "surge_active": WebWorker.surge_active,
    }
    stats["channels"] = notifications.channel_status()
    return stats


@app.get("/api/admin/poll-keys")
async def get_admin_poll_keys(is_admin: bool = Depends(verify_admin)):
    keys = await repo.get_all_poll_states()
    return {"poll_keys": keys}


@app.get("/api/admin/users")
async def get_admin_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    is_admin: bool = Depends(verify_admin),
):
    users = await repo.admin_list_users(limit=limit, offset=offset)
    return {"users": users}


@app.patch("/api/admin/users/{user_uid}")
async def admin_update_user(
    user_uid: str,
    data: UserProfileUpdate,
    is_admin: bool = Depends(verify_admin),
):
    """Admin endpoint to update user profile (e.g. add/edit WhatsApp or Email)."""
    updates = {k: v for k, v in data.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update")
    updated = await repo.update_user_profile(user_uid, updates)
    return {"status": "success", "user": updated}


@app.get("/api/admin/watches")
async def get_admin_watches(
    status: str = Query("all"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    is_admin: bool = Depends(verify_admin),
):
    watches = await repo.admin_list_watches(limit=limit, offset=offset, status_filter=status)
    return {"watches": watches}


@app.post("/api/admin/broadcast")
async def create_broadcast(
    data: BroadcastCreateRequest,
    is_admin: bool = Depends(verify_admin),
):
    """Deliver a promotional broadcast or announcement to users across their configured channels."""
    campaign = await repo.create_broadcast(
        title=data.title,
        message=data.message,
        channels=data.channels,
        cta_text=data.cta_text,
        cta_url=data.cta_url,
    )
    users = await repo.admin_list_users(limit=1000)
    sent_count = 0
    failed_count = 0
    skipped_count = 0
    recipient_breakdown = []

    requested_channels = [c.lower() for c in (data.channels or ["email", "whatsapp"])]
    whatsapp_text = notifications.render_broadcast_text(
        title=data.title,
        message=data.message,
        cta_text=data.cta_text,
        cta_url=data.cta_url,
    )
    email_html = notifications.render_broadcast_html(
        title=data.title,
        message=data.message,
        cta_text=data.cta_text,
        cta_url=data.cta_url,
    )

    for u in users:
        targets = notifications.user_targets(u)
        has_any_target = any(targets.get(ch) for ch in requested_channels)

        if not has_any_target:
            skipped_count += 1
            recipient_breakdown.append({
                "uid": u.get("uid"),
                "email": targets.get("email"),
                "whatsapp": targets.get("whatsapp"),
                "status": "skipped",
                "detail": f"Missing destination for requested channel(s): {', '.join(requested_channels)}",
            })
            continue

        results = await notifications.deliver_custom_async(
            u,
            f"📢 TicketFox: {data.title}",
            whatsapp_text,
            email_html,
            channels=requested_channels,
        )

        sent_on_any = any(r["status"] == notifications.SENT for r in results)
        failed_on_any = any(r["status"] == notifications.FAILED for r in results)

        user_status_details = [f"{r['channel']}: {r['status']} ({r.get('detail', '')})" for r in results]

        if sent_on_any:
            sent_count += 1
            recipient_breakdown.append({
                "uid": u.get("uid"),
                "email": targets.get("email"),
                "whatsapp": targets.get("whatsapp"),
                "status": "delivered",
                "detail": ", ".join(user_status_details),
            })
        elif failed_on_any:
            failed_count += 1
            recipient_breakdown.append({
                "uid": u.get("uid"),
                "email": targets.get("email"),
                "whatsapp": targets.get("whatsapp"),
                "status": "failed",
                "detail": ", ".join(user_status_details),
            })
        else:
            skipped_count += 1
            recipient_breakdown.append({
                "uid": u.get("uid"),
                "email": targets.get("email"),
                "whatsapp": targets.get("whatsapp"),
                "status": "skipped",
                "detail": ", ".join(user_status_details),
            })

    await repo.update_broadcast_status(campaign["id"], "sent", sent_count, failed_count)
    
    summary_parts = [f"Delivered to {sent_count} user(s)"]
    if skipped_count:
        summary_parts.append(f"{skipped_count} skipped (missing channel info)")
    if failed_count:
        summary_parts.append(f"{failed_count} delivery failed")
    
    return {
        "status": "success",
        "campaign_id": campaign["id"],
        "sent_count": sent_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "total_attempted": len(users),
        "details": recipient_breakdown,
        "message": f"Broadcast complete: {', '.join(summary_parts)}.",
    }


@app.get("/api/admin/broadcasts")
async def list_broadcasts(is_admin: bool = Depends(verify_admin)):
    campaigns = await repo.get_broadcasts()
    return {"campaigns": campaigns}


@app.post("/api/worker/cycle")
async def trigger_worker_cycle(is_admin: bool = Depends(verify_admin)):
    import time
    from datetime import datetime, timezone
    from app.worker import WebWorker

    worker = WebWorker()
    start_t = time.time()
    keys_polled = await worker.run_cycle()
    duration = round(time.time() - start_t, 2)
    return {
        "status": "success",
        "duration_seconds": duration,
        "keys_polled": keys_polled,
        "poll_keys_handled": keys_polled,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }




