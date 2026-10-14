# Redesign follow-up 1: match the boards exactly

The staging build at http://localhost:8790/ has the right structure, real listings and working routes, but it does not look like the approved boards. The causes are specific and small. Fix all of them, then re-check every page against `cmc-redesign/pages/*.dc.html` at 390, 820 and 1280 wide before reporting back.

## 1. Replace `assets/rd.css` with the updated stylesheet

`cmc-redesign/design-system/components/bundle.css` has been updated (base page styles, `color-scheme: light`, and it now styles any `input`/`select`/`textarea` placed directly inside `.cmc-field__control`, with or without the `cmc-field__input` class). Rebuild `rd.css` from `tokens.css` + the new `bundle.css` exactly as delivered, in that order, and keep any site-specific rules you added after them in a clearly marked third section. Do not edit the delivered rules; add overrides below them if something is missing.

## 2. Use the delivered class names, not your own

Audit every page for markup that drifted from the component contracts in `index.d.ts` and the `<Component>/README.md` files:

- Every `<input>`, `<select>` and `<textarea>` gets `class="cmc-field__input"` (`cmc-field__input cmc-field__input--select` for selects). 21 controls on `/calculator/` currently have no class, which is why they render with browser defaults (dark boxes, Arial, inset borders).
- Pill tabs: the active state class is `cmc-pill--active`, not `cmc-pill--on`. When pills are links, that is fine (the CSS now covers `a.cmc-pill`), but keep the class name.
- Header: every top-level nav item, including Home, is wrapped in `<div class="cmc-header__item">` (dropdown items in `cmc-header__item cmc-header__item--menu`), so spacing and the active underline match. Currently Home sits unwrapped and renders taller than its neighbours.
- Buttons: `cmc-btn cmc-btn--primary|secondary|ghost|onDark cmc-btn--sm|md`, with `cmc-btn--block` where the board says block.
- Listing cards, calculator panel, badges, byline, back-to-top: compare each rendered element's class list with `bundle.js` and correct any renamed or missing classes.

## 3. Missing pieces on `/calculator/`

- `window.XLSX` and `window.jspdf` are both undefined, so "Download full schedule (Excel)" and "Save as PDF" cannot work. Load SheetJS 0.18.5 and jsPDF 2.5.1 (CDN or vendored) and port the `download` and `savePdf` functions from `pages/Calculator.dc.html` as written, including the CSV fallback.
- The board's "Your household in detail" and "Fee assumptions" are collapsible `<details>` sections; the page currently has none. Restore them, with "Your household in detail" open by default and "Fee assumptions" closed.
- The hero on the calculator page is taller and plainer than the board: use the board's 40px-padded `navy-100` title band, 32px heading, 16px lead, not a full-height hero.

## 4. Things that are right and must stay

Real listings from the scraper (Elite Realty etc.) with photos, prices, monthly estimates and "View on agent's site"; the sticky header, dropdown toggles, back-to-top, footer columns, no long dashes in the rendered text, the bylines and summary section. Keep all of it.

## 5. Check before reporting

For each route, screenshot at 390, 820 and 1280 and compare with the matching board. Confirm: form controls look like the board (white field, 1px `line-100` border, teal focus ring, CI$ and % affixes inside the border); nav items align on one baseline; pills show the white active capsule; Excel and PDF downloads produce files; no element overflows the viewport (no horizontal page scroll). List anything you could not match in `REDESIGN-PLAN.md`.
