"""ERA Cayman Islands (www.eracayman.com) scraper.

WordPress + the "Essential Real Estate" (ERE) plugin; listings are not exposed
through /wp-json/ and are rendered server-side as `.ere-item-wrap` cards.

The site carries two sets of listings:
  * /properties/ and /real-estate/<type>/ -- the whole CIREBA MLS (IDX) feed
    (~24 pages x 40 cards, including commercial; cards lack photos/MLS #).
  * /featured-listings/ -- "all company listings of ERA Cayman Islands"
    (~110 cards on a single page, sorted by price).

We scrape only /featured-listings/ (the agency's own listings).  Each card has
title, link, CIREBA property type, price with "CI"/"US" prefix, location,
beds/baths and lot size (acres).  The thumbnail is served as
/images/properties/listing<MLS>-thumb.jpg, which gives the MLS number (checked
against detail pages, whose <title> reads "... | MLS 418610 | ...").

The site lists sales only (no rentals on this page); commercial categories are
skipped.  robots.txt only disallows /wp-admin/, /page/* and cache paths.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper.common import Listing, get, num, norm_type, HOME, CONDO, LAND

SOURCE = "ERA"
BASE = "https://www.eracayman.com"
START = f"{BASE}/featured-listings/"
SQFT_PER_ACRE = 43560.0

# CIREBA categories -> calculator types.  None = skip (commercial etc.).
TYPE_MAP = {
    "single family home": HOME,
    "residential": HOME,
    "condominium": CONDO,
    "semi-detached/duplex/triplex": CONDO,
    "townhouse": CONDO,
    "low density residential": LAND,
    "med density residential": LAND,
    "medium density residential": LAND,
    "high density residential": LAND,
    "agriculture": LAND,
    "beach front": LAND,
    "canal front": LAND,
    "land": LAND,
    "little cayman/cayman brac": None,  # resolved below: house if beds, else land
}
SKIP_TYPES = ("commercial", "industrial", "office", "retail", "hotel", "mixed use",
              "business", "multi-family", "other")


def _ptype(site_type: str, beds) -> str | None:
    t = site_type.strip().lower()
    if any(k in t for k in SKIP_TYPES):
        return None
    if t in TYPE_MAP:
        v = TYPE_MAP[t]
        if v is None:
            return HOME if beds else LAND
        return v
    guess = norm_type(t)
    return guess if guess in (HOME, CONDO, LAND) else None


def _price(txt: str) -> tuple[float | None, str]:
    txt = " ".join((txt or "").split())
    cur = "KYD" if re.search(r"\bCI\b|CI\s*\$|KYD", txt, re.I) else "USD"
    m = re.search(r"\d[\d,]*(?:\.\d+)?", txt)
    price = float(m.group(0).replace(",", "")) if m else None
    return (price or None), cur


def _parse(html: str) -> list[Listing]:
    soup = BeautifulSoup(html, "lxml")
    out: list[Listing] = []
    for card in soup.select(".ere-item-wrap"):
        try:
            a = card.select_one("h4.property-title a[href]") or card.select_one("a.property-link[href]")
            if not a:
                continue
            url = urljoin(BASE, a["href"].strip())
            title = a.get_text(" ", strip=True) or a.get("title", "")
            pr = card.select_one(".property-price")
            price, cur = _price(pr.get_text(" ") if pr else "")
            if not price:
                continue

            beds = baths = acres = None
            for attr in card.select(".propertyAttribute"):
                lbls = attr.select(".lbl")
                if len(lbls) < 2:
                    continue
                v, label = num(lbls[0].get_text()), lbls[1].get_text(strip=True).lower()
                if "bed" in label:
                    beds = v
                elif "bath" in label:
                    baths = v
                elif "lot" in label or "acre" in label:
                    acres = v

            ty = card.select_one(".propertyType")
            site_type = ty.get_text(strip=True) if ty else ""
            ptype = _ptype(site_type, beds) if site_type else norm_type(title)
            if ptype not in (HOME, CONDO, LAND):
                continue

            loc = card.select_one(".propertyLocation")
            img = card.select_one(".property-image img")
            src = ""
            if img:
                src = img.get("data-src") or img.get("src") or ""
                if src.startswith("data:"):
                    src = ""
            m = re.search(r"listing(\d{5,7})", src)

            out.append(Listing(
                source=SOURCE,
                url=url,
                title=title,
                price=price,
                currency=cur,
                ptype=ptype,
                location=loc.get_text(" ", strip=True) if loc else "",
                beds=beds,
                baths=baths,
                sqft=round(acres * SQFT_PER_ACRE) if (ptype == LAND and acres) else None,
                acres=acres,
                image=urljoin(BASE, src) if src else "",
                mls=m.group(1) if m else "",
                status="For Sale",
            ))
        except Exception:
            continue
    return out


def fetch(max_pages: int = 5) -> list[Listing]:
    """Fetch ERA's own for-sale listings. The featured page currently holds
    everything on one page; `max_pages` caps any pagination that appears."""
    results: list[Listing] = []
    seen: set[str] = set()
    for page in range(1, max_pages + 1):
        url = START if page == 1 else f"{START}page/{page}/"
        try:
            r = get(url)
        except Exception as e:
            if page == 1:
                raise RuntimeError(f"ERA: could not load {url}: {e}") from e
            break
        if page == 1 and "ere-item-wrap" not in r.text:
            raise RuntimeError("ERA: no listing cards found on /featured-listings/ "
                               "(layout changed or request blocked)")
        for l in _parse(r.text):
            if l.url not in seen:
                seen.add(l.url)
                results.append(l)
        if f"/featured-listings/page/{page + 1}/" not in r.text:
            break
    return results
