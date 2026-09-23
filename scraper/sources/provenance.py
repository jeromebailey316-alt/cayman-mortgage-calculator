"""Provenance Properties (www.provenanceproperties.com) scraper.

Not Wix: the site is Umbraco (built by dart.ky).  The "Residential Listings
for Sale" page renders nothing server-side; its JS module calls a public JSON
endpoint (declared in the page as `data-endpoint`):

    /umbraco/api/propertydata/GetListings?size=N&page=P
        &propertyType=Residential&saleType=Sale&excludeStatuses=

-> {"totalResultCount", "totalPages", "properties": [...]}.  Each property has
title, price ("USD 1,047,560" / "KYD 1,850,000"), propertyType, mls
("MLS 418706"), bedrooms, bathrooms, squareFootageValue, region /
displayLocation, images, propertyUrl and dataSource.

The endpoint returns the whole CIREBA feed (dataSource "Cireba", ~490) plus
Provenance's own listings (dataSource "Property Base", their CRM, ~14).  By
default (OWN_ONLY = True) we keep only Provenance's own listings, since the
CIREBA-feed items duplicate what the CIREBA scraper already collects.
robots.txt: "Allow: /".
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from scraper.common import Listing, get, num, HOME, CONDO, LAND, OTHER

SOURCE = "Provenance"
BASE = "https://www.provenanceproperties.com"
API = BASE + "/umbraco/api/propertydata/GetListings"
PAGE_SIZE = 1000              # the site's own page asks for 1500 in one call
OWN_ONLY = True               # False -> include the full CIREBA IDX feed
OWN_SOURCES = {"property base"}
SQFT_PER_ACRE = 43560.0


def _ptype(t: str, title: str) -> str | None:
    """Map the site's propertyType; None means skip (not whole residential)."""
    s = (t or "").lower()
    if "fractional" in s or "commercial" in s:
        return None
    if "land" in s or "lot" in s:
        return LAND
    if "standalone home" in s or "single family" in s:
        return HOME
    if any(k in s for k in ("condo", "townhouse", "townhome", "duplex", "apartment", "villa")):
        return CONDO
    tt = (title or "").lower()
    if "land" in tt or "acre" in tt:
        return LAND
    return OTHER


def _price(raw) -> tuple[float | None, str]:
    s = str(raw or "")
    cur = "KYD" if re.search(r"KYD|CI\s*\$", s, re.I) else "USD"
    m = re.search(r"\d[\d,]*(?:\.\d+)?", s)
    p = float(m.group(0).replace(",", "")) if m else None
    return (p or None), cur


def _acres(title: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*[- ]?\s*acres?\b", title or "", re.I)
    return float(m.group(1)) if m else None


def fetch(max_pages: int = 5) -> list[Listing]:
    """`max_pages` caps API pages of PAGE_SIZE items (the whole feed is
    ~500 items, so one page normally suffices)."""
    out: list[Listing] = []
    seen: set[str] = set()
    for page in range(max(1, max_pages)):
        r = get(API, params={"size": PAGE_SIZE, "page": page, "propertyType": "Residential",
                             "saleType": "Sale", "excludeStatuses": ""},
                headers={"Accept": "application/json"})
        data = r.json()
        props = data.get("properties") or []
        for p in props:
            try:
                if OWN_ONLY and (p.get("dataSource") or "").lower() not in OWN_SOURCES:
                    continue
                if p.get("saleType") not in (0, None):
                    continue
                status = (p.get("marketStatus") or "").strip()
                if re.search(r"sold|rent|leased|withdrawn|expired", status, re.I):
                    continue
                title = (p.get("title") or "").strip()
                ptype = _ptype(p.get("propertyType"), title)
                if ptype is None:
                    continue
                url = urljoin(BASE, p.get("propertyUrl") or "")
                price, cur = _price(p.get("price"))
                if not p.get("propertyUrl") or not price or url in seen:
                    continue
                sqft = p.get("squareFootageValue") or num(p.get("squareFootage"))
                acres = _acres(title)
                if ptype == LAND and acres is None and sqft:
                    acres = round(sqft / SQFT_PER_ACRE, 3)
                imgs = p.get("images") or []
                mls = re.sub(r"^\s*MLS\s*#?\s*", "", p.get("mls") or "", flags=re.I).strip()
                beds = p.get("bedrooms")
                baths = p.get("bathrooms")
                out.append(Listing(
                    source=SOURCE,
                    url=url,
                    title=title,
                    price=price,
                    currency=cur,
                    ptype=ptype,
                    location=(p.get("region") or p.get("displayLocation") or "").strip(),
                    beds=float(beds) if beds and ptype != LAND else None,
                    baths=float(baths) if baths and ptype != LAND else None,
                    sqft=float(sqft) if sqft else None,
                    acres=acres,
                    image=urljoin(BASE, imgs[0]) if imgs else "",
                    mls=mls,
                    status="For Sale" if status.lower() in ("", "available") else status,
                ))
                seen.add(url)
            except Exception:
                continue
        total_pages = data.get("totalPages") or 0
        if not props or page + 1 >= total_pages:
            break
    return out
