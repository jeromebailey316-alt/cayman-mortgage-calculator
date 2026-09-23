"""MOD Realty (modrealtycayman.com) scraper.

WordPress + the "WP RealEstate" plugin (JustHome theme).  The REST route
/wp-json/wp/v2/property exists but carries no price/beds/baths (ACF is empty),
so we parse the server-rendered status archive, which lists only for-sale
listings, 8 per page:

    https://modrealtycayman.com/property-status/for-sale/[page/N/]

Each <article class="property-item ..."> card has the price (with a "CI"
prefix for CI$ prices), beds, baths, size, image and, in its CSS classes, the
site's own taxonomy slugs (property_type-*, property_location-*,
property_status-*).  One extra REST call fetches the location taxonomy so
district names/parents are exact.

MOD only shows its own listings (no CIREBA IDX feed) and does not display
CIREBA MLS numbers anywhere, including detail pages, so `mls` is empty.
"""
from __future__ import annotations

import html as htmlmod
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper.common import Listing, get, norm_type, HOME, CONDO, LAND, OTHER

SOURCE = "MOD Realty"
BASE = "https://modrealtycayman.com"
LIST_PATH = "/property-status/for-sale/"

# The site's property_type slugs -> calculator types (None = skip).
TYPE_MAP = {
    "single-family": HOME,
    "apartment": CONDO,
    "duplex-one-side": CONDO,
    "land": LAND,
    "multi-unit": OTHER,       # residential multi-unit / investment buildings
    "commercial": None,
    "office": None,
    "retail": None,
}
SKIP_STATUS = {"for-rent", "rented", "sold"}
SQFT_PER_ACRE = 43560.0


def _page_url(page: int) -> str:
    return f"{BASE}{LIST_PATH}" if page == 1 else f"{BASE}{LIST_PATH}page/{page}/"


def _locations() -> dict[str, tuple[str, int, int]]:
    """slug -> (name, id, parent) from the REST taxonomy; {} on failure."""
    try:
        r = get(f"{BASE}/wp-json/wp/v2/property_location?per_page=100&_fields=id,slug,name,parent")
        return {t["slug"]: (htmlmod.unescape(t["name"]), t["id"], t.get("parent", 0)) for t in r.json()}
    except Exception:
        return {}


def _classes(el, prefix: str) -> list[str]:
    return [c[len(prefix):] for c in el.get("class", []) if c.startswith(prefix)]


def _location(slugs: list[str], locs: dict) -> str:
    if not slugs:
        return ""
    if locs:
        known = [s for s in slugs if s in locs]
        if known:
            # Prefer the most specific term: one that is not a parent of another.
            parents = {locs[s][2] for s in known}
            leaf = [s for s in known if locs[s][1] not in parents] or known
            return locs[leaf[0]][0]
    return slugs[-1].replace("-", " ").title()


def _street(card) -> str:
    """Fallback: the card's address line, e.g. "Spotts, Grand Cayman"."""
    el = card.select_one(".property-location")
    return el.get_text(" ", strip=True) if el else ""


def _price(card) -> tuple[float | None, str]:
    box = card.select_one(".property-price")
    if not box:
        return None, "USD"
    txt = box.get_text(" ", strip=True)
    pt = box.select_one(".price-text")
    m = re.search(r"\d[\d,]*(?:\.\d+)?", pt.get_text() if pt else txt)
    if not m:
        return None, "USD"
    cur = "KYD" if re.search(r"\bCI\b|CI\s*\$|KYD", txt, re.I) else "USD"
    return (float(m.group(0).replace(",", "")) or None), cur


def _metas(card) -> dict:
    out: dict = {}
    for meta in card.select(".property-meta"):
        suf = meta.select_one(".suffix")
        label = (suf.get_text(strip=True).lower() if suf else "")
        m = re.search(r"\d[\d,]*(?:\.\d+)?|\.\d+", meta.get_text(" ", strip=True))
        v = float(m.group(0).replace(",", "")) if m else None
        if v is None:
            continue
        if "bed" in label:
            out["beds"] = v
        elif "bath" in label:
            out["baths"] = v
        elif "acre" in label:
            out["acres"] = v
        elif "sq" in label or "ft" in label:
            out["size"] = v
    return out


def _parse_card(card, locs: dict) -> Listing | None:
    a = card.select_one("h2.property-title a[href]") or card.select_one("a.property-image[href]")
    if not a:
        return None
    url = urljoin(BASE, a["href"].strip())
    title = a.get_text(" ", strip=True)

    statuses = set(_classes(card, "property_status-"))
    if statuses & SKIP_STATUS and "for-sale" not in statuses:
        return None
    types = _classes(card, "property_type-")
    mapped = [TYPE_MAP.get(t, norm_type(t)) for t in types]
    if types and all(m is None for m in mapped):
        return None  # commercial / office / retail only
    mapped = [m for m in mapped if m is not None]
    # A card tagged e.g. apartment + duplex keeps the first residential type.
    ptype = next((m for m in mapped if m != OTHER), mapped[0] if mapped else norm_type(title))

    price, cur = _price(card)
    if not price:
        return None

    md = _metas(card)
    sqft, acres = md.get("size"), md.get("acres")
    # The size field is free-form: small values ("0.23 sqft") are acres.
    if sqft is not None and sqft < 50:
        acres, sqft = acres or sqft, None
    if acres is None:
        m = re.search(r"(\d+(?:\.\d+)?)\s*[- ]?\s*acres?\b", title, re.I)
        if m:
            acres = float(m.group(1))
    if ptype == LAND and acres is None and sqft:
        acres = round(sqft / SQFT_PER_ACRE, 3)

    label_txt = " ".join(x.get_text(" ", strip=True) for x in card.select(".status-property-label")).lower()
    if "under contract" in label_txt or "under-contract" in statuses:
        status = "Under Contract"
    else:
        status = "For Sale"

    img = card.get("data-img") or ""
    im = card.select_one(".property-image img")
    if im is not None:
        img = im.get("data-src") or (im.get("src") if not (im.get("src") or "").startswith("data:") else "") or img

    return Listing(
        source=SOURCE,
        url=url,
        title=title,
        price=price,
        currency=cur,
        ptype=ptype,
        location=_location(_classes(card, "property_location-"), locs) or _street(card),
        beds=md.get("beds"),
        baths=md.get("baths"),
        sqft=sqft,
        acres=acres,
        image=urljoin(BASE, img) if img else "",
        mls="",
        status=status,
    )


def fetch(max_pages: int = 5) -> list[Listing]:
    """For-sale listings from the status archive (8 per page, ~6 pages total)."""
    results: list[Listing] = []
    seen: set[str] = set()
    locs = _locations()

    for page in range(1, max_pages + 1):
        try:
            r = get(_page_url(page))
        except Exception as e:
            if page == 1:
                raise RuntimeError(f"{SOURCE}: could not load {_page_url(page)}: {e}") from e
            break  # 404 past the last page
        soup = BeautifulSoup(r.text, "lxml")
        cards = soup.select("article.property-item")
        if not cards:
            break
        for card in cards:
            try:
                li = _parse_card(card, locs)
                if li and li.url not in seen:
                    seen.add(li.url)
                    results.append(li)
            except Exception:
                continue
        if f"{LIST_PATH}page/{page + 1}/" not in r.text:
            break
    return results
