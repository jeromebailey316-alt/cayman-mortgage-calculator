# Apply the redesign

Implements `cmc-redesign/HANDOFF.md`. Fourteen routes, the design system's tokens and
components, real listings throughout, and the calculators driven by the engine the site
already tests. Nothing is deployed: the workflow publishes from `main`, and this is
`redesign`.

## Approach

Kept the Python static generator and ported the eleven reference components to plain ES5
builders that emit the class names `bundle.css` already defines, so the delivered
stylesheet is used rather than reimplemented. `tokens.css` and `bundle.css` ship as
delivered, concatenated with a small `web/rd.css` into one request.

The handoff allowed React 18 from a CDN. I chose not to: these pages are documents with
a few interactive panels, React plus ReactDOM is roughly twice the site's entire
JavaScript budget, and section 7 asks for Lighthouse performance of 90 or better on the
phone profile. Reasoning in `REDESIGN-PLAN.md` section 2.

Boards with no live arithmetic are translated by `rd_board.py` rather than retyped:
`x-import` becomes the ported component, `sc-for` expands, `{{vars}}` resolve, and
`.dc.html` hrefs become real routes. It raises rather than emitting half-translated
markup. Transcribing approved legal copy by hand would have risked dropping a paragraph
or reintroducing an em dash.

## The one thing to read before merging

**The calculator board's duty arithmetic is wrong in two ways, so it was not used.**
Its `dutyRate` returns a flat 7.5% for a standard buyer and never reads the island it
asks the visitor to choose. It has no CI$2,000,000 band and no Cayman Brac rule.
Measured on the built site:

| | Board's logic | `core.js`, used here |
| --- | --- | --- |
| CI$1,999,000, standard | CI$149,925 | CI$149,925 |
| CI$2,000,000, standard | CI$150,000 | **CI$200,000** |
| Cayman Brac raw land, CI$255,000 | CI$19,125 | **nothing**, concession named |

203 of the 873 listings on the site are at or above CI$2M, and 117 are on Cayman Brac.
The calculators, the listings comparison and both guide panels all read `core.js`, so no
two pages can disagree: a first-time Caymanian buyer at CI$650,000 is told CI$90,575 on
the day by the calculator and by the closing-costs guide alike.

## Still needs a decision

**What does a buyer of *developed* property on Cayman Brac pay?** `core.js` charges 3%,
capped at CI$2M and expiring at the end of 2030, from the Lands and Survey 2025 rates
PDF. The StampDuty board describes the duty as waived entirely, with no cap, conditional
on completing development within two years. Both cite concession documents and they may
be two coexisting programmes. Until it is settled the guide ships without its Cayman Brac
section, since a guide contradicting this site's own calculator is worse than no guide.

## Decisions already taken

- **"Listings only with permission"** means attribution and linking, not gating. All 873
  listings stay, each crediting its agency and linking to the agent's own page.
- **Rent vs Buy is kept**, redesigned as a fourth calculator. The handoff's site map
  omits it; it is live today and linked from the nav.

## What is built

All fourteen routes pass the same sweep: one `h1`, no horizontal scroll at 390px, no em
or en dashes, no placeholder links, no NaN, every control named, every input labelled,
landmarks present once each.

Calculators `/calculator/` `/affordability/` `/equity/` `/rent-vs-buy/`; guides
`/guides/stamp-duty/` `/guides/closing-costs/` `/guides/refinancing/`; `/listings/` with
filters, sort, paging and compare; and `/` `/about/` `/contact/` `/agents/` `/privacy/`
`/terms/`.

Shared inputs with cross-tab sync, compare kept as snapshots so a selection survives
paging and reload, Excel and PDF export with a CSV fallback, print styles, the icon set
rendered from `icon-512.svg`, manifest, sitemap, robots, canonicals, Open Graph, JSON-LD
on every page, and a content security policy.

## Bugs found by testing, not by reading

- **The amortisation tables showed a column of zeros.** `core.js` writes its schedule
  rows as `{m, pay, p, i, bal}`; both the calculator's year-by-year table and rent vs buy
  read `.payment`, `.interest`, `.principal`, `.balance`. All undefined, and `CMC.money`
  renders NaN as `CI$0`, so it looked tidy rather than broken. I had checked that five
  rows rendered without checking what was in them.
- **The compare control could throw a visitor off the site.** It sits inside each card's
  anchor; with a delegated handler one missed interception opened the agency's website
  mid-task. It happened once in testing. Handlers are bound per button now.
- **The calculator overflowed a 390px viewport by 62px.** The phone grid rule used `1fr`,
  whose automatic minimum is the content's min-content width.
- **Canonicals were relative.** Built from an empty base, so `/about` declared its
  canonical as `about` and the homepage had none.
- **The byline failed AA.** `--ink-500` on `--surface-100` is 4.38:1 at 12px. Darkened to
  `--ink-700`, overridden in `rd.css` so the delivered bundle is untouched.
- `CI$-400,000` rendered with the sign after the symbol in the equity breakdown.

## Not done

`GA_MEASUREMENT_ID` is an empty placeholder in `redesign.py` until you supply it; the
Privacy page already describes what it measures. Lighthouse has not been run: it needs
the site served over HTTPS at its real domain, which happens on merge.

## How to review

```bash
git checkout redesign
.venv/bin/python build_redesign.py
.venv/bin/python -m http.server 8790 --directory site-rd
```

`node test/core.test.js` still passes its 92 assertions; the engine is unchanged.
