"""Williams2 Real Estate (Cayman Islands) scraper.

How the site serves data
------------------------
* www.williams2.com is a parked GoDaddy domain; the brokerage lives at
  https://williams2realestate.com (WordPress, custom theme "williams2").
* robots.txt disallows `/*?action=search_properties*` (the HTML search page),
  so we never touch /search/.
* Listings are a public custom post type exposed by the WordPress REST API:
      /wp-json/wp/v2/app_property?app_action_type=12&app_type=10,29,24
  (action 12 = "buy"; type 10 = residential, 29 = condo, 24 = land).
  With `_embed=wp:featuredmedia,wp:term` each item carries its URL, title,
  featured image and the type / location term names. X-WP-TotalPages gives
  pagination. The REST data has NO price, beds, baths, sqft or MLS number
  (ACF fields are not exposed).
* Those come from the server-rendered detail page header
  (`header.section__head .section__list li`): price in both USD and KYD,
  "MLS# nnnnnn", type, "n FT2", bedrooms and bathrooms (identified by icon).
  Detail fetches are capped at MAX_DETAILS per run; listings beyond the cap
  are returned with REST-only fields (price None).
* The theme also references an Algolia index, but that Algolia app no longer
  resolves, so it is not usable.
"""
from __future__ import annotations

import html
import re

from bs4 import BeautifulSoup

from scraper.common import CONDO, HOME, LAND, Listing, get, norm_type, num, parse_price

SOURCE = "Williams2"

BASE = "https://williams2realestate.com"
API = BASE + "/wp-json/wp/v2/app_property"
PER_PAGE = 20
MAX_DETAILS = 40

BUY_ID = 12
TYPE_IDS = {10: HOME, 29: CONDO, 24: LAND}   # residential, condo, land
TYPE_NAMES = {"residential": HOME, "condo": CONDO, "land": LAND}
CONDO_RE = re.compile(
    r"\b(condo\w*|apartments?|apt|townhomes?|townhouses?|penthouse|studio|suites?|"
    r"units?|villas?|duplex|loft|residences?|flat)\b|#\s*\d", re.I)


def _text(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(BeautifulSoup(s or "", "lxml").get_text(" "))).strip()


def _abs(u: str) -> str:
    if not u:
        return ""
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("/"):
        return BASE + u
    return u


def _roundness(v: float) -> int:
    n, z = int(round(v)), 0
    while n and n % 10 == 0:
        n //= 10
        z += 1
    return z


def _pick_price(text: str) -> tuple[float | None, str]:
    """'$6,091,463 USD / $4,995,000 KYD' -> the originally advertised amount.

    The site shows both currencies, one converted from the other. The
    advertised figure is the round one (e.g. 4,995,000 KYD, not 6,091,463 USD);
    ties go to USD.
    """
    amounts = []
    for m in re.finditer(r"([\d][\d,]*(?:\.\d+)?)\s*(USD|KYD|CI\$|US\$)?", text):
        v = num(m.group(1))
        if not v or v < 1000:
            continue
        cur = "KYD" if (m.group(2) or "").upper() in ("KYD", "CI$") else "USD"
        amounts.append((v, cur))
    if not amounts:
        return parse_price(text) if text else (None, "USD")
    if len(amounts) == 1:
        return amounts[0]
    usd = next((a for a in amounts if a[1] == "USD"), None)
    kyd = next((a for a in amounts if a[1] == "KYD"), None)
    if usd and kyd:
        return kyd if _roundness(kyd[0]) > _roundness(usd[0]) else usd
    return amounts[0]


def _status(*texts: str) -> str:
    t = " ".join(texts).lower()
    if "under offer" in t:
        return "Under Offer"
    if "under contract" in t or "pending" in t:
        return "Under Contract"
    if re.search(r"\bsold\b", t):
        return "Sold"
    return "For Sale"


def _acres(text: str) -> float | None:
    m = re.search(r"(\d*\.?\d+)\s*(?:-\s*)?acres?\b", text.replace(",", ""), re.I)
    return float(m.group(1)) if m else None


def _from_rest(p: dict) -> Listing | None:
    url = _abs(p.get("link") or "")
    if not url:
        return None
    title = _text((p.get("title") or {}).get("rendered", ""))
    emb = p.get("_embedded") or {}

    image = ""
    fm = emb.get("wp:featuredmedia") or []
    if fm and isinstance(fm[0], dict):
        image = _abs(fm[0].get("source_url") or "")

    terms = {}
    for group in emb.get("wp:term") or []:
        for t in group or []:
            if isinstance(t, dict):
                terms.setdefault(t.get("taxonomy"), []).append(html.unescape(t.get("name", "")))

    ptype = next((TYPE_IDS[i] for i in p.get("app_type") or [] if i in TYPE_IDS), None)
    if ptype is None:
        ptype = norm_type(" ".join(terms.get("app_type", [])) + " " + title)
    elif ptype == HOME and CONDO_RE.search(title):
        # The site files most condos/townhomes under "Residential".
        ptype = CONDO
    location = (terms.get("app_location") or [""])[0]

    content = _text((p.get("content") or {}).get("rendered", ""))
    # Descriptions often mention the whole development's acreage, so only trust
    # the body text for land listings.
    acres = _acres(title) or (_acres(content) if ptype == LAND else None)
    return Listing(
        source=SOURCE, url=url, title=title, price=None, ptype=ptype,
        location=location, image=image, acres=acres, status=_status(title),
    )


def _enrich(l: Listing) -> bool:
    """Fill price / MLS / beds / baths / sqft from the detail page header.

    Returns False when the listing is gone: withdrawn/sold properties stay in
    the REST feed but their page 301-redirects to the home page.
    """
    r = get(l.url)
    if r.url.rstrip("/") == BASE or "/property/" not in r.url:
        return False
    s = BeautifulSoup(r.text, "lxml")
    head = s.select_one("header.section__head")
    if head is None:
        return True
    if not l.title:
        t = head.select_one(".section__title")
        l.title = t.get_text(" ", strip=True) if t else ""
    for li in head.select(".section__list li"):
        cls = li.get("class") or []
        txt = li.get_text(" ", strip=True).replace("\xa0", " ")
        img = li.find("img", attrs={"data-lazy-src": True}) or li.find("img")
        icon = ((img.get("data-lazy-src") or img.get("src") or "") if img else "").rsplit("/", 1)[-1]
        if "section__price" in cls:
            l.price, l.currency = _pick_price(txt)
        elif "section__number" in cls or txt.upper().startswith("MLS"):
            m = re.search(r"(\d{4,})", txt)
            if m:
                l.mls = m.group(1)
        elif "bedroom" in icon:
            l.beds = num(txt)
        elif "bathroom" in icon:
            l.baths = num(txt)
        elif "square" in icon:
            l.sqft = num(txt)
        elif "section__loc" in cls and not l.location:
            l.location = txt
        elif icon.startswith("ico-") and txt.lower() in TYPE_NAMES:
            # "Residential" is used for condos too, so keep the title-based
            # condo guess unless the page says condo or land explicitly.
            if TYPE_NAMES[txt.lower()] != HOME:
                l.ptype = TYPE_NAMES[txt.lower()]
    if not l.image:
        og = s.find("meta", property="og:image")
        if og and og.get("content"):
            l.image = _abs(og["content"])
    l.status = _status(l.title, head.get_text(" ", strip=True))
    return True


def fetch(max_pages: int = 5) -> list[Listing]:
    out: list[Listing] = []
    seen: set[str] = set()
    total_pages = None
    for page in range(1, max_pages + 1):
        if total_pages is not None and page > total_pages:
            break
        try:
            r = get(API, params={
                "per_page": PER_PAGE,
                "page": page,
                "app_action_type": BUY_ID,
                "app_type": ",".join(str(i) for i in TYPE_IDS),
                "orderby": "date",
                "order": "desc",
                "_embed": "wp:featuredmedia,wp:term",
                "_fields": "id,link,title,content,app_type,app_location,app_action_type,_links,_embedded",
            })
        except Exception as e:  # past the last page WP returns 400
            print(f"[{SOURCE}] page {page} failed: {e}")
            break
        try:
            total_pages = int(r.headers.get("X-WP-TotalPages") or 0) or None
        except ValueError:
            pass
        items = r.json()
        if not isinstance(items, list) or not items:
            break
        for p in items:
            try:
                # Skip rental-only posts defensively (filter should already exclude them).
                if BUY_ID not in (p.get("app_action_type") or [BUY_ID]):
                    continue
                l = _from_rest(p)
                if l and l.url not in seen:
                    seen.add(l.url)
                    out.append(l)
            except Exception as e:
                print(f"[{SOURCE}] bad item {p.get('id')}: {e}")

    gone = set()
    for l in out[:MAX_DETAILS]:
        try:
            if not _enrich(l):
                gone.add(l.url)
        except Exception as e:
            print(f"[{SOURCE}] detail failed {l.url}: {e}")
    return [l for l in out if l.url not in gone]
