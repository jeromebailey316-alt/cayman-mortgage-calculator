"""Stone Land Properties (https://www.stonelandproperties.ky).

WingCMS (Netclues), same platform family as trident.py / rainbow.py but a
newer theme, so the class names differ.  Everything is server-rendered HTML;
there is no JSON listing endpoint.

    /properties-for-sale?page=N      6 cards per page, 5 pages, 29 listings

Cards are complete: title, detail URL, status badge, location, price and
beds / baths / sq ft (or lot width / depth for land).  The price element
carries `data-default` in the currency the listing is advertised in, plus
converted `data-usd` / `data-ci` values, so the advertised currency is exact.

The detail URL encodes the category:
    /property-detail/<area>/<category>/<slug>
with <category> one of residential-properties-for-sale-in-cayman-islands,
lands-for-sale-in-cayman-islands or commercial-properties-for-sale-in-cayman-islands.
House vs condo is not published anywhere (detail pages have no "Property Type"
field), so we infer it from the title the way rainbow.py does.

We deliberately do NOT use /sitemap.xml for discovery even though it lists
50+ detail URLs: it keeps stale pages, and those pages are indistinguishable
from live ones - e.g. .../residential-properties-for-sale-.../furnished-3bedroom-
villa-for-rent is a CI$3,900/month rental still badged "Current".  The
paginated /properties-for-sale index is the only reliable list of what is
actually on the market.  (A price floor catches any that slip through.)

Status badges seen: New, Current, Pen/Con.  Only New and Current are kept.

Stone Land is not a CIREBA member site: no listing shows an MLS number, only
the site's own "ID#: 202628".  `Listing.mls` is left empty on purpose - run.py
de-dupes globally on `mls:<digits>`, and these 6-digit site IDs sit in the same
range as real CIREBA MLS numbers, so putting them there would merge unrelated
properties.  The detail URL is the per-listing identity instead.

robots.txt (checked 5 Oct 2026) is `Disallow:` - empty, i.e. everything is
allowed.  Images live under /caches/ and we only record their URLs anyway.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from scraper.common import Listing, get, parse_price, num, HOME, CONDO, LAND

SOURCE = "Stone Land"
BASE = "https://www.stonelandproperties.ky"
LIST_URL = BASE + "/properties-for-sale"
DETAIL_CAP = 40
SQFT_PER_ACRE = 43560.0

# Anything cheaper than this is a monthly rent, not an asking price.
MIN_PRICE = 20_000.0

_CONDO_RE = re.compile(
    r"condo|apartment|\bapt\b|town\s*house|town\s*home|duplex|triplex|semi[-\s]?detached|"
    r"\bunit\b|#\s*\d|\bsuite\b|strata|residences?\b|villas?\b|phase\s*\d", re.I)
_RENT_RE = re.compile(r"for\s*rent|rental|per\s*month|/\s*month|\bmonthly\b|all\s*inclusive", re.I)


def _clean(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _category(url: str) -> str:
    parts = urlparse(url).path.strip("/").split("/")
    # property-detail/<area>/<category>/<slug>
    return parts[2].lower() if len(parts) >= 4 and parts[0] == "property-detail" else ""


def _status(badge: str) -> str | None:
    """None -> drop the listing."""
    b = badge.strip().lower()
    if not b:
        return "For Sale"
    if re.search(r"\bsold\b|\brented\b|\bleased\b|withdrawn|expired|off\s*market", b):
        return None
    if re.search(r"pen\s*/\s*con|pending|under\s*(offer|contract)|contract", b):
        return None            # not genuinely available
    return "For Sale"          # New / Current / Reduced / Price Change / ...


def _image(card, page_url: str) -> str:
    img = card.select_one(".thumbnail img[src]") or card.select_one("img[src]")
    if img is not None:
        src = (img.get("src") or "").strip()
        if src and "loader.svg" not in src:
            return urljoin(page_url, src)
    src_el = card.select_one("picture source[srcset]")
    if src_el is not None:
        first = (src_el.get("srcset") or "").split(",")[0].strip().split(" ")[0]
        if first:
            return urljoin(page_url, first)
    return ""


def _parse_card(card, page_url: str) -> Listing | None:
    link = card.select_one(".ac-lptitle a[href]") or card.select_one(".-more a[href]")
    if not link:
        return None
    url = urljoin(page_url, link["href"].strip())
    if "/property-detail/" not in url:
        return None

    cat = _category(url)
    if "commercial" in cat or "for-rent" in cat or "rental" in cat:
        return None
    # NB: "cayman-islands" contains "land", so match the category word exactly.
    if "residential" in cat:
        ptype = None           # house vs condo decided from the title below
    elif re.match(r"lands?-", cat) or re.search(r"\blots?\b", cat):
        ptype = LAND
    else:
        return None

    title = _clean(link.get("title") or link.get_text())
    if _RENT_RE.search(title):
        return None

    badge = card.select_one(".-pro-list-label")
    status = _status(_clean(badge.get_text()) if badge else "")
    if status is None:
        return None

    pe = card.select_one(".-price")
    price, cur = parse_price(pe.get("data-default") or pe.get_text()) if pe is not None else (None, "USD")
    if not price or price < MIN_PRICE:
        return None

    loc = card.select_one(".-pro-list-location")
    location = _clean(loc.get_text()) if loc else ""
    location = re.sub(r",?\s*Cayman Islands$", "", location, flags=re.I)

    beds = baths = sqft = acres = None
    width = depth = None
    for li in card.select("ul.-pro-list-amenities li"):
        icon = li.select_one("[data-icon]")
        kind = (icon.get("data-icon") or "") if icon is not None else ""
        txt = _clean(li.get_text(" "))
        if txt.lower().startswith("id#"):
            continue
        v = num(txt)
        if kind == "sl-bed":
            beds = v
        elif kind == "sl-bath":
            baths = v
        elif kind == "sl-sq-ft":
            sqft = v
        elif kind == "icon-width":
            width = v
        elif kind == "icon-depth":
            depth = v

    if ptype is None:
        ptype = CONDO if _CONDO_RE.search(title) else HOME

    if ptype == LAND:
        beds = baths = None
        if sqft is None and width and depth:
            sqft = round(width * depth)
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:\+\s*)?acres?\b", title, re.I)
        if m:
            acres = float(m.group(1))
        elif sqft:
            acres = round(sqft / SQFT_PER_ACRE, 3)

    return Listing(
        source=SOURCE, url=url, title=title, price=price, currency=cur,
        ptype=ptype, location=location, beds=beds, baths=baths, sqft=sqft,
        acres=acres, image=_image(card, page_url), status=status,
    )


def _enrich(l: Listing) -> bool:
    """Confirm the status badge and pick up acreage / sq ft / the site's own
    listing ID from the detail page.  False -> drop the listing."""
    soup = BeautifulSoup(get(l.url).text, "lxml")

    badge = soup.select_one(".-pro-list-label")
    if badge is not None:
        if _status(_clean(badge.get_text())) is None:
            return False

    pe = soup.select_one("[data-default]")
    if pe is not None:
        price, cur = parse_price(pe.get("data-default"))
        if price and price >= MIN_PRICE:
            l.price, l.currency = price, cur

    for li in soup.select("ul.-pro-list-amenities li"):
        icon = li.select_one("[data-icon]")
        kind = (icon.get("data-icon") or "") if icon is not None else ""
        txt = _clean(li.get_text(" "))
        if re.match(r"ID#\s*:?\s*\w+", txt, re.I):
            # Stone Land's own listing ID, NOT a CIREBA MLS number - see the
            # module docstring for why it must not go into Listing.mls.
            continue
        if kind == "sl-sq-ft" and l.sqft is None:
            l.sqft = num(txt)
        elif kind == "sl-bed" and l.beds is None:
            l.beds = num(txt)
        elif kind == "sl-bath" and l.baths is None:
            l.baths = num(txt)

    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    text = _clean(soup.get_text(" "))
    if _RENT_RE.search(text[:400]):      # title area only, descriptions mention rentals
        return False
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:\+\s*)?(?:-\s*)?acres?\b", text, re.I)
    if m and l.acres is None:
        acres = float(m.group(1))
        if 0 < acres < 500:
            l.acres = acres
    if l.acres and l.ptype == LAND and l.sqft is None:
        l.sqft = round(l.acres * SQFT_PER_ACRE)
    return True


def fetch(max_pages: int = 5) -> list[Listing]:
    """Stone Land's for-sale residential + land listings.  `max_pages` caps the
    /properties-for-sale index pages read (6 cards each); the whole site is 5
    pages.  Up to DETAIL_CAP detail pages are then read for acreage."""
    listings: list[Listing] = []
    seen: set[str] = set()
    pages_read = 0

    for page in range(1, max(1, max_pages) + 1):
        url = LIST_URL + (f"?page={page}" if page > 1 else "")
        try:
            r = get(url)
        except Exception as exc:
            if page == 1:
                raise RuntimeError(f"{SOURCE}: cannot read {url}: {exc}") from exc
            break
        pages_read += 1
        soup = BeautifulSoup(r.text, "lxml")
        cards = soup.select("div.-pro-items")
        if not cards:
            break
        for card in cards:
            try:
                l = _parse_card(card, url)
            except Exception:
                continue
            if l and l.url and l.url not in seen:
                seen.add(l.url)
                listings.append(l)
        if not soup.select_one(f'a[href*="page={page + 1}"]'):
            break

    if pages_read and not listings and not seen:
        raise RuntimeError(f"{SOURCE}: {LIST_URL} returned no listing cards - layout changed?")

    keep: list[Listing] = []
    budget = DETAIL_CAP
    for l in listings:
        if budget > 0:
            budget -= 1
            try:
                if not _enrich(l):
                    continue
            except Exception:
                pass
        keep.append(l)
    return keep
