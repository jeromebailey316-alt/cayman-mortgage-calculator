# Asking agencies for permission

Four agencies publish terms that bar republishing their content without written
permission: **ERA Cayman**, **MOD Realty**, **Shoreline Properties** and
**Provenance Properties**. Williams2 asserts ownership without prohibiting anything,
so asking them is the cautious course. Provenance separately requires written consent
even to link to their site.

The underlying listing data is mostly CIREBA's MLS inventory rather than each
agency's own, so CIREBA is worth approaching as well — permission from an agency may
be necessary but not sufficient. CIREBA's own terms page is an unpublished
placeholder, so there is no public rule to read.

Send from your own address, one per agency. Keep it short; you are offering them
something.

---

## Template

**Subject:** Permission to show your listings on caymanmortgagecalculator.com

Hello [name],

I run caymanmortgagecalculator.com, a free tool that works out what a Cayman
property actually costs a buyer — stamp duty, mortgage duty, closing costs and the
monthly payment. Alongside the calculator I show properties currently for sale so
people can price a real home rather than a round number.

For each of your listings the site shows the price, district, bedrooms, bathrooms,
floor area, your agency's name, the photo from your own page, and a link straight to
your listing. It carries no descriptive text from your site. Every click goes to you.
The data refreshes every four hours and I remove anything that disappears from your
site.

Your terms ask for written permission before content is republished, so I am asking.
Would you be happy for your listings to appear on this basis?

I am glad to adjust anything that would make it work better for you — attribution,
how the photo is shown, or leaving particular listings out. If you would rather not,
tell me and I will remove your listings.

[your name]
[phone] · [email]

---

## If they say yes

Record it: date, who agreed, and what they agreed to. A one-line note in
`docs/permissions.md` is enough, and it is what you would want if the question ever
came up.

## If they say no, or do not reply

Tell me and I will disable that source. It is one line in `scraper/run.py`, and the
page will show the agency as unavailable rather than silently dropping listings.

## Worth knowing before you send

- **The embedded-thumbnail build is the weaker position.** The website hotlinks
  photos, so the agency still hosts the image. The single-file build published to
  claude.ai stores a copy of each photo, which is squarely "reproduce" under all four
  sets of terms. That build is easy to change.
- **ERA's disclaimer bars embedding or framing specifically**, which is the closest
  anything in the set comes to naming the hotlinked-photo pattern.
- **Provenance prohibits inbound links**, so "we only link to you" is not available
  as a mitigation there.
