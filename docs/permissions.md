# Permissions on record

What each agency has agreed to, and when. This is the record referred to in
`docs/permission-request.md`. Keep it factual: date, who agreed, what they agreed
to, and where the agreement is (an email in your inbox is fine — note the subject
so it can be found again).

A source only needs an entry here if its terms require permission. Most do not.

---

## Utopia Realty — confirmed

- **Date recorded:** 5 October 2026
- **Agreed:** Jerome Bailey reports having received confirmation from Utopia Realty
  that their listings may appear on caymanmortgagecalculator.com.
- **Who gave it / where it is:** _to fill in — name of the person who replied, and
  the date and subject of their email._
- **Note:** Utopia's terms did not in fact require permission, so this is a
  belt-and-braces record rather than a condition of listing them. They have been
  live since 5 October 2026 and are unaffected either way.

---

## Paradise Realty (Cayman Brac) — confirmed

- **Date recorded:** 8 October 2026
- **Agreed:** Jerome Bailey reports having received permission from Paradise Realty
  for their listings to appear on caymanmortgagecalculator.com.
- **Who gave it / where it is:** _to fill in — name of the person who replied, and
  the date and subject of their email._
- **Note:** As with Utopia, Paradise's terms did not require permission, so this is
  a record rather than a condition. Their 17 Cayman Brac land listings have been
  live since 5 October 2026 and are unaffected either way. Scraped from
  paradiserealtycyb.com by `scraper/sources/paradisebrac.py`.

---

## Still awaiting a reply

These four are paused in `scraper/run.py` because their terms require written
permission before their content is republished. Each shows on the site as
unavailable, with the reason. Restoring one is a single line.

| Agency | Why it is paused | Status |
| --- | --- | --- |
| ERA | Terms require written permission to republish listings, and bar embedding or framing images | awaiting reply |
| MOD Realty | Clause 5 requires prior written permission to reproduce or republish content | awaiting reply |
| Shoreline | Clause 4 requires prior written consent to reproduce or display content | awaiting reply |
| Provenance | Requires written permission to copy, republish or extract content, and separately to link to the site | awaiting reply |

When one replies yes, add a section above and tell me which — I will move it from
`DISABLED` back into `SOURCES` and restore its cached listings from
`data/raw/paused/`.

If one replies no, tell me and it stays paused; I will delete its cached copy.
