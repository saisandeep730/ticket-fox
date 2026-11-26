# Hallmark · v2.0.0 · audit

Target: `frontend/` (Next.js app, 4 routes: `/`, `/about`, `/faq`, `/admin`)
Record: `.hallmark/before.json` · `.hallmark/before.txt` · `.hallmark/before/` (20 screenshots)
Scope: page · genre inferred **modern-minimal** (a SaaS/utility product page; no stamp exists to declare one)
Depth: **audit only — no project file is changed by this run.**

---

## The read

**What the page is for.** TicketFox watches BookMyShow and District for ticket drops across Indian cities and alerts by WhatsApp and email. The visitor's one action is to create a watch. The audience is Indian moviegoers chasing premiere-day and reopening seats, on a phone, at midnight.

**What works and stays.** The dark obsidian canvas with a single orange signal is a real system, and [`frontend/DESIGN.md`](frontend/DESIGN.md) already names it: one anchor hue, a stated motion curve, a stated contrast bar. The fox wordmark, the Now Showing / My Active Hunts segmented control, the FAQ accordion and the admin gate are all honest, working objects. The copy is specific and un-invented: BookMyShow, District, Hyderabad, IMAX/4DX, the retry-five-times delivery detail. Nothing on the page claims a number it does not have.

**What reads as generated.** The orange-to-amber gradient on "Opening Day" ([`frontend/app/page.tsx:488`](frontend/app/page.tsx:488), 2b + 38iii); the 130px blurred orb behind the hero ([`frontend/app/page.tsx:483`](frontend/app/page.tsx:483), 29); glass cards with a chromatic zero-offset glow ([`frontend/app/globals.css:47`](frontend/app/globals.css:47), 29); eyebrow pills ("The TicketFox Platform", "Frequently Asked Questions", "Trending Highlight", 54); tracked-caps labels in 38 places (67); an emoji icon set in 27 places (30a); middle-dot meta rows (63); the equal icon-tile grids on About (3); the AI nav and AI footer, unnamed (42).

**What is broken.** 46 focus rings at 1.00 to 1.06:1 — keyboard users cannot see focus anywhere on the site (26a). Nine contrast failures, including the Sign In label at 2.61:1 and field edges at 1.24:1 (40). Horizontal scroll at 320 and 375 (34). The FAQ hero runs 1449px past a 1920x1080 screen (44d). And the home page's catalog is an empty state sitting behind an API error banner, so the page's one job is invisible on first load.

---

## Floor · 245 FAIL · nothing ships

| Gate | Count | Where | The tell |
| --- | --- | --- | --- |
| 10a | 87 | every component and page | `transition-all` on buttons, links, inputs, cards |
| 26a | 46 | all 4 routes, 1440px | focus ring 1.00 to 1.06:1 against what it is drawn over |
| 67 | 38 | admin, faq, modals, footer, wizard | tracked-caps labels at 9 to 15px |
| 30a | 27 | admin, wizard, WatchCard, MovieDetailModal | emoji standing in for an icon |
| 48 | 22 | [`frontend/app/globals.css:26`](frontend/app/globals.css:26) to `:88`, [`frontend/app/admin/page.tsx:840`](frontend/app/admin/page.tsx:840) to `:873` | colour literals outside the token block |
| 40 | 9 | all 4 routes, 1280px | text 2.61:1 and 4.23:1; field edges 1.24:1 |
| 58 | 4 | `/` 107 words, `/about` 242 words, `/faq` 114 words | more than 80 words in one 900px window |
| 19 | 3 | [`frontend/app/about/page.tsx:137`](frontend/app/about/page.tsx:137), [`frontend/app/admin/page.tsx:375`](frontend/app/admin/page.tsx:375), [`frontend/app/faq/page.tsx:98`](frontend/app/faq/page.tsx:98) | an em dash, "Unlock", "Everything You Need to" |
| 34 | 3 | [`frontend/app/globals.css:29`](frontend/app/globals.css:29) | `overflow-x: hidden` on body; scrollWidth 385 at 320 and 375 |
| 63 | 3 | [`frontend/app/page.tsx:763`](frontend/app/page.tsx:763), [`frontend/components/Footer.tsx:143`](frontend/components/Footer.tsx:143) | middle-dot meta strings |
| 44d | 1 | `/faq` at 1920 | hero ends at 1449px |
| 54 | 1 | [`frontend/components/FlixOrbitDiscovery.tsx:116`](frontend/components/FlixOrbitDiscovery.tsx:116) | eyebrow "Trending Highlight" |
| 33 | 1 | [`frontend/components/AuthModal.tsx:98`](frontend/components/AuthModal.tsx:98) | `<svg>` with no `aria-hidden` and no label |
| 20 | 1 (judged) | [`frontend/app/globals.css:1`](frontend/app/globals.css:1) | no Hallmark stamp; the file opens on `@tailwind` |

**The shape of it.** 87 of the 245 are one mechanical habit (`transition-all`), 46 are one missing token (`--color-focus`), 38 are one missing label recipe, 27 are one missing icon set, 22 are one missing token block. Five decisions clear 220 of the 245. The remaining 25 are real: the contrast pairs, the overflow, the FAQ hero, the screen budget, the copy.

---

## Reflex · 19 reported, 11 more by judgement

**Reported by sloplint**

| Gate | Count | Where | The tell |
| --- | --- | --- | --- |
| 44c | 4 | all 4 routes | hero ends at 465px, 624px, 64px of a 900px screen; `/faq` runs past the fold |
| 75 | 4 | all 4 routes | 9px and 10px running text |
| 79 | 3 | `/`, `/about`, `/admin` | 500px, 276px, 849px of nothing between the hero and the fold |
| 2b | 2 | [`frontend/app/page.tsx:488`](frontend/app/page.tsx:488), [`frontend/components/TicketFoxLogo.tsx:53`](frontend/components/TicketFoxLogo.tsx:53) | gradient text, three stops across two hues |
| 39b | 2 | `/`, `/faq` | controls at 30 to 32px, and 92px |
| 64 | 2 | [`frontend/app/admin/page.tsx:1073`](frontend/app/admin/page.tsx:1073), [`frontend/components/WatchWizardModal.tsx:1131`](frontend/components/WatchWizardModal.tsx:1131) | mono on labels |
| 3 | 1 | `/about` | equal columns of icon-above-heading tiles |
| 12 | 1 | [`frontend/components/MovieDetailModal.tsx:247`](frontend/components/MovieDetailModal.tsx:247) | `animate-bounce` on a bell |

**Judged from the screenshots**

- **8, the AI template.** `/about` is hero, two feature cards, four numbered steps, three feature cards, contact, footer. That is the reflex sequence with the numbers swapped in. `/` is hero, app shell, footer: two sections, no page.
- **9, section rhythm.** `/about` separates every section with the same card gap on the same surface. No rung of the ladder is climbed twice differently.
- **11, hover.** Three elements scale on hover in `FlixOrbitDiscovery`, three in `Footer`, and the `MovieCard` image itself scales ([`frontend/components/MovieCard.tsx:47`](frontend/components/MovieCard.tsx:47)).
- **29, glow and wash.** The 130px orb, the footer orb, the glass panel's backdrop blur, and `.glow-fox`'s zero-offset chromatic shadow. Four separate washes on one page.
- **38iii, the accented word.** "Opening Day" in orange inside a white heading, and again in the logo lockup.
- **42, chrome by reflex.** Wordmark left, inline links, button right, hairline under; footer with three link columns, a social row and a copyright. Neither is named in a stamp.
- **6b, the hero shape.** Headline, lede and two actions all on one centred axis, with no stamped posture.
- **66, decoration text.** The `v2.0` pill in the admin header, and the "TICKET ALERTS ⚡" caps strip under the wordmark.
- **69, the echo.** "Never Miss Opening Day" is the home hero and the About hero; the footer paragraph restates the hero's claim on every route.
- **47c, imitation material.** `via.placeholder.com` in `FlixOrbitDiscovery` (also a WARN).
- **23, accent footprint.** Under 5% on every route. Does not fire.

---

## WARN · 57 · confirm or dismiss

- **74 ×14** — the stock swatch: 8 to 28 distinct Tailwind palette classes per file (`text-slate-400`, `bg-rose-500`, `border-emerald-500`) beside the project's own `obsidian`/`fox` tokens. The project has a token system; the components do not use it.
- **49 ×11** — long button labels with no `nowrap` ("Polling Showtimes... Trigger Immediate", "Creating Watch... Enter 10-Digit").
- **F2 ×6** — three-period ellipses in prose.
- **F19 ×4** — five font weights in running use (400, 500, 600, 700, 800).
- **77 ×4** — every route reports 2 sections, hero and footer included.
- **29 ×4** — the washes above, as WARN.
- **11 ×3** — hover scale, as WARN.
- **F24 ×3** — a hairline border under a wide soft shadow.
- **F26 ×3** — heads ending on a stub at 375.
- **28a ×2** — the first image is lazy-loaded and is likely the LCP.
- **47c ×1**, **58 ×1** (the hero lede runs 22 words).

---

## What each depth settles

| Depth | Settles | Leaves |
| --- | --- | --- |
| **polish** | 10a, 26a, 30a, 33, 34, 40, 48, 54, 63, 67, 19, 2b, 12, 39b, 64, 75, 29, 11, 42 (named), 47c, and the F-checks. Roughly 240 of the 245 FAILs, mechanically. | 58, 44c, 79, 6b, 8, 9, 77, 38iii, 66, 69, 74, F19. The page still reads as a hero over an app shell. |
| **restyle** | all of polish, plus 74 (one token set), F19 (three weights), the type scale, the focus token, the icon set, the surface ladder. | 58, 44c, 79, 6b, 8, 9, 77, 38iii, 66, 69. The composition is untouched. |
| **full** | everything above, plus the composition: a hero with a posture that fills its screen, a page built from the category's anatomy rather than hero-plus-shell, sections with mass, the product shown. | Nothing in the gate list. |

**What only a full run would settle, and why it matters here.** The home page's problem is not its tells. It is that the page is a hero, then a tabbed app shell, then a footer, and the app shell is empty on first load because the backend is down. The one action the page exists to drive (create a watch) sits under an error banner. A polish makes that page clean and still leaves it a landing strip. A full run would give the hero a posture, put the product's own object in it (a watch being created, a drop being caught), and build the sections from what this category actually has: the city, the cinema, the showtime, the alert channel, the record of what was caught.

**What a full run would not fix, and should not pretend to.** The catalog is empty because `localhost:8000` is not running. No depth fixes that; it is a wiring fact, and the audit records it as such.

---

## Files a full run would touch

Read-only here; listed so the scope is visible before anyone approves a build.

- **Edit:** [`frontend/app/globals.css`](frontend/app/globals.css) (the stamp, the token block, the focus token, `overflow-x: clip`), [`frontend/app/page.tsx`](frontend/app/page.tsx), [`frontend/app/about/page.tsx`](frontend/app/about/page.tsx), [`frontend/app/faq/page.tsx`](frontend/app/faq/page.tsx), [`frontend/app/admin/page.tsx`](frontend/app/admin/page.tsx), [`frontend/components/Navbar.tsx`](frontend/components/Navbar.tsx), [`frontend/components/Footer.tsx`](frontend/components/Footer.tsx), [`frontend/components/MovieCard.tsx`](frontend/components/MovieCard.tsx), [`frontend/components/WatchCard.tsx`](frontend/components/WatchCard.tsx), [`frontend/components/MovieDetailModal.tsx`](frontend/components/MovieDetailModal.tsx), [`frontend/components/WatchWizardModal.tsx`](frontend/components/WatchWizardModal.tsx), [`frontend/components/AuthModal.tsx`](frontend/components/AuthModal.tsx), [`frontend/components/SettingsModal.tsx`](frontend/components/SettingsModal.tsx), [`frontend/components/AlertHistory.tsx`](frontend/components/AlertHistory.tsx), [`frontend/components/FlixOrbitDiscovery.tsx`](frontend/components/FlixOrbitDiscovery.tsx), [`frontend/components/MobileNav.tsx`](frontend/components/MobileNav.tsx), [`frontend/components/TicketFoxLogo.tsx`](frontend/components/TicketFoxLogo.tsx), [`frontend/components/Toast.tsx`](frontend/components/Toast.tsx), [`frontend/tailwind.config.js`](frontend/tailwind.config.js).
- **Create:** `frontend/app/tokens.css`, `frontend/app/base.css`.
- **Delete:** none. No route, component or test is removed.
- **Kept:** every link, form, field, handler, `id` and test hook recorded in `.hallmark/before.json` (24 handlers and 4 ids on `/admin`, the FAQ toggle, the mailto and social links on `/about` and `/faq`), the `obsidian`/`fox` palette, Outfit and Plus Jakarta Sans, the `DESIGN.md` motion curve.

---

## Verdict

**Floor 245 FAIL · Reflex 19 reported + 11 judged · WARN 57.** The system is real and the copy is honest; the execution is where the machine shows. The lightest depth that clears the Floor is **polish**. The depth that makes the home page do its job is **full**, because the page's shape, not its tells, is what is failing.
