"""CIREBA (Cayman Islands Real Estate Brokers Association MLS) scraper.

The site (Laravel/WingCMS) renders result cards server-side; there is no public
JSON listing endpoint. Search filters are encoded as path segments:

    https://www.cireba.com/cayman-residential-property-for-sale/listingtype_14,5/filterby_N?page=2
    https://www.cireba.com/cayman-land-for-sale/filterby_N?page=2

  listingtype_14 = Condominiums, 5 = Semi-detached/Duplex/Triplex,
  listingtype_4  = Single Family Home, 15 = Standalone Home (Part of Strata)
  filterby_N     = newest first (default is price high-to-low)

30 cards per page. Each card carries MLS#, title, sqft/beds/baths or acres,
district, and the price in both currencies (data-usd / data-ci), with
data-default holding the currency the listing is advertised in.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..common import Listing, get, parse_price, norm_type, num, HOME, CONDO, LAND

SOURCE = "CIREBA"
BASE = "https://www.cireba.com"

# (path, property type). Timeshare/fractional, multi-unit, commercial are skipped.
CATEGORIES = [
    ("cayman-residential-property-for-sale/listingtype_4,15/filterby_N", HOME),
    ("cayman-residential-property-for-sale/listingtype_14,5/filterby_N", CONDO),
    ("cayman-land-for-sale/filterby_N", LAND),
]
PER_PAGE = 30


def _abs(u: str) -> str:
    if not u:
        return ""
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("/"):
        return BASE + u
    return u


def _parse_card(art, ptype: str) -> Listing | None:
    cap = art.select_one("div.-caption a[href]")
    if not cap:
        return None
    url = _abs(cap["href"].strip())
    if "/property-detail/" not in url:
        return None
    if re.search(r"for-rent|rental", url, re.I):
        return None  # safety: never include rentals

    h2 = cap.find("h2")
    title = (h2.get_text(" ", strip=True) if h2 else cap.get("title", "")).strip()

    mls = ""
    for div in cap.find_all("div", recursive=False):
        t = div.get_text(" ", strip=True)
        m = re.search(r"MLS#?:?\s*(\d+)", t)
        if m:
            mls = m.group(1)
            break
    if not mls:
        fav = art.select_one("a.addfavorites[mls]")
        mls = fav["mls"] if fav else ""

    beds = baths = sqft = acres = None
    for li in cap.select("ul li"):
        t = li.get_text(" ", strip=True)
        tl = t.lower()
        if "bed" in tl:
            beds = num(t)
        elif "bath" in tl:
            baths = num(t)
        elif "acre" in tl:
            acres = num(t)
        elif "sq" in tl:
            sqft = num(t)

    location = ""
    loc = cap.select_one("div.text-truncate")
    if loc:
        location = loc.get_text(" ", strip=True)
        # "Seven Mile Beach, Grand Cayman" -> keep district, drop island if Grand Cayman
        location = re.sub(r",\s*Grand Cayman$", "", location)

    price, currency = None, "USD"
    pdiv = cap.select_one("div.-price") or art.select_one("[data-default]")
    if pdiv:
        raw = pdiv.get("data-default") or pdiv.get_text(" ", strip=True)
        price, currency = parse_price(raw)

    image = ""
    img = art.select_one("img[data-src]") or art.select_one("img[src]")
    if img:
        src = img.get("data-src") or img.get("src") or ""
        if "loader.svg" not in src:
            image = _abs(src)

    # Refine type from title when the category is broad (e.g. duplex in condo bucket is fine;
    # a "home" standalone strata listing stays house).
    if ptype != LAND and norm_type(title) == LAND and not beds:
        ptype = LAND

    return Listing(
        source=SOURCE, url=url, title=title, price=price, currency=currency,
        ptype=ptype, location=location, beds=beds, baths=baths, sqft=sqft,
        acres=acres, image=image, mls=mls, status="For Sale",
    )


def fetch(max_pages: int = 5) -> list[Listing]:
    """Fetch newest for-sale houses, condos and land.

    `max_pages` is applied per category (houses, condos, land), so the total number
    of result-page requests is at most 3 * max_pages. No detail pages are fetched.
    """
    out: list[Listing] = []
    seen: set[str] = set()
    for path, ptype in CATEGORIES:
        for page in range(1, max_pages + 1):
            url = f"{BASE}/{path}" + (f"?page={page}" if page > 1 else "")
            try:
                html = get(url).text
            except Exception as e:  # network / HTTP error: move to next category
                print(f"[{SOURCE}] {url}: {e}")
                break
            soup = BeautifulSoup(html, "lxml")
            cards = soup.select("article.pro-item-01")
            for art in cards:
                try:
                    l = _parse_card(art, ptype)
                except Exception as e:
                    print(f"[{SOURCE}] card parse error on {url}: {e}")
                    continue
                if not l or not l.url:
                    continue
                key = l.mls or l.url
                if key in seen:
                    continue
                seen.add(key)
                out.append(l)
            # Stop when this was the last page.
            m = re.search(r"Showing\s+\d+\s*-\s*(\d+)\s+Results of\s+(\d+)", soup.get_text(" "))
            if len(cards) < PER_PAGE or (m and int(m.group(1)) >= int(m.group(2))):
                break
    return out
