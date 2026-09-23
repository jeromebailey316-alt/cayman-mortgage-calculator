"""Shoreline Properties (www.shoreline.ky) scraper.

WordPress + WP Residence theme.  The site carries the whole CIREBA MLS feed
(/buy/ is ~1,000 for-sale listings, 12 per page).  The firm's own listings
are the property_category "Our Listings" (~12), shown at

    https://www.shoreline.ky/listings/our-listings/[page/N/]

The REST route /wp-json/wp/v2/estate_property exposes no price/beds/etc. (no
meta), so we parse the server-rendered cards (price with US$/CI$, MLS#,
beds, baths, ft², location, image; `data-listid` = WP post id) and join them
with ONE REST call per page (`?include=<ids>`) to get the site's own
taxonomy: sale/rent category, residential/land/commercial action, status and
the untruncated title.  No detail pages are fetched.

OWN_ONLY = True (default) scrapes "Our Listings"; False scrapes /buy/ (full
feed).  robots.txt only disallows /feed/ and /advanced-search/.
"""
from __future__ import annotations

import html as htmlmod
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scraper.common import Listing, get, num, norm_type, HOME, CONDO, LAND, OTHER

SOURCE = "Shoreline"
BASE = "https://www.shoreline.ky"
API = f"{BASE}/wp-json/wp/v2/estate_property"
OWN_ONLY = True
OWN_PATH = "/listings/our-listings/"
ALL_PATH = "/buy/"
SQFT_PER_ACRE = 43560.0

SKIP_ACTIONS = {"commercial", "business"}
CONDO_WORDS = re.compile(
    r"\bcondo|apartment|townho|town home|penthouse|duplex|strata|unit\b|#\s*\d|"
    r"\bsuite|residence\s*#|\bfloor\b|\bphase\b", re.I)
HOME_WORDS = re.compile(r"\bhome\b|\bhouse\b|\bbungalow|\bestate\b|\bcottage|family", re.I)


def _page_url(path: str, page: int) -> str:
    return f"{BASE}{path}" if page == 1 else f"{BASE}{path}page/{page}/"


def _text(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip() if el else ""


def _price(txt: str) -> tuple[float | None, str]:
    m = re.search(r"\d[\d,]*(?:\.\d+)?", txt or "")
    if not m:
        return None, "USD"
    cur = "KYD" if re.search(r"CI\s*\$|KYD|\bCI\b", txt, re.I) else "USD"
    return (float(m.group(0).replace(",", "")) or None), cur


def _cards(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    out = []
    for w in soup.select("div.listing_wrapper[data-listid]"):
        try:
            d: dict = {"id": int(w["data-listid"])}
            d["url"] = urljoin(BASE, (w.get("data-modal-link") or "").strip())
            if not w.get("data-modal-link"):
                a = w.select_one("h4 a[href]")
                d["url"] = urljoin(BASE, a["href"]) if a else ""
            d["title"] = htmlmod.unescape(w.get("data-modal-title") or _text(w.select_one("h4")))
            m = re.search(r"MLS#?:?\s*([A-Za-z0-9-]+)", _text(w.select_one(".s1_mls")))
            d["mls"] = m.group(1) if m else ""
            loc = _text(w.select_one(".s1_location"))
            d["location"] = re.sub(r",?\s*Cayman Islands\s*$", "", loc).strip()
            pr = w.select_one(".s1_price")
            d["price_txt"] = _text(pr)
            d["beds"] = num(_text(w.select_one(".inforoom")))
            d["baths"] = num(_text(w.select_one(".infobath")))
            size = w.select_one(".infosize")
            size_txt = _text(size)
            if size_txt:
                v = num(size_txt)
                if re.search(r"\bac(re)?s?\b", size_txt, re.I):
                    d["acres"] = v
                else:
                    d["sqft"] = v
            img = w.select_one(".carousel-inner .item.active img") or w.select_one("img")
            src = ""
            if img is not None:
                src = img.get("src") or img.get("data-lazy-load-src") or ""
            d["image"] = urljoin(BASE, src) if src and not src.startswith("data:") else (w.get("data-main-modal") or "")
            out.append(d)
        except Exception:
            continue
    return out


def _taxonomy(ids: list[int]) -> dict[int, dict]:
    """post id -> {title, classes} via one REST call; {} on failure."""
    if not ids:
        return {}
    try:
        r = get(f"{API}?include={','.join(map(str, ids))}&per_page={len(ids)}&_fields=id,title,class_list",
                headers={"Accept": "application/json"})
        return {int(x["id"]): {"title": htmlmod.unescape((x.get("title") or {}).get("rendered") or ""),
                               "classes": x.get("class_list") or []} for x in r.json()}
    except Exception:
        return {}


def _cls(classes: list[str], prefix: str) -> list[str]:
    return [c[len(prefix):] for c in classes if c.startswith(prefix)]


def _ptype(actions: list[str], title: str) -> str | None:
    if set(actions) & SKIP_ACTIONS:
        return None
    if "land" in actions:
        return LAND
    if "multi-unit" in actions:
        return OTHER
    if "residential" in actions or not actions:
        if CONDO_WORDS.search(title):
            return CONDO
        if HOME_WORDS.search(title):
            return HOME
        if re.search(r"\bvillas?\b", title, re.I):
            return CONDO
        t = norm_type(title)
        return t if t != OTHER else (HOME if "residential" in actions else OTHER)
    return norm_type(title)


def _status(slugs: list[str]) -> str:
    if not slugs:
        return "For Sale"
    s = slugs[0]
    return {"current": "For Sale", "new": "New", "pending-conditional": "Pending/Conditional",
            "back-on-the-market": "Back On The Market"}.get(s, s.replace("-", " ").title())


def fetch(max_pages: int = 5) -> list[Listing]:
    """For-sale listings; 12 cards per page.  "Our Listings" fits on one page."""
    path = OWN_PATH if OWN_ONLY else ALL_PATH
    results: list[Listing] = []
    seen: set[str] = set()

    for page in range(1, max_pages + 1):
        url = _page_url(path, page)
        try:
            r = get(url)
        except Exception as e:
            if page == 1:
                raise RuntimeError(f"{SOURCE}: could not load {url}: {e}") from e
            break  # 404 past the last page
        cards = _cards(r.text)
        if not cards:
            if page == 1 and re.search(r"captcha|cf-chl|challenge-platform", r.text, re.I):
                raise RuntimeError(f"{SOURCE}: bot protection on {url}")
            break
        tax = _taxonomy([c["id"] for c in cards])

        for c in cards:
            try:
                if not c.get("url") or c["url"] in seen:
                    continue
                t = tax.get(c["id"], {})
                classes = t.get("classes", [])
                cats = _cls(classes, "property_category-")
                if "rent" in cats and "sale" not in cats:
                    continue
                title = (t.get("title") or c.get("title") or "").strip()
                ptype = _ptype(_cls(classes, "property_action_category-"), title)
                if ptype is None:
                    continue
                price, cur = _price(c.get("price_txt", ""))
                if not price:
                    continue
                status = _status(_cls(classes, "property_status-"))
                if re.search(r"sold|rented|withdrawn", status, re.I):
                    continue

                acres = c.get("acres") or None
                sqft = c.get("sqft")
                if sqft is not None and sqft < 50:  # land cards show "0 ft²"
                    sqft = None
                if acres is None:
                    m = re.search(r"(\d+(?:\.\d+)?)\s*[- ]?\s*acres?\b", title, re.I)
                    if m:
                        acres = float(m.group(1))
                if ptype == LAND and acres is not None:
                    sqft = None  # land cards' ft² is unreliable; keep acres
                if ptype == LAND and acres is None and sqft:
                    acres = round(sqft / SQFT_PER_ACRE, 3)

                results.append(Listing(
                    source=SOURCE,
                    url=c["url"],
                    title=title,
                    price=price,
                    currency=cur,
                    ptype=ptype,
                    location=c.get("location", ""),
                    beds=c.get("beds") if ptype != LAND else None,
                    baths=c.get("baths") if ptype != LAND else None,
                    sqft=sqft,
                    acres=acres,
                    image=c.get("image", ""),
                    mls=c.get("mls", ""),
                    status=status,
                ))
                seen.add(c["url"])
            except Exception:
                continue

        if f"{path}page/{page + 1}/" not in r.text:
            break
    return results
