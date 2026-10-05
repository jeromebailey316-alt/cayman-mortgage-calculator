"""Elite Real Estate (eliterealty.ky) scraper.

How the site serves data
------------------------
* WordPress + WpResidence theme.  Listings are the `estate_property` post type
  but the WP REST API does NOT expose it: /wp-json/wp/v2/estate_property is a
  hard 404, so there is no JSON feed to use.
* Discovery therefore comes from the WordPress core sitemap,
  /wp-sitemap-posts-estate_property-1.xml, which lists every published
  listing (17 as of Oct 2026).  This is deliberately preferred over the
  /properties_search/page/N/ HTML list, because that search view is both
  incomplete and buggy: it returns only 12 of the 17 live listings (it drops
  e.g. "#16 Garden Retreat" and "New 2Bed|2Bath ... (END UNIT)", both of
  which are status "Current"), and its page 2 repeats the last three cards of
  page 1.  The sitemap has no such gaps.
* Everything else is read from the server-rendered detail page
  /properties/<slug>/ : the H1 title, `.price_area`, the `.listing_detail`
  label/value rows (Address, City, Area, State/County, Property Id, Price,
  Property Size, Property Lot Size, Bedrooms, Bathrooms, Year Built, ...),
  `.status-wrapper` and the og:image meta tag.
* No MLS/CIREBA number is published anywhere on the site.  "Property Id" is
  the internal WpResidence post id (e.g. 18894), not an MLS number, so it is
  deliberately NOT written into Listing.mls -- putting it there would create
  false de-dupe matches against the CIREBA feed.
* The site sells only; its search "Types" dropdown offers "Sales" and nothing
  else, and no rental listings exist.  The rental/sold keyword filter below is
  a safety net in case that changes.

robots.txt and terms
--------------------
robots.txt is two lines -- `User-agent: *` plus `Crawl-delay: 10` -- with no
Disallow at all.  common.HOST_DELAY already enforces that 10 second delay, so
a full run takes roughly three minutes.  The Terms of Use page
(/terms-of-user/, checked 5 Oct 2026) is the unmodified WpResidence demo
boilerplate -- it is actually a privacy policy and still refers to "Real
Estate WordPress Theme" rather than to Elite -- and says nothing whatsoever
about scraping, crawling, automated access, reuse, redistribution,
reproduction or commercial use.  Nothing there restricts this scraper.

Currency
--------
Prices render as a bare "$" with no currency code anywhere on the site, and
the CIREBA/CIRO portal labels the same listings "KYD $...".  We record KYD,
on this evidence:

  * The theme is configured with the symbol "$" only (`"curency":"$"`).  The
    one "USD" string in the page source is `"submission_curency":"USD"`,
    which is WpResidence's *paid-listing-submission payment* currency, not
    the price display currency, and it is the theme default.
  * Decisive: the only two non-round prices on the site are each exactly 0.82
    (common.KYD_PER_USD, the local bank rate) times a round USD figure --
    1,311,180 = 0.82 x 1,599,000 and 892,980 = 0.82 x 1,089,000.  Converting
    the other way round, i.e. treating the shown figure as USD derived from a
    round KYD price, yields 1,075,167.60 and 732,243.60: not round.  The
    displayed numbers are therefore the KYD side of a USD -> KYD conversion.
  * cirealtors.org shows "KYD $1,311,180" for that same listing: the same
    numeral, explicitly labelled KYD.

So the figure on the page is KYD, and PRICE_CURRENCY below is "KYD".  Note
this is a site-wide setting rather than a per-listing label, so if Elite ever
switches its display currency the only clue will be the price arithmetic
again.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from scraper.common import CONDO, HOME, LAND, OTHER, Listing, get, num

SOURCE = "Elite Realty"

BASE = "https://eliterealty.ky"
SITEMAP = BASE + "/wp-sitemap-posts-estate_property-1.xml"

PER_PAGE = 10          # the site's own /properties_search/ page size
MAX_DETAILS = 40       # hard cap on detail fetches (10s each -- see module docstring)
SQFT_PER_ACRE = 43560.0

# See the "Currency" section of the module docstring.
PRICE_CURRENCY = "KYD"

# A lot size below this is being quoted in acres, not square feet: WpResidence
# labels the field "ft2" regardless of what the agent typed into it.
ACRES_IF_UNDER = 100.0

_CONDO_RE = re.compile(
    r"\b(condo\w*|apartments?|apt|townhom\w*|townhous\w*|penthouse|studio|suites?|"
    r"units?|villas?|duplex|loft|residences?|flat|strata)\b|#\s*\d", re.I)
_HOUSE_RE = re.compile(
    r"\b(houses?|homes?|single[- ]family|detached|bungalows?|cottages?|estates?)\b", re.I)
_LAND_RE = re.compile(r"\b(land|lots?|acres?|acreage|parcels?)\b", re.I)

# Anything here means the listing is not a plain residential for-sale listing.
_REJECT_RE = re.compile(
    r"\b(sold|rented|rental|for rent|to rent|leased|for lease|under offer|under contract|"
    r"pending|withdrawn|expired|off market|commercial|office space|retail space|warehouse)\b", re.I)
# Rental price formats, e.g. "$2,500 / month".
_PERIOD_RE = re.compile(r"(per|/|a)\s*(month|mo\b|week|wk\b|night|day|annum|year|yr\b)", re.I)


def _soup(url: str) -> BeautifulSoup:
    return BeautifulSoup(get(url).text, "lxml")


def _clean(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()


def _abs(u: str) -> str:
    if not u:
        return ""
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("/"):
        return BASE + u
    return u


def discover() -> list[str]:
    """Every published listing URL, from the WordPress sitemap (1 request)."""
    xml = get(SITEMAP).text
    seen, urls = set(), []
    for u in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml):
        if "/properties/" in u and u not in seen:
            seen.add(u)
            urls.append(u)
    return urls


def _details(s: BeautifulSoup) -> dict[str, str]:
    """The `.listing_detail` label/value rows, keyed by lowercased label.

    Elite writes "Property Id :" with a stray space, so labels are normalised.
    """
    out: dict[str, str] = {}
    for d in s.select(".listing_detail"):
        txt = _clean(d.get_text(" ", strip=True))
        if ":" not in txt:
            continue
        k, v = txt.split(":", 1)
        k = re.sub(r"[^a-z0-9 ]+", "", k.strip().lower()).strip()
        if k and v.strip():
            out.setdefault(k, v.strip())
    return out


def _location(det: dict[str, str]) -> str:
    """District, preferring the Area field and dropping a trailing island name.

    City is inconsistent: sometimes the island ("Grand Cayman") with the
    district in Area, sometimes the district itself ("West Bay"), sometimes
    both ("Georgetown, Grand Cayman").
    """
    islands = ("grand cayman", "cayman brac", "little cayman", "cayman islands")
    for key in ("area", "city", "statecounty"):
        v = _clean(det.get(key))
        if not v:
            continue
        parts = [p.strip() for p in v.split(",") if p.strip()]
        kept = [p for p in parts if p.lower() not in islands]
        if kept:
            return ", ".join(kept)
        if key == "area":      # Area was only an island name -- try City next
            continue
        return ", ".join(parts)
    return ""


def _ptype(title: str, desc: str, det: dict[str, str]) -> str:
    """house / condo / land.

    Only the *title* is matched against the house/condo words: listing
    descriptions on this site are marketing copy and say things like "make it
    your HOME" about a townhouse unit.  The description is consulted just for
    land, and only once beds and interior size have both come back empty --
    a listing with neither is not a dwelling.  "Queens Ridge" is the case
    that needs it: the title names only the development, and nothing but the
    description ("Residential Lots on Queens Highway") says it is land.
    """
    size = num(det.get("property size"))
    lot = num(det.get("property lot size"))
    beds = num(det.get("bedrooms"))
    dwelling = bool(beds or size)
    if not dwelling and (_LAND_RE.search(title) or _LAND_RE.search(desc)):
        return LAND
    if lot and not dwelling:
        return LAND
    if _CONDO_RE.search(title):
        return CONDO
    if _HOUSE_RE.search(title):
        return HOME
    # Elite's inventory is new-development strata units. Interior size but no
    # lot of its own means a condo/townhouse rather than a free-standing house.
    if size and not lot:
        return CONDO
    return HOME if lot else OTHER


def _status(raw: str) -> str:
    t = _clean(raw)
    return "For Sale" if t.lower() in ("", "current", "new", "active", "for sale", "sales") else t


def _parse(url: str) -> Listing | None:
    """Build a Listing from a detail page, or None if it is out of scope."""
    s = _soup(url)
    for tag in s(["script", "style", "noscript"]):
        tag.decompose()

    h1 = s.select_one("h1")
    title = _clean(h1.get_text(" ", strip=True)) if h1 else ""
    det = _details(s)
    pa = s.select_one(".price_area")
    price_txt = _clean(pa.get_text(" ", strip=True)) if pa else _clean(det.get("price"))
    sw = s.select_one(".status-wrapper")
    status_txt = _clean(sw.get_text(" ", strip=True)) if sw else ""

    # For-sale residential only.
    if _PERIOD_RE.search(price_txt) or _REJECT_RE.search(f"{title} {status_txt}"):
        return None

    price = num(price_txt)
    if not price:
        return None

    dsc = s.select_one(".property_description, .wpestate_property_description, .entry-content")
    desc = _clean(dsc.get_text(" ", strip=True))[:2000] if dsc else ""
    ptype = _ptype(title, desc, det)
    size = num(det.get("property size"))
    lot = num(det.get("property lot size"))
    acres = sqft = None
    if lot:
        acres = lot if lot < ACRES_IF_UNDER else lot / SQFT_PER_ACRE
    if ptype == LAND:
        sqft = lot if (lot and lot >= ACRES_IF_UNDER) else (
            round(acres * SQFT_PER_ACRE) if acres else None)
    else:
        sqft = size
    acres = round(acres, 4) if acres else None

    og = s.find("meta", property="og:image")
    return Listing(
        source=SOURCE,
        url=url,
        title=title,
        price=price,
        currency=PRICE_CURRENCY,
        ptype=ptype,
        location=_location(det),
        beds=num(det.get("bedrooms")) if ptype != LAND else None,
        baths=num(det.get("bathrooms")) if ptype != LAND else None,
        sqft=sqft,
        acres=acres,
        image=_abs(og.get("content", "")) if og else "",
        mls="",            # not published -- see module docstring
        status=_status(status_txt),
    )


def fetch(max_pages: int = 5) -> list[Listing]:
    """Elite Real Estate's for-sale residential listings.

    There is no JSON feed and no usable paginated source, so `max_pages` is
    interpreted as "pages worth of listings" at the site's own 10 per page:
    detail fetches are capped at min(MAX_DETAILS, max_pages * 10).  Every
    request waits 10s for the robots.txt Crawl-delay, so fetch(2) -- enough
    for the whole 17-listing inventory -- takes about three minutes, and
    fetch(1) is the cheap smoke test.
    """
    try:
        urls = discover()
    except Exception as e:
        raise RuntimeError(f"Elite Realty: sitemap unavailable ({e})") from e

    limit = max(1, min(MAX_DETAILS, max_pages * PER_PAGE))
    out: list[Listing] = []
    for url in urls[:limit]:
        try:
            l = _parse(url)
            if l:
                out.append(l)
        except Exception as e:
            print(f"[{SOURCE}] detail failed {url}: {e}")
    out.sort(key=lambda l: -(l.price_kyd or 0))
    return out
