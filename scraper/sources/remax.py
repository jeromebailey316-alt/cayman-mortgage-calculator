"""RE/MAX Cayman Islands (www.remax.ky) scraper.

The site is WordPress with a custom listings theme (no listings REST route).
The search page's own JS calls the archive URL with `ajax=1`, which returns
JSON: {"html": <rendered result cards>, "listings": [...]}.  With `show-map=1`
the `listings` array is populated (id, title, link, location, beds, baths,
price, lat/long, img) and the HTML contains compact cards (6 per page) that
add MLS # and sq ft.  We join the two on the WordPress post id.

    https://www.remax.ky/listings/[page/N/]?type=Home&show-map=1&ajax=1

Rentals are only included with `lease=1`, so the default archive is for sale.
We query per type (Home, Condominium, Land) so the property type is known
without fetching detail pages.
"""
from __future__ import annotations

import html as htmlmod
import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from scraper.common import Listing, get, num, HOME, CONDO, LAND

SOURCE = "RE/MAX"
BASE = "https://www.remax.ky"
TYPES = [("Home", HOME), ("Condominium", CONDO), ("Land", LAND)]
SQFT_PER_ACRE = 43560.0


def _clean_url(u: str) -> str:
    """Absolute URL with query/fragment removed (cards append ?back=...)."""
    p = urlsplit(urljoin(BASE, (u or "").strip()))
    return urlunsplit((p.scheme, p.netloc, p.path, "", ""))


def _text(s) -> str:
    return re.sub(r"\s+", " ", htmlmod.unescape(BeautifulSoup(s or "", "lxml").get_text(" "))).strip()


def _price(raw: str) -> tuple[float | None, str]:
    txt = _text(raw)
    if not re.search(r"\d", txt):
        return None, "USD"
    # Strip the currency code before parsing: parse_price() would read the
    # "K" of "KYD" as a thousands suffix ("5,706,000 KYD" -> 5.7e9).
    cur = "KYD" if re.search(r"KYD|CI\s*\$|\bCI\b", txt, re.I) else "USD"
    m = re.search(r"\d[\d,]*(?:\.\d+)?", txt)
    price = float(m.group(0).replace(",", "")) if m else None
    return (price or None), cur


def _cards(soup: BeautifulSoup) -> dict[int, dict]:
    """Extract per-card extras (MLS, sqft, beds, baths, status) keyed by post id."""
    out: dict[int, dict] = {}
    for a in soup.select("a.property-card-small[data-id]"):
        try:
            pid = int(a["data-id"])
            d: dict = {"url": _clean_url(a.get("href", ""))}
            t = a.select_one(".property-card-small--title")
            d["title"] = t.get_text(" ", strip=True) if t else ""
            for tab in a.select(".property-tabs"):
                cls = tab.get("class", [])
                v = num(tab.get_text())
                for k in ("bed", "bath", "sqft"):
                    if k in cls:
                        d[k] = v
            m = re.search(r"MLS\s*#?:?\s*([A-Za-z0-9-]+)", a.get_text(" ", strip=True))
            if m:
                d["mls"] = m.group(1)
            pr = a.select_one(".property-price")
            if pr:
                d["price_html"] = str(pr)
            img = a.select_one("img[src]")
            if img:
                d["img"] = img["src"].strip()
            full = a.get_text(" ", strip=True).lower()
            if "under offer" in full:
                d["status"] = "Under Offer"
            elif re.search(r"\bsold\b", full):
                d["status"] = "Sold"
            out[pid] = d
        except Exception:
            continue
    return out


def _acres_from_title(title: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*[- ]?\s*(?:acres?|ac)\b", title or "", re.I)
    return float(m.group(1)) if m else None


def _page_url(type_name: str, page: int) -> str:
    path = "/listings/" if page == 1 else f"/listings/page/{page}/"
    return f"{BASE}{path}?type={type_name}&show-map=1&ajax=1"


def fetch(max_pages: int = 5) -> list[Listing]:
    """Fetch for-sale listings. `max_pages` is the page cap *per property type*
    (Home, Condominium, Land); each page holds 6 listings."""
    results: list[Listing] = []
    seen: set[str] = set()

    for type_name, ptype in TYPES:
        for page in range(1, max_pages + 1):
            try:
                r = get(_page_url(type_name, page), headers={"Accept": "application/json"})
                data = r.json()
            except Exception:
                break  # 404 past the last page, or a bad response
            items = data.get("listings") or []
            html = data.get("html") or ""
            soup = BeautifulSoup(html, "lxml")
            cards = _cards(soup)
            if not items and not cards:
                break

            by_id = {}
            for it in items:
                try:
                    by_id[int(it.get("id"))] = it
                except Exception:
                    continue
            ids = list(dict.fromkeys(list(by_id) + list(cards)))

            for pid in ids:
                try:
                    it = by_id.get(pid, {})
                    c = cards.get(pid, {})
                    url = _clean_url(it.get("link") or c.get("url") or "")
                    if not url or url.rstrip("/").endswith("/listings") or url in seen:
                        continue
                    title = _text(it.get("title")) or c.get("title", "")
                    price, cur = _price(it.get("price") or c.get("price_html") or "")
                    sqft = c.get("sqft")
                    acres = _acres_from_title(title)
                    lt = ptype  # from the site's own type filter
                    if lt == LAND and acres is None and sqft:
                        acres = round(sqft / SQFT_PER_ACRE, 3)
                    beds = num(it.get("bedrooms")) if it.get("bedrooms") not in (None, "") else c.get("bed")
                    baths = num(it.get("bathrooms")) if it.get("bathrooms") not in (None, "") else c.get("bath")
                    img = (it.get("img") or c.get("img") or "").strip()
                    results.append(Listing(
                        source=SOURCE,
                        url=url,
                        title=title,
                        price=price,
                        currency=cur,
                        ptype=lt,
                        location=_text(it.get("location")),
                        beds=beds,
                        baths=baths,
                        sqft=sqft,
                        acres=acres,
                        image=urljoin(BASE, img) if img else "",
                        mls=c.get("mls", ""),
                        status=c.get("status", "For Sale"),
                    ))
                    seen.add(url)
                except Exception:
                    continue

            # Stop if there is no link to the next page.
            if f"/page/{page + 1}/" not in html:
                break
    return results
