"""Island Realty (islandrealty.com.ky) scraper -- Cayman Brac / Little Cayman.

Island Realty is the Sister Islands brokerage: every current listing is on
Cayman Brac (the site has a Little Cayman section too, empty at the time of
writing), so Listing.location always names the island.

How the site serves data
------------------------
* WordPress + WpResidence theme.  Unlike eliterealty.ky, the REST API *is*
  exposed: /wp-json/wp/v2/estate_property returns all listings (11 as of Oct
  2026, X-WP-Total / X-WP-TotalPages give the counts).  With
  `_embed=wp:featuredmedia,wp:term` each item carries its URL, title,
  description, featured image and the taxonomy term *names*:
      property_category         -> Single Family Home / Condo / Vacant Land /
                                   Commercial Property
      property_action_category  -> Sales (all of them currently)
      property_city             -> the local area, e.g. "Interior / Bluff"
      property_county_state     -> the island, when the agent filled it in
      property_status           -> e.g. "NEW PRICING!", "Under Contract"
* The REST payload has NO price and no numeric fields (the WpResidence ACF
  meta is not registered for REST), so price, currency, MLS number, beds,
  baths and sizes all come from the detail page /estate_property/<slug>/ --
  `.price_area` and the `.listing_detail` label/value rows.  Detail fetches
  are capped at MAX_DETAILS; anything past the cap is dropped rather than
  returned priceless, since a listing with no price is useless here.

MLS number
----------
The detail page carries a "Listing #" row -- e.g. 101B00H66, 95C00C18928,
104A00A305306 -- which is what de-duplicates these against the CIREBA feed,
so it goes into Listing.mls.  One listing writes the value as
"Listing #95C00C189H35" (label duplicated inside the value), so the prefix is
stripped.

Currency
--------
Per-listing, and stated on the page: `.price_area` reads "CI $349,000",
"US $249,000", "$320,000 US", "$75,000 CI" or "CI $40,000 each".  The marker
appears before *or* after the amount, which is why common.parse_price is not
used here -- its regex only recognises a "CI$" prefix and would silently call
"$75,000 CI" a USD price.  _price() below looks for CI/KYD or US/USD anywhere
in the string and defaults to USD when neither appears.

Scope
-----
Sales only, and rentals/sold/under-contract are dropped.  Vacant land is
kept (land is a property type the calculator handles).  Two land parcels are
tagged both "Vacant Land" and "Commercial Property"; they are kept as land,
and only a listing that is commercial *and* has no land or residential
category is dropped.  Flip _is_commercial_only to a plain "any commercial
category" test if you would rather exclude those two as well.
"""
from __future__ import annotations

import html
import re

from bs4 import BeautifulSoup

from scraper.common import CONDO, HOME, LAND, OTHER, Listing, get, num

SOURCE = "Island Realty"

BASE = "https://islandrealty.com.ky"
API = BASE + "/wp-json/wp/v2/estate_property"

PER_PAGE = 50
MAX_DETAILS = 40
SQFT_PER_ACRE = 43560.0

# Lot sizes are usually square feet but some are typed in acres under the same
# "ft2" label (0.19 for a house lot).  No real parcel is under 100 sq ft.
ACRES_IF_UNDER = 100.0

ISLANDS = ("Little Cayman", "Cayman Brac", "Grand Cayman")
DEFAULT_ISLAND = "Cayman Brac"   # the brokerage's home island

CATEGORY_TYPES = {
    "single family home": HOME,
    "house": HOME,
    "home": HOME,
    "condo": CONDO,
    "condominium": CONDO,
    "townhouse": CONDO,
    "apartment": CONDO,
    "vacant land": LAND,
    "land": LAND,
}
_COMMERCIAL_RE = re.compile(r"\b(commercial|office|retail|industrial|warehouse|business)\b", re.I)
_SALE_RE = re.compile(r"\b(sale|sales|buy|for sale)\b", re.I)
# Statuses that mean the listing is no longer plainly available.
_DEAD_RE = re.compile(
    r"\b(sold|under contract|under offer|pending|contingent|withdrawn|expired|"
    r"off market|rented|leased)\b", re.I)
_PERIOD_RE = re.compile(r"(per|/|a)\s*(month|mo\b|week|wk\b|night|day|annum|year|yr\b)", re.I)


def _status(*texts: str) -> str:
    """One of the handful of values the calculator filters on.

    property_status is a marketing badge on this site ("NEW PRICING!"), not a
    sale state, so anything that is not an explicit hold becomes "For Sale".
    """
    t = " ".join(texts).lower()
    if "under contract" in t or "contingent" in t:
        return "Under Contract"
    if "under offer" in t:
        return "Under Offer"
    if "pending" in t:
        return "Pending"
    if re.search(r"\b(sold|rented|leased)\b", t):
        return "Sold"
    return "For Sale"


def _clean(s: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(s or "").replace("\xa0", " ")).strip()


def _text(markup: str | None) -> str:
    return _clean(BeautifulSoup(markup or "", "lxml").get_text(" "))


def _abs(u: str) -> str:
    if not u:
        return ""
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("/"):
        return BASE + u
    return u


def _price(text: str) -> tuple[float | None, str]:
    """'CI $349,000' / '$75,000 CI' / 'US $249,000' -> (amount, currency).

    The CI/US marker sits on either side of the amount, so match it anywhere.
    """
    t = _clean(text)
    if re.search(r"\bCI\b|\bKYD\b|CI\s*\$", t, re.I):
        cur = "KYD"
    elif re.search(r"\bUS\b|\bUSD\b|US\s*\$", t, re.I):
        cur = "USD"
    else:
        cur = "USD"
    return (num(t) or None), cur


def _terms(item: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for group in (item.get("_embedded") or {}).get("wp:term") or []:
        for t in group or []:
            if isinstance(t, dict) and t.get("name"):
                out.setdefault(t.get("taxonomy") or "", []).append(_clean(t["name"]))
    return out


def _is_commercial_only(cats: list[str]) -> bool:
    """True for a purely commercial listing. Land tagged commercial is kept."""
    if not any(_COMMERCIAL_RE.search(c) for c in cats):
        return False
    return not any(CATEGORY_TYPES.get(c.lower()) for c in cats)


def _ptype(cats: list[str], title: str) -> str:
    for c in cats:
        t = CATEGORY_TYPES.get(c.lower())
        if t:
            return t
    for c in cats:
        for key, t in CATEGORY_TYPES.items():
            if key in c.lower():
                return t
    if re.search(r"\b(land|lots?|acres?|acreage|parcels?)\b", title, re.I):
        return LAND
    if re.search(r"\b(condo\w*|apartments?|unit\b|#\s*\d)", title, re.I):
        return CONDO
    return OTHER


def _island(*blobs: str) -> str:
    """Name the island. property_county_state when set, else the text."""
    for b in blobs:
        # Ordered by precedence: a blurb naming two islands is describing a
        # Sister Islands property, so match those before Grand Cayman.
        for isl in ISLANDS:
            if isl.lower() in (b or "").lower():
                return isl
    return DEFAULT_ISLAND


def _details(s: BeautifulSoup) -> dict[str, str]:
    out: dict[str, str] = {}
    for d in s.select(".listing_detail"):
        txt = _clean(d.get_text(" ", strip=True))
        if ":" not in txt:
            continue
        k, v = txt.split(":", 1)
        k = re.sub(r"[^a-z0-9 #]+", "", k.strip().lower()).strip()
        if k and v.strip():
            out.setdefault(k, v.strip())
    return out


def _from_rest(item: dict) -> Listing | None:
    """A Listing with everything the REST feed carries, or None if out of scope.

    Price, currency, MLS and the numeric fields are not in the feed; _enrich
    adds them from the detail page.  A listing whose category taxonomy gives
    no residential or land type is dropped rather than guessed at.
    """
    url = _abs(item.get("link") or "")
    if not url:
        return None
    terms = _terms(item)
    cats = terms.get("property_category", [])
    actions = " ".join(terms.get("property_action_category", []))
    statuses = " ".join(terms.get("property_status", []))
    title = _clean((item.get("title") or {}).get("rendered", ""))

    # Sales only, and nothing already sold / under contract / rented.
    # "Sales" is the only action category in use; a listing filed purely under
    # a rental/lease action is not for sale.
    if actions and not _SALE_RE.search(actions):
        return None
    if _DEAD_RE.search(f"{statuses} {title}"):
        return None
    if _is_commercial_only(cats):
        return None

    ptype = _ptype(cats, title)
    if ptype == OTHER:
        return None

    body = _text((item.get("content") or {}).get("rendered", ""))
    media = (item.get("_embedded") or {}).get("wp:featuredmedia") or []
    image = _abs(media[0].get("source_url") or "") if media and isinstance(media[0], dict) else ""
    city = (terms.get("property_city") or [""])[0]
    island = _island(" ".join(terms.get("property_county_state", [])), title, body)
    location = f"{city}, {island}" if city else island

    l = Listing(
        source=SOURCE, url=url, title=title, price=None, ptype=ptype,
        location=location, image=image,
        status=_status(statuses),
    )
    return l


def _enrich(l: Listing) -> bool:
    """Fill price, currency, MLS, beds, baths, sizes from the detail page.

    Returns False when the page turns out to be out of scope (a rental price
    period, or a sold/under-contract banner the REST terms did not show).
    """
    s = BeautifulSoup(get(l.url).text, "lxml")
    for tag in s(["script", "style", "noscript"]):
        tag.decompose()
    det = _details(s)
    pa = s.select_one(".price_area")
    price_txt = _clean(pa.get_text(" ", strip=True)) if pa else _clean(det.get("price"))
    sw = s.select_one(".status-wrapper")
    status_txt = _clean(sw.get_text(" ", strip=True)) if sw else ""

    if _PERIOD_RE.search(price_txt) or _DEAD_RE.search(status_txt):
        return False

    l.price, l.currency = _price(price_txt)
    if not l.price:
        return False

    mls = det.get("listing #") or det.get("listing") or det.get("mls") or ""
    l.mls = re.sub(r"^\s*(listing\s*#?|mls\s*#?)\s*", "", _clean(mls), flags=re.I)

    if l.ptype != LAND:
        l.beds = num(det.get("bedrooms"))
        l.baths = num(det.get("bathrooms"))

    size = num(det.get("property size"))
    lot = num(det.get("property lot size"))
    if lot:
        l.acres = round(lot if lot < ACRES_IF_UNDER else lot / SQFT_PER_ACRE, 4)
    if l.ptype == LAND:
        l.sqft = lot if (lot and lot >= ACRES_IF_UNDER) else (
            round(l.acres * SQFT_PER_ACRE) if l.acres else None)
    else:
        l.sqft = size

    if not l.image:
        og = s.find("meta", property="og:image")
        if og and og.get("content"):
            l.image = _abs(og["content"])
    # l.status already holds the normalised REST value; fold in the page banner.
    l.status = _status(l.status, status_txt)
    return True


def fetch(max_pages: int = 5) -> list[Listing]:
    """Island Realty's for-sale residential listings (Cayman Brac / Little Cayman).

    One REST request per page of 50 for discovery, then one detail request per
    listing for the price and the rest of the fields, capped at MAX_DETAILS.
    The whole inventory is 11 listings, so max_pages=1 is enough.
    """
    items: list[dict] = []
    total_pages = None
    for page in range(1, max_pages + 1):
        if total_pages is not None and page > total_pages:
            break
        try:
            r = get(API, params={
                "per_page": PER_PAGE,
                "page": page,
                "orderby": "date",
                "order": "desc",
                "_embed": "wp:featuredmedia,wp:term",
                "_fields": "id,link,title,content,_links,_embedded",
            }, headers={"Accept": "application/json"})
        except Exception as e:
            if page == 1:
                raise RuntimeError(f"Island Realty: REST API unavailable ({e})") from e
            print(f"[{SOURCE}] page {page} failed: {e}")
            break
        try:
            total_pages = int(r.headers.get("X-WP-TotalPages") or 0) or None
        except ValueError:
            pass
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        items.extend(batch)

    out: list[Listing] = []
    seen: set[str] = set()
    for item in items:
        try:
            l = _from_rest(item)
            if not l or l.url in seen:
                continue
            seen.add(l.url)
            out.append(l)
        except Exception as e:
            print(f"[{SOURCE}] bad item {item.get('id')}: {e}")

    kept: list[Listing] = []
    for l in out[:MAX_DETAILS]:
        try:
            if _enrich(l):
                kept.append(l)
        except Exception as e:
            print(f"[{SOURCE}] detail failed {l.url}: {e}")
    kept.sort(key=lambda l: -(l.price_kyd or 0))
    return kept
