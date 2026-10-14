# Redesign plan

Required by `cmc-redesign/HANDOFF.md` section 0. Written before any page work.

---

## 1. The stack I found

| | |
| --- | --- |
| **Build** | Python static site generator. `build_site.py` assembles `site/` from `page.py` (head, nav, footer, JSON-LD), `home.py` (front-page body) and HTML fragments in `web/`. No `package.json`, no npm, no bundler, no framework. |
| **Front end** | One hand-written stylesheet (`web/app.css`, 629 lines) and one shared engine (`web/core.js`, ES5, ~20 KB) exposing a `Core` global. Page logic is inline ES5 in each fragment. |
| **Tests** | `test/core.test.js`, 92 assertions over the financial engine, run with `node test/core.test.js`. No dependencies. |
| **Hosting** | GitHub Pages from `.github/workflows/update-listings.yml`. No server, so no HTTP headers and no server-side redirects. |
| **Listings** | 21 scrapers in `scraper/sources/`, merged by `scraper/run.py` into `data/listings.json` (~880 listings) and published beside the pages. Refreshed every four hours; a push carrying `data/` publishes as committed instead of re-scraping. |
| **Security** | Content Security Policy in a `<meta>` tag. Script origins today: `'self'`, `'unsafe-inline'`, `static.cloudflareinsights.com`. |
| **Current routes** | `/`, `/calculator/`, `/equity/`, `/rent-vs-buy/`, `404.html`. |

## 2. The approach I chose

**Keep the Python generator; port the components to vanilla ES5; keep the tested engine.**

The handoff offers three routes (section 0.2). This site is the first case, "plain
HTML/CSS/JS". Within that it allows either a vanilla layer or React 18 from a CDN.
I chose vanilla, for four reasons:

1. **React from a CDN costs three new script origins** (React, ReactDOM, plus SheetJS
   and jsPDF later) and a CSP change on every page, to render markup that is almost
   entirely static. The pages are documents with a few interactive panels, not an app.
2. **It would make the site slower on the profile it is judged on.** Section 7 sets
   Lighthouse performance ≥ 90 on the phone profile. React 18 plus ReactDOM is ~45 KB
   gzipped before any component code, render-blocking on a 4G phone. The current page
   weight is ~20 KB of JavaScript in total.
3. **The templating in the boards is a design-tool syntax**, not React source. It has
   to be translated either way; translating to the generator's existing fragment model
   is no more work than translating to React.
4. **The repo has no toolchain**, and the handoff explicitly prefers not adding one.

The reference `bundle.js` and `bundle.css` stay in the repo as the specification. Each
component is ported to a generator function in `web/` with the same name and the same
props, and `bundle.css` supplies the styling, rewritten to use the tokens directly.

**Tokens** are taken from `design-system/tokens.css` unchanged and become the single
source of colour, radius, shadow and type for the new stylesheet.

## 3. What this replaces, and what survives

**Replaced:** `web/app.css`, the nav and footer in `page.py`, the four page bodies, and
the front-page composition in `home.py`.

**Kept:** the scraper and its data contract, the GitHub Pages workflow and the
data-push behaviour, the per-source cache and stale handling, `web/core.js` and its 92
tests, the CSP mechanism, and the paused-agency disclosure.

## 4. Decisions needed from the owner

These are requirements I cannot meet as written without either breaking the site or
contradicting something the owner has already decided. Section 0 says to say so rather
than silently dropping them. **Work on the affected pages is paused until these are
answered;** everything else proceeds.

### 4.1 The calculator board drops two duty rules the live site implements

The board's duty logic (`pages/Calculator.dc.html`) contains the Caymanian concession
bands, which match the live site exactly. It does **not** contain:

- **The 10% band at CI$2,000,000.** Live law and live code: duty is 10% of the *whole*
  value once the price reaches CI$2M, not 7.5%. Source already cited in `core.js`:
  [gov.ky](https://gov.ky/w/legislation-passed-to-increase-stamp-duty-on-properties-worth-2m-and-over).
  **203 of the 873 listings on the site today are at or above CI$2M** (the data refreshes every four hours, so these counts move). Porting the
  board faithfully would under-state duty on every one of them, by CI$50,000 on a
  CI$2M property.
- **Any Cayman Brac rule.** The board's island selector offers Cayman Brac, but the
  duty function ignores the island, so a Brac property would be charged Grand Cayman
  duty. This is the exact defect I fixed on 12 October; it affects 117 listings.

**There is also a factual conflict about what the Brac scheme is.** The live site
implements 3% on developed property and 0% on undeveloped, capped at CI$2M, expiring
31 December 2030, from the Lands & Survey 2025 rates PDF. The `StampDuty` board
describes something different: a full waiver on any value, for anyone, conditional on
completing development within two years, with a 10% penalty for missing the deadline.
Both cite Cayman Brac concession documents, but they are not the same scheme.

**I propose:** keep `core.js` as the duty engine (it has the 10% band, the Brac rules
and 92 tests behind it) and drive the new interface from it, rather than porting the
board's arithmetic. The board's *presentation* is adopted in full. **Which Brac scheme
is correct still needs settling** before the stamp duty guide can ship.

### 4.2 "Listings only with permission" — ANSWERED 14 Oct: attribution and linking

**Decision:** all 873 listings stay. Every card credits the agency, links to the
listing on their own site, and photos remain hotlinked from the agency as the live
site already does. Photos are therefore shown, not gated behind confirmation.

The original question follows for the record.

### 4.2a The question as asked

Section 2 states this as a non-negotiable. Read strictly it means the site may show
only the two agencies that have confirmed in writing: Utopia Realty and Paradise
Realty Brac, which is **40 of 873 listings**. Four agencies are paused awaiting
replies; the other fifteen have never been asked.

The rest of the clause is about attribution, so this may mean "credited and linked,
never republished wholesale". I have not guessed. **Does this mean (a) attribution and
linking, which the site already does, or (b) actually restricting the site to agencies
that have confirmed?**

### 4.3 Inter replaces Sora, two days after the opposite decision

Section 2 makes Inter the only font. On 13 October the owner reviewed a single-font
system, rejected it, and asked to keep Sora for headings. The handoff is newer and
arrives with a full brand book, so I will follow it unless told otherwise, but it
reverses a recent explicit decision and is worth confirming.

### 4.4 Rent vs buy — ANSWERED 14 Oct: keep it, redesigned

**Decision:** port it to the new design system as a fourth calculator. It has been
added to the Calculators dropdown and the footer. No inbound link breaks.

The original question follows for the record.

### 4.4a The question as asked

`/rent-vs-buy/` is a live page with its own calculator, horizon control, scenario
bands and break-even chart. It is absent from the section 3 site map. Section 3 also
says not to break inbound links. **Keep it, redesigned to the new system, or retire it
with a redirect?** It is currently linked from the homepage and the main nav.

### 4.5 Redirects are not really available

Section 3 asks for redirects on renamed routes. GitHub Pages serves static files only:
no 301s. The options are a meta-refresh page at each old URL, which search engines
treat as a weak redirect, or keeping both paths. I will keep the existing paths as the
canonical ones wherever the handoff's route differs only by a trailing slash
(`/calculator/` not `/calculator`), which avoids the problem for three of four routes.

## 5. Scraper field mapping

`ListingCard` props against `data/listings.json`. Gaps listed as section 5.6 requires.

| Prop | Source | Notes |
| --- | --- | --- |
| `price` | `price_kyd` | Always KYD; the card's `currency` handles display |
| `address` | `title` | The scrapers produce a title, not a street address |
| `locality` | `location` | District or area as the agency wrote it |
| `beds` `baths` `sqft` | same names | Often null; the card must omit rather than show 0 |
| `image` | `image` | Hotlinked from the agency; may 404, needs the existing fallback |
| `agency` | `sources[0]` | First of the merged sources |
| `href` | `url` | Already absolute, already opens in a new tab with `rel="noopener"` |
| `badge` / `badgeTone` | `status` | "Under Offer" and "Pending/Conditional" map to the warning tone |
| `monthly` | computed | From shared inputs via `core.js`, not from the scraper |
| **`imageAlt`** | **missing** | Scrapers do not capture alt text. Proposal: leave empty, since the photo is decorative beside the title, which is the accessible name |
| **`period`** | **missing** | No rentals are scraped; every listing is for sale. The Buy/Rent tabs in section 5.6 have no data behind the Rent side |

**Two gaps worth flagging beyond the table:** there is no rental data at all, so the
Listings page's Rent tab and the rent-mode comparison have nothing to show; and
`acres`, `mls`, `ptype`, `scraped_at` and the merged `sources`/`also` lists have no
prop on the card, though the live site surfaces all of them. The new card loses the
MLS number, the land area, the "also listed with" cross-reference and the
"checked at" provenance line unless the component is extended.

## 6. Order of work

1. Tokens and the base stylesheet.
2. Header, footer, back-to-top, shared inputs; the page shell in `page.py`.
3. Listing card and the Listings page, on real data.
4. Mortgage calculator on `core.js`, then Affordability and Equity.
5. Guides, then About, Contact, Agents, Privacy, Terms.
6. SEO, JSON-LD, favicons, manifest.
7. Responsive and accessibility passes at 390, 820 and 1280.
8. Lighthouse, then the pull request.

Nothing deploys. The workflow publishes from `main`; this work stays on `redesign`
until the owner merges.
