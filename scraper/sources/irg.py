"""International Realty Group (https://www.irgcayman.com).

Runs on the same PowerPanel/WingCMS platform as CIREBA and Trident; listings are
server-rendered HTML, no public JSON endpoint.

  * https://www.irgcayman.com/properties-for-sale-in-the-cayman-islands
        IRG's own for-sale listings (~25 cards, all on one page; ?page=N works).
  * .../<category>/ldx-feed  (e.g. /residential-properties-in-cayman-islands/ldx-feed)
        the full CIREBA IDX feed, 30/page. NOT used: we scrape only IRG's own
        listings, which everyone else's IDX pages already cover.

Cards (div.feature-box) give URL, title, MLS#, price (`data-default` in the
advertised currency, US$ or CI$), beds/baths/sq ft (land: width/depth) and an
image. The detail URL path is /property-detail/<area>/<type>/<slug> with
<type> in residential | land | commercial (commercial is skipped).

"residential" covers both houses and condos, and the card has no district,
status or acreage, so we fetch each own listing's detail page (capped at 40)
for Type ("Homes (Residential)", "Condos (Residential)", "Residential (Land)"),
Status, Acreage and the location line.

robots.txt disallows /powerpanel/, /memberlogin/, /resources/, /vendor/,
/front-html/ -- none are requested. Image URLs live under /caches/, which is
not disallowed.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from scraper.common import Listing, get, parse_price, norm_type, num, HOME, CONDO, LAND, OTHER

SOURCE = "IRG"
BASE = "https://www.irgcayman.com"
OWN_URL = BASE + "/properties-for-sale-in-the-cayman-islands"
DETAIL_CAP = 40


def _clean(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _path_type(url: str) -> str:
    parts = urlparse(url).path.strip("/").split("/")
    return parts[2] if len(parts) >= 4 and parts[0] == "property-detail" else ""


def _parse_card(card) -> Listing | None:
    link = card.select_one("a.p-title[href]") or card.select_one("a[href*='/property-detail/']")
    if link is None:
        return None
    url = urljoin(BASE, link["href"])
    if "/property-detail/" not in url:
        return None
    seg = _path_type(url)
    if seg == "commercial" or re.search(r"rent|lease", seg):
        return None
    title = _clean(link.get("title") or link.get_text())

    pe = card.select_one(".price")
    price, cur = (parse_price(pe.get("data-default") or pe.get_text()) if pe is not None
                  else (None, "USD"))
    if not price:
        return None

    mls = ""
    mn = card.select_one(".number")
    if mn is not None:
        m = re.search(r"(\d{4,})", mn.get_text())
        mls = m.group(1) if m else ""
    if not mls:
        fav = card.select_one("a.addfavorites[mls]")
        mls = fav["mls"] if fav else ""

    beds = baths = sqft = None
    for li in card.select(".feature-desc li"):
        t = _clean(li.get_text())
        tl = t.lower()
        if "bed" in tl:
            beds = num(t)
        elif "bath" in tl:
            baths = num(t)
        elif "sq" in tl:
            sqft = num(t)

    image = ""
    img = card.select_one("img[data-src]") or card.select_one("img[src]")
    if img is not None:
        src = img.get("data-src") or img.get("src") or ""
        if src and "loader" not in src:
            image = urljoin(BASE, src)

    if seg == "land":
        ptype = LAND
    else:
        ptype = norm_type(title)
        if ptype == OTHER:
            ptype = HOME if seg == "residential" else OTHER

    m = re.search(r"(\d+(?:\.\d+)?)\s*acres?\b", title, re.I)
    return Listing(
        source=SOURCE, url=url, title=title, price=price, currency=cur,
        ptype=ptype, location="", beds=beds, baths=baths, sqft=sqft,
        acres=float(m.group(1)) if m else None, image=image, mls=mls,
        status="For Sale",
    )


def _enrich(l: Listing) -> bool:
    """Fill type / status / location / acreage from the detail page.
    Returns False if the listing should be dropped."""
    soup = BeautifulSoup(get(l.url).text, "lxml")
    fields: dict[str, str] = {}
    for n in soup.select("span.name"):
        v = n.find_next_sibling("span")
        if v is not None:
            fields.setdefault(_clean(n.get_text()).lower(), _clean(v.get_text()))

    mtype = soup.select_one(".mls-type")
    mt = _clean(mtype.get_text()) if mtype else ""
    if re.search(r"rent|lease", mt, re.I):
        return False

    typ = fields.get("type", "")
    tl = typ.lower()
    if "commercial" in tl or "timeshare" in tl or "fractional" in tl or "business" in tl:
        return False
    if "land" in tl:
        l.ptype = LAND
    elif "condo" in tl or "apartment" in tl or "town" in tl or "duplex" in tl:
        l.ptype = CONDO
    elif "home" in tl or "house" in tl or "single" in tl:
        l.ptype = HOME
    elif "multi" in tl:
        l.ptype = OTHER

    st = fields.get("status", "")
    sl = st.lower()
    if "sold" in sl or "withdrawn" in sl or "expired" in sl:
        return False
    if sl in ("", "current", "active", "new", "reduced", "increased", "price change", "back on market"):
        l.status = "For Sale"
    elif "pen" in sl or "con" in sl or "offer" in sl:
        l.status = "Under Offer"
    else:
        l.status = st

    ac = num(fields.get("acreage") or fields.get("lot size"))
    if ac:
        l.acres = ac
    if l.beds is None and fields.get("bed"):
        l.beds = num(fields["bed"])
    if l.baths is None and fields.get("bath"):
        l.baths = num(fields["bath"])

    loc = soup.select_one(".location") or soup.select_one(".s-location")
    if loc is not None:
        t = _clean(loc.get_text(" "))
        t = re.sub(r",?\s*Cayman Islands$", "", t, flags=re.I).strip(" ,")
        l.location = t
    if not l.mls:
        mn = soup.select_one(".mls-num")
        m = re.search(r"(\d{4,})", mn.get_text()) if mn else None
        l.mls = m.group(1) if m else ""
    return True


def fetch(max_pages: int = 5, detail_limit: int = DETAIL_CAP) -> list[Listing]:
    """IRG's own for-sale listings (houses, condos, land; commercial skipped).
    Up to `max_pages` result pages (normally 1 is enough) plus up to
    `detail_limit` (<=40) detail pages."""
    listings: list[Listing] = []
    seen: set[str] = set()
    for page in range(1, max(1, max_pages) + 1):
        url = OWN_URL + (f"?page={page}" if page > 1 else "")
        try:
            soup = BeautifulSoup(get(url).text, "lxml")
        except Exception as e:
            if page == 1:
                raise RuntimeError(f"[{SOURCE}] could not load {url}: {e}") from e
            break
        cards = soup.select("div.feature-box")
        new = 0
        for card in cards:
            try:
                l = _parse_card(card)
            except Exception as e:
                print(f"[{SOURCE}] card parse error on {url}: {e}")
                continue
            if not l or not l.url or not l.price or l.url in seen:
                continue
            seen.add(l.url)
            listings.append(l)
            new += 1
        m = re.search(r"Showing\s+([\d,]+)\s+Properties", soup.get_text(" "))
        total = int(m.group(1).replace(",", "")) if m else None
        if not cards or not new or (total is not None and len(cards) >= total):
            break

    out: list[Listing] = []
    budget = min(detail_limit, DETAIL_CAP)
    for l in listings:
        if budget > 0:
            budget -= 1
            try:
                if not _enrich(l):
                    continue
            except Exception as e:
                print(f"[{SOURCE}] detail error {l.url}: {e}")
        out.append(l)
    return out
