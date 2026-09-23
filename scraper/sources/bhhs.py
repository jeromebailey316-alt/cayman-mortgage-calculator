"""Berkshire Hathaway HomeServices Cayman Islands scraper.

Note: www.bhhscayman.com is a parked GoDaddy domain.  The brokerage's site is
www.bhhscaymanislands.com (Nuxt front end) backed by a public Laravel JSON API
at api.bhhscaymanislands.com (robots.txt on both allows everything).  The
older www.berkshirehathawayhomeservicescaymanislands.com is behind a
Cloudflare challenge and is not used.

    GET /api/properties?type=buy&page=N   -> whole CIREBA MLS (~990 listings,
        9/page, is_ldx feed listings "courtesy of <other brokerage>") with
        BHHS's own listings pinned first under the default "featured" sort.
    GET /api/agents                       -> the BHHS agents (6)
    GET /api/agents/<slug>                -> agent profile incl. `properties`
        (their own listings: for sale, sold and rentals)

We scrape only BHHS's *own* listings: the union of every agent's
`properties`, filtered to for-sale (rental == 0, no sold_date, status not
Sold/Rented) residential/land listings.  Each property already carries the
CIREBA `mlsid`, price + currency ("US$" / "CI$"), district, beds, baths,
sqft, lot_size (acres) and pictures, so no detail pages are needed.

The API only types listings as Residential / Land / Commercial, so condo vs
house is inferred from the title (and a zero lot size, typical of strata).
"""
from __future__ import annotations

import re

from scraper.common import Listing, get, num, norm_type, HOME, CONDO, LAND

SOURCE = "Berkshire Hathaway HomeServices"
SITE = "https://www.bhhscaymanislands.com"
API = "https://api.bhhscaymanislands.com/api"
SQFT_PER_ACRE = 43560.0
_CONDO_RE = re.compile(r"condo|apartment|penthouse|townho|\bunit\b|\bapt\b|#\s*\d|strata|suite", re.I)


def _json(url: str):
    return get(url, headers={"Accept": "application/json"}).json()


def _ptype(p: dict) -> str | None:
    t = (p.get("type") or "").lower()
    name = p.get("name") or ""
    if "land" in t:
        return LAND
    if "residential" not in t:
        return None  # Commercial, Business, ...
    if _CONDO_RE.search(name):
        return CONDO
    if norm_type(name) == HOME:  # house / home / estate ...
        return HOME
    # "Villa", "Retreat", ... are ambiguous: strata units have no own lot.
    lot = num(p.get("lot_size"))
    return HOME if lot and lot >= 0.05 else CONDO


def _price(p: dict) -> tuple[float | None, str]:
    cur = "KYD" if re.search(r"CI|KYD", p.get("currency") or "", re.I) else "USD"
    v = num(p.get("price"))
    return (v or None), cur


def fetch(max_pages: int = 5) -> list[Listing]:
    """Fetch BHHS Cayman's own for-sale listings via the agents API.

    Costs 1 + <number of agents> requests (currently 7); `max_pages` caps the
    number of agent profiles fetched at max(6, 2 * max_pages)."""
    try:
        agents = _json(f"{API}/agents")
    except Exception as e:
        raise RuntimeError(f"BHHS Cayman: agents API unavailable ({e})") from e
    if isinstance(agents, dict):
        agents = agents.get("data") or []
    slugs = [a.get("slug") for a in agents if isinstance(a, dict) and a.get("slug")]

    props: dict = {}
    for slug in slugs[: max(6, 2 * max_pages)]:
        try:
            d = _json(f"{API}/agents/{slug}")
            d = d.get("data", d) if isinstance(d, dict) else {}
            for p in d.get("properties") or []:
                if isinstance(p, dict) and p.get("id") is not None:
                    props.setdefault(p["id"], p)
        except Exception:
            continue

    results: list[Listing] = []
    for p in props.values():
        try:
            status = (p.get("status") or "").strip()
            if p.get("rental") or p.get("sold_date") or re.search(r"\b(sold|rented|rental|leased|withdrawn|expired)\b", status, re.I):
                continue
            ptype = _ptype(p)
            if ptype is None:
                continue
            slug = p.get("slug")
            price, cur = _price(p)
            if not slug or not price:
                continue
            sqft = num(p.get("sqft")) or None
            acres = num(p.get("lot_size")) or None
            if ptype == LAND and sqft is None and acres:
                sqft = round(acres * SQFT_PER_ACRE)
            pics = p.get("pictures") or []
            img = (pics[0].get("card@2x") or pics[0].get("card") or "") if pics and isinstance(pics[0], dict) else ""
            results.append(Listing(
                source=SOURCE,
                url=f"{SITE}/properties/{slug}",
                title=re.sub(r"\s+", " ", p.get("name") or "").strip(),
                price=price,
                currency=cur,
                ptype=ptype,
                location=p.get("district") if isinstance(p.get("district"), str) else ((p.get("district") or {}).get("name") or ""),
                beds=num(p.get("bedrooms")) if ptype != LAND else None,
                baths=num(p.get("bathrooms")) if ptype != LAND else None,
                sqft=sqft,
                acres=acres,
                image=img,
                mls=str(p.get("mlsid") or ""),
                status="For Sale" if status.lower() in ("", "current", "new", "active") else status,
            ))
        except Exception:
            continue
    results.sort(key=lambda l: -(l.price_kyd or 0))
    return results
