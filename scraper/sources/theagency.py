"""The Agency Cayman Islands (theagencyre.ky) scraper.

WordPress + Houzez theme.  Listings are imported from the CIREBA feed (WP All
Import) and the standard REST route exposes everything as JSON, including the
Houzez `property_meta` (price, currency, beds, baths, size, land acres, CIREBA
MLS #, CIREBA image URLs):

    https://theagencyre.ky/wp-json/wp/v2/properties
        ?property_status=<For Sale id>&_mls_=<AGENCY LISTINGS id>&per_page=100

The site carries the whole CIREBA MLS feed (~950 for sale).  The agency's own
listings are tagged with the `_mls_` term "AGENCY LISTINGS"; by default we
fetch only those (OWN_ONLY = True).  Set OWN_ONLY = False for the full feed.

Term ids are looked up by name at run time (falling back to the ids seen when
this was written) so a re-created taxonomy term does not silently break it.
robots.txt allows everything.
"""
from __future__ import annotations

import html as htmlmod
import re

from scraper.common import Listing, get, num, norm_type, HOME, CONDO, LAND, OTHER

SOURCE = "The Agency"
BASE = "https://theagencyre.ky"
API = f"{BASE}/wp-json/wp/v2"
OWN_ONLY = True
PER_PAGE = 100
FIELDS = "id,link,title,class_list,property_meta,property_type,property_area,_listing-type"

# Fallback term ids (as of 2026-09).
FALLBACK_FOR_SALE = 32
FALLBACK_AGENCY = 264

# _listing-type slugs that are not residential
COMMERCIAL_LT = {
    "commercial", "industrial", "office", "offices-mixed-use", "retail", "warehouse",
    "restaurant", "restaurant-bar-nightclub", "hotel", "beach-hotel-tourism", "watersports",
}
CONDO_LT = {"condominium", "1-2-duplex", "duplex", "semi-detached-duplex-triplex", "triplex", "fourplex",
            "apartment-building-condo-building", "standalone-home-part-of-strata"}
HOME_LT = {"single-family-home", "residential"}
SKIP_LT = {"condominium-time-share", "fractional-ownership"}  # not whole-unit sales


def _term_id(tax: str, name: str, fallback: int) -> int:
    try:
        r = get(f"{API}/{tax}?per_page=100&_fields=id,name")
        for t in r.json():
            if htmlmod.unescape(t["name"]).strip().lower() == name.lower():
                return int(t["id"])
    except Exception:
        pass
    return fallback


def _area_names() -> dict[int, str]:
    try:
        r = get(f"{API}/property_area?per_page=100&_fields=id,name")
        return {int(t["id"]): htmlmod.unescape(t["name"]).strip() for t in r.json()}
    except Exception:
        return {}


def _m(meta: dict, key: str) -> str:
    v = meta.get(key)
    if isinstance(v, list):
        v = v[0] if v else ""
    return str(v or "").strip()


def _classes(item: dict, prefix: str) -> list[str]:
    return [c[len(prefix):] for c in item.get("class_list") or [] if c.startswith(prefix)]


def _ptype(item: dict, meta: dict, title: str) -> str | None:
    """Calculator type, or None to skip (commercial / timeshare)."""
    lts = set(_classes(item, "_listing-type-"))
    pts = _classes(item, "property_type-")
    if lts & COMMERCIAL_LT or lts & SKIP_LT:
        return None
    if any(p in ("commercial", "business") for p in pts):
        return None
    if "land" in pts:
        return LAND
    if lts & CONDO_LT:
        return CONDO
    if lts & HOME_LT:
        return HOME
    if "multi-unit" in pts:
        return OTHER
    t = norm_type(_m(meta, "fave_listing-type") or title)
    if t == OTHER and "residential" in pts:
        return HOME if re.search(r"\bhome|house|villa|estate\b", title, re.I) else OTHER
    return t


def _price(meta: dict) -> tuple[float | None, str]:
    v = num(_m(meta, "fave_property_price"))
    cur_txt = _m(meta, "fave_currency")
    cur = "KYD" if re.search(r"CI|KYD", cur_txt, re.I) else "USD"
    return (v or None), cur


def _image(meta: dict) -> str:
    for part in _m(meta, "external_image_url").split(","):
        part = part.strip()
        if part.startswith("http"):
            return part
    return ""


def _parse(item: dict, area_names: dict[int, str]) -> Listing | None:
    meta = item.get("property_meta") or {}
    url = (item.get("link") or "").strip()
    if not url:
        return None
    if "for-rent" in _classes(item, "property_status-"):
        return None
    title = htmlmod.unescape((item.get("title") or {}).get("rendered") or "").strip()
    ptype = _ptype(item, meta, title)
    if ptype is None:
        return None
    price, cur = _price(meta)
    if not price:
        return None

    status = _m(meta, "fave_status")
    if re.search(r"\bsold\b|withdrawn|expired|rented|leased", status, re.I):
        return None
    if not status or status.lower() in ("current", "new", "active"):
        status = "For Sale" if not status or status.lower() != "new" else "New"

    sqft = num(_m(meta, "fave_property_size")) or num(_m(meta, "fave_areasqft")) or None
    acres = num(_m(meta, "fave_property_land")) or num(_m(meta, "fave_land")) or None
    beds = num(_m(meta, "fave_property_bedrooms"))
    baths = num(_m(meta, "fave_property_bathrooms"))
    if ptype == LAND:
        beds = beds or None
        baths = baths or None

    area = next((area_names[i] for i in item.get("property_area") or [] if i in area_names), "")
    if not area and _classes(item, "property_area-"):
        area = _classes(item, "property_area-")[0].replace("-", " ").title()
    location = _m(meta, "fave_property_address") or _m(meta, "fave_property_map_address")
    if area:
        location = f"{location}, {area}" if location and location.lower() not in area.lower() else (location or area)

    mls = _m(meta, "fave_cireba-mls") or _m(meta, "fave_property_id")

    return Listing(
        source=SOURCE,
        url=url,
        title=title,
        price=price,
        currency=cur,
        ptype=ptype,
        location=location,
        beds=beds,
        baths=baths,
        sqft=sqft,
        acres=acres,
        image=_image(meta),
        mls=mls,
        status=status,
    )


def fetch(max_pages: int = 5) -> list[Listing]:
    """For-sale listings via the REST API, PER_PAGE (100) per page.  With
    OWN_ONLY (default) one page covers all ~70 agency listings."""
    for_sale = _term_id("property_status", "For Sale", FALLBACK_FOR_SALE)
    params = f"property_status={for_sale}&per_page={PER_PAGE}&_fields={FIELDS}&orderby=date&order=desc"
    if OWN_ONLY:
        params += f"&_mls_={_term_id('_mls_', 'AGENCY LISTINGS', FALLBACK_AGENCY)}"

    area_names = _area_names()
    results: list[Listing] = []
    seen: set[str] = set()
    for page in range(1, max_pages + 1):
        url = f"{API}/properties?{params}&page={page}"
        try:
            r = get(url, headers={"Accept": "application/json"})
            items = r.json()
        except Exception as e:
            if page == 1:
                raise RuntimeError(f"{SOURCE}: REST request failed ({url}): {e}") from e
            break  # 400 past the last page
        if not isinstance(items, list) or not items:
            break
        for it in items:
            try:
                li = _parse(it, area_names)
                if li and li.url not in seen:
                    seen.add(li.url)
                    results.append(li)
            except Exception:
                continue
        try:
            if page >= int(r.headers.get("X-WP-TotalPages") or 0):
                break
        except ValueError:
            pass
    return results
