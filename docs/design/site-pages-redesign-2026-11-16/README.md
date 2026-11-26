# Design log — Site pages redesign

**Date:** 2026-11-16
**Scope:** About, FAQ, 404, blog index, blog post, footer, admin isolation
**Bar:** award-level craft, system fidelity, no AI-slop tells

---

## 1. The brief

The first pass shipped functional pages that read as generic. The rejection was
specific: *"i need a separate about, faq it should follow the same design
language and 404 is not it can be more creative and we need a proper blog system
and we need to link all these pages at the bottom of the website and remove
admin from main website."*

So the work is not "add pages" — it is **give each page a point of view that
only TicketFox could have**, while staying inside the existing token system.

## 2. The organising idea

TicketFox is a **projection booth**: it watches screens, it never sells seats.
Every page is framed as a piece of cinema infrastructure rather than a generic
marketing surface.

| Page | Direction | Why it is not generic |
| --- | --- | --- |
| About | **The Projection Booth** | A credit roll, a production timeline, a list of *refusals* — the things the product will not do. |
| FAQ | **The Ledger** | A grouped, indexed ledger with counts, not a flat accordion dump. |
| 404 | **The Dead Screen** | A struck showtime board — the listing that got cancelled. |
| Blog index | **The Screening Room** | A lead story plus "rest of the programme", with a tag archive. |
| Blog post | **The print** | Reading progress, a sticky table of contents, prev/next navigation. |
| Footer | **The mast** | A four-column masthead that links every page. |

## 3. System fidelity

No new colours, no new fonts, no new radii. Everything is built from
[`tokens.css`](../../../frontend/app/tokens.css):

- Spacing: `--space-*` only.
- Type: `--text-*`, `--tracking-display`, `--font-display` / `--font-body`.
- Colour: `--color-ink`, `--color-muted`, `--color-rule`, `--color-accent`,
  `--color-accent-2`, `--color-paper*`.
- Motion: `--dur-micro` / `--dur-short` / `--dur-long`, `--ease-out`.
- Depth: `--z-sticky`, `--z-sticky-nav`.

The new CSS lives in a single appended **STAGE 5** layer in
[`globals.css`](../../../frontend/app/globals.css) so the semantic class layer
stays readable and the new work is auditable in one place.

## 4. What was built

### About — The Projection Booth
- `CREDITS` rendered as a `<dl>` credit roll (role / name).
- `TIMELINE` as an ordered list with an accent hairline and year marks.
- `PRINCIPLES` reuses the existing `.steps` pattern (Radar / Bell / ShieldCheck).
- `REFUSALS` — five things the product will not do, each struck with an X mark.
- `FACTS` as a `.spec` table with an `sr-only` caption.
- Contact + "more" rows, then a close.

### FAQ — The Ledger
- Six groups: alerts, channels, filters, coverage, reliability, privacy.
- A ledger index with per-group counts that jumps to each section.
- One-open-at-a-time accordion (`FAQAccordion`), grouped, with a tag chip per
  question. Defaults to the first question open.

### 404 — The Dead Screen
- A drifting marquee ("NO SHOW · …").
- A dead-code `404`, a struck showtime board with a "Cancelled" status, and
  useful links. `robots: { index: false, follow: true }`.

### Blog — The Screening Room
- A lead story (newest post) with meta, title, line and foot.
- "Rest of the programme" as `.post-card`s.
- A tag archive with counts, from `getAllTags()`.

### Blog post — the print
- `ReadingProgress` (rAF-throttled, `position: fixed` above the sticky nav).
- A sticky table of contents built from `getPostHeadings()`.
- Anchored section headings via `slugifyHeading()`.
- Prev/next navigation from `getAdjacentPosts()`.
- `BlogPosting` JSON-LD retained.

### Footer — the mast
- Four columns: brand, Product, Company, Contact.
- Links every page: Now showing, How it works, FAQ, About, The Screening Room.
- A foot note: *"Not affiliated with BookMyShow or District. Alerts only —
  never bookings."*

## 5. Admin isolation

Admin is removed from the main site's navigation and footer. It is reachable
**only** at `admin.ticketfox.site`, enforced in
[`middleware.ts`](../../../frontend/middleware.ts):

- On an `admin.*` host, non-`/admin` paths are rewritten to `/admin`.
- On the main host, `/admin` redirects to `admin.<host>`.
- On a bare IP, `/admin` returns a plain 404 (no redirect to a host that does
  not exist).

## 6. Verification

- `npm run build` — all routes compile, static generation succeeds.
- Admin unreachable from the main host (redirect) and from a bare IP (404).
- Reduced-motion honoured for the marquee and progress transitions.

## 7. Files touched

- `frontend/lib/blog.ts` — 5th post + tag/adjacent/heading helpers.
- `frontend/app/about/page.tsx`
- `frontend/app/faq/page.tsx`, `frontend/app/faq/FAQAccordion.tsx`
- `frontend/app/not-found.tsx`
- `frontend/app/blog/page.tsx`
- `frontend/app/blog/[slug]/page.tsx`, `frontend/app/blog/[slug]/ReadingProgress.tsx`
- `frontend/components/Footer.tsx`
- `frontend/app/globals.css` — STAGE 5 layer + mast grid + `.mast-foot-note`.
