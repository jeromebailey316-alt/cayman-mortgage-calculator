"""Trident Properties (https://www.tridentproperties.ky).

The site (WingCMS / Laravel) renders listings as plain server-side HTML; there
is no public JSON endpoint.

  * https://www.tridentproperties.ky/for-sale
        Trident's own ("featured") for-sale listings, single page (~20 cards).
  * https://www.tridentproperties.ky/for-sale/idx_Y?page=N
        The full CIREBA IDX feed (~860 listings, 32 cards/page, price high->low).

Cards give title, URL, location, beds, baths, (sometimes) sq ft, price and an
image. The price element carries `data-default` in the currency the listing is
advertised in (US$ or CI$), plus converted `data-usd` / `data-ci` values.
The detail URL path encodes the type: /property-detail/<area>/<type>/<slug>.

The CIREBA MLS number, status, acreage and sq ft are only on detail pages, so
we fetch a capped number of detail pages (Trident's own listings first).

robots.txt disallows /caches/ etc. for crawlers; we never request those paths
(image URLs pointing there are only recorded, not fetched).
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from scraper.common import Listing, get, parse_price, norm_type, num, HOME, CONDO, LAND, OTHER

SOURCE = "Trident"
BASE = "https://www.tridentproperties.ky"
OWN_URL = BASE + "/for-sale"
IDX_URL = BASE + "/for-sale/idx_Y"
DETAIL_CAP = 40

# URL path type segment -> calculator type (None = skip)
_PATH_TYPES = {
    "residential": HOME,
    "residential-for-sale": HOME,
    "condominium-for-sale": CONDO,
    "condominium": CONDO,
    "land": LAND,
    "multi-unit": OTHER,
    "commercial": None,
}


def _clean(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _path_type(url: str):
    parts = urlparse(url).path.strip("/").split("/")
    # property-detail/<area>/<type>/<slug>
    seg = parts[2] if len(parts) >= 4 and parts[0] == "property-detail" else ""
    if seg in _PATH_TYPES:
        return _PATH_TYPES[seg]
    return norm_type(seg) if seg else OTHER


def _acres_from_text(text: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:\+\s*)?acres?\b", text or "", re.I)
    return float(m.group(1)) if m else None


def _parse_card(card, page_url: str) -> Listing | None:
    link = card.select_one(".prop_title a[href]") or card.select_one("a.thumbnail[href]")
    if not link:
        return None
    url = urljoin(page_url, link["href"])
    if "/property-detail/" not in url:
        return None
    ptype = _path_type(url)
    if ptype is None:  # commercial
        return None
    title = _clean(link.get("title") or link.get_text())

    price, cur = None, "USD"
    pe = card.select_one(".prop_price")
    if pe is not None:
        price, cur = parse_price(pe.get("data-default") or pe.get_text())

    loc = card.select_one(".location")
    location = _clean(loc.get_text()) if loc else ""
    location = re.sub(r",?\s*Cayman Islands$", "", location, flags=re.I)

    beds = baths = sqft = None
    for li in card.select(".prop_main_featurs li"):
        t = _clean(li.get_text())
        tl = t.lower()
        if "bed" in tl:
            beds = num(t)
        elif "bath" in tl:
            baths = num(t)
        elif "sq" in tl:
            sqft = num(t)

    image = ""
    img = card.select_one("img[data-src]") or card.select_one("img[src]")
    if img is not None:
        src = img.get("data-src") or img.get("src") or ""
        if src and "loader.svg" not in src:
            image = urljoin(page_url, src)

    return Listing(
        source=SOURCE, url=url, title=title, price=price, currency=cur,
        ptype=ptype, location=location, beds=beds, baths=baths, sqft=sqft,
        acres=_acres_from_text(title), image=image, status="For Sale",
    )


def _parse_page(html: str, page_url: str) -> list[Listing]:
    soup = BeautifulSoup(html, "lxml")
    out = []
    for card in soup.select(".properties_lisiting .property_info_wrap"):
        try:
            l = _parse_card(card, page_url)
            if l and l.url:
                out.append(l)
        except Exception:
            continue
    return out


def _enrich(l: Listing) -> bool:
    """Fill MLS / status / sqft / acres from the detail page. Returns False if
    the listing should be dropped (e.g. turns out to be a rental/commercial)."""
    soup = BeautifulSoup(get(l.url).text, "lxml")
    fields: dict[str, str] = {}
    for li in soup.select("li"):
        span = li.find("span")
        if span is None:
            continue
        full = _clean(li.get_text(" "))
        stext = _clean(span.get_text(" "))
        # "Label: <span>value</span>"
        if ":" in full and full.endswith(stext):
            label = full[: len(full) - len(stext)].strip().rstrip(":").strip().lower()
            if label and len(label) < 30:
                fields.setdefault(label, stext)
        # "<span>Label</span>value"
        elif full.startswith(stext):
            val = full[len(stext):].strip()
            if val and len(stext) < 30:
                fields.setdefault(stext.lower(), val)

    mls = fields.get("mls#") or fields.get("mls")
    if not mls:
        m = re.search(r"MLS#\s*(\d{4,})", soup.title.get_text() if soup.title else "")
        mls = m.group(1) if m else ""
    if mls:
        l.mls = re.sub(r"\D", "", mls)

    typ = fields.get("type", "")
    if re.search(r"\(rent", typ, re.I) or re.search(r"commercial", typ, re.I):
        return False
    if typ and l.ptype == OTHER:
        l.ptype = norm_type(typ)

    st = soup.select_one(".prop_staus span")
    if st:
        s = _clean(st.get_text())
        sl = s.lower()
        if sl in ("current", "active", "new", "increased", "reduced", "price change", "back on market"):
            l.status = "For Sale"
        elif "pen" in sl or "con" in sl:
            l.status = "Under Offer"
        elif s:
            l.status = s

    sq = fields.get("sq. ft") or fields.get("sq ft") or fields.get("sqft")
    if sq and not l.sqft:
        l.sqft = num(sq)
    ac = fields.get("acreage") or fields.get("acres")
    if ac and num(ac):
        l.acres = num(ac)
    if l.beds is None and fields.get("bedrooms"):
        l.beds = num(fields["bedrooms"])
    if l.baths is None and fields.get("bathrooms"):
        l.baths = num(fields["bathrooms"])
    return True


def fetch(max_pages: int = 5, detail_limit: int = DETAIL_CAP) -> list[Listing]:
    """Page budget: 1 page of Trident's own listings + (max_pages-1) IDX pages.
    Then up to `detail_limit` (<=40) detail pages for MLS numbers."""
    listings: list[Listing] = []
    seen: set[str] = set()

    def add(items):
        for l in items:
            if l.url not in seen:
                seen.add(l.url)
                listings.append(l)

    pages = [OWN_URL] + [IDX_URL if p == 1 else f"{IDX_URL}?page={p}"
                         for p in range(1, max(0, max_pages - 1) + 1)]
    for url in pages[:max(1, max_pages)]:
        try:
            items = _parse_page(get(url).text, url)
        except Exception:
            continue
        if not items and url != OWN_URL:
            break
        add(items)

    keep: list[Listing] = []
    budget = min(detail_limit, DETAIL_CAP)
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
