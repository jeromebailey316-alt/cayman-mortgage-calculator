"""Rainbow Realty (www.rainbowrealty.ky) scraper.

Not Wix: the site runs on WingCMS (Netclues) and renders listing cards
server-side, 24 per page, paginated with `?page=N`.  There is no JSON listing
endpoint (the only embedded JSON is the homepage's featured carousel).

The site separates Rainbow's own listings from the CIREBA IDX feed: URLs that
end in `/idx_Y` show the full MLS feed, the plain category pages show only
Rainbow's own listings.  We scrape only the own-listing pages:

    /cayman-islands-residential-real-estate   (houses, condos, duplexes)
    /cayman-islands-real-estate-land

Each card gives MLS#, area, title, beds / baths / sq ft (or acres for land),
price with currency (CI$ / US$), a status badge (Current / New / Pen/Con)
and a photo.  The site does not expose house-vs-condo for residential
listings (not even on detail pages, which just say "Type: Residential"), so
we infer it from the title.  robots.txt only disallows /wingcms and /wingai.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper.common import Listing, get, num, HOME, CONDO, LAND

SOURCE = "Rainbow Realty"
BASE = "https://www.rainbowrealty.ky"
CATEGORIES = [
    ("/cayman-islands-residential-real-estate", HOME),
    ("/cayman-islands-real-estate-land", LAND),
]
SQFT_PER_ACRE = 43560.0
_CONDO_RE = re.compile(r"condo|apartment|\bapt\b|town\s*house|town\s*home|duplex|triplex|"
                       r"\bunit\b|#\s*\d|\bsuite\b|strata|residences?\b|villas?\b", re.I)
_SKIP_RE = re.compile(r"fractional|time\s*share|commercial|industrial|business|"
                      r"for rent|rental|warehouse|office|retail|parking", re.I)


def _price(txt: str) -> tuple[float | None, str]:
    cur = "KYD" if re.search(r"CI\s*\$|KYD", txt, re.I) else "USD"
    m = re.search(r"\d[\d,]*(?:\.\d+)?", txt)
    p = float(m.group(0).replace(",", "")) if m else None
    return (p or None), cur


def _status(badge: str) -> str | None:
    b = badge.strip().lower()
    if re.search(r"\bsold\b|\bfor rent\b|\brented\b|\bleased\b|withdrawn|expired", b):
        return None
    if re.search(r"pen\s*/\s*con|pending|under\s*(offer|contract)", b):
        return "Under Offer"
    return "For Sale"


def _parse_card(card, cat_type: str) -> Listing | None:
    a = card.select_one(".t-listing a[href]") or card.select_one("a[href*='/property-detail/']")
    if not a:
        return None
    url = urljoin(BASE, a["href"].strip())
    if "/property-detail/" not in url:
        return None
    # The category segment of the URL, e.g. residential-properties-for-sale-...
    seg = url.split("/property-detail/", 1)[1].split("/")
    cat = seg[1] if len(seg) > 1 else ""
    if "for-sale" not in cat or re.search(r"commercial|business|multi-unit|rent", cat):
        return None
    title = a.get_text(" ", strip=True) or a.get("title", "")
    if _SKIP_RE.search(title):
        return None

    badge = card.select_one(".listing-featured")
    status = _status(badge.get_text(" ", strip=True) if badge else "")
    if status is None:
        return None

    pr = card.select_one(".l-price strong") or card.select_one(".l-price")
    price, cur = _price(pr.get_text(" ", strip=True) if pr else "")
    if not price:
        return None

    mls, location = "", ""
    pid = card.select_one(".p-id")
    if pid:
        spans = [s.get_text(" ", strip=True) for s in pid.find_all("span")]
        for s in spans:
            m = re.search(r"MLS\s*#?\s*:?\s*([A-Za-z0-9-]+)", s, re.I)
            if m:
                mls = m.group(1)
            elif s:
                location = s

    beds = baths = sqft = acres = None
    for sp in card.select(".l-s > span"):
        icon = sp.select_one("[data-icon]")
        kind = icon.get("data-icon", "") if icon else ""
        txt = sp.get_text(" ", strip=True)
        v = num(txt)
        if kind == "bed":
            beds = v
        elif kind == "bathtub":
            baths = v
        elif re.search(r"acre", txt, re.I):
            acres = v
        elif re.search(r"sq\.?\s*ft|ft", txt, re.I) or kind == "ruler":
            sqft = v

    if cat_type == LAND or cat.startswith("lands-"):
        ptype = LAND
        if acres is None:
            m = re.search(r"(\d+(?:\.\d+)?)\s*acres?", title, re.I)
            acres = float(m.group(1)) if m else (round(sqft / SQFT_PER_ACRE, 3) if sqft else None)
        beds = baths = None
    else:
        ptype = CONDO if _CONDO_RE.search(title) else HOME

    img = card.select_one("img[src]")
    image = urljoin(BASE, img["src"].strip()) if img else ""
    return Listing(source=SOURCE, url=url, title=title, price=price, currency=cur,
                   ptype=ptype, location=location, beds=beds, baths=baths, sqft=sqft,
                   acres=acres, image=image, mls=mls, status=status)


def fetch(max_pages: int = 5) -> list[Listing]:
    """Rainbow's own for-sale residential + land listings.  `max_pages` caps
    result pages (24 cards each) per category."""
    out: list[Listing] = []
    seen: set[str] = set()
    for path, cat_type in CATEGORIES:
        for page in range(1, max_pages + 1):
            url = f"{BASE}{path}" + (f"?page={page}" if page > 1 else "")
            try:
                r = get(url)
            except Exception:
                break
            soup = BeautifulSoup(r.text, "lxml")
            cards = soup.select("div.p-listing")
            if not cards:
                break
            for card in cards:
                try:
                    l = _parse_card(card, cat_type)
                    if l and l.url not in seen:
                        seen.add(l.url)
                        out.append(l)
                except Exception:
                    continue
            if not soup.select_one(f'a.page-link[href*="page={page + 1}"]'):
                break
    return out
