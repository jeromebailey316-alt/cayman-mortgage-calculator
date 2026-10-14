# Cayman Mortgage Calculator: apply the redesign

You are working in the repository for caymanmortgagecalculator.com. This folder (`cmc-redesign/`) is the hand-off from the design phase. Your job is to apply the redesign to the live site, page by page, keeping everything that already works (the listings scraper, hosting, routing) and replacing the look, the page structure and the calculators with what is specified here.

Work in a branch. Commit in small steps with clear messages. When something in the repo makes a decision below impossible or unwise, say so and choose the closest equivalent; do not silently drop a requirement.

## 0. First, inspect the repo and choose the approach

The owner does not know offhand what the site is built with. Before writing code:

1. Read the repo: package.json (if any), the entry pages, build scripts, hosting config, and the scraper that produces the listings (it already provides listing images and details; find where its output lands and in what shape).
2. Decide how to apply the redesign with the least disruption:
   - Plain HTML/CSS/JS site: build the components as a small vanilla or React layer, whichever the site can serve without a new toolchain. The reference components in `design-system/components/bundle.js` are classic-script React 18 (no JSX, no bundler); they can be used as they are with React loaded from a CDN, or ported to the site's own stack.
   - A framework (Next, Astro, Vite, etc.): port the components into that framework's conventions, keep the tokens as CSS custom properties.
   - A site builder: say so and describe what can and cannot be applied.
3. Write a short `REDESIGN-PLAN.md` at the repo root stating the stack you found, the approach you chose and why, then proceed.

## 1. What is in this folder

```
cmc-redesign/
  HANDOFF.md                     this file
  design-system/
    README.md                    the brand book: principles, colour, type, spacing, components, layout patterns, copy rules
    tokens.json                  every design token (light and dark themes)
    tokens.css                   the same tokens compiled to CSS custom properties
    components/
      bundle.js                  the 11 reference components (window.CMC), React 18, classic script
      bundle.css                 their styles, all values from tokens
      index.d.ts                 prop types for every component
      <Component>/README.md      usage rules per component
      <Component>/preview.html   how each one is used
  pages/                         the 16 approved page boards (HTML with the runtime templating noted in section 4)
  brand/
    logos/*.svg                  12 logo lockups (primary, secondary, stacked, wordmark, mark, submark; colour and reversed)
    icons/favicon.svg, icon-512.svg, favicon.ico
```

Read `design-system/README.md` and `design-system/components/index.d.ts` before building anything. Read each page board before building that page.

## 2. Non-negotiables

- **Tokens, not hex values.** Every colour, radius, shadow and font comes from `tokens.css`. Inter from Google Fonts (`wght@400;500;600;700`).
- **Teal (`teal-600`) is the single accent**; navy carries structure; white carries content. No green, no other accent.
- **No em or en dashes anywhere in copy**, including generated text, labels, titles, alt text and the PDF/Excel exports. Use a colon, semicolon, comma or full stop; a hyphen only in ranges ("0.5-1%") or compound words. The page boards already comply; keep them that way.
- **No email capture, newsletter sign-up or contact form.** Contact is the email address and Instagram handle only.
- **Every estimate is labelled an estimate**; the "not financial advice" lines stay.
- **Listings only with permission**; every listing card links to the listing on the agent's own site, opening in a new tab with `rel="noopener"`, and shows "View on agent's site".
- **Lucide icons only** (the subset in `bundle.js`; add from lucide.dev if a new one is needed, same stroke width 1.5).
- Phone first: see section 6.

## 3. Site map and navigation

Header (sticky on every width, `position: sticky; top: 0`):

```
Home | Calculators ▾ (Mortgage, Equity, Affordability) | Listings | Guides ▾ (Stamp duty, Closing costs, Refinancing) | Agents | About      [Run the numbers]
```

- The logo links to the homepage. The word "Calculators" or "Guides" links to the section's first page; the chevron beside it is a separate button that expands or collapses the dropdown (click again, click elsewhere or Escape closes it). Hover previews on desktop.
- Below 860px: utility bar hidden, header row 60px, logo capped at 36px, nav and CTA collapse behind a menu button that opens a full-width drawer (every link, groups expanded with icons, CTA as a block button at the bottom). Escape or any link closes it.
- Footer: brand column + Calculators (Mortgage, Equity, Affordability), Guides (Stamp duty, Closing costs, Refinancing), Listings (Buy, Rent, For agents), About (About the site, Contact, Privacy, Terms); legal row with © line and Privacy / Terms.
- Every page opens at the top (`history.scrollRestoration = 'manual'`, scroll to 0 on load and `pageshow`, unless the URL has a hash).
- A BackToTop floating button on every page (appears after 400px of scroll, bottom-right, hidden when printing).

Pages (board file → suggested route):

| Board | Route | Notes |
|---|---|---|
| Main | `/` | Hero, 3-step strip, CalculatorPanel, 4 feature items, featured listings (4 real listings from the scraper), 3 guide cards, footer |
| Calculator | `/calculator` or existing mortgage calculator route | Full mortgage calculator (section 5) |
| Equity | `/equity` | Equity calculator |
| Affordability | `/affordability` | Affordability calculator |
| Listings | `/listings` | Buy/Rent tabs, filters, grid of real listings, compare |
| StampDuty | `/guides/stamp-duty` | Guide |
| ClosingCosts | `/guides/closing-costs` | Guide with cash-at-closing panel |
| Refinancing | `/guides/refinancing` | Guide with break-even calculator |
| Contact | `/contact` | Email + Instagram, two reasons, "before you write" box, no form |
| About | `/about` | Founder cards: Jerome Bailey (Founder) with the quote, Janique Bailey (Co-Founder) |
| Agents | `/agents` | For agents; the "Agencies showing listings here" row stays hidden until agencies confirm |
| Privacy | `/privacy` | Google Analytics named; browser-local storage of inputs explained |
| Terms | `/terms` | |
| MobileHome, MobileCalculator, TabletHome | n/a | Phone and tablet views of the above; use them to check responsive layout |

Keep the site's existing URLs where they already exist (do not break inbound links); add redirects for anything you rename. Generate `sitemap.xml` and `robots.txt`.

## 4. Reading the page boards

Each `pages/*.dc.html` is the approved page. The markup is plain HTML plus a small template syntax from the design tool:

- `<x-import component-from-global-scope="CMC.Header" nav="{{nav}}" ...>Text</x-import>` renders that component with those props (kebab-case attribute → camelCase prop; `{{name}}` takes the value from `renderVals()`; inner text is `children`).
- `<sc-for list="{{items}}" as="it">...</sc-for>` repeats its contents.
- `{{a.b}}` in text or attributes substitutes a value.
- The `<script type="text/x-dc">` at the bottom holds the page's logic as a class with `renderVals()` (and sometimes constructor state / `setState`). Port this logic faithfully: formulas, stamp duty bands, conditions, labels and all generated text. The hrefs ending in `.dc.html` map to the routes above; `/_blob/...` images are the logo files in `brand/logos/` (`cmc-secondary-color.svg` on light, `cmc-secondary-reversed.svg` on dark).
- Inline styles on the boards are the intended layout; move them into stylesheets as you see fit but keep the result visually identical.

## 5. Behaviour that must work exactly as specified

### 5.1 Shared inputs (site-wide)
Price, deposit %, rate, term and currency are entered once and used everywhere. Reference implementation: `CMC.inputs` in `bundle.js` (`get()`, `set()`, `subscribe()`, `reset()`), persisted in `localStorage` under `cmc.inputs`, synced across tabs with the `storage` event. Defaults: CI$650,000, 10%, 7.75%, 25 years, KYD. All maths stays in CI$; `currency: 'USD'` only converts display and entry at the fixed peg CI$1 = US$1.20 (`fx`, `symbol`). The homepage panel, the mortgage, affordability and equity pages, the listings' monthly estimates, the stamp duty quick estimate and the closing-costs panel all read and write the same values (any `Input` with `bind="price" | "deposit" | "rate" | "term"` is a live two-way control).

### 5.2 Mortgage calculator (`pages/Calculator.dc.html`)
Inputs: currency toggle; Property (price, Government valuation if higher, island select, house/condo vs raw land); Buyer (stamp duty status: Caymanian first property / second property / standard 7.5%; one buyer vs 2-10 Caymanians jointly); Mortgage (down payment as CI$ and %, both live; rate; term; extra monthly payment; gross monthly income; cash available); "Your household in detail" (strata, life insurance, building insurance included-in-strata checkbox, building insurance as % of price or quote, maintenance %); "Fee assumptions" (legal %, bank fee %, valuation CI$, mortgage stamp duty read-only).

Results: monthly payment banner with "See homes that fit these numbers" → `/listings?max=<price>&monthly=<monthly>`; four stat cards; Monthly cost of owning; Cash you need at closing (compares with cash entered); stamp duty box with the rate explanation; Affordability check (40% total debt service guideline, editable on the affordability page); year-by-year table (first five years); Download full schedule (Excel); Sources block with Byline; Summary with Save as PDF and Print.

Rules (port from the board's script):
- Stamp duty on the transfer: 7.5% of the higher of price and Government valuation. Caymanian first property, single buyer: 0% to CI$250,000 and 3.75% to CI$350,000 for raw land; 0% to CI$550,000 and 3.75% to CI$650,000 for developed property; group of 2-10 Caymanians: land 450k / 550k, developed 600k / 700k; above the band 7.5%. Second property: flat 3.75% up to 300k (single, land), 600k (single, developed), 550k (group, land), 700k (group, developed); 7.5% above. Source: Ministry of Finance concession form v16.4.26.
- Stamp duty on the mortgage: 1% of the sum secured up to CI$300,000; 1.5% of the whole sum above (Stamp Duty Act 2019 Revision, Schedule: Mortgage).
- Amortising formula; extra payments reduce principal monthly; "paid off in X yrs Y mo, saving CI$Z".
- Rate hint text and default: "KYD prime is 7.00%, raised from 6.75% on 18 September 2026 (Cayman National notice, checked 1 October 2026). A primary residence usually prices at prime plus 0.5-1%, so 7.75% is a planning figure, not a quote. Enter the rate your bank quoted." Keep the figure and date in one config constant so they are easy to update.
- Excel: SheetJS (`xlsx` 0.18.5) building two sheets, Summary and Schedule (month, payment, principal, interest, extra, balance), in the display currency; CSV fallback.
- PDF: jsPDF 2.5.1, one A4 page: navy header, Property and buyer, Mortgage, Cash and running costs, first five years, disclaimer; file name `cayman-mortgage-summary-<price>-<currency>.pdf`. Print button uses `window.print()` with print CSS that shows only the summary.

### 5.3 Affordability calculator
Two limits: (1) income: ceiling % (default 40) × gross income, minus other debts and running costs, converted to a loan with the amortising formula, then to a price at the shared deposit %; (2) cash: the highest price whose down payment + transfer duty (by status) + mortgage duty + legal 1% + valuation CI$600 + bank fee 1% of loan fits the cash entered (bisection, since duty bands step). Lower limit wins; say which. "Run this price in the mortgage calculator" writes the price into shared inputs and navigates.

### 5.4 Equity calculator
Equity = value − mortgage balance − other secured loans; available = value × max LTV (default 80%) − everything secured. Links to the refinancing guide.

### 5.5 Refinancing guide break-even
Current balance, current rate, years left, new rate, new term, "new lender / new legal charge" checkbox (switches mortgage stamp duty on), legal, valuation, bank fee %, early-repayment charge. Outputs monthly saving, total cost, break-even months, interest over the term now vs new plus costs, net saving.

### 5.6 Listings
- Replace every sample listing, `[Agency]` name and `agency.example` link with the real listings the scraper already provides. Map the scraper's fields to the ListingCard props (`price, period, address, locality, beds, baths, sqft, image, imageAlt, badge, badgeTone, monthly, agency, href`). Keep images and links exactly as the scraper sources them. If a field has no match, leave that prop out rather than inventing data, and list the gaps in `REDESIGN-PLAN.md`.
- `monthly` on every sale card is this site's estimate from the shared inputs (deposit %, rate, term); the caption under the grid states the assumptions. Rentals show `period="mo"` and no monthly.
- Buy / Rent tabs, filters (district, type, min/max price, beds), sort. Pagination (or load-more) using real data; `/listings?max=&monthly=` from the calculator pre-filters to listings at or under that price.
- Compare: a "Compare" chip on each card, up to four; selection kept in `localStorage` (`cmc.compare`) as a snapshot of each chosen listing so it survives paging, filtering and reload; a compare bar (centred pill on desktop; full-width strip fixed to the bottom on phones with the BackToTop button lifted above it; count, Compare button, × to clear) and a comparison table (price, estimated monthly, down payment, stamp duty, beds, baths, size, price per sq ft, status, district; best value per row in teal; a button to each listing on the agent's site). Rent mode compares rent per month and per year.
- The homepage shows four real listings (the newest for sale, or whatever ordering the scraper already uses).

### 5.7 Guides and provenance
Each guide and calculator ends with a numbered Sources block (links exactly as on the boards: Stamp Duty Act 2019 Revision, Ministry of Finance concession form, Cayman Brac concession PDF, Cayman National notices) and a `Byline`: Written by Jerome Bailey · Reviewed by Janique Bailey · Sources checked 14 October 2026 · Last updated 14 October 2026. Keep the dates in one place per page so they can be updated.

## 6. Responsive rules (phone first)

Breakpoints: desktop above 860px; tablet 600 to 860px (multi-column grids drop to two columns, nav collapses to the drawer); phone below 600px (single column). Specifics already handled in `bundle.css`: fields shrink inside grids (`min-width: 0; width: 100%`), buttons wrap on small screens, 44px touch targets, wide tables scroll sideways inside a wrapper with a "Swipe sideways to see every column." hint shown only on small screens, header behaviour as in section 3, BackToTop respects the safe-area inset. Test every page at 390, 820 and 1280 wide; no horizontal page scroll anywhere.

## 7. SEO, analytics, assets

- `<title>` per page as on the boards ("Cayman Mortgage Calculator: Stamp duty guide"), a meta description per page, canonical URLs, Open Graph tags using `brand/icons/icon-512.svg` rendered to PNG.
- JSON-LD: `WebSite` + `Organization` (name, URL, logo, founders Jerome Bailey and Janique Bailey, email caymanmortgagecalculator@gmail.com, sameAs Instagram https://www.instagram.com/caymanmortgagecalc) on every page; `FAQPage` on the stamp duty and refinancing guides (from their FAQ sections); `SoftwareApplication` on the calculators; `BreadcrumbList` where there are breadcrumbs.
- Google Analytics 4 with IP anonymisation; put the measurement ID in config (`GA_MEASUREMENT_ID`, placeholder until the owner supplies it). The Privacy page already describes it.
- Favicons: `favicon.svg`, `favicon.ico`, and PNGs generated from `icon-512.svg` at 16, 32, 48, 180 (apple-touch-icon), 192, 512 and a 512 maskable; `site.webmanifest`.
- Lighthouse targets on the phone profile: performance ≥ 90, accessibility ≥ 95, best practices ≥ 95, SEO ≥ 95.

## 8. Accessibility

Semantic landmarks (header, nav, main, footer), one h1 per page, labels on every input (visible or `aria-label`), focus-visible rings (teal), `aria-expanded` on the dropdown chevrons and the menu button, `aria-pressed` on favourite and compare chips, `role="status"` on the compare bar, colour contrast at AA (the tokens already pass; do not lighten text colours), reduced-motion respected for the BackToTop transition.

## 9. Definition of done

- Every route in section 3 exists, matches its board at desktop, tablet and phone widths, and every link on the site resolves (no `#` placeholders except where a feature is intentionally not yet built, which should be none).
- Shared inputs, currency, compare persistence, Excel, PDF and Print all work in Chrome, Safari (iOS) and Firefox.
- Real listings render from the scraper; no sample data or `[Agency]` text remains.
- No em or en dashes in any rendered text (grep the built output for `—` and `–`).
- `REDESIGN-PLAN.md` lists the stack, the approach, any requirement you could not meet and why, and the field-mapping gaps from the scraper.
- Lighthouse report attached or summarised in the PR description.

Open a pull request with a summary of the changes and the items above. Do not deploy to production; the owner will review and deploy.
