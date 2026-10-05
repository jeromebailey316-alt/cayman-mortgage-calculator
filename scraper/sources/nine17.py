"""Nine17 Realty Group (nine17realty.com) scraper.

WordPress + the AgentImage "AIOS" listings plugin.  Two useful endpoints:

    /wp-json/aios-listings/v1/listing      -> JSON list of listings
    /aios-listings-sitemap.xml             -> one <loc> per listing

The JSON route ignores `per_page` / `page` / `limit` and returns 10 items, but
it passes unknown query args straight into WP_Query, so `?posts_per_page=100`
(with `&paged=N`) returns the whole set -- 37 items as of Oct 2026, exactly
the 37 URLs in the sitemap, which we still read as a cross-check / fallback.

Each item carries `listing_details`: `list_price`, `price_arrangement`,
`details_mls_number` (the agency's own "Listing" reference shown on the page),
`details_bedrooms`, `details_bathrooms`, `details_appx_living_area`,
`details_lot_area`, `full_address` and `image_full`.  It does NOT carry the
listing's status or property type: `property_statuses` / `property_types` come
back as empty arrays for every listing even though the detail page renders
them.  So we fetch the detail page of each sale candidate and read the
"Status" / "Property Type" / "Neighborhoods" rows from `ul.listings-extras`.
That matters: without it we would publish Sold and Pending listings (7 of the
20 sale-priced posts are Sold or Pending).

CURRENCY: everything is KYD.  `price_currency` is the useless string "Dollar"
for every listing and the price widget renders a bare "$", but every
description that names a currency names CI$ -- and the figure matches the
`list_price` exactly (CI$105,000 / CI$380,000 / CI$589,000 / CI$1,100,000 /
CI $599,000).  No listing mentions US$ or USD.  We therefore default to KYD
and only switch to USD when a description explicitly says US$/USD.

REFERENCE CODES: "R####" is reliably a rental, but "S" is not reliably a sale
-- S0108 is "Modern 1-Bedroom Apartment for Rent" at $2,500/month.  Rentals
are instead rejected on price (nothing in Cayman sells below CI$25k), on the
rent wording in the title, and finally on the detail page's own status.

robots.txt: "User-Agent: * / Disallow:" (everything allowed).
"""
from __future__ import annotations

import html as htmlmod
import re

from bs4 import BeautifulSoup

from scraper.common import Listing, get, num, norm_type, HOME, CONDO, LAND, OTHER

SOURCE = "Nine17 Realty"
BASE = "https://nine17realty.com"
API = f"{BASE}/wp-json/aios-listings/v1/listing"
SITEMAP = f"{BASE}/aios-listings-sitemap.xml"
PER_PAGE = 100
MAX_DETAILS = 40          # hard cap on detail-page fetches
SALE_MIN = 25000.0        # below this a "price" is a monthly/weekly rent
SQFT_PER_ACRE = 43560.0

RENT_TITLE_RE = re.compile(
    r"\bfor\s+rent\b|\brentals?\b|\bfor\s+lease\b|\bshort[\s-]?term\b|\blong[\s-]?term\b", re.I)
DEAD_STATUS_RE = re.compile(
    r"\bsold\b|\bpending\b|under\s+(?:offer|contract)|\brented\b|\bleased\b|"
    r"off\s*market|withdrawn|expired|for\s+rent|for\s+lease", re.I)
USD_RE = re.compile(r"US\s?\$|\bUSD\b")
KYD_RE = re.compile(r"CI\s?\$|\bKYD\b")


def _txt(v) -> str:
    return htmlmod.unescape(str(v or "")).strip()


def _api_items(max_pages: int) -> list[dict]:
    items: list[dict] = []
    for page in range(1, max(1, max_pages) + 1):
        url = f"{API}?posts_per_page={PER_PAGE}&paged={page}"
        try:
            r = get(url, headers={"Accept": "application/json"})
            batch = r.json()
        except Exception as e:
            if page == 1:
                raise RuntimeError(f"{SOURCE}: listings API failed ({url}): {e}") from e
            break
        if not isinstance(batch, list) or not batch:
            break
        items.extend(batch)
        if len(batch) < PER_PAGE:
            break
    return items


def _sitemap_urls() -> list[str]:
    try:
        xml = get(SITEMAP).text
    except Exception:
        return []
    return [u.strip() for u in re.findall(r"<loc>\s*([^<]+?)\s*</loc>", xml) if "/listings/" in u]


def _detail_rows(soup: BeautifulSoup) -> dict[str, str]:
    """The Status / Year Built / Property Type / Neighborhoods block."""
    rows: dict[str, str] = {}
    for li in soup.select("ul.listings-extras li"):
        label = li.select_one("span")
        if not label:
            continue
        lab = label.get_text(" ", strip=True)
        val = li.get_text(" ", strip=True)[len(lab):].strip(" :")
        if lab:
            rows[lab] = val
    return rows


def _description(soup: BeautifulSoup) -> str:
    h = soup.find(["h2", "h3"], string=re.compile(r"About This Property", re.I))
    node = h.find_parent(["section", "div"]) if h else None
    return re.sub(r"\s+", " ", (node or soup).get_text(" ", strip=True))


def _currency(desc: str) -> str:
    if USD_RE.search(desc) and not KYD_RE.search(desc):
        return "USD"
    return "KYD"          # site-wide convention, see module docstring


def _ptype(type_terms: str, title: str, desc: str, beds: float | None) -> str | None:
    terms = [t.strip().lower() for t in type_terms.split(",") if t.strip()]
    if any(t in ("land", "lot", "vacant land") for t in terms):
        return LAND
    if any(t in ("townhouse", "townhome", "condo", "condominium", "apartment",
                 "villa", "duplex") for t in terms):
        return CONDO
    if any(t in ("residential", "single family", "single-family", "single family home",
                 "house", "home") for t in terms):
        return HOME
    if terms and all(t in ("commercial", "office", "retail", "industrial", "business")
                     for t in terms):
        return None
    # No usable taxonomy: judge from the words.
    if re.search(r"\blots?\b|\bland\b|\bparcel\b|\bhomesite\b|\bacres?\b", title, re.I):
        return LAND
    if beds:
        if re.search(r"townhome|townhouse|condo|apartment|\bunit\b", f"{title} {desc[:400]}", re.I):
            return CONDO
        return HOME
    t = norm_type(title)
    return t if t != OTHER else norm_type(desc[:300])


def _from_desc(desc: str, pat: str) -> float | None:
    m = re.search(pat, desc, re.I)
    return float(m.group(1).replace(",", "")) if m else None


def _parse(item: dict, html: str) -> Listing | None:
    d = item.get("listing_details") or {}
    url = (item.get("url") or "").strip()
    price = num(d.get("list_price") or d.get("price"))
    if not url or not price or price < SALE_MIN:
        return None

    soup = BeautifulSoup(html, "lxml")
    rows = _detail_rows(soup)
    status = rows.get("Status", "").strip()
    if DEAD_STATUS_RE.search(status):
        return None
    desc = _description(soup)
    title = _txt(item.get("title"))
    if RENT_TITLE_RE.search(title):
        return None

    beds = num(d.get("details_bedrooms")) or _from_desc(desc, r"(\d+)[\s-]*bed")
    baths = num(d.get("details_bathrooms")) or _from_desc(desc, r"(\d+(?:\.\d+)?)[\s-]*bath")
    # The site mislabels every unit as "acres"; living area is really sq ft and
    # lot area really acres (0.2301, 0.3714, ...).
    sqft = num(d.get("details_appx_living_area")) or \
        _from_desc(desc, r"([\d,]+)\s*(?:sq\.?\s*ft|square\s*feet|sqft)")
    acres = num(d.get("details_lot_area")) or _from_desc(desc, r"([\d.]+)[\s-]*acres?\b")

    ptype = _ptype(rows.get("Property Type", ""), title, desc, beds)
    if ptype is None:
        return None
    if ptype == LAND:
        beds = baths = None
        if acres and not sqft:
            sqft = round(acres * SQFT_PER_ACRE)

    district = rows.get("Neighborhoods", "").strip()
    addr = _txt(d.get("full_address"))
    if addr.lower() in ("grand cayman", "cayman islands"):
        addr = ""
    location = f"{addr}, {district}" if addr and district and district.lower() not in addr.lower() \
        else (addr or district)

    return Listing(
        source=SOURCE,
        url=url,
        title=title,
        price=price,
        currency=_currency(desc),
        ptype=ptype,
        location=location,
        beds=beds or None,
        baths=baths or None,
        sqft=sqft or None,
        acres=acres or None,
        image=_txt(item.get("image_full") or item.get("image_large")),
        mls=_txt(d.get("details_mls_number")),
        status=status or "For Sale",
    )


def _is_sale_candidate(item: dict) -> bool:
    d = item.get("listing_details") or {}
    price = num(d.get("list_price") or d.get("price"))
    if not price or price < SALE_MIN:
        return False                                   # rent, or no price at all
    if re.match(r"^R\d", _txt(d.get("details_mls_number")), re.I):
        return False                                   # R#### is always a rental
    return not RENT_TITLE_RE.search(_txt(item.get("title")))


def fetch(max_pages: int = 5) -> list[Listing]:
    """`max_pages` caps pages of PER_PAGE (100) listings from the JSON API;
    the whole site is ~37 listings, so one page is enough.  Detail pages are
    then fetched for the sale candidates only, capped at MAX_DETAILS."""
    items = _api_items(max_pages)
    if not items:
        raise RuntimeError(f"{SOURCE}: listings API returned nothing ({API})")

    by_url = {(it.get("url") or "").rstrip("/"): it for it in items if it.get("url")}
    # Sitemap cross-check: if the API ever stops honouring posts_per_page we
    # still see the missing listings (price/beds then come from the page only).
    for u in _sitemap_urls():
        key = u.rstrip("/")
        if key not in by_url:
            by_url[key] = {"url": u, "title": "", "listing_details": {}}

    cands = [it for it in by_url.values() if _is_sale_candidate(it)]
    out: list[Listing] = []
    seen: set[str] = set()
    for item in cands[:MAX_DETAILS]:
        url = item["url"]
        try:
            html = get(url).text
            li = _parse(item, html)
            if li and li.url.rstrip("/") not in seen:
                seen.add(li.url.rstrip("/"))
                out.append(li)
        except Exception:
            continue
    return out
