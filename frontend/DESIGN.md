# TicketFox Design System (DESIGN.md)

## 1. Visual DNA & Archetype
- **Archetype**: Cinema Command Center — high-velocity, high-density yet breathable, dark-mode-first aesthetic with radiant amber/fox accents.
- **Tone**: Precision, authoritative, real-time, responsive, fluid.
- **Anti-AI-Slop Guardrails**:
  - No generic blue/cyan gradients.
  - No decorative oversized blurred blobs that cause scroll stutter.
  - No fake buttons or inert controls.
  - Real contrast ratios complying with WCAG 2.2 AA.
  - Micro-interactions following Emil Kowalski's motion physics (ease-out-expo `cubic-bezier(0.16, 1, 0.3, 1)`, tactile spring feedback, subtle scale downs).

## 2. Color Palette & Semantic Roles

All colour lives in `frontend/app/tokens.css` as CSS custom properties in the
`oklch()` space. Components never hard-code a colour; they consume either a token
or a semantic class (see §7).

- **Base Canvas (Obsidian Dark)** — `--color-paper` ladder:
  - `--color-paper`: `oklch(0.13 0.008 265)` — deepest canvas (`#06070a`)
  - `--color-paper-2`: `oklch(0.155 0.010 265)` — cards, dialogs, drawers
  - `--color-paper-3`: `oklch(0.185 0.012 265)` — sunken inputs, table stripes
  - `--color-paper-4`: `oklch(0.215 0.014 265)` — hovered cards, overlays
- **Ink**:
  - `--color-ink`: `oklch(0.97 0.005 250)` — primary text
  - `--color-ink-2`: `oklch(0.88 0.010 250)` — secondary text
  - `--color-muted`: `oklch(0.71 0.020 250)` — captions, hints
- **Borders & Dividers**:
  - `--color-rule`: `oklch(0.30 0.014 265)` — default border
  - `--color-rule-soft`: `oklch(0.24 0.012 265)` — subtle divider
- **Primary Accent — cinematic amber/orange**:
  - `--color-accent`: `oklch(0.70 0.20 48)` — `#ff7a00`, the brand
  - `--color-accent-hover`: `oklch(0.76 0.17 52)` — hover
  - `--color-accent-quiet`: `oklch(0.62 0.19 45)` — active / deep
  - `--color-accent-ink`: `oklch(0.13 0.008 265)` — dark ink on amber (8.1:1)
  - `--color-focus`: `oklch(0.76 0.17 52)` — focus ring (8.4:1 on paper)
- **Secondary Accent — restrained violet** (new; never competes with amber):
  - `--color-accent-2`: `oklch(0.62 0.19 295)` — secondary emphasis
  - `--color-accent-2-hover`: `oklch(0.68 0.19 295)`
  - `--color-accent-2-quiet`: `oklch(0.62 0.19 295 / 0.14)` — wash for chips/rails
  - `--color-accent-2-ink`: `oklch(0.98 0.01 295)` — light ink on violet fills
  - **When to use violet**: secondary CTA / "browse" affordance, informational
    states, the admin "operate" mode, and secondary data emphasis. Amber always
    wins for the primary action and brand moments.
- **Semantic Feedback**:
  - Success / Open: `--color-success` `oklch(0.78 0.15 165)`
  - Warning / 15-min radar: `--color-warning` `oklch(0.84 0.16 85)`
  - Info / Universal search: `--color-info` `oklch(0.78 0.12 230)`
  - Danger / Delete / Expired: `--color-error` `oklch(0.72 0.16 15)`
- **Semantic aliases** (so components stop naming raw ladders):
  - `--surface-canvas` / `--surface-raised` / `--surface-sunken` / `--surface-overlay`
  - `--text-primary` / `--text-secondary` / `--text-muted`
  - `--border-strong` / `--border-soft`

## 3. Typography
- **Headings**: `Outfit` (`--font-display`, geometric, cinematic punch, 600-800 weight)
- **Body & Data UI**: `Plus Jakarta Sans` (`--font-body`, neutral, crisp numerals)
- **Scale** (from `tokens.css`):
  - `--text-display`: `clamp(2.75rem, 5vw + 1rem, 5.25rem)` — hero
  - `--text-display-s`: `clamp(2.25rem, 4vw + 0.5rem, 3.75rem)`
  - `--text-section`: `clamp(2rem, 2.5vw + 1rem, 3.5rem)` — section headers
  - `--text-title`: `clamp(1.25rem, 0.75vw + 0.875rem, 1.625rem)` — card titles
  - `--text-lead`: `clamp(1.125rem, 0.35vw + 1rem, 1.375rem)` — lead paragraphs
  - `--text-md` / `--text-sm` / `--text-xs` — body, data, captions
- Display tracking: `--tracking-display: -0.025em`.

## 4. Spacing & Responsive Rhythm
- Spacing scale: `--space-3xs` (2px) → `--space-4xl` (144px).
- Section rhythm: `--section-gap-s` (120px) / `--section-gap` (144px) / `--section-gap-l` (176px).
- Container: `--container: 1440px`, gutter `--gutter: 64px`, column gap `--gap-columns: 32px`.
- Mobile safe-area: `env(safe-area-inset-bottom)`.
- Touch target minimum: `44px × 44px` for interactive mobile touchpoints.
- Breakpoints: `60rem` (tablet) and `40rem` (mobile) are the standard cut points.

## 5. Motion & Transitions (Emil Kowalski Physics)
- Durations: `--dur-micro` (120ms) / `--dur-short` (220ms) / `--dur-long` (420ms).
- Easing: `--ease-out: cubic-bezier(0.16, 1, 0.3, 1)` (out-expo, crisp entrance).
- **Never use `transition-all`** — transition the specific properties
  (`background-color`, `border-color`, `color`, `transform`, `opacity`).
- Button feedback: `active: scale(0.97–0.98)` tactile press.
- Radar pulse: 2s loop on active hunts with subtle outer ring fade.
- Reduced motion: `@media (prefers-reduced-motion: reduce)` disables scale,
  pulse, and the semantic-layer entrance animations.

## 6. Semantic Class Layer (the rule)

`frontend/app/globals.css` defines a semantic layer that every component must
use instead of Tailwind colour literals. **No component may use `bg-obsidian-*`,
`text-slate-*`, `text-amber-*`, `glass-card`, `glass-panel`, `border-white/*`, or
`transition-all`.** Use:

- Surfaces: `.surface` / `.surface-raised` / `.surface-sunken` / `.surface-overlay`
- Text: `.text-primary` / `.text-secondary` / `.text-muted` / `.text-accent` / `.text-accent-2`
- Borders: `.border-strong` / `.border-soft`
- Badges: `.badge` + `.badge--accent` / `.badge--accent-2` / `.badge--success` /
  `.badge--warning` / `.badge--danger` / `.badge--muted`
- Buttons: `.icon-btn` (icon-only), plus the existing `.btn-primary` / `.btn-quiet`
- Modal shell: `.modal-backdrop` / `.modal-panel` / `.modal-head` / `.modal-body` / `.modal-foot`
- Toast: `.toast` + `.toast--success` / `.toast--error` / `.toast--info`
- Loading: `.skeleton`
- Fields: `.field-label` / `.field-input` / `.field-hint` / `.field-error`
- Empty states: `.empty-state` / `.empty-state-title`

Icons are `lucide-react` components — **no emoji used as UI icons**.

## 7. Data Sources (single source of truth)
- All network calls go through `lib/api.ts` (`apiFetch` + `ApiError`); no component
  calls `fetch` against the backend directly.
- Cities come from `GET /api/cities` via `lib/cities.ts`; there is no local city list.
- The admin identity comes from `lib/admin.ts`, matching the backend `ADMIN_UID`.
- Phone input is normalised by `lib/phone.ts` `toIndianDigits` in both the wizard and
  Settings, so the two cannot disagree about what a valid number looks like.
- TMDB reads go through `lib/tmdb.ts` -> `GET /api/tmdb`; the API key never ships to
  the browser and no component builds a TMDB URL itself.
