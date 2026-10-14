# Design system brief — Cayman Mortgage Calculator

A prompt for creating a new design system for **caymanmortgagecalculator.com**.
Hand this to a designer or an AI assistant. It describes a real, shipped site, so
read the constraints before proposing anything: several obvious choices are ruled
out by how this site is built.

---

## 1. What this is

A free tool that works out what buying a property in the Cayman Islands actually
costs, then shows the homes and land for sale that fit. It is not a lead-generation
funnel and not a listings portal. Its value is arithmetic the visitor can trust.

**Who uses it**

- First-time Caymanian buyers, who get substantial stamp duty relief and are usually
  working out whether they can buy at all.
- Residents and expatriates, often non-residents buying remotely, who do not know
  Cayman's duty rules and are comparing against prices in another currency.
- Owners weighing releasing equity, or renting against buying.

Most arrive on a phone. Many are doing the single largest financial calculation of
their life. **The design's job is to make a stack of numbers legible and credible.**

---

## 2. Hard constraints

These are not preferences. A design system that ignores them cannot be built here.

| Constraint | Detail |
| --- | --- |
| **No framework, no build step** | Hand-written CSS and ES5 JavaScript. No Tailwind, no Sass, no PostCSS, no npm. Python assembles the HTML. |
| **One stylesheet** | `web/app.css`, currently 629 lines and 498 selectors, served as one file. |
| **No CSS nesting or `@layer`** | Must work in older Safari on iOS. Custom properties and `@media` are fine. `:has()` is used twice, for the disabled and
invalid states of `.control`, and must stay a progressive enhancement. |
| **Static hosting** | GitHub Pages. No server, no headers, no cookies, no runtime theming service. |
| **Content Security Policy** | Set via `<meta>`. External resources are limited to Google Fonts and Cloudflare analytics. No new third-party origins without changing the CSP. |
| **Two fonts, by the owner's decision** | Sora for headings, Instrument Sans for body. A single-font system was built and rejected. Do not propose dropping Sora. |
| **Three theme states** | System, forced light, forced dark — via `prefers-color-scheme` **and** a `data-theme` attribute on `<html>`. Every colour decision must resolve in all three. |
| **Native form controls** | `<select>` and `<input>` are the real browser widgets, themed with `color-scheme`. Do not propose custom dropdowns. |
| **Images are hotlinked** | Listing photos come from ~21 agency servers at unknown dimensions and aspect ratios, and some fail to load. No `srcset` is possible. |

---

## 3. The surfaces

Five pages, sharing a header, footer, theme toggle and skip link.

1. **Home** (`/`) — hero, an eight-tile statistics banner, six featured property
   cards, a market-by-district table, four explainer cards, an FAQ accordion.
2. **Mortgage calculator** (`/calculator/`) — by far the densest page. A long input
   form, a headline result, a stacked cost bar, an amortisation chart and optional
   table, scenario comparison, saved scenarios, a duty-facts panel, and the full
   listings browser (filters, source chips, card grid, compare tray, shortlist).
3. **Equity calculator** (`/equity/`) — two routes (borrow more / refinance), inputs,
   results, LTV guidance, sources.
4. **Rent vs buy** (`/rent-vs-buy/`) — horizon control, scenario bands, a break-even
   chart, a sensitivity table.
5. **404** — header, apology, routes back.

---

## 4. Component inventory

Grouped by the class prefixes actually in the stylesheet. Counts are top-level
selectors beginning with that prefix.

| Prefix | Rules | What it is |
| --- | --- | --- |
| `lx-` | 22 | The listings browser: card, photo, tags, price, facts, calc grid, missing-data note, actions, status line, filters, empty states |
| `hero-` | 7 | Hero band, lede, CTA pair, large figure |
| `cmp-` | 7 | Compare panel — a modal with a side-by-side table |
| `bd-` | 7 | Breakdown dialog — itemised cost sheets for "monthly to own" and "cash to close" |
| `stat`, `top`, `feat`, `faq`, `section`, `card` | ~15 | Front-page furniture |
| `scen-`, `saved-`, `meter-`, `multi-`, `src-` | ~11 | Scenario comparison, saved scenarios, affordability meters, multi-select area menu, source status |
| `skel-` | 3 | Loading skeletons |
| `toast`, `tip`, `tag`, `sw` | 4 | Transient feedback, tooltips, chips, switch |

Also: buttons (`.btn`, `.btn.primary`, `.btn.icon`, `.go`, `.alt`), pills
(`.pill.good/.warn/.crit/.neutral/.taken`), form fields (`.field`, `.control`,
`.inputs`, `.seg`, `.chip`), hairline-divided grids (`.kpis`, `.budget`,
`.duty-facts`, `.stat-grid`, `.lx-calc`, `.faq`).

---

## 5. Current tokens

The starting point. Replace or refine; do not assume these are good.

**Light**

```
--bg:#f5f3ee        --surface:#ffffff     --surface-2:#eceae4
--ink:#0e2a47       --ink-2:#4a5868       --ink-3:#71808f
--line:#ded9d0      --line-strong:#c2bcb1
--accent:#0f7c7e    --accent-soft:#dfefee --on-accent:#ffffff
--hero-bg:#0e2a47   --hero-ink:#ffffff    --hero-ink-2:#a9c4d8
--good:#0ca30c      --warn:#fab219        --crit:#d03b3b
--s1:#2a78d6        --s2:#eb6834          --s3:#1baf7a     (chart series)
--shadow:0 1px 2px rgba(15,34,48,.05), 0 10px 28px rgba(15,34,48,.06)
```

**Dark** overrides the same names; the accent is `#4bb3ad`, deliberately
desaturated from the light `#0f7c7e`.

**Type** — six screen sizes: `12 / 14 / 16 / 20 / clamp(22,2.6vw,28) /
clamp(28,4vw,44)`. Headings track `-2.5%` at `1.15` leading.

**Spacing** — a 4-point scale: `4 8 12 16 20 24 28 32 40 48`. Note `1px` gaps are
used deliberately as hairline dividers over a coloured background; they are borders,
not spacing, and must survive.

---

## 6. Problems to solve

Found by auditing the live stylesheet. Address each explicitly.

1. **No breakpoint scale.** Thirteen distinct media conditions are in use:
   `330, 560, 620, 700, 939.98, 940, 1000, 1100`, plus `pointer:coarse`,
   `prefers-reduced-motion`, two spellings of `prefers-color-scheme`, and `print`.
   Define a small named scale and migrate everything to it.
2. **No grid system.** Layouts use ad-hoc `auto-fill`/`auto-fit` with varying
   `minmax()` floors. The target is 12/8/4 columns at desktop/tablet/mobile, with
   bespoke sections free to break out.
3. **Density is unmanaged.** A listing card carries price, original currency, title,
   area, up to five facts, two figures with info buttons, a caveat band, a
   provenance line and three controls. The calculator page is denser still. There is
   no defined notion of a compact versus comfortable density.
4. **Colour is not derived.** The palette was hand-picked rather than generated from
   a primary. Tints and shades should be derived and documented.
5. **Elevation is one token.** A single `--shadow` serves cards, popovers and modals,
   which should not read the same.
6. **Chart colours sit outside the system.** `--s1/--s2/--s3` were chosen ad hoc and
   are not checked for colour-blind safety or dark-mode legibility.
7. **Headline figures exceed the dashboard ceiling.** The standard caps dashboard
   numbers near 24px; the hero figure is `clamp(28,4vw,44)`. Resolve deliberately —
   either cap it or justify the exception.
8. **Button padding is unsystematic.** The standard asks width ≈ 2× height in padding.

---

## 7. Quality standard to meet

**Hierarchy and signifiers.** The UI explains itself: containers group, active and
selected states are visible, inactive items are greyed, tooltips where needed. No
instructions required. Build hierarchy with size, position and colour contrast — the
most important item largest, boldest, highest. Use icons and alignment rather than
words to show relationships.

**Layout and spacing.** Grids are guides, not rules: 12/8/4 columns for repeating
content, bespoke sections may break out. Prioritise white space; 32px between items
by default, pulling related items closer. All spacing on a 4-point scale.

**Typography.** Max six font sizes on landing pages; dashboards top out around 24px.
Large headings: letter-spacing −2% to −3%, line-height 110–120%.

**Colour.** Start from one primary and derive lighter tints for backgrounds, darker
shades for text. Semantic colour only where it carries meaning — blue for
trust/information, red for danger, yellow for warning, green for success. Never
decorative.

**Dark mode.** Lower-contrast borders. Depth from cards lighter than the background,
not from shadows. Desaturate and dim bright accents.

**Shadows (light mode).** Low opacity, high blur. Subtle on cards, stronger on
popovers and overlays. A shadow should never be the first thing noticed.

**Icons and buttons.** Icon size equals adjacent text line height. Pair a primary CTA
with a ghost secondary. Button width ≈ 2× height in padding.

**Feedback and states.** Every button: default, hover, pressed, disabled, and loading
where relevant. Every input: focus, error with a red border and a message, warning
where relevant. Loading states, success confirmations, and micro-interactions for
every action.

**Images with text.** Never a flat full overlay. Use a linear gradient fading to a
readable background; progressive blur optional.

---

## 8. Domain rules the design must protect

This site's credibility rests on these. A redesign that breaks one is a failure even
if it looks better.

- **Unknown is not zero.** A listing never publishes a condo's strata fee. Those read
  "Not listed" in italics, are excluded from totals, and the total is labelled a
  floor ("Monthly, from"). Never style an unknown as if it were a figure.
- **Estimates are labelled as estimates**, and the settings that produced them are
  always stated.
- **Stale data says so.** When a source could not be read, its listings still show,
  marked with the time they were last read. Design a treatment for stale-but-shown.
- **Excluded sources are explained, not hidden.** Four agencies are paused pending
  permission and appear on the page with the reason.
- **Two currencies.** Prices show in KYD with the original (often USD) beneath.
  Figures use tabular numerals and must not shift as they change.
- **Thresholds matter more than gradients.** Cayman duty steps at CI$550k, 600k, 650k,
  700k, 2M, and 300k for mortgage duty. Crossing one costs real money, so the design
  must be able to call out a cliff.
- **Concessions are the good news.** A zero duty line is the Cayman Brac concession or
  first-time relief working. Zero must be displayable and explainable, never hidden
  as an empty value.
- **Status is not decoration.** "Under Offer" and "Pending/Conditional" use the
  warning colour because they change what the reader should do.

---

## 9. Accessibility

Non-negotiable, and already partly in place.

- WCAG 2.2 AA contrast in all three theme states, including text over the navy hero
  and text over listing photographs.
- Visible focus on every interactive element. A skip link is the first tab stop.
- Modals trap nothing but manage focus: focus moves in on open, returns to the
  trigger on close, Escape closes.
- Respect `prefers-reduced-motion` — all current transforms and the skeleton shimmer
  already disable under it.
- Touch targets at least 44×44 CSS px; there is a `pointer:coarse` block today.
- Colour never the sole carrier of meaning.
- Live regions announce asynchronous changes such as listings loading.

---

## 10. Do not change

Content, arithmetic and behaviour are out of scope.

- No wording changes to figures, captions, disclaimers or duty explanations.
- No change to what is calculated or how. `web/core.js` and its 92 tests stay as they
  are.
- Keep the existing URL structure, the five page types, and the nav order: Home,
  Mortgage Calculator, Equity Calculator, Listings, Rent vs Buy.
- Keep the logo and the brand navy `#0e2a47`.
- Keep every feature: shortlist, compare, saved scenarios, shareable links, the
  breakdown dialogs, filters and source chips.

---

## 11. Deliverables

1. **Token set** as CSS custom properties, defined for light and dark, covering
   colour, type, spacing, radius, elevation, motion and breakpoints. Document how
   each colour is derived from the primary.
2. **Type scale** of at most six screen sizes, with the role of each, and the
   dashboard ceiling resolved.
3. **Grid and breakpoint system** — named breakpoints, 12/8/4 columns, container
   widths, gutters.
4. **Component specifications** for the inventory in §4. For each: anatomy, every
   state, density behaviour, and mobile treatment. Prioritise the listing card, the
   stat tile, the breakdown dialog, form fields, and buttons.
5. **A rewritten `web/app.css`** honouring §2, replacing the current file, with the
   1px hairline dividers preserved.
6. **A migration note** listing every class that changed, since the HTML templates
   (`web/*.html`, `page.py`, `home.py`) reference these names directly.
7. **A one-page visual reference** showing the system applied to: a listing card, the
   stat banner, a populated form, the breakdown dialog, and an empty state — in light
   and dark.

---

## 12. Acceptance checks

The result is done when all of these hold.

- [ ] Every surface in §3 renders correctly in system, forced light and forced dark.
- [ ] At most six screen font sizes; all spacing on the 4-point scale; hairline
      dividers intact.
- [ ] One named breakpoint scale, with the thirteen ad-hoc conditions gone.
- [ ] Every button has default, hover, pressed, disabled and loading states; every
      input has focus and error states.
- [ ] AA contrast throughout, including over the hero and over photographs.
- [ ] Keyboard-only navigation works end to end, skip link first.
- [ ] `prefers-reduced-motion` disables all motion.
- [ ] No horizontal scroll at 320px.
- [ ] No new third-party origins, or the CSP is updated to match.
- [ ] `node test/core.test.js` still passes 92 tests.
- [ ] Every §8 rule is visibly honoured, especially "Not listed", stale sources and
      zero-duty concessions.

---

## 13. How to work

Propose the token set and the listing card first, and get those agreed before going
further — the card is the most repeated and most information-dense element on the
site, and a system that handles it will handle the rest. Work on a branch, build with
`python build_site.py`, and review against the live site before merging. Nothing
deploys without the owner's approval.
