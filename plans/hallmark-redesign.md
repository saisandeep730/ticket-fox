# Hallmark · Redesign plan · TicketFox

**Verb** `redesign` · **Depth** `full` · **Target** `frontend/` · **Genre** `modern-minimal` (inferred from the page: a utility product page, no stamp exists)
**Brand** kept, by the user's instruction · **Composition** changes, by the user's instruction

---

## Pre-flight findings

```
Pre-flight findings:
· Locked system: frontend/DESIGN.md — Cinema Command Center, dark-first, amber/fox accents
· Font stack: Outfit (headings) + Plus Jakarta Sans (body), declared at
  frontend/app/globals.css:6 and frontend/tailwind.config.js:36
  — but never loaded: frontend/app/layout.tsx has no next/font import and no
  stylesheet link, so the page renders in system-ui today
· Palette: :root custom properties, frontend/app/globals.css:5
  (--color-canvas #06070a, --color-surface-1..3, --color-fox #ff7a00)
· Palette (Tailwind): obsidian 950..500 and fox 50..950 scales,
  frontend/tailwind.config.js:11
· Motion: framer-motion 11 + CSS keyframes (radar, fadeIn, scaleIn, slideUp),
  frontend/package.json:11, frontend/tailwind.config.js:40
· Spacing: Tailwind default 4pt scale, container max-w-7xl (1280px)
· Framework: Next.js 14.1 app router, React 18.2, Tailwind 3.4, TypeScript 5.3
· Product: reachable at http://localhost:3000 (screenshots in .hallmark/before/)
  — the backend at http://localhost:8000 was down during the audit, so the
  catalog rendered its empty state behind an error banner
· Kept record: .hallmark/before.json — every link, form, field, handler, id
Hallmark will preserve: the fox brand (logo.jpg, the TicketFox wordmark), the
  obsidian/orange palette, Outfit + Plus Jakarta Sans, every link, form, field,
  handler and id in .hallmark/before.json, all four routes.
Hallmark will introduce: the Hallmark stamp, frontend/app/tokens.css,
  frontend/app/base.css, real font loading, a new composition (shape, hero,
  sections, chrome).
```

Cached to `.hallmark/preflight.json` at build time.

### Blocking precondition

`redesign.md` § What a redesign keeps: *"In a git project, start from a clean tree, `.hallmark/` aside (ask the user to commit or stash; never do it for them)."*

`.git/` exists at the workspace root. **The user must commit or stash before the build starts** so the redesign is one readable, revertable diff. This is not something I do for them.

---

## The read (carried from the audit)

- **What the page is for:** a movie-ticket watcher for Indian cinema-goers. The one action is **create a watch** — pick a film, a city, a format, a channel, and let the engine poll BookMyShow and District until seats open.
- **What works and stays:** the fox mark, the obsidian/orange palette, the real catalog component, the watch wizard, the honest copy about polling and Cloudflare.
- **What reads as generated:** a centred hero over a blurred orange blob, gradient-clipped words, `transition-all` on 87 elements, emoji as icons, tracked-caps labels, a 1.00:1 focus ring, 22 colour literals outside tokens.
- **What is broken:** the page is a hero, then a tabbed app shell, then a footer — two sections, no page. The one action sits under an API error banner. The brand faces never load.

---

## Shape

**Workbench** ([`macrostructures/05-workbench.md`](C:\Users\saisa\.agents\skills\hallmark\references\macrostructures\05-workbench.md)) — the product in use is the sale, and here the product is genuinely reachable, so the page can show it rather than describe it.

**Job:** `sign up` — the action in the hero, repeated beside the spec sheet, and at the close. Never a newsletter.

**Hero posture:** **Counter** — the action is the visual. The watch composer (film, city, format, channel) set large, with the watch card it produces beside it. This is the one posture that makes a working control the hero legitimately, and it is the opposite of the centred text-over-blob the page has now.

**Signature:** *the watch being created* — a real composer in the hero that fills a watch card as you choose, and the card's caught state (a drop detected, the seats open) shown at the moment it matters.

**Fingerprint:** `Hanging|Asymmetric spans|Hairline|Solid|Margin-aligned|None`

**Deck deviations** (SaaS deck, `macrostructures.md` § SaaS section deck): `-changelog` (no real release dates to show) · `-pricing` (the product has no price; inventing one is gate 46a) · `+comparison` · the worked example promoted into the hero's place.

**Mirror test:** a neighbouring prompt in this category would get a centred hero, three feature cards and an email band. This gets a working composer, a real catalog, a lifecycle, a spec sheet and a comparison table. Different.

---

## Sections (8, hero and footer included)

| # | Section | Composition | Content (all real) |
| --- | --- | --- | --- |
| 1 | Hero | Counter | Head (≤7 words) + one sentence + the composer: film, city, format, channel → **Create Ticket Watch** (`openWizardWithMovie(null)`) |
| 2 | The catalog | Showcase + Grid | The real catalog: search field, city select, format filter, the Now Showing / My Hunts control, the movie grid. Every handler kept |
| 3 | How a watch runs | Steps (real `<ol>`) | create → scan → catch → notify. Polling every few seconds, Cloudflare bypass, retry five times, WhatsApp + email |
| 4 | What it watches | Table | BookMyShow · District · IMAX, 4DX, 3D, 2D · PVR, INOX, Cinepolis, Miraj, Asian · the city list · WhatsApp + email |
| 5 | By hand vs. TicketFox | Table | Row by row, no scores: refreshing a page vs. a poll every few seconds; missing the drop vs. an alert the second it opens |
| 6 | Questions | Rows | Four real objections, each linking to `/faq` |
| 7 | Close | Band | The action again, one button |
| 8 | Footer | Mast | The wordmark, the real links, the creator line, the legal line |

Pace: dense (2) → quiet (3) → dense (4, 5) → quiet (6) → close (7). No two neighbours share a skeleton. No photographs: the product is the picture, so the photo share is zero and the theme's Range carries every section.

---

## The Picks block

```markdown
**Hallmark · v2.0.0**

- **Redesign** · full · 4 pages (/, /about, /faq, /admin)
- **Before** · Floor 245 FAIL · Reflex 19 · a centred hero over a blurred orange blob, then a tabbed app shell; the catalog component and the wizard are real and stay
- **Keeps** · every link, field and handler in .hallmark/before.json · the fox mark and logo.jpg · the obsidian/orange palette · Outfit + Plus Jakarta Sans · the catalog, the watch wizard, the four routes
- **Files** · edit: frontend/app/page.tsx, frontend/app/layout.tsx, frontend/app/globals.css, frontend/components/Navbar.tsx, frontend/components/Footer.tsx, frontend/components/TicketFoxLogo.tsx, frontend/tailwind.config.js · create: frontend/app/tokens.css, frontend/app/base.css · delete: none
- **Shape** · Workbench · genre modern-minimal · job: sign up, the action in the hero, beside the spec sheet and at the close
- **Theme** · brand (kept): obsidian 950–500, fox 50–950, Outfit + Plus Jakarta Sans, 8px radius, thin visible borders
- **Chrome** · nav: edge-aligned, the wordmark and one action · footer: a mast, the wordmark over the real links
- **Hero** · Counter: the composer on columns 1 to 6, the watch card it builds on 7 to 12, the action inside the composer
- **Signature** · the watch being created, built live in the hero, and its caught state
- **Sections** · Hero (the composer) · Catalog (the real grid) · Lifecycle (four stages) · Spec sheet (table) · Comparison (table) · Questions (rows) · Close (band) · Footer
- **Material** · real: BookMyShow, District, IMAX/4DX/3D/2D, PVR/INOX/Cinepolis/Miraj/Asian, the city list, WhatsApp + email, polling every few seconds, Cloudflare bypass, retry five times, Y Sai Sandeep, TicketFox1@outlook.com, github.com/saisandeep730, @saisandeepy456 · pictures: the live product at localhost:3000, no library photos · absent: logos, quotes, metrics, prices
- **Sweep** · run after build
```

---

## Build order

1. **Precondition** — the user commits or stashes; `.hallmark/` aside.
2. **Scaffold** — `node <skill-dir>/scripts/theme.mjs scaffold ticketfox --brand --redesign full`, tokens filled from `frontend/DESIGN.md` and `frontend/tailwind.config.js` (no `check`: the coordinates are the user's). Writes `frontend/app/tokens.css` and `frontend/app/base.css`.
3. **Fonts** — load Outfit and Plus Jakarta Sans through `next/font/google` in [`frontend/app/layout.tsx`](frontend/app/layout.tsx:1), exposed as `--font-outfit` and `--font-jakarta` so the existing declarations resolve.
4. **Hero first** — nav + the Counter hero only, then `sloplint frontend/app/page.tsx --render --stage hero`, then the hero review in fresh context.
5. **Sections** — 2 through 7, each swept before the next.
6. **Chrome** — the nav and the footer mast, keeping every link and handler.
7. **The other three pages** — `/about` and `/faq` at full depth on the shared system; `/admin` as an app screen (`--scope app`), shell and tokens only.
8. **Sweep** — `sloplint frontend --genre modern-minimal --render --kept`; walk `gates.md` § 5; the finish review with the `before` screenshots; write `.hallmark/compare.html`.
9. **Project checks** — `next build`, `next lint`, `tsc --noEmit`.
10. **Log + handoff** — `theme.mjs log` with `mode: redesign`, `depth: full`, `scope: page`; the handoff block ahead of the material ask.

---

## Risks and decisions to confirm

- **The tab strip.** `setActiveTab("discover")` and `setActiveTab("watches")` are called from the hero and from `MobileNav`. The redesign keeps the control, moved into the catalog section as its filter, so `activeTab` keeps its meaning and no handler is orphaned. Removing it would leave two dead calls.
- **The backend is down.** The catalog section renders the real component, so it shows its own empty and error states honestly. No mocked UI, no stand-in photo. The handoff names the screens to capture once the backend runs.
- **`/admin` is an app screen, not a page.** It gets the tokens, the shell and the control states, not a hero or a section rhythm.
- **No pricing, no logos, no quotes, no metrics.** The product has none, and inventing them is gate 46a. The comparison table carries the argument instead.
