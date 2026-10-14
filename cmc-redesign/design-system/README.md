# Cayman Mortgage Calculator

Plan your home. Know your numbers.

The design system for caymanmortgagecalculator.com. Its light theme was measured from one page screenshot of a real-estate site layout (the file in `assets/Other/`) chosen as the reference; every light value below was read from the pixels or inferred from the layout. The dark theme is derived from the same navies, not measured. Where the screenshot could not settle something, the section says so under **Open**.

## Principles

- **Navy carries the brand; white carries the content; teal points.** Three navies (`navy-900`, `navy-700`, `navy-600`) do the structural work — bars, buttons, the one accent word in a heading. One teal (`teal-600`, the logo's own) marks what is new, positive or live: badges, trend figures, focus rings. It is a highlighter, never a surface — no teal buttons, no teal bands.
- **Cards, not sections.** Content is grouped in rounded white cards and bands (`radius-md`, `radius-lg`) with hairline edges (`line-100`) and a soft shadow (`shadow-sm`), never left-border or coloured cards.
- **One accent word.** Headings are `ink-900`; a single word may switch to `navy-700` ("Find Your Perfect **Home**"). Never more than one per heading.
- **Room to breathe.** An 8px grid, 48px between sections, 24px between cards, 96px side margins at desktop.
- **Phone first.** Most visitors arrive on a phone. Three breakpoints: desktop above 860px; tablet 600 to 860px, where multi-column grids drop to two columns and the nav collapses into a drawer; phone below 600px, single column. Touch targets are 44px or more, wide tables scroll sideways with a "swipe" hint, the header is sticky (utility bar hidden on small screens, logo capped at 36px, CTA moves into the drawer), every page opens at the top, and a BackToTop button appears after a screen of scrolling.
- **Plain punctuation in copy.** No em or en dashes anywhere on the site (page titles, labels, hints, guides, generated text). Join clauses with a colon, semicolon, comma or full stop instead; write ranges as "0.5-1%" or "CI$250,000 to CI$350,000"; a hyphen only where a word or range needs one.

## Colour

| Token | Value | Where it appears in the source |
| --- | --- | --- |
| `navy-900` | `#011533` · dark `#050f24` | utility bar, footer, CTA band |
| `navy-700` | `#002767` · dark `#3b6fd1` | primary buttons, hero accent word, outline icons, active nav |
| `navy-600` | `#013484` · dark `#2f5fbf` | Subscribe button, "For sale" badge, button hover |
| `navy-300` | `#6e92d0` | translucent favourite chip over listing photos |
| `navy-100` | `#eaf2fd` · dark `#16284a` | newsletter band, feature-row icon circles |
| `teal-600` | `#0f7c7e` · dark `#5fd4cb` | "For rent" / "New" badges, +12.5% trend figure, focus rings (replaces the reference's green) |
| `teal-300` / `teal-100` | `#5fd4cb` / `#e3f4f3` (dark `#12393c`) | highlights on navy / badge and callout tint |
| `on-teal` | `#ffffff` (dark `#0b1730`) | text on teal-600 |
| `ink-900` / `ink-700` / `ink-500` | `#0a0b10` / `#3f3f44` / `#707072` (dark: `#f4f6fb` / `#d3d9e6` / `#9aa6bd`) | headings and prices / body / secondary text |
| `line-300` / `line-100` | `#88888c` / `#e7e9ee` (dark: `#566480` / `#1f2d49`) | outline-button borders / dividers and input borders |
| `surface-100` / `surface-0` | `#f0f1f5` / `#ffffff` (dark: `#15223d` / `#0b1730`) | inactive pill tabs / page and cards |
| `on-dark` / `on-dark-muted` | `#ffffff` / `#a6b7d5` (same in both themes) | text on any navy |

Rules:

- Text on `surface-0` is `ink-700` or darker; `ink-500` is the floor (4.7:1 light, 6.9:1 dark) and is for secondary lines only.
- **Dark theme** — `surface-0` becomes a navy ground (`#0b1730`); the two action navies lift to `#3b6fd1` / `#2f5fbf` so white text stays above 4.5:1, and `navy-900` drops a step below the ground so bars and the footer still read as bands. Switch with `data-theme="dark"` on `<html>`.
- Every navy takes `on-dark` text. `on-dark-muted` is for footer links and secondary lines on `navy-900` only.
- `teal-600` passes 5.0:1 with white text in light; in dark the token itself lifts to Shallows and takes `on-teal` (navy) text. `teal-300` is for navy surfaces only.
- Status is told apart by lightness, not hue: "For sale" is `navy-600`, "For rent" is `teal-600` — both read as a label even without colour because the text differs.

## Typography

One sans family across the whole page: **Inter**, weights 400–700, hosted on Google Fonts (no files in this system). Load it once per page:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

The `sans` stack falls back to the system UI face if the link is missing.

- `display` 56/60 700 — hero only
- `heading-2` 32/40 700 under a `label` eyebrow — section titles
- `heading-3` 24/32 700 — headline in a dark band
- `heading-4` 18/24 700 — card prices, feature titles
- `body` 16/26, `body-sm` 14/22, `caption` 12/16 500
- `label` 12/16 700, uppercase, +0.08em — eyebrows ("FEATURED PROPERTIES") and badges
- `button` 14/20 600, `nav` 14/20 500

Sizes assume the 736px screenshot is a half-scale render of a 1440px page. If the real page is 1280 or 1920 wide, scale the Display group only.

## Spacing, radius, shadow

- Spacing: `space-1` 4 → `space-9` 96 on an 8px grid (4px only for icon gaps).
- Radius: `radius-sm` 6 (buttons, inputs, badges), `radius-md` 12 (cards, search panel), `radius-lg` 16 (bands), `radius-full` (icon circles, pill tabs).
- Shadow: `shadow-sm` on cards at rest; `shadow-md` only on the two floating elements (search panel over the hero, home-value chip over the CTA photo).

## Components

Eleven React components ship in `components/` under the `CMC` global (React 18 carried in `components/lib/`): `Button`, `Input`, `Select`, `PillTabs`, `Badge`, `Icon` (the Lucide subset), `ListingCard`, `CalculatorPanel`, `Header`, `Footer`, `Byline` (author, reviewer, sources-checked and updated dates: on every guide and calculator), `BackToTop` (floating return-to-top button on every page), plus the exported `payment()` formula. Each has guidelines in its own README and a live preview. Together they build the nine patterns below; the homepage and calculator page mockups are composed from them.

### Shared inputs

Purchase price, deposit %, interest rate and term are entered once and used everywhere. `CMC.inputs` holds the four values (`get()`, `set({...})`, `subscribe(fn)`, `reset()`), persists them in `localStorage` under `cmc.inputs`, and syncs across open tabs through the `storage` event. `CalculatorPanel` reads and writes it; any `Input` with `bind="price" | "deposit" | "rate" | "term"` is a live two-way control on the same value; pages that only display a figure (listings' monthly estimates, the stamp duty and closing-cost pages) read `CMC.inputs.get()` and re-render on `subscribe`. A fifth shared value, `currency` (`KYD` default or `USD`), chooses the display currency: all maths stays in CI$ (stamp duty bands are set in CI$) and `get()` returns `fx` (1 or 1.20, the fixed peg CI$1 = US$1.20) and `symbol` (`CI$`/`US$`) for display and entry. Defaults: CI$650,000, 10% down, 7.75% (KYD prime 7.00% + 0.75), 25 years. The visitor never types the same number twice, and a figure shown on one page always matches the next. On the live site, prefer `localStorage` over URL parameters for this; URL parameters are for sharing a link to a specific set of numbers.

## Layout patterns seen

1. **Utility bar** — `navy-900`, `caption` text with a leading outline icon, social icons right.
2. **Header** — logo left, `nav` links centred (Home · Calculators ▾ Mortgage / Equity / Affordability · Listings · Guides ▾ Stamp duty / Closing costs / Refinancing · Agents · About), one primary button right (`navy-700`, `radius-sm`).
3. **Hero** — `display` heading with one accent word, `body` lead, primary + outline button pair, photo bleeding right with `radius-lg`.
4. **Search panel** — white card (`radius-md`, `shadow-md`) overlapping the hero bottom by half its height; pill tabs (Buy / Rent / Sell) above, labelled selects in a row, primary button at the end.
5. **Feature row** — four items: `navy-100` circle with a `navy-700` outline icon, `heading-4` title, `body-sm` in `ink-500`.
6. **Listing card** — photo with a `label` badge top-left, a favourite chip top-right and a "Compare" chip bottom-left (up to four listings go into a side-by-side table with the best value per row in teal); `heading-4` price, `body-sm` address, a `caption` meta row with icons separated by `line-100`.
7. **Dark CTA band** — `navy-900`, `radius-lg`, `heading-3` + `body` in `on-dark`, white button; photo on the right with a floating white chip.
8. **Newsletter band** — `navy-100`, icon circle, `heading-4`, input + `navy-600` button.
9. **Footer** — `navy-900`, brand column plus four link columns (Calculators, Guides, Listings, About) in `body-sm` `on-dark-muted`, hairline (`on-dark` at low alpha) above the legal row.

## Iconography

**Lucide** (lucide.dev), outline, `stroke-width` 1.5, round caps and joins, on its 24px grid — the same construction as the reference's icons and the logo mark. Colour is `navy-700` on light surfaces, `on-dark` on navy. In feature rows and bands an icon sits centred in a 48px `navy-100` circle (`radius-full`); when the feature is a calculator result the circle is `teal-100` and the icon `teal-600`. On photos the icon sits in a 32px translucent `navy-300` circle in `on-dark`. No filled icons.

Recommended set for this site: `house`, `calculator`, `percent`, `landmark` (bank), `file-text` (stamp duty), `receipt` (closing costs), `map-pin`, `bed-double`, `bath`, `ruler`, `search`, `heart`, `arrow-right`, `chevron-down`, `mail`, `phone`, `shield-check`, `trending-up`, `external-link` (listing opens on the agent’s site).

## App icons

`assets/App icons/` holds the favicon set built from the mark on a `logo-navy` rounded square: `favicon.svg` (any size, 2-key calculator), `favicon-16/32/48.png`, `apple-touch-icon-180.png`, `icon-192.png`, `icon-512.png` and `icon-512-maskable.png` (square bleed for Android). `icon-512.svg` is the full 6-key source. A `favicon.ico` (16+32) exists in the site repo but the system cannot store `.ico`; generate it from `favicon-16.png` + `favicon-32.png` at build time.

## Logo

Twelve SVG lockups live in `assets/Logos/` (see its README for the table): mark, submark, wordmark, secondary, primary and stacked, each in a `-color` version for light surfaces and a `-reversed` version for navy and photos.

- **Header**: `cmc-secondary-color.svg` at 160px wide on `surface-0`; `cmc-secondary-reversed.svg` on `navy-900`.
- **Footer**: `cmc-secondary-reversed.svg` at 140px wide.
- **Hero / documents**: `cmc-primary-*.svg` (carries the tagline).
- **Favicon / avatars**: `cmc-mark-*.svg`; square social slots: `cmc-submark-*.svg`.

The files use `logo-navy` `#0e2a47` for the mark and name and `teal-600` / `teal-300` for the roofline bar — the same teal the UI now uses as its accent, so the logo and the page agree. Never recolour the files to match `navy-700`.

## Open

- **Sora** — the brand pack named Sora; this system uses Inter by decision (Oct 2026). Revisit if print collateral needs to match.
