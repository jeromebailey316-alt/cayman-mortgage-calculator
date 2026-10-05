"""TCG Realty (tcgrealty.ky) scraper.

WordPress 5.4 + Houzez.  The standard REST route exposes the whole Houzez
`property_meta` as JSON, so no detail-page HTML is needed:

    https://tcgrealty.ky/wp-json/wp/v2/properties?per_page=100

It is a small site: 10 published properties (X-WP-Total: 10) -- 7 with
property_status "for-sale", 3 "for-rent".

DEMO LISTINGS: the site's sitemap (https://tcgrealty.ky/sitemap.xml, generated
by the host's "Managed SSL" tooling, not by WordPress) still lists 30 Houzez
*theme demo* properties -- "Gorgeous Villa", "Modern Apartment on the Bay",
"Luxury Family Home", "test-apartment-411" and so on, with Miami and London
addresses.  Every one of them now 404s and none appears in the REST feed, so
driving discovery from the REST API rather than that sitemap is what keeps
them out.  Two further guards are kept in case such posts are ever
re-published: demo titles are rejected by name, and so are listings whose
property_city / property_state is outside Cayman ("london", "flordia" are
both still registered terms).  Note we do NOT filter on the geocode here:
Houzez's default coordinates (25.68654,-80.431345, Miami) are left on real
listings, e.g. the Multi-Family Residential post.

Sold / under-offer listings keep property_status "for-sale" and are marked
only by a `property_label` term ("sold", "under-offer",
"sold-subject-to-contract"), which the detail page renders as a second badge
next to "For Sale".  Those labels are therefore the real status filter: 4 of
the 7 for-sale posts are Sold or Under Offer.

PRICE: free text in `fave_property_price` -- "KYD 1.7 M", "KYD1500",
"KYD 450,000", "USD 500000", "950000", "215000" -- and `fave_currency` is
empty on every listing.  common.parse_price handles the suffixes.  Where the
agency wrote no currency at all we record KYD (PRICE_DEFAULT_CURRENCY): the
Houzez config publishes only `currency_symbol: "$"` with no currency code,
and every price on the site that *is* labelled and is on Grand Cayman is
labelled KYD (the one USD label is the Little Cayman parcel).  This is an
assumption, not something the site states; flip the constant if it turns out
the bare figures are US$.

robots.txt only disallows /wp-admin/.
"""
from __future__ import annotations

import html as htmlmod
import re

from scraper.common import Listing, get, num, parse_price, norm_type, HOME, CONDO, LAND, OTHER

SOURCE = "TCG Realty"
BASE = "https://tcgrealty.ky"
API = f"{BASE}/wp-json/wp/v2"
PER_PAGE = 100
FIELDS = ("id,link,slug,title,featured_media,property_meta,property_type,"
          "property_status,property_label,property_area,property_city,property_state")
SQFT_PER_ACRE = 43560.0

# See the module docstring.
PRICE_DEFAULT_CURRENCY = "KYD"

SALE_STATUS = {"for-sale", "sale", "for-sale-by-owner"}
DEAD_LABELS = {"sold", "sold-subject-to-contract", "under-offer", "under-contract",
               "pending", "rented", "leased", "off-market"}
DEAD_STATUS = {"for-rent", "rented", "sold", "pending", "leased", "short-term-rental"}

TYPE_MAP = {
    "land": LAND, "lot": LAND, "vacant-land": LAND,
    "condo": CONDO, "condominium": CONDO, "apartment": CONDO, "townhouse": CONDO,
    "villa": CONDO, "duplex": CONDO,
    "residential": HOME, "single-family-home": HOME, "house": HOME, "home": HOME,
    "multi-unit": OTHER, "multi-family-home": OTHER,
    "commercial": None, "office": None, "retail": None, "industrial": None,
    "mixed-use": None,
}

# Houzez theme-demo listings (the stale sitemap still lists these).
DEMO_TITLE_RE = re.compile(
    r"^(?:gorgeous|modern|luxury|ample|amazing|contemporary|relaxing|confortable|"
    r"comfortable|penthouse|modern\s+day|test)\b.*"
    r"(?:apartment|villa|home|penthouse|house|\d{3})\s*\d*$", re.I)
NON_CAYMAN_PLACES = {"london", "flordia", "florida", "miami", "new-york", "hackney",
                     "winchmorehill", "crans-montana"}
CAYMAN_CITIES = {"grand-cayman", "little-cayman", "cayman-brac", "cayman-islands"}


def _m(meta: dict, key: str) -> str:
    v = meta.get(key)
    if isinstance(v, list):
        v = v[0] if v else ""
    return str(v or "").strip()


def _terms(tax: str) -> dict[int, tuple[str, str]]:
    """{id: (slug, name)} for a property taxonomy."""
    try:
        r = get(f"{API}/{tax}?per_page=100&_fields=id,name,slug",
                headers={"Accept": "application/json"})
        return {int(t["id"]): (t.get("slug") or "",
                               htmlmod.unescape(t.get("name") or "").strip())
                for t in r.json()}
    except Exception:
        return {}


def _media_urls(ids: list[int]) -> dict[int, str]:
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


def _price(raw: str) -> tuple[float | None, str]:
    """'KYD 1.7 M' -> (1700000, 'KYD'); '215000' -> (215000, KYD by default)."""
    value, cur = parse_price(raw)
    if cur == "USD" and not re.search(r"US\s?\$|\bUSD\b|\bUS\b", raw or "", re.I):
        cur = PRICE_DEFAULT_CURRENCY
    return value, cur


def _ptype(type_slugs: list[str], title: str) -> str | None:
    mapped = [TYPE_MAP[s] for s in type_slugs if s in TYPE_MAP]
    if mapped and all(m is None for m in mapped):
        return None                                   # purely commercial
    real = [m for m in mapped if m is not None]
    if LAND in real:
        return LAND
    if OTHER in real:
        return OTHER          # multi-unit / multi-family: not a single dwelling
    if CONDO in real:
        return CONDO
    if HOME in real:
        # "Residential" is the catch-all term here; let the title refine it.
        t = norm_type(title)
        return t if t in (CONDO, LAND) else HOME
    if real:
        return real[0]                                # multi-unit -> other
    t = norm_type(title)
    return t


def _parse(item: dict, tax: dict[str, dict[int, tuple[str, str]]],
           images: dict[int, str]) -> Listing | None:
    meta = item.get("property_meta") or {}
    url = (item.get("link") or "").strip()
    if not url:
        return None
    title = htmlmod.unescape((item.get("title") or {}).get("rendered") or "").strip()
    if DEMO_TITLE_RE.match(title):
        return None

    def slugs(tx: str) -> list[str]:
        table = tax.get(tx, {})
        return [table[i][0] for i in item.get(tx) or [] if i in table]

    def names(tx: str) -> list[str]:
        table = tax.get(tx, {})
        return [table[i][1] for i in item.get(tx) or [] if i in table]

    statuses, labels = slugs("property_status"), slugs("property_label")
    if not any(s in SALE_STATUS for s in statuses) or any(s in DEAD_STATUS for s in statuses):
        return None
    if any(l in DEAD_LABELS for l in labels):
        return None

    places = set(slugs("property_city")) | set(slugs("property_state")) | set(slugs("property_area"))
    if places & NON_CAYMAN_PLACES:
        return None
    cities = set(slugs("property_city"))
    if cities and not (cities & CAYMAN_CITIES):
        return None

    price, cur = _price(_m(meta, "fave_property_price"))
    if not price:
        return None

    ptype = _ptype(slugs("property_type"), title)
    if ptype is None:
        return None

    sqft = num(_m(meta, "fave_property_size"))
    if sqft and "acre" in _m(meta, "fave_property_size_prefix").lower():
        sqft = round(sqft * SQFT_PER_ACRE)
    acres = num(_m(meta, "fave_property_land"))
    if acres and "sqft" in _m(meta, "fave_property_land_postfix").lower().replace(" ", ""):
        acres = round(acres / SQFT_PER_ACRE, 3)
    beds = num(_m(meta, "fave_property_bedrooms"))
    baths = num(_m(meta, "fave_property_bathrooms"))
    if ptype == LAND:
        beds = baths = None
        if acres is None and sqft:
            acres = round(sqft / SQFT_PER_ACRE, 3)

    area = next(iter(names("property_area")), "")
    city = next((c for c in names("property_city")), "")
    addr = _m(meta, "fave_property_address")
    parts: list[str] = []
    for p in (addr, area, city):
        if p and not any(p.lower() in q.lower() or q.lower() in p.lower() for q in parts):
            parts.append(p)
    location = ", ".join(parts)

    img = images.get(int(item.get("featured_media") or 0), "")
    if not img:
        for aid in (meta.get("fave_property_images") or []):
            if images.get(int(aid or 0)):
                img = images[int(aid)]
                break

    label_names = [n for n, s in zip(names("property_label"), labels)
                   if s not in ("hot-offer", "newly-listed", "new", "open-house")]
    status = "For Sale" + (f" ({label_names[0]})" if label_names else "")

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
        mls=_m(meta, "fave_property_id"),
        status=status,
    )


def fetch(max_pages: int = 5) -> list[Listing]:
    """All for-sale listings via the WP REST API, PER_PAGE (100) per page.
    The site has 10 properties in total, so one page covers it."""
    raw: list[dict] = []
    for page in range(1, max(1, max_pages) + 1):
        url = f"{API}/properties?per_page={PER_PAGE}&page={page}&_fields={FIELDS}"
        try:
            r = get(url, headers={"Accept": "application/json"})
            items = r.json()
        except Exception as e:
            if page == 1:
                raise RuntimeError(f"{SOURCE}: REST request failed ({url}): {e}") from e
            break
        if not isinstance(items, list) or not items:
            break
        raw.extend(items)
        try:
            if page >= int(r.headers.get("X-WP-TotalPages") or 0):
                break
        except ValueError:
            break

    tax = {t: _terms(t) for t in ("property_type", "property_status", "property_label",
                                 "property_area", "property_city", "property_state")}
    media_ids: list[int] = []
    for it in raw:
        media_ids.append(int(it.get("featured_media") or 0))
        for aid in ((it.get("property_meta") or {}).get("fave_property_images") or [])[:1]:
            try:
                media_ids.append(int(aid))
            except (TypeError, ValueError):
                pass
    images = _media_urls(media_ids)

    out: list[Listing] = []
    seen: set[str] = set()
    for it in raw:
        try:
            li = _parse(it, tax, images)
            if li and li.url not in seen:
                seen.add(li.url)
                out.append(li)
        except Exception:
            continue
    return out
