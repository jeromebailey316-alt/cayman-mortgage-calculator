# Redesign follow-up 2: review of the staging build (desktop and phone)

Reviewed http://localhost:8790/ on 14 October 2026 at desktop width and in a 375px phone viewport: homepage, calculator, listings, stamp duty guide. What works: Inter loads, no console errors, no horizontal overflow, sticky header, dropdown chevrons, phone drawer, back-to-top, shared inputs persist across pages (`cmc.inputs`), SheetJS and jsPDF load, bylines and sources present, no long dashes, real listings with photos and agent links. Fix everything below, in this order, then report.

## A. Must fix

1. **Listing cards are different heights.** On `/listings/` and the homepage the first cards are 562px tall and the rest 411px, because the photo sets the height of `.cmc-listing__media` (a 1080x1080 image renders 224px tall, a 1928x2560 one 297px, a 16:9 one 168px). `cmc-redesign/design-system/components/bundle.css` has been updated: the image is now absolutely positioned inside the 4:3 frame and clipped. Rebuild `rd.css` from the updated file. Every card in a row must be the same height; verify with `getBoundingClientRect()` across all cards.
2. **Cards without a photo show an empty pale box.** Render `<div class="cmc-listing__placeholder">` with the `house` icon (as in `bundle.js`) when the scraper has no image, and check why only 4 of 12 cards on `/listings/` had an image at all: if images are lazy-loaded, confirm they load on scroll; if the scraper has no photo for those listings, the placeholder applies.
3. **Listing titles are raw scraper strings** ("New 2Bed|2Bath in Prime Location in West Bay(END UNIT)"). Clean them before display: replace `|` with ", ", add a space before "(", collapse double spaces, keep the agent's wording otherwise. The address line is now clamped to two lines in CSS.
4. **"Buy" tab sits alone and is underlined.** Either restore the Rent tab (the board has Buy / Rent) with the scraper's rentals, or remove the pill bar until rentals exist. Underlines on pills come from the old CSS; the updated `bundle.css` fixes `a.cmc-pill`.
5. **Calculator banner mixes two figures.** It is labelled "Estimated monthly payment" but shows the all-in figure (CI$5,502, which includes insurance and maintenance), with the line "strata fees not entered, so this is a floor". Follow the board: the banner shows the mortgage payment (CI$4,419 at the defaults) with "on a CI$585,000 loan at 7.75% over 25 years"; the "Monthly cost of owning" card carries the all-in total. Remove the "floor" sentence.
6. **Currency toggle is missing** on the calculator (and affordability page). Add the CI$ / US$ pill toggle at the top of the inputs, bound to the shared `currency` input, converting display and entry at CI$1 = US$1.20 as in `pages/Calculator.dc.html`.
7. **Money inputs show raw digits** ("650000") and the price field in the homepage panel clips the value at narrower widths. Format money inputs with thousands separators on blur (text input, `inputmode="decimal"`, strip separators on parse), and give the panel's price column enough width that CI$1,000,000 fits at 1024px.
8. **Rent vs buy** appears in the nav drawer and footer but is not in the approved site map and has no board. Remove it from navigation (and the route, unless it already existed on the live site; if so, say so in `REDESIGN-PLAN.md`) rather than shipping an undesigned page.
9. **Stamp duty guide table on phones**: the first column wraps "Group of 2-10 Caymanians" over three lines. Set `white-space: nowrap` on the first column, shorten the label to "Group of 2-10", or let the column take 40% width. Same check for the closing-costs tables.
10. **Phone headings**: apply the boards' phone sizes (`h1` 36px/42px below 860px) so "Homes for sale in the Cayman Islands" does not run to three lines at 44px.

## B. Should fix

11. **Nav text crispness.** The owner sees the "L" of "Listings" pixelated on his screen. Make sure nothing in the header uses a fractional transform or `backdrop-filter` while text is rendered (the sticky header must not be inside a transformed ancestor), that the active underline is an exact 2px border, and that the Inter 500 weight is actually loaded (`document.fonts.check('500 14px Inter')`), not synthesised from 400.
12. **Utility bar** lost its right-hand text ("Grand Cayman, Cayman Islands") and the second item; restore from the homepage board.
13. **Favourite (heart) chip** is missing from listing cards; the board has it top-right, with the state kept in `localStorage` like compare.
14. **Compare**: tick two cards and confirm the bar (pill on desktop, full-width strip on phones with the back-to-top lifted) and the comparison table render as on `pages/Listings.dc.html`; it was not exercised in this review.
15. **Closing-cost rows not in the board** ("Land Registry fees CI$100", the 45-day deadline) are fine if sourced; each needs an entry in the Sources block.

## C. Correction to the boards (already applied in `pages/`)

The staging build calculates the Caymanian first-property concession correctly: 3.75% applies only to the part of the value above the 0% threshold ("on the difference above $550,000 only", per the Ministry of Finance form). The earlier boards applied 3.75% to the whole value; `pages/Calculator.dc.html` and `pages/Affordability.dc.html` are now corrected and match. Keep the staging logic; use the boards' wording for the label ("3.75% above CI$550,000").

## D. Before reporting

Re-screenshot `/`, `/calculator/`, `/listings/`, `/affordability/`, `/guides/stamp-duty/` at 375, 820 and 1280 wide. Confirm every listing card in a row is the same height, the banner figure equals the mortgage payment, the currency toggle works, and no pill is underlined. Update `REDESIGN-PLAN.md` with anything you could not do and why.
