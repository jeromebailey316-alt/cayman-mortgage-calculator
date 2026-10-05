"""Premier Realty Cayman (premierrealtycayman.com).

A Wix **Stores** site: every listing is a shop "product", so prices are in the
store currency (KYD) and the whole catalogue is served as JSON inside the
`wix-warmup-data` script tag of any page that holds a product grid.

Discovery is therefore one request. `/shop` carries the "All Products" grid
with `totalCount: 20` and all 20 products inline -- name, ribbon, price,
currency, `urlPart` and media -- which is the entire catalogue, so we never
touch `/store-products-sitemap.xml` or page through anything.

The site's own navigation is mislabelled by URL: `/land` is the **homes**
grid (nav label "HOMES") and `/copy-of-land` is the **land** page (nav label
"LAND"). `/copy-of-land` is hand-laid-out Wix content with no product links at
all, and its figures are stale -- it still advertises two lots the store marks
SOLD, at a price that no longer matches. So we ignore both and read `/shop`.

Beds / baths / sq ft appear only on the grid card, in the product `ribbon`
("5 Bed l 4 Bath l 2,622 Sq. Ft." -- the separator is a lowercase L, not a
pipe), not as structured product fields and not on the detail page. Acreage is
the other way round: only the detail page's description has it ("Acres:0.2350").

**Almost nothing here is genuinely for sale.** Of the 20 products, 7 are
rentals (priced per month), 9 are sold / leased / withdrawn, one is an
unpublished "Copy of ..." duplicate and the same Cayman Brac lot is entered
three times. What survives is **two** Cayman Brac bluff lots, #504 and #506,
both CI$85,000 at 0.235 acres. The module is worth keeping only because that is
cheap Cayman Brac land the larger agencies do not carry -- on volume alone it
barely earns its place.

Status is recorded inconsistently and no single field can be trusted:

  * `isInStock` is True for every product, sold ones included -- useless.
  * The grid `ribbon` holds "SOLD" / "Withdrawn" / "LEASED" for some, but for
    VALENCIA HEIGHTS it holds only "2 Bed l 2 Bath l 900 Sq. Ft." although the
    property is sold.
  * The product `name` holds the marker for others ("SOUTH COVE APARTMENT
    Sold", "BUTTERFLY CIRCLE HOME - WITHDRAWN").
  * The detail page's "Additional Information" table has a structured
    "Status:" field, which catches VALENCIA HEIGHTS (Status: Sold) -- but it is
    itself stale for LAND ON CAYMAN BRAC, which reads "Status: Current" while
    the ribbon says "Withdrawn".

So we treat a sold/rented/withdrawn marker in *any* of name, ribbon or the
detail table as disqualifying, and keep a listing only if none of them objects.

Detail pages are fetched best-effort, one per surviving listing (so at most a
handful), to enrich acreage, the real category ("LAND" / "HOMES"), the property
type and the address -- and to read that "Status:" field. They render
intermittently: some requests answer 200 with an empty shell carrying no
warmup data at all (seen repeatedly on /product-page/income-generation-home
and /product-page/copy-of-cayman-brac-bluff-lot-504-1, both of which render
fine on other attempts). So a listing is never dropped for failing to render,
only for what a page that does render says. The cost of that choice: when a
detail page flakes out, stock whose only sold/withdrawn marker lives in that
table can slip through for one run -- INCOME GENERATING PROPERTY is
"Status: Withdrawn" there while its grid card looks perfectly live.

robots.txt: "Allow: /", with Crawl-delay only for dotbot and AhrefsBot and
"Disallow: *?lightbox=" (we never request those). common.py still throttles
this host to 10s between requests, so a run takes ~50 seconds.
"""
from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from scraper.common import Listing, get, num, HOME, CONDO, LAND, OTHER

SOURCE = "Premier Realty"
BASE = "https://www.premierrealtycayman.com"
SHOP_URL = BASE + "/shop"
PRODUCT_URL = BASE + "/product-page/"
WIX_MEDIA = "https://static.wixstatic.com/media/"

# Everything in the store is priced in the store currency, KYD. Sale prices are
# six figures; anything under this is a monthly rent (the rentals run
# CI$1,500-2,900), so it is a useful backstop for rentals we fail to name.
MIN_SALE_PRICE = 20_000
DETAIL_LIMIT = 12          # hard cap on best-effort detail requests per run

GONE = re.compile(r"\bsold\b|\bwithdrawn\b|\bleased\b|\brented\b|\bunder\s+(offer|contract)\b"
                  r"|\bpending\b|\bno\s+longer\s+available\b", re.I)
RENTAL = re.compile(r"\brent(al|ed|s)?\b|\bfor\s+rent\b|\bper\s+month\b|\bp/?m\b|\blease\b", re.I)
COMMERCIAL = re.compile(r"\bcommercial\b|\boffice\b|\bretail\b|\bwarehouse\b", re.I)
ACRES = re.compile(r"acre\(?s?\)?\s*[:\-]?\s*(\d+(?:\.\d+)?)", re.I)
ACRES_ALT = re.compile(r"(\d+(?:\.\d+)?)\s*acres?\b", re.I)


def _clean(s: str | None) -> str:
    return re.sub(r"[\s​\xa0]+", " ", s or "").strip()


def _warmup(html: str) -> dict:
    tag = BeautifulSoup(html, "lxml").find("script", id="wix-warmup-data")
    if tag is None or not tag.string:
        return {}
    try:
        return json.loads(tag.string)
    except ValueError:
        return {}


def _find_key(obj, key: str):
    """Depth-first search for the first value stored under `key`."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            hit = _find_key(v, key)
            if hit is not None:
                return hit
    elif isinstance(obj, list):
        for v in obj:
            hit = _find_key(v, key)
            if hit is not None:
                return hit
    return None


def _ricos_text(raw: str | None) -> str:
    """Wix stores rich text as Ricos JSON; pull out the plain text."""
    if not raw:
        return ""
    try:
        doc = json.loads(raw)
    except ValueError:
        return _clean(raw)
    parts: list[str] = []

    def walk(o):
        if isinstance(o, dict):
            if o.get("type") == "TEXT":
                parts.append((o.get("textData") or {}).get("text") or "")
            for v in o.values():
                walk(v)
            if o.get("type") in ("PARAGRAPH", "TABLE_CELL"):
                parts.append("\n")
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(doc)
    return re.sub(r"\n+", "\n", "".join(parts)).strip()


def _image(media) -> str:
    """Product media url is "<id>~mv2.jpg/v1/fit/w_955,.../file.jpg"; the media
    id alone is the full-size original."""
    for m in media or []:
        raw = m.get("url") or ""
        if raw:
            return WIX_MEDIA + raw.split("/")[0]
        full = m.get("fullUrl") or ""
        if full:
            return full
    return ""


def _ribbon_facts(ribbon: str) -> tuple[float | None, float | None, float | None]:
    """"5 Bed l 4 Bath l 2,622 Sq. Ft." -> (5, 4, 2622)."""
    beds = baths = sqft = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*\.?\s*bed", ribbon, re.I)
    if m:
        beds = float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*\.?\s*bath", ribbon, re.I)
    if m:
        baths = float(m.group(1))
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*sq", ribbon, re.I)
    if m:
        sqft = num(m.group(1))
    return beds, baths, sqft


def _ptype(category: str, prop_type: str, name: str) -> str:
    """Prefer the store category / detail "Property Type", fall back to the name."""
    for src in (prop_type, category):
        s = (src or "").lower()
        if "land" in s or "lot" in s:
            return LAND
        if any(k in s for k in ("condo", "apartment", "townhouse", "townhome", "duplex", "villa")):
            return CONDO
        if any(k in s for k in ("home", "house", "residential")):
            return HOME
    n = (name or "").lower()
    if re.search(r"\blot\b|\bland\b|\bacre", n):
        return LAND
    if re.search(r"apartment|condo|townhouse", n):
        return CONDO
    if re.search(r"home|house|property", n):
        return HOME
    return OTHER


def _detail(url_part: str) -> dict:
    """Best-effort product detail. Returns {} when the page does not render."""
    html = get(PRODUCT_URL + url_part).text
    prod = _find_key(_warmup(html), "product")
    if not isinstance(prod, dict) or "name" not in prod:
        return {}

    desc = _ricos_text(prod.get("description"))
    info_parts = [desc]
    for ai in prod.get("additionalInfo") or []:
        info_parts.append(_ricos_text(ai.get("description")))
    info = "\n".join(p for p in info_parts if p)

    def field(label: str) -> str:
        m = re.search(rf"{label}\s*:\s*([^\n|]*)", info, re.I)
        return _clean(m.group(1)) if m else ""

    acres = None
    m = ACRES.search(info) or ACRES_ALT.search(info)
    if m:
        acres = float(m.group(1))

    cats = [c.get("name") or "" for c in prod.get("categories") or []
            if (c.get("name") or "").lower() != "all products"]

    # The address table has no label; it is a titled section of its own.
    address = field("address")
    if not address:
        for ai in prod.get("additionalInfo") or []:
            if re.search(r"address", ai.get("title") or "", re.I):
                address = _clean(_ricos_text(ai.get("description")).replace("\n", ", "))
                break

    return {
        "acres": acres,
        "category": cats[0] if cats else "",
        "prop_type": field("property type"),
        "status": field("status"),
        "address": address,
        "text": info,
    }


def _location(name: str, address: str) -> str:
    """Keep the island explicit when the listing names it -- Cayman Brac has
    its own stamp-duty rates. Never guess an island that is not stated."""
    blob = f"{name} {address}"
    island = ""
    if re.search(r"cayman\s+brac", blob, re.I):
        island = "Cayman Brac"
    elif re.search(r"little\s+cayman", blob, re.I):
        island = "Little Cayman"
    elif re.search(r"grand\s+cayman", blob, re.I):
        island = "Grand Cayman"

    base = address or ""
    if island and island.lower() not in base.lower():
        base = f"{base}, {island}".strip(", ")
    return _clean(base)


def fetch(max_pages: int = 1) -> list[Listing]:
    """Premier Realty's genuinely-for-sale stock.

    `/shop` returns the whole 20-product catalogue in one response, so there is
    nothing to page through and `max_pages` only decides whether to run.
    Costs 1 request plus one best-effort detail request per surviving listing
    (typically 4 in total).
    """
    if max_pages < 1:
        return []

    grid = _find_key(_warmup(get(SHOP_URL).text), "productsWithMetaData")
    products = (grid or {}).get("list") or []
    if not products:
        print(f"[{SOURCE}] no product grid in /shop warmup data")
        return []

    # Cheap pass first: drop rentals, sold/withdrawn stock and the agent's
    # unpublished duplicates, and collapse the same lot entered several times,
    # so that we only spend detail requests on plausible listings.
    candidates: list[dict] = []
    seen_product: set[tuple[str, float]] = set()
    for p in products:
        try:
            name = _clean(p.get("name"))
            ribbon = _clean(p.get("ribbon"))
            url_part = p.get("urlPart") or ""
            blob = f"{name} {ribbon} {url_part}"

            if not url_part or name.lower().startswith("copy of"):
                continue
            if GONE.search(name) or GONE.search(ribbon):
                continue
            if RENTAL.search(blob) or COMMERCIAL.search(blob):
                continue

            price = p.get("price")
            price = float(price) if price else None
            if not price or price < MIN_SALE_PRICE:
                continue

            key = (re.sub(r"[^a-z0-9]+", "", name.lower()), price)
            if key in seen_product:
                continue
            seen_product.add(key)
            candidates.append(p)
        except Exception as e:
            print(f"[{SOURCE}] product filter error: {e}")
            continue

    out: list[Listing] = []
    for p in candidates[:DETAIL_LIMIT]:
        try:
            name = _clean(p.get("name"))
            ribbon = _clean(p.get("ribbon"))
            url_part = p["urlPart"]
            url = PRODUCT_URL + url_part

            try:
                d = _detail(url_part)
            except Exception as e:
                print(f"[{SOURCE}] detail unavailable for {url_part}: {e}")
                d = {}

            # A detail page that renders gets the last word on status.
            if d and (GONE.search(d.get("status") or "") or GONE.search(d.get("category") or "")):
                continue
            if d and COMMERCIAL.search(d.get("prop_type") or ""):
                continue

            price = float(p["price"])
            beds, baths, sqft = _ribbon_facts(ribbon)
            ptype = _ptype(d.get("category", ""), d.get("prop_type", ""), name)
            if ptype == LAND:
                beds = baths = sqft = None

            out.append(Listing(
                source=SOURCE,
                url=url,
                title=name,
                price=price,
                currency=p.get("currency") or "KYD",
                ptype=ptype,
                location=_location(name, d.get("address", "")),
                beds=beds,
                baths=baths,
                sqft=sqft,
                acres=d.get("acres"),
                image=_image(p.get("media")),
                mls="",                     # the site shows no CIREBA MLS numbers
                status="For Sale",
            ))
        except Exception as e:
            print(f"[{SOURCE}] listing error on {p.get('urlPart')}: {e}")
            continue

    return out
