"""Engel & Völkers Cayman Islands scraper.

caymanislands.evrealestate.com 308-redirects to
https://www.evrealestate.com/en/shops/caymanislands (a Next.js app).  A plain
curl got 403, but normal browser-like headers (as sent by common.get()) work;
there is no challenge page.

How the data is served
----------------------
The "Our Listings" grid is filled by React Server Component requests to
`/en/shops/caymanislands/properties/our-listings?currentPage=N&...`, but
robots.txt disallows `/*/properties/our-listings?` (query URLs), so we do not
use it.  What robots.txt *does* allow for generic crawlers:

  * the geographic listings sitemap
        https://www.evrealestate.com/sitemaps/listings/ky.xml
    (~1,000 Cayman URLs: the whole CIREBA feed as `...-CaymanIslands-<MLS>`,
    plus E&V's own listings as `...-CaymanIslandsEngelAndVolkers-<MLS>`), and
  * listing detail pages `/*/properties/our-listings/<slug>`.

Each detail page embeds the RESO listing record (ListingId = CIREBA MLS #,
ListPrice, CurrencyCode, PropertyType/SubType, beds, baths, area, lot acres,
MLSAreaMajor, StandardStatus, Media[]) in its RSC payload.

So: read the sitemap, keep only E&V's *own* listings (unique MLS #s, ~20),
and fetch their detail pages (hard cap 40).  `max_pages` maps to 10 detail
pages per "page".  Rentals (PropertyType "Residential Lease") and commercial
records are skipped.

Note: the same robots.txt disallows /*/properties/* and /sitemaps/listings*
for named AI agents (ClaudeBot, ChatGPT-User, ...).  This scraper identifies
with the project's own User-Agent and follows the `User-Agent: *` group.
"""
from __future__ import annotations

import gzip
import json
import re

from scraper.common import Listing, get, norm_type, HOME, CONDO, LAND, OTHER

SOURCE = "Engel & Völkers"
BASE = "https://www.evrealestate.com"
SITEMAP = f"{BASE}/sitemaps/listings/ky.xml"
OWN_TAG = "CaymanIslandsEngelAndVolkers"
PER_PAGE = 10          # detail pages per unit of max_pages
MAX_DETAILS = 40       # hard cap on detail-page requests
SQFT_PER_ACRE = 43560.0

_PUSH_RE = re.compile(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)')


def _sitemap_urls() -> list[tuple[str, str]]:
    """[(mls, url)] for E&V's own listings, unique by MLS #, shop URL preferred."""
    r = get(SITEMAP)
    body = r.content
    if body[:2] == b"\x1f\x8b":           # served as a raw .gz body
        body = gzip.decompress(body)
    text = body.decode("utf-8", "replace")
    out: dict[str, str] = {}
    for loc in re.findall(r"<loc>([^<]+)</loc>", text):
        loc = loc.strip()
        m = re.search(OWN_TAG + r"-(\d+)$", loc)
        if not m or "/en/" not in loc:
            continue
        mls = m.group(1)
        if mls not in out or "/shops/caymanislands/" in loc:
            out[mls] = loc
    return list(out.items())


def _listing_record(html: str, mls: str) -> dict | None:
    """Pull the full RESO listing object out of the Next.js RSC payload."""
    chunks = []
    for m in _PUSH_RE.finditer(html):
        try:
            chunks.append(json.loads(m.group(1)))
        except Exception:
            continue
    p = "".join(chunks)
    dec = json.JSONDecoder()
    best: dict | None = None
    for m in re.finditer(r'"ListingId":"%s"' % re.escape(mls), p):
        depth, i = 0, m.start()
        while i > 0:
            i -= 1
            c = p[i]
            if c == "}":
                depth += 1
            elif c == "{":
                if depth == 0:
                    try:
                        o, _ = dec.raw_decode(p, i)
                    except Exception:
                        o = None
                    if isinstance(o, dict) and o.get("ListPrice") is not None:
                        if best is None or len(o) > len(best):
                            best = o
                    break
                depth -= 1
    return best


def _ptype(rec: dict) -> str | None:
    """house/condo/land, or None for rentals/commercial (skip)."""
    pt = (rec.get("PropertyType") or "").lower()
    sub = (rec.get("PropertySubType") or rec.get("RawMlsPropertySubType") or "").lower()
    if "lease" in pt or "rent" in pt or "commercial" in pt or "business" in pt:
        return None
    if pt == "land" or "land" in sub or "lot" in sub:
        return LAND
    if any(k in sub for k in ("condo", "townhouse", "apartment", "duplex", "strata", "villa")):
        return CONDO
    if "single family" in sub or "house" in sub or "home" in sub:
        return HOME
    if pt == "residential":
        t = norm_type(sub)
        return t if t != OTHER else HOME
    return OTHER if pt in ("residential income", "farm") else None


def _v(rec: dict, key: str):
    """Field value, ignoring unresolved RSC references like "$2e:props:..."."""
    v = rec.get(key)
    return None if isinstance(v, str) and v.startswith("$") else v


def _title(rec: dict, ptype: str) -> str:
    t = (_v(rec, "BuildingName") or _v(rec, "UnparsedAddress") or "").strip()
    if not t:
        t = " ".join(str(_v(rec, k) or "") for k in ("StreetNumber", "StreetName", "StreetSuffix")).strip()
    t = t.title() if t.isupper() else t
    # Land records often carry only the parcel number as the "address".
    if not re.search(r"[A-Za-z]{3}", t):
        area = _v(rec, "CityRegion") or _v(rec, "MLSAreaMajor") or "Cayman Islands"
        kind = "Land" if ptype == LAND else "Property"
        t = f"{kind}, {area}" + (f" (Parcel {t})" if t else "")
    return t


def _image(rec: dict, html: str) -> str:
    media = rec.get("Media")
    media = [m for m in media if isinstance(m, dict) and m.get("MediaURL")] if isinstance(media, list) else []
    media.sort(key=lambda m: m.get("Order", 999))
    if media:
        return media[0]["MediaURL"]
    m = re.search(r'property="og:image" content="([^"]+)"', html) \
        or re.search(r'MediaURL\\?":\\?"(https?://[^"\\]+)', html)
    return m.group(1).split("?")[0] if m else ""


def _status(rec: dict) -> str:
    s = rec.get("StandardStatus") or rec.get("MlsStatus") or ""
    return {"Active": "For Sale", "ActiveUnderContract": "Under Offer",
            "Pending": "Under Offer"}.get(s, s)


def fetch(max_pages: int = 5) -> list[Listing]:
    """E&V Cayman's own for-sale residential listings (not the full MLS feed).
    `max_pages` * 10 detail pages are fetched, never more than 40."""
    urls = _sitemap_urls()
    limit = min(MAX_DETAILS, max(1, max_pages) * PER_PAGE)
    results: list[Listing] = []
    for mls, url in urls[:limit]:
        try:
            html = get(url).text
            rec = _listing_record(html, mls)
            if not rec:
                continue
            # Drop unresolved RSC references ("$2e:props:...") so fallbacks apply.
            rec = {k: v for k, v in rec.items() if not (isinstance(v, str) and v.startswith("$"))}
            if (rec.get("StandardStatus") or "") in ("Closed", "Canceled", "Expired", "Withdrawn"):
                continue
            ptype = _ptype(rec)
            if ptype is None:
                continue
            price = rec.get("ListPrice")
            price = float(price) if price else None
            if not price:
                continue
            cur = (rec.get("CurrencyCode") or "USD").upper()
            cur = "KYD" if cur in ("KYD", "CI$", "CID") else "USD"
            acres = rec.get("LotSizeAcres") or rec.get("DerivedLotSizeAcres")
            acres = float(acres) if acres else None
            sqft = rec.get("LivingArea") or rec.get("BuildingAreaTotal")
            if not sqft and ptype == LAND and acres:
                sqft = round(acres * SQFT_PER_ACRE)
            baths = rec.get("BathroomsTotalDecimal") or rec.get("RawMlsBathroomsTotal") \
                or rec.get("BathroomsTotalInteger")
            if baths is None and rec.get("BathroomsFull") is not None:
                baths = (rec.get("BathroomsFull") or 0) + 0.5 * (rec.get("BathroomsHalf") or 0)
            beds = rec.get("BedroomsTotal")
            loc = rec.get("MLSAreaMajor") or rec.get("CityRegion") or rec.get("City") or ""
            results.append(Listing(
                source=SOURCE,
                url=url,
                title=_title(rec, ptype),
                price=price,
                currency=cur,
                ptype=ptype,
                location=loc,
                beds=float(beds) if beds not in (None, "") and ptype != LAND else None,
                baths=float(baths) if baths not in (None, "") and ptype != LAND else None,
                sqft=float(sqft) if sqft else None,
                acres=acres,
                image=_image(rec, html),
                mls=str(rec.get("ListingId") or mls),
                status=_status(rec),
            ))
        except Exception:
            continue
    return results
