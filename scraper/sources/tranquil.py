"""Tranquil Realty (https://www.tranquilrealty.ky).

Netclues PowerPanel - the same engine as trident.py, with the older
"propeties-listing" card markup.  Plain server-rendered HTML, no JSON feed.

    /for-sale?page=N       20 cards per page, 2 pages, 28 listings

Tranquil only sells on the Sister Islands, and every card states the island
("Cayman Brac" or "Little Cayman") next to the price; the detail URL repeats it
as /property-detail/<caymanbrac|littlecayman>/<type>/<slug>.  We put the island
in `location` (and append it to the title when the title does not already name
it) so downstream code can tell Brac from Little Cayman - this is the only
source in the set that is not Grand Cayman, and the price bands are very
different.

Cards are rich: island, price in the advertised currency (US$ or CI$), the
site's listing ID, a status ribbon, and either Width / Depth / Acres (land) or
Bedrooms / Bathrooms / Sq Ft / Lot Size (residential).  Detail pages add a
`ul.p-detail-list` of Property Type / Listing Type / Property Status / Address
/ Year Built, which we use to confirm the status, fix house-vs-condo and
improve the location with the street address.

Status ribbons seen: Current, Reduced, Pending, Sold.  Sold and Pending are
dropped; Reduced is still on the market.  One card quotes "Contact us for More
info" instead of a price - no price means we skip it.

The ".mlsinfo" element is a misnomer: it holds Tranquil's own "Listing ID#"
(10007, 100077, ...), not a CIREBA MLS number, and the Sister Islands are not
on the CIREBA MLS.  `Listing.mls` is left empty on purpose - run.py de-dupes
globally on `mls:<digits>`, so a site-internal ID there could merge unrelated
properties from other sources.  The detail URL is the per-listing identity.

robots.txt (checked 5 Oct 2026) disallows only /powerpanel/, /resources/ and
/vendor/; none of those are touched.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from scraper.common import Listing, get, parse_price, num, HOME, CONDO, LAND

SOURCE = "Tranquil Realty"
BASE = "https://www.tranquilrealty.ky"
LIST_URL = BASE + "/for-sale"
DETAIL_CAP = 40
SQFT_PER_ACRE = 43560.0
MIN_PRICE = 20_000.0          # below this it is a monthly rent, not a price

ISLANDS = {"caymanbrac": "Cayman Brac", "littlecayman": "Little Cayman",
           "grandcayman": "Grand Cayman"}

_CONDO_RE = re.compile(
    r"condo|apartment|\bapt\b|town\s*house|town\s*home|duplex|triplex|"
    r"\bunit\b|#\s*\d|\bsuite\b|strata|residences?\b|seafarers", re.I)
_SKIP_RE = re.compile(r"for\s*rent|rental|commercial|industrial|warehouse|office|retail|"
                      r"business|fractional|time\s*share", re.I)


def _clean(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _url_parts(url: str) -> tuple[str, str]:
    """('caymanbrac', 'land') from /property-detail/caymanbrac/land/<slug>."""
    parts = urlparse(url).path.strip("/").split("/")
    if len(parts) >= 4 and parts[0] == "property-detail":
        return parts[1].lower(), parts[2].lower()
    return "", ""


def _status(ribbon: str) -> str | None:
    """None -> drop the listing."""
    b = ribbon.strip().lower()
    if re.search(r"\bsold\b|\brented\b|\bleased\b|withdrawn|expired|off\s*market", b):
        return None
    if re.search(r"pending|pen\s*/\s*con|under\s*(offer|contract)", b):
        return None
    return "For Sale"          # Current / Reduced / New / "" ...


def _parse_card(card, page_url: str) -> Listing | None:
    link = card.select_one("h3.title-listing a[href]") or card.select_one("a[href*='/property-detail/']")
    if not link:
        return None
    url = urljoin(page_url, link["href"].strip())
    if "/property-detail/" not in url:
        return None

    island_seg, cat = _url_parts(url)
    if cat.startswith("land"):
        ptype = LAND
    elif cat.startswith("residential"):
        ptype = None           # from the title / detail page
    else:
        return None            # commercial, rentals, ...

    title = _clean(link.get("title") or link.get_text())
    if _SKIP_RE.search(title):
        return None

    ribbon = card.select_one(".porperty-option .ribbon span") or card.select_one(".porperty-option")
    status = _status(_clean(ribbon.get_text()) if ribbon is not None else "")
    if status is None:
        return None

    # <div class="price"><span>Cayman Brac</span><span class="divider">|</span><span>US$975,000</span>
    bits = [_clean(s.get_text()) for s in card.select(".price > span")
            if "divider" not in (s.get("class") or [])]
    island = ISLANDS.get(island_seg, "")
    price, cur = None, "USD"
    for b in bits:
        if re.search(r"\d", b) and re.search(r"\$", b):
            price, cur = parse_price(b)
        elif b and not island:
            island = b
    if not price or price < MIN_PRICE:
        return None

    beds = baths = sqft = acres = None
    width = depth = None
    for li in card.select("ul.list-facilites li"):
        t = _clean(li.get_text(" "))
        tl = t.lower()
        v = num(t)
        if tl.startswith("bedroom"):
            beds = v
        elif tl.startswith("bathroom"):
            baths = v
        elif tl.startswith("sq"):
            sqft = v
        elif tl.startswith("acre"):
            acres = v
        elif tl.startswith("lot size"):
            acres = v
        elif tl.startswith("width"):
            width = v
        elif tl.startswith("depth"):
            depth = v

    if ptype is None:
        ptype = CONDO if _CONDO_RE.search(title) else HOME
    if ptype == LAND:
        beds = baths = None
        if acres is None and width and depth:
            acres = round(width * depth / SQFT_PER_ACRE, 3)
        if sqft is None and acres:
            sqft = round(acres * SQFT_PER_ACRE)

    image = ""
    img = card.select_one("img[data-src]") or card.select_one("img[src]")
    if img is not None:
        src = (img.get("data-src") or img.get("src") or "").strip()
        if src and "loader.svg" not in src:
            image = urljoin(page_url, src)

    location = island or _clean(island_seg)
    if island and not re.search(re.escape(island), title, re.I):
        title = f"{title} ({island})"

    return Listing(
        source=SOURCE, url=url, title=title, price=price, currency=cur,
        ptype=ptype, location=location, beds=beds, baths=baths, sqft=sqft,
        acres=acres, image=image, status=status,
    )


def _enrich(l: Listing) -> bool:
    """Read ul.p-detail-list on the detail page.  False -> drop the listing."""
    soup = BeautifulSoup(get(l.url).text, "lxml")
    fields: dict[str, str] = {}
    for li in soup.select("ul.p-detail-list li"):
        label = li.select_one("span.title")
        value = li.find("p")
        if label is None or value is None:
            continue
        fields[_clean(label.get_text()).lower()] = _clean(value.get_text())

    st = fields.get("property status", "")
    if st and _status(st) is None:
        return False

    ltype = fields.get("listing type", "")
    ptype = fields.get("property type", "")
    if re.search(r"commercial|industrial|warehouse|office|retail", f"{ptype} {ltype}", re.I):
        return False
    if l.ptype != LAND and ltype:
        if re.search(r"condo|apartment|town\s*house|duplex|strata|multi", ltype, re.I):
            l.ptype = CONDO
        elif re.search(r"single\s*family|house|home|cottage", ltype, re.I):
            l.ptype = HOME
    if ptype.lower().startswith("land"):
        l.ptype = LAND
        l.beds = l.baths = None

    addr = fields.get("address", "")
    if addr:
        # Keep the island in `location`; prefix the street so both survive.
        if l.location and l.location.lower() not in addr.lower():
            l.location = f"{addr}, {l.location}"
        else:
            l.location = addr

    for key in ("acreage", "acres", "lot size", "land area"):
        if fields.get(key) and num(fields[key]):
            l.acres = num(fields[key])
            break
    if l.acres and l.sqft is None and l.ptype == LAND:
        l.sqft = round(l.acres * SQFT_PER_ACRE)

    # Facilities list is repeated on the detail page; use it to fill gaps.
    for li in soup.select("ul.list-facilites li"):
        t = _clean(li.get_text(" "))
        tl = t.lower()
        if tl.startswith("bedroom") and l.beds is None:
            l.beds = num(t)
        elif tl.startswith("bathroom") and l.baths is None:
            l.baths = num(t)
        elif tl.startswith("sq") and l.sqft is None:
            l.sqft = num(t)
        elif tl.startswith("acre") and l.acres is None:
            l.acres = num(t)
    return True


def fetch(max_pages: int = 3) -> list[Listing]:
    """Tranquil's for-sale residential + land listings on Cayman Brac and
    Little Cayman.  `max_pages` caps the /for-sale index pages read (20 cards
    each); the whole site is 2 pages.  Up to DETAIL_CAP detail pages follow."""
    listings: list[Listing] = []
    seen: set[str] = set()
    pages_read = 0

    for page in range(1, max(1, max_pages) + 1):
        url = LIST_URL + (f"?page={page}" if page > 1 else "")
        try:
            r = get(url)
        except Exception as exc:
            if page == 1:
                raise RuntimeError(f"{SOURCE}: cannot read {url}: {exc}") from exc
            break
        pages_read += 1
        soup = BeautifulSoup(r.text, "lxml")
        cards = soup.select("div.propeties-listing")
        if not cards:
            break
        before = len(seen)
        for card in cards:
            try:
                l = _parse_card(card, url)
            except Exception:
                continue
            if l and l.url and l.url not in seen:
                seen.add(l.url)
                listings.append(l)
        if len(seen) == before and page > 1:
            break          # the site serves page 1 again for out-of-range pages
        if not soup.select_one(f'a[href*="page={page + 1}"]'):
            break

    if pages_read and not seen:
        raise RuntimeError(f"{SOURCE}: {LIST_URL} returned no listing cards - layout changed?")

    keep: list[Listing] = []
    budget = DETAIL_CAP
    for l in listings:
        if budget > 0:
            budget -= 1
            try:
                if not _enrich(l):
                    continue
            except Exception:
                pass
        keep.append(l)
    return keep
