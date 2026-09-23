"""MyRealtor (https://www.myrealtor.agency; myrealtor.ky redirects there).

A Webflow site that lists only MyRealtor's own listings (no IDX / MLS feed).
All for-sale listings are rendered server-side in one Webflow CMS collection
list on https://www.myrealtor.agency/sales (~30 cards; Finsweet CMS filter just
filters client-side). There is no JSON endpoint. Rentals live on /rent.

Each card carries: location, property type (Land / House / Town house /
Apartment / Condo), price, status badge ("For Sale" / "Under Contract"),
title, description, beds, baths, acres and a gallery of image URLs.

Prices: the `data-kyd` attribute holds the price in CI$ (the site's own JS
converts to US$ at 0.82 on demand and defaults to KYD), so currency is KYD.
The site shows no CIREBA MLS numbers, and no sq ft field (we pull a sq ft
figure from the card description when one is stated).

robots.txt is empty (nothing disallowed). Images are on cdn.prod.website-files.com.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper.common import Listing, get, num, norm_type, HOME, CONDO, LAND, OTHER

SOURCE = "MyRealtor"
BASE = "https://www.myrealtor.agency"
SALES_URL = BASE + "/sales"

_TYPES = {
    "land": LAND,
    "house": HOME,
    "town house": CONDO,
    "townhouse": CONDO,
    "apartment": CONDO,
    "condo": CONDO,
    "duplex": CONDO,
}


def _clean(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _field(a, name: str) -> str:
    el = a.select_one(f'[fs-cmsfilter-field="{name}"]')
    return _clean(el.get_text(" ")) if el else ""


def _visible_value(block) -> float | None:
    """Value inside a beds/baths/acres block, unless Webflow hid it."""
    if block is None or "w-condition-invisible" in (block.get("class") or []):
        return None
    for d in block.find_all("div"):
        v = num(d.get_text())
        if v is not None:
            return v
    return None


def _parse_card(item) -> Listing | None:
    a = item.select_one("a.property_item-content[href]")
    if a is None:
        return None
    url = urljoin(BASE, a["href"])
    if "/properties/" not in url or re.search(r"\brent(al)?\b", a["href"], re.I):
        return None

    badge = a.select_one(".property_badge-text")
    status = _clean(badge.get_text()) if badge else ""
    sl = status.lower()
    if "rent" in sl or "sold" in sl or "leased" in sl:
        return None
    if "contract" in sl or "offer" in sl or "pending" in sl:
        status = "Under Offer"
    elif not status or "sale" in sl:
        status = "For Sale"

    title_el = a.select_one(".listiings_title, .listings_title")
    title = _clean(title_el.get_text()) if title_el else ""
    desc_el = a.find("p")
    desc = _clean(desc_el.get_text(" ")) if desc_el else ""

    site_type = _field(a, "property-type")
    tl = site_type.lower()
    if "commercial" in tl or "office" in tl or "retail" in tl:
        return None
    if re.search(r"timeshare|fractional", title, re.I):
        return None
    ptype = _TYPES.get(tl) or norm_type(site_type or title)

    pe = a.select_one(".property-price[data-kyd]") or a.select_one(".property-price")
    price = None
    if pe is not None:
        price = num(pe.get("data-kyd") or pe.get_text())
    if not price:
        return None

    beds = _visible_value(a.select_one(".listing-posting_bedrooms-number"))
    baths = _visible_value(a.select_one(".listing-postings_bathrooms-number"))
    acres = _visible_value(a.select_one(".listing-posting_acres"))

    sqft = None
    m = re.search(r"(\d{1,3}(?:,\d{3})+|\d{3,6})\s*(?:\+\s*)?(?:sq\.?\s*ft|sq\.?\s*feet|square\s+f(?:ee|oo)t)",
                  desc, re.I)
    if m:
        sqft = num(m.group(1))

    image = ""
    img = item.select_one(".hidden-gallery img[src]")
    if img is not None:
        src = img.get("src") or ""
        if src and "placeholder" not in src:
            image = urljoin(BASE, src)

    return Listing(
        source=SOURCE, url=url, title=title, price=price, currency="KYD",
        ptype=ptype, location=_field(a, "location"), beds=beds, baths=baths,
        sqft=sqft, acres=acres, image=image, mls="", status=status,
    )


def fetch(max_pages: int = 5) -> list[Listing]:
    """All MyRealtor for-sale listings. Normally one request (/sales); follows
    Webflow pagination ("Next" link) up to `max_pages` pages if it ever appears."""
    out: list[Listing] = []
    seen: set[str] = set()
    url = SALES_URL
    for _ in range(max(1, max_pages)):
        soup = BeautifulSoup(get(url).text, "lxml")
        for item in soup.select(".property_item.w-dyn-item"):
            try:
                l = _parse_card(item)
            except Exception as e:
                print(f"[{SOURCE}] card parse error: {e}")
                continue
            if not l or not l.url or not l.price or l.url in seen:
                continue
            seen.add(l.url)
            out.append(l)
        nxt = soup.select_one("a.w-pagination-next[href]")
        if nxt is None:
            break
        url = urljoin(url, nxt["href"])
    return out
