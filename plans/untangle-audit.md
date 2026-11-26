# TicketFox — Untangle Audit & Redesign

Scope: the whole repository (`backend/` FastAPI + shared scraping engine, `frontend/` Next.js).
This document is **read-only analysis**. No source file is changed until the redesign below is approved.

Optional additions chosen by the user: **Comments** (remove comments that only restate the code) and **Tests** (remove tests that cannot catch a real bug; fix tests that fail for no real reason).

---

## How to read this

Four problem categories, per the skill:

- **Hidden links** — copies of the same logic/value, global or file coupling, a feature split across layers, an implicit call-order convention.
- **Needless links** — a caller reaching into internals, a stable module importing a volatile one, a parameter that only exists for one caller, a shallow module.
- **Surplus** — pass-through wrappers, speculative generality, dead code.
- **Special cases** — an `if` for one value, a parameter for one caller, a swallowed exception, a retry/sleep, a disabled test.

Each problem is tagged `H#`, `N#`, `S#`, `X#`. The redesign (Step 3) lists each fix and the problem tags it removes.

---

## 1. Hidden links

### H1 — The `/api/worker/cycle` route is defined twice; the first is dead
[`backend/app/main.py`](backend/app/main.py:303) defines `POST /api/worker/cycle` with inline admin auth (reads `X-Admin-Key` / `Authorization` by hand, returns `poll_keys_handled` + `last_cycle_duration_seconds`).
[`backend/app/main.py`](backend/app/main.py:1128) defines the **same path and method again**, using the shared `verify_admin` dependency and returning a different shape (`duration_seconds`, `keys_polled`, `poll_keys_handled`, `timestamp`).
FastAPI keeps the last registration, so the first handler is unreachable dead code. Two copies of the same auth rule and the same "run a cycle" body now exist, and they disagree on the response contract.

### H2 — Admin identity is hardcoded in three places, in two languages
- [`backend/app/config.py`](backend/app/config.py:68) `ADMIN_UID = "1tXP1wmqmgXhVZvOiIgDL5L8sm03"`, `ADMIN_EMAIL = "saisandeepy567@gmail.com"`.
- [`frontend/components/Navbar.tsx`](frontend/components/Navbar.tsx:172) compares `user.email` to `NEXT_PUBLIC_ADMIN_EMAIL || "saisandeepy567@gmail.com"` and `user.uid === "1tXP1wmqmgXhVZvOiIgDL5L8sm03"`.
- [`frontend/app/admin/page.tsx`](frontend/app/admin/page.tsx:49) repeats the same email/uid literals.

The same two values are copied across the backend config and two frontend files. Changing the admin requires editing three files in two languages, and the frontend copy silently drifts from the backend copy.

### H3 — Title normalization is implemented three times
- [`backend/app/main.py`](backend/app/main.py:398) `_norm` strips `(telugu|hindi|tamil|kannada|malayalam|english|2d|3d|imax|4dx)`.
- [`backend/app/engine/sources/resolver.py`](backend/app/engine/sources/resolver.py:126) `_normalize_title` strips the same list **plus** `bengali|marathi|punjabi|dolby`.
- [`backend/app/engine/sources/catalog.py`](backend/app/engine/sources/catalog.py:55) `_normalize_title` is a byte-for-byte copy of the resolver one.

Three copies of "what counts as a title decoration", two of which already disagree on the language list. `_names_match` is likewise duplicated in `resolver.py` and `catalog.py`.

### H4 — WhatsApp number normalization is implemented four times
- [`backend/app/main.py`](backend/app/main.py:716) `create_watch`: digits → `+91…` / `+…`.
- [`backend/app/whatsapp.py`](backend/app/whatsapp.py:71) `chat_id`: digits → `91…@c.us`.
- [`frontend/components/WatchWizardModal.tsx`](frontend/components/WatchWizardModal.tsx:342) and again at [line 456](frontend/components/WatchWizardModal.tsx:456): `replace(/\D/g,"")` + `startsWith("91")`.
- [`frontend/components/SettingsModal.tsx`](frontend/components/SettingsModal.tsx:41) `extract10Digits`: the same rule again.

Four independent implementations of "turn a typed phone number into the canonical Indian form". They will drift (e.g. the `00` prefix is handled in `whatsapp.py` but nowhere else).

### H5 — The cinema-budgeting loop is copy-pasted in `notifications.py`
[`render_alert_text`](backend/app/notifications.py:124) and [`render_new_shows_text`](backend/app/notifications.py:240) contain the **identical** `for max_c, max_s in ((min(len(cinema_items), 8), 3), (5, 2), (3, 2), (1, 2))` budget loop, the identical `c_lines` builder, and the identical truncation fallback. The only difference is the header lines above it.

### H6 — The three worker notify methods are near-identical
[`notify`](backend/app/worker.py:476), [`notify_new_shows`](backend/app/worker.py:498), [`notify_back_in_stock`](backend/app/worker.py:523) share the same body: fetch user → deliver → loop results skipping `SKIPPED` �� `log_alert` → `delivered = any(SENT)` → `summary if not delivered`. Only the renderer, subject, and log status differ.

### H7 — The city list is duplicated and already inconsistent
[`backend/app/engine/cities.py`](backend/app/engine/cities.py:26) `CITY_NAMES` has **10** cities (adds `Ahmedabad`, `Chandigarh`, and spells `Delhi-NCR`).
[`frontend/components/Navbar.tsx`](frontend/components/Navbar.tsx:27) `CITIES` has **8** (spells `Delhi`), and is re-exported and consumed by [`frontend/app/page.tsx`](frontend/app/page.tsx:8). The two lists already disagree on membership and on the Delhi spelling.

### H8 — The dual-platform watch-creation block duplicates the single-platform block
[`backend/app/main.py`](backend/app/main.py:734) builds a primary watch and a secondary watch with two ~20-line `repo.create_watch(...)` calls that repeat the same 15 keyword arguments, then [line 819](backend/app/main.py:819) repeats them a third time for the single-source path. The slug fallback `re.sub(r'[^a-z0-9]+','-', title.lower())` is inlined twice.

### H9 — TMDB access is implemented three times
- [`backend/app/main.py`](backend/app/main.py:427) `fetch_tmdb` (inline, inside `get_movie_info`).
- [`backend/app/main.py`](backend/app/main.py:548) `_resolve_release_date_sync` (a second, separate TMDB call).
- [`frontend/lib/tmdb.ts`](frontend/lib/tmdb.ts:31) a full third TMDB client used by `FlixOrbitDiscovery`.

Three clients, three key reads, three error-handling styles for one external service.

### H10 — The "deliver then log" convention is repeated in four call sites
The pattern "deliver → for each non-SKIPPED result call `repo.log_alert` → compute delivered" appears in [`worker.notify*`](backend/app/worker.py:476) (×3) and [`main.dispatch_test_alert`](backend/app/main.py:222). It is an implicit convention: every new alert type must remember to log, and `expire_stale_watch` / `_handle_poll_failure` log with `channel="system"` in a slightly different way.

---

## 2. Needless links

### N1 — `fetchWithAuth` is a pass-through wrapper
[`frontend/lib/api.ts`](frontend/lib/api.ts:61) `export const fetchWithAuth = (endpoint, options = {}, token?) => apiFetch(endpoint, options, token);` adds nothing. Callers must know both names; some files use `apiFetch`, some use `fetchWithAuth`, for the same call.

### N2 — `Repository.update_user` is an alias of `update_user_profile`
[`backend/app/database/repository.py`](backend/app/database/repository.py:210) `update_user = update_user_profile`. Two names for one method; `main.py` uses the alias, tests use the real name.

### N3 — `main.py` reaches into engine internals
[`backend/app/main.py`](backend/app/main.py:398) defines its own title normalizer instead of using the engine's, and [line 736](backend/app/main.py:736) decides "is this a District id" with `data.movie_id.isdigit() or startswith("MV") or "district" in slug` — a rule that belongs to the engine's URL/id layer ([`urls.normalise_district_id`](backend/app/engine/urls.py:106) already knows District id shapes).

### N4 — `main.py` imports `parse_show_time` and builds `Show` objects for a fake drill
[`backend/app/main.py`](backend/app/main.py:185) `sample_shows` constructs engine `Show` objects and parses times in the API layer. The API layer now depends on engine value-object construction details.

### N5 — `page.tsx` imports `CITIES` from a component
[`frontend/app/page.tsx`](frontend/app/page.tsx:8) `import Navbar, { CITIES } from "../components/Navbar"`. A page depends on a presentational component for a domain constant. The constant should live in a data module, not in `Navbar`.

### N6 — `SettingsModal` and `WatchWizardModal` call endpoints that do not exist
[`SettingsModal`](frontend/components/SettingsModal.tsx:96) POSTs `/api/user/preferences` and [line 128](frontend/components/SettingsModal.tsx:128) POSTs `/api/user/test-alert`. The backend exposes `PATCH /api/user/me` and `POST /api/user/me/test-alert`. The frontend depends on a contract the backend never had — the settings save and the test-alert button are silently broken (404).

### N7 — `page.tsx` reads a response field the backend never sends
[`handleBatchDelete`](frontend/app/page.tsx:354) reads `res.deleted_count`, but [`batch_delete_watches_endpoint`](backend/app/main.py:861) returns `{"status": "deleted", "count": count}`. The toast always falls back to the local count; the real deleted count is ignored.

### N8 — `admin/page.tsx` sends `X-Admin-Key` while the rest of the app uses Bearer tokens
[`admin/page.tsx`](frontend/app/admin/page.tsx:110) builds `adminHeaders(key)` with `X-Admin-Key`, but `verify_admin` also accepts `Authorization: Bearer`. Two auth conventions for the same guard.

---

## 3. Surplus

### S1 — Dead duplicate route handler (see H1)
The first `trigger_worker_cycle` is unreachable.

### S2 — `_upgrade_schema` manual migration hack
[`backend/app/database/models.py`](backend/app/database/models.py:134) keeps an `_ADDED_COLUMNS` tuple and issues raw `ALTER TABLE … ADD COLUMN` inside a `try/except: pass`. It is a hand-rolled migration system that silently swallows every error, duplicating what `create_all` + a real migration tool would do.

### S3 — `update_user` alias (see N2).

### S4 — `fetchWithAuth` wrapper (see N1).

### S5 — Unused imports in tests
[`test_database.py`](backend/tests/test_database.py:4) imports `_upgrade_schema` but never calls it. [`test_config.py`](backend/tests/test_config.py:2) imports `Settings` but never uses it. [`test_repository.py`](backend/tests/test_repository.py:3) imports `pytest_asyncio` but never uses it.

### S6 — `test_advanced_features.test_create_dual_platform_watch` hits the live network
[`test_create_dual_platform_watch`](backend/tests/test_advanced_features.py:116) calls `POST /api/watches` with `source="both"`, which runs `catalog.search(...)` — a live scrape of BookMyShow/District. The test passes only when the network and the sites cooperate; it cannot catch a real bug deterministically and it leaves a watch row behind.

### S7 — Brittle implementation-detail assertions
[`test_mock_uid_length`](backend/tests/test_auth.py:21) asserts `len(uid) == 21` (a hash-length detail, not behavior). [`test_postgresql_ddl_compilation`](backend/tests/test_database.py:7) asserts on exact DDL substrings (`"uid VARCHAR NOT NULL"`), which breaks on any SQLAlchemy formatting change without indicating a real defect.

### S8 — `test_infer_state` restates the implementation
[`test_infer_state`](backend/tests/test_worker_engine.py:12) asserts `infer_state(True) == AVAILABLE`, which is the function body verbatim.

---

## 4. Special cases

### X1 — Swallowed exception in `_upgrade_schema`
[`models.py`](backend/app/database/models.py:144) `except Exception: pass` hides every migration failure, including a genuinely broken schema.

### X2 — `if (data.source or "").lower() in ("both", "all")` — a branch for one client value
[`main.py`](backend/app/main.py:735) special-cases the literal strings `"both"`/`"all"` inside `create_watch`, splitting the endpoint into two divergent code paths (H8).

### X3 — `is_district_primary` heuristic for one caller
[`main.py`](backend/app/main.py:736) guesses the primary source from the id shape only for the dual-platform path.

### X4 — `channel == "email"` / `channel == "whatsapp"` chains repeated
The channel dispatch `if channel == "email": … elif channel == "whatsapp": …` appears in [`_deliver_one`](backend/app/notifications.py:504) and again in [`deliver_custom`](backend/app/notifications.py:637), with slightly different fallbacks (`"unknown channel"` vs `"unsupported channel"`).

### X5 — `test_watch_alert` and `test_user_alert` duplicate the drill body
[`test_watch_alert`](backend/app/main.py:864) and [`test_user_alert`](backend/app/main.py:910) both call `dispatch_test_alert` and both raise `502` on non-delivery — the same two lines, twice.

### X6 — `expire_stale_watch` and `_handle_poll_failure` log with `channel="system"` inline
[`worker.py`](backend/app/worker.py:301) and [line 378](backend/app/worker.py:378) hand-roll a `log_alert(channel="system", …)` instead of going through the shared delivery/logging path (H10).

---

## 5. Redesign from first principles (decision log)

Each fix is written above the problems it removes. Fixes are ordered so that later ones depend on earlier ones.

### F1 — One admin guard, one admin identity source
Make `verify_admin` the single admin check and delete the inline copy. Expose the admin identity from one place: the backend reads `settings.ADMIN_UID` / `settings.ADMIN_EMAIL`; the frontend reads `NEXT_PUBLIC_ADMIN_EMAIL` / `NEXT_PUBLIC_ADMIN_UID` from a single `lib/admin.ts` helper used by both `Navbar` and `admin/page.tsx`.
Removes: **H1** (auth half), **H2**, **N8** (one header convention: Bearer).

### F2 — One `/api/worker/cycle` handler
Delete the first definition; keep the `verify_admin`-guarded one and make its response the single contract (`keys_polled`, `duration_seconds`, `timestamp`). Update `admin/page.tsx` to read that shape.
Removes: **H1**, **S1**.

### F3 — One title-normalization module in the engine
Add `normalize_title` / `names_match` to a single engine module (e.g. `engine/titles.py`) and have `resolver.py`, `catalog.py`, and `main.py` import it. Delete the three copies.
Removes: **H3**, **N3** (title half).

### F4 — One phone-normalization helper per side
Backend: a single `normalize_phone` in `whatsapp.py` (or a small `app/phone.py`) used by `create_watch` and `chat_id`. Frontend: a single `lib/phone.ts` `toIndianDigits` used by `WatchWizardModal` and `SettingsModal`.
Removes: **H4**.

### F5 — One alert-rendering core
Extract the shared cinema-budget loop into one private `_render_cinema_block(grouped, multi_day, limit)` used by `render_alert_text` and `render_new_shows_text` (and the HTML variants). Extract the channel dispatch into one `_send(channel, target, subject, text, html)` used by `_deliver_one` and `deliver_custom`.
Removes: **H5**, **X4**.

### F6 — One delivery+logging path in the worker
Add `WebWorker._dispatch(watch, subject, text, html, log_status)` that delivers, logs non-SKIPPED results, and returns `(delivered, summary)`. `notify`, `notify_new_shows`, `notify_back_in_stock`, `expire_stale_watch`, and `_handle_poll_failure` all call it.
Removes: **H6**, **H10**, **X6**.

### F7 — One city catalog, served to the frontend
Keep `engine/cities.py` as the single source. Expose the list via the existing `/api/channels`-style config endpoint (or a new `/api/cities`) and have the frontend fetch it; delete the `CITIES` literal from `Navbar` and the `import { CITIES }` in `page.tsx`.
Removes: **H7**, **N5**.

### F8 — One watch-creation builder
Extract `_build_watch(user_id, data, source, movie_id, movie_slug, region, theatres)` in `main.py`; the single-source path and both dual-platform paths call it. Move the "is this a District id" decision into the engine's id layer.
Removes: **H8**, **X2**, **X3**, **N3** (id half).

### F9 — One TMDB client
Move the two inline TMDB calls in `main.py` behind a single `app/tmdb.py` client; the frontend keeps `lib/tmdb.ts` but both read the key from config/env consistently.
Removes: **H9**.

### F10 — One test-alert path
`test_watch_alert` and `test_user_alert` both call `dispatch_test_alert`; keep the shared helper and delete the duplicated 502 handling.
Removes: **X5**.

### F11 — One API client name
Delete `fetchWithAuth`; use `apiFetch` everywhere. Fix the two broken endpoints in `SettingsModal` to `PATCH /api/user/me` and `POST /api/user/me/test-alert`, and fix `page.tsx` to read `count`.
Removes: **N1**, **S4**, **N6**, **N7**.

### F12 — One repository method name
Delete the `update_user` alias; call `update_user_profile` everywhere.
Removes: **N2**, **S3**.

### F13 — Replace the schema hack with a real migration step
Either adopt Alembic, or (minimal) make `_upgrade_schema` log failures instead of swallowing them and keep it as the single documented migration point. Decision needed from the user (see open questions).
Removes: **S2**, **X1**.

### F14 — Test cleanup
- Delete `test_create_dual_platform_watch` (live network) or rewrite it to stub `catalog.search`.
- Delete `test_mock_uid_length` and `test_infer_state` (implementation restatement).
- Relax `test_postgresql_ddl_compilation` to assert table/column *presence* via the inspector, not exact DDL strings.
- Remove unused imports.
Removes: **S5**, **S6**, **S7**, **S8**.

### F15 — Comments pass
Remove comments that only restate the code (e.g. `# Create primary watch`, `# 1st failure -> admin alerted`, `# Cleanup`). Keep comments that explain *why* (e.g. the CORS wildcard note, the "worker must not create users" note).
Removes: comment noise across `main.py`, `worker.py`, `notifications.py`, tests.

---

## 6. Dependency order for implementation (Step 4)

1. F3, F4 (pure helpers, no callers change yet)
2. F5, F6 (notifications + worker internals)
3. F1, F2 (admin guard + route)
4. F8, F10 (watch creation + test alert)
5. F9 (TMDB)
6. F7 (cities endpoint + frontend)
7. F11, F12 (frontend API client + repository alias)
8. F13 (migration decision)
9. F14, F15 (tests + comments)
10. Update `README.md` / `frontend/DESIGN.md` to match.

---

## 7. Resolved questions

1. **F13 migration** -> keep the lightweight `_upgrade_schema`, but stop swallowing errors.
   It now logs each added column and lets a failure abort startup.
2. **F7 cities** -> add `/api/cities`; the frontend fetches it via `lib/cities.ts`.
3. **F9 TMDB** -> proxy through the backend at `/api/tmdb`; the key stays server-side.
4. **F14** -> rewrite `test_create_dual_platform_watch` with a stubbed catalog instead of deleting it.

---

## 8. Completion record

All of F1-F15 are implemented, plus one duplication found during Step 5:
`main._district_slug` was the same function as `resolver.slug_from_title` and has been deleted.

Verification:

| Check | Result |
|---|---|
| `cd backend && python -m pytest tests -q` | 29 passed, 2 warnings (both third-party deprecations) |
| `cd frontend && npx tsc --noEmit` | exit 0 |
| `cd frontend && npm run build` | compiled successfully, 7/7 static pages |

Step 5 search pass found no remaining references to any removed symbol:
`fetchWithAuth`, `NEXT_PUBLIC_TMDB_KEY`, `api.themoviedb.org`, `update_user(`,
`_release_date_cache`, the local `CITIES` list, or `_district_slug`.
Docs (`README.md`, `frontend/DESIGN.md`) now describe the single sources of truth.
