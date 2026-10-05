"""Utopia Cayman Realty (www.utopiacaymanrealty.com) scraper.

WordPress + Houzez theme.  The standard REST route serves everything we need
as JSON, including the whole Houzez `property_meta` block, so no detail-page
HTML is needed:

    https://www.utopiacaymanrealty.com/wp-json/wp/v2/properties
        ?property_status=<For Sale id>&per_page=100&page=N

Useful meta: `fave_property_price` (plain number) + `fave_currency`
("USD" / "KYD" -- the site renders KYD as "CI$", verified against
/property/prime-redevelopment-opportunity-.../), `fave_property_size`
(+ `_size_prefix`), `fave_property_land` (+ `_land_postfix`, sqft or acres),
`fave_property_bedrooms`, `fave_property_bathrooms`,
`fave_property_address` and `houzez_geolocation_lat`/`_long`.
Districts come from the `property_label` taxonomy; the main photo is the
featured image, resolved in one batched /wp/v2/media?include=... call.

FOREIGN LISTINGS: the agency also sells in Panama and Costa Rica, and those
are *not* reliably tagged -- several Costa Rica properties carry Cayman
`property_label` districts ("west-bay", "seven-mile-beach-corridor") and some
inherit the office address "11 Invicta Drive".  We therefore test the
geocode against a Cayman bounding box, and for the handful with no geocode
fall back to country/place keywords in the title, address and postcode.
As of Oct 2026 that drops 9 of the 32 for-sale posts (1 Panama, 8 Costa Rica).

No MLS/CIREBA number is published (`fave_property_id` is just the post id),
so `mls` is left empty.  robots.txt only disallows /wp-admin/.
"""
from __future__ import annotations

import html as htmlmod
import re

from scraper.common import Listing, get, num, norm_type, HOME, CONDO, LAND, OTHER

SOURCE = "Utopia Realty"
BASE = "https://www.utopiacaymanrealty.com"
API = f"{BASE}/wp-json/wp/v2"
PER_PAGE = 100
FIELDS = ("id,link,title,featured_media,class_list,property_meta,"
          "property_label,property_type,property_status")

FALLBACK_FOR_SALE = 121          # property_status term id as of 2026-10
SQFT_PER_ACRE = 43560.0

# property_status slugs that mean "not an active sale"
DEAD_STATUS = {"rented", "rentals", "just-sold", "sold", "pastsales", "past-sales",
               "pending", "under-offer", "under-contract", "off-market", "leased"}

# property_type slugs -> calculator type.  None = skip the listing.
TYPE_MAP = {
    "land": LAND,
    "condo": CONDO, "townhouse": CONDO, "studio": CONDO, "duplex": CONDO,
    "apartment": CONDO, "villa": CONDO,
    "single-family-home": HOME, "residential": HOME,
    "multi-family-home": OTHER,
    "commercial": None, "office": None, "retail": None, "industrial": None,
    "warehouse": None, "business": None,
}

# Cayman Islands bounding box (Grand Cayman, Little Cayman, Cayman Brac).
LAT_RANGE = (19.0, 19.95)
LON_RANGE = (-81.60, -79.60)

# Place/country names that mark a listing as being outside Cayman.
FOREIGN_RE = re.compile(
    r"panama|costa\s*rica|escaz|alajuela|atenas|guanacaste|nandayure|bejuco|"
    r"san\s*jose\s*province|playa\s*blanca|jamaica|honduras|belize|nicaragua",
    re.I)


def _m(meta: dict, key: str) -> str:
    v = meta.get(key)
    if isinstance(v, list):
        v = v[0] if v else ""
    return str(v or "").strip()


def _slugs(item: dict, prefix: str) -> list[str]:
    return [c[len(prefix):] for c in item.get("class_list") or [] if c.startswith(prefix)]


def _term_id(tax: str, name: str, fallback: int) -> int:
    """Look the term id up by name so a re-created term does not break us."""
    try:
        r = get(f"{API}/{tax}?per_page=100&_fields=id,name", headers={"Accept": "application/json"})
        for t in r.json():
            if htmlmod.unescape(t["name"]).strip().lower() == name.lower():
                return int(t["id"])
    except Exception:
        pass
    return fallback


def _label_names() -> dict[int, str]:
    try:
        r = get(f"{API}/property_label?per_page=100&_fields=id,name",
                headers={"Accept": "application/json"})
        return {int(t["id"]): htmlmod.unescape(t["name"]).strip() for t in r.json()}
    except Exception:
        return {}


def _media_urls(ids: list[int]) -> dict[int, str]:
    """Resolve featured-image ids to URLs, 100 at a time."""
    out: dict[int, str] = {}
    ids = [i for i in ids if i]
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        try:
            r = get(f"{API}/media?include={','.join(map(str, chunk))}"
                    f"&per_page=100&_fields=id,source_url",
                    headers={"Accept": "application/json"})
            for m in r.json():
                if m.get("source_url"):
                    out[int(m["id"])] = m["source_url"]
        except Exception:
            continue
    return out


def _in_cayman(meta: dict, title: str, labels: list[str]) -> bool:
    """True when the listing really is in the Cayman Islands."""
    if any(l in ("costa-rica", "panama", "jamaica") for l in labels):
        return False
    lat, lon = num(_m(meta, "houzez_geolocation_lat")), None
    lon_txt = _m(meta, "houzez_geolocation_long")
    m = re.search(r"-?\d+(?:\.\d+)?", lon_txt)
    if m:
        lon = float(m.group(0))
    if lat is not None and lon is not None:
        return LAT_RANGE[0] <= lat <= LAT_RANGE[1] and LON_RANGE[0] <= lon <= LON_RANGE[1]
    # No geocode: judge on the text we do have.
    blob = " ".join((title, _m(meta, "fave_property_address"),
                     _m(meta, "fave_property_map_address"), _m(meta, "fave_property_zip")))
    return not FOREIGN_RE.search(blob)


def _ptype(item: dict, meta: dict, title: str, beds: float | None,
           land_acres: float | None) -> str | None:
    for slug in _slugs(item, "property_type-"):
        if slug in TYPE_MAP:
            return TYPE_MAP[slug]
    t = norm_type(title)
    if t != OTHER:
        return t
    # "Pre Construction" / untyped posts: a unit with bedrooms and no land of
    # its own is a condo; with land it is a house.
    if beds:
        return HOME if land_acres else CONDO
    return OTHER


def _land_acres(meta: dict) -> float | None:
    v = num(_m(meta, "fave_property_land"))
    if not v or v <= 1:          # several posts carry a junk "0" or "1"
        return None
    post = _m(meta, "fave_property_land_postfix").lower()
    if "acre" in post:
        return round(v, 3)
    return round(v / SQFT_PER_ACRE, 3)


def _size_sqft(meta: dict) -> float | None:
    v = num(_m(meta, "fave_property_size"))
    if not v:
        return None
    if "acre" in _m(meta, "fave_property_size_prefix").lower():
        return round(v * SQFT_PER_ACRE)
    return v


def _parse(item: dict, labels: dict[int, str], images: dict[int, str]) -> Listing | None:
    meta = item.get("property_meta") or {}
    url = (item.get("link") or "").strip()
    if not url:
        return None

    statuses = _slugs(item, "property_status-")
    if any(s in DEAD_STATUS for s in statuses):
        return None

    title = htmlmod.unescape((item.get("title") or {}).get("rendered") or "").strip()
    label_slugs = _slugs(item, "property_label-")
    if not _in_cayman(meta, title, label_slugs):
        return None

    price = num(_m(meta, "fave_property_price"))
    if not price:
        return None
    cur = "KYD" if re.search(r"KYD|CI\s*\$", _m(meta, "fave_currency"), re.I) else "USD"

    beds = num(_m(meta, "fave_property_bedrooms"))
    baths = num(_m(meta, "fave_property_bathrooms"))
    acres = _land_acres(meta)
    sqft = _size_sqft(meta)

    ptype = _ptype(item, meta, title, beds, acres)
    if ptype is None:
        return None
    if ptype == LAND:
        beds = baths = None
        if acres is None and sqft:
            acres = round(sqft / SQFT_PER_ACRE, 3)

    district = next((labels[i] for i in item.get("property_label") or [] if i in labels), "")
    if not district and label_slugs:
        district = label_slugs[0].replace("-", " ").title()
    addr = _m(meta, "fave_property_address") or _m(meta, "fave_property_map_address")
    # Posts with no address of their own inherit the agency's office address.
    if addr.lower().startswith("11 invicta"):
        addr = ""
    location = f"{addr}, {district}" if addr and district and district.lower() not in addr.lower() \
        else (addr or district)

    status = "For Sale"
    if "pre-construction" in statuses or "pre-construction" in _slugs(item, "property_type-"):
        status = "For Sale (Pre-Construction)"
    elif "new-listing" in statuses:
        status = "For Sale (New)"

    img = images.get(int(item.get("featured_media") or 0), "")

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
        image=img,
        mls="",
        status=status,
    )


def fetch(max_pages: int = 5) -> list[Listing]:
    """For-sale Cayman listings via the WP REST API, PER_PAGE (100) per page.
    There are ~32 for-sale posts in total, so one page covers the site."""
    for_sale = _term_id("property_status", "For Sale", FALLBACK_FOR_SALE)
    labels = _label_names()

    raw: list[dict] = []
    for page in range(1, max(1, max_pages) + 1):
        url = (f"{API}/properties?property_status={for_sale}&per_page={PER_PAGE}"
               f"&page={page}&_fields={FIELDS}&orderby=date&order=desc")
        try:
            r = get(url, headers={"Accept": "application/json"})
            items = r.json()
        except Exception as e:
            if page == 1:
                raise RuntimeError(f"{SOURCE}: REST request failed ({url}): {e}") from e
            break                      # 400 past the last page
        if not isinstance(items, list) or not items:
            break
        raw.extend(items)
        try:
            if page >= int(r.headers.get("X-WP-TotalPages") or 0):
                break
        except ValueError:
            break

    images = _media_urls([int(it.get("featured_media") or 0) for it in raw])

    out: list[Listing] = []
    seen: set[str] = set()
    for it in raw:
        try:
            li = _parse(it, labels, images)
            if li and li.url not in seen:
                seen.add(li.url)
                out.append(li)
        except Exception:
            continue
    return out
