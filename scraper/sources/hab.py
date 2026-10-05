"""H.A. Bodden Realty (https://www.habrealtycayman.com).

A custom PHP CMS (not WingCMS), server-rendered HTML throughout, no JSON feed.
Prices are quoted in CI$ only.

Discovery uses three sources, because none of them is complete on its own:

  * /for-sale                          the live index, 6 cards, NOT paginated
                                       (`?page=2` is ignored and returns the
                                       same unfiltered set, so we read it once)
  * /residential-for-sale, /condominiums-for-sale, /residential-land-for-sale
                                       category pages, subsets of the above
  * /sitemap.xml                       ~15 detail URLs, including ones the
                                       index has dropped; most of those turn
                                       out to be "Status: Sold"

/for-rent is read as well, purely to build an exclusion set - the one rental on
the site (id 1153) sits under a /property-detail/<district>/residential-1/
path, so the URL category alone will not identify it.

Detail URL: /property-detail/<district>/<type>/<slug>/<id>.  The <district>
segment is unreliable (a Cayman Brac lot is filed under "southsound"), so
`location` comes from the card's district link and the detail page's
"Location" field instead.  The trailing numeric <id> is the site's own listing
number; there is no CIREBA MLS number anywhere on the site.  `Listing.mls` is
left empty on purpose - run.py de-dupes globally on `mls:<digits>`, so a
site-internal ID there would risk merging unrelated properties from other
sources.  The detail URL is the per-listing identity instead.

Detail pages carry `section.about-sec ul li` ("Status", "Lot Size", ...) and
`ul.fetaured_ul li` ("Land Square Footage", "Possession", ...).  Sold listings
drop the price element entirely, which is a second signal on top of the status.

ROBOTS: robots.txt disallows /upimages/ AND /cache/ - and every listing photo
is served from one of those two paths (/cache/listing/images/... on the pages
we saw).  We record the photo URL in Listing.image but NEVER request it; no
code path in this module fetches an image.  robots.txt also advertises
`Sitemap: https://www.haboddenrealty.com/sitemap.xml`, a dead domain, so we
request https://www.habrealtycayman.com/sitemap.xml directly.
Checked 5 Oct 2026.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from scraper.common import Listing, get, parse_price, num, HOME, CONDO, LAND

SOURCE = "H.A. Bodden Realty"
BASE = "https://www.habrealtycayman.com"
INDEX_URLS = [
    BASE + "/for-sale",
    BASE + "/residential-for-sale",
    BASE + "/condominiums-for-sale",
    BASE + "/residential-land-for-sale",
]
RENT_URL = BASE + "/for-rent"
SITEMAP_URL = BASE + "/sitemap.xml"
DETAIL_CAP = 40
SQFT_PER_ACRE = 43560.0
MIN_PRICE = 20_000.0          # below this it is a monthly rent, not a price

# Paths robots.txt forbids. Image URLs are recorded but never requested; this
# guard makes sure no future change starts fetching one by accident.
DISALLOWED = ("/powerpanel/", "/upimages/", "/ckeditor/", "/admin-media/",
              "/application/", "/system/", "/cache/", "/front-media/mailtemplates/",
              "/old/", "/beta/")

_CONDO_RE = re.compile(r"condo|apartment|\bapt\b|town\s*house|town\s*home|duplex|triplex|"
                       r"\bunit\b|\bsuite\b|strata|residences?\b", re.I)
_SKIP_RE = re.compile(r"for\s*rent|for\s*lease|rental|commercial|industrial|warehouse|"
                      r"office|retail|business|fractional|time\s*share", re.I)


def _clean(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _allowed(url: str) -> bool:
    path = urlparse(url).path.lower()
    return not any(path.startswith(p) for p in DISALLOWED)


def _fetch(url: str):
    """get() with a robots.txt guard, so a disallowed path can never be hit."""
    if not _allowed(url):
        raise RuntimeError(f"{SOURCE}: refusing to fetch robots-disallowed path {url}")
    return get(url)


def _url_category(url: str) -> str:
    parts = urlparse(url).path.strip("/").split("/")
    # property-detail/<district>/<type>/<slug>/<id>
    return parts[2].lower() if len(parts) >= 4 and parts[0] == "property-detail" else ""


def _status(text: str) -> str | None:
    """None -> drop the listing."""
    b = text.strip().lower()
    if not b:
        return "For Sale"
    if re.search(r"\bsold\b|\brented\b|\bleased\b|withdrawn|expired|off\s*market", b):
        return None
    if re.search(r"pending|pen\s*/\s*con|under\s*(offer|contract)", b):
        return None
    return "For Sale"          # Active / New / Reduced / ...


def _ptype(cat: str, title: str) -> str | None:
    """None -> not a residential for-sale listing we want."""
    if "commercial" in cat or "industrial" in cat:
        return None
    if _SKIP_RE.search(title):
        return None
    if "land" in cat or "lot" in cat:
        return LAND
    if "condo" in cat:
        return CONDO
    if "residential" in cat:
        return CONDO if _CONDO_RE.search(title) else HOME
    return None


def _parse_card(card, page_url: str) -> Listing | None:
    link = card.select_one(".prop_title a[href]") or card.select_one("a.thumbnail[href]")
    if not link:
        return None
    url = urljoin(page_url, link["href"].strip())
    if "/property-detail/" not in url:
        return None

    # The <h2> text is truncated with an ellipsis; the title attribute is full.
    title = _clean(link.get("title") or link.get_text())
    title = re.sub(r"\s+for sale,\s*\d+,.*$", "", title, flags=re.I)

    ptype = _ptype(_url_category(url), title)
    if ptype is None:
        return None

    label = card.select_one(".prop_label")
    status = _status(_clean(label.get_text()) if label is not None else "")
    if status is None:
        return None

    pe = card.select_one(".prop_price") or card.select_one(".price_prop_div")
    price, cur = parse_price(_clean(pe.get_text())) if pe is not None else (None, "KYD")
    if not price or price < MIN_PRICE:
        return None
    if not re.search(r"US\s*\$", _clean(pe.get_text()), re.I):
        cur = "KYD"            # H.A. Bodden quotes CI$ throughout

    district = ""
    de = card.select_one(".prop_title_div span a") or card.select_one(".prop_title_div span")
    if de is not None:
        district = _clean(de.get_text())

    beds = baths = sqft = acres = None
    for li in card.select("ul.bed_bath_info li"):
        t = _clean(li.get_text(" "))
        if not t:
            continue
        kind = (li.get("title") or "").lower()
        v = num(t)
        if "bed" in kind or re.search(r"\bbed", t, re.I):
            beds = v
        elif "bath" in kind or re.search(r"\bbath", t, re.I):
            baths = v
        elif re.search(r"acre", t, re.I):
            acres = v
        elif re.search(r"sq\s*ft|sqft", t, re.I):
            sqft = v

    if ptype == LAND:
        beds = baths = None

    image = ""
    img = card.select_one("img[src]")
    if img is not None:
        src = (img.get("src") or "").strip()
        if src and "loader" not in src.lower():
            image = urljoin(page_url, src)   # recorded only - never fetched

    return Listing(
        source=SOURCE, url=url, title=title, price=price, currency=cur,
        ptype=ptype, location=district, beds=beds, baths=baths, sqft=sqft,
        acres=acres, image=image, status=status,
    )


def _detail_fields(soup) -> dict[str, str]:
    fields: dict[str, str] = {}
    for li in soup.select("section.about-sec ul li, ul.fetaured_ul li"):
        t = _clean(li.get_text(" "))
        if ":" not in t or len(t) > 200:
            continue
        label, _, value = t.partition(":")
        label, value = label.strip().lower(), value.strip()
        if label and value and len(label) < 40:
            fields.setdefault(label, value)
    return fields


def _parse_detail(url: str, base: Listing | None = None) -> Listing | None:
    soup = BeautifulSoup(_fetch(url).text, "lxml")
    fields = _detail_fields(soup)

    status = _status(fields.get("status", ""))
    if status is None:
        return None

    h = soup.select_one("h2.main_title") or soup.select_one("h1")
    title = _clean(h.get_text()) if h is not None else (base.title if base else "")
    cat = _url_category(url)
    ptype = _ptype(cat, title) or (base.ptype if base else None)
    if ptype is None:
        return None
    if base is None and _SKIP_RE.search(title):
        return None

    pe = soup.select_one(".price_prop_div") or soup.select_one(".prop_price")
    price, cur = parse_price(_clean(pe.get_text())) if pe is not None else (None, "KYD")
    if not re.search(r"US\s*\$", _clean(pe.get_text()) if pe is not None else "", re.I):
        cur = "KYD"
    if (not price or price < MIN_PRICE) and base is not None:
        price, cur = base.price, base.currency
    if not price or price < MIN_PRICE:
        return None            # sold listings drop the price element

    l = base or Listing(source=SOURCE, url=url, title=title, price=price,
                        currency=cur, ptype=ptype)
    l.title = title or l.title
    l.price, l.currency, l.ptype, l.status = price, cur, ptype, status

    loc = fields.get("location") or fields.get("address") or ""
    if loc and len(loc) < 120:
        l.location = f"{loc}, {l.location}" if l.location and l.location.lower() not in loc.lower() else (loc or l.location)

    for key in ("lot size", "acreage", "acres", "land area"):
        if fields.get(key) and num(fields[key]):
            l.acres = num(fields[key])
            break
    for key in ("square footage", "living square footage", "total square footage", "sq ft", "area"):
        if fields.get(key) and num(fields[key]):
            l.sqft = num(fields[key])
            break
    if l.sqft is None and l.ptype == LAND:
        lsf = fields.get("land square footage")
        if lsf and num(lsf):
            l.sqft = num(lsf)
            if l.acres is None:
                l.acres = round(num(lsf) / SQFT_PER_ACRE, 3)

    for li in soup.select("ul.bed_bath_info li"):
        t = _clean(li.get_text(" "))
        kind = (li.get("title") or "").lower()
        if not t:
            continue
        if ("bed" in kind or re.search(r"\bbed", t, re.I)) and l.beds is None:
            l.beds = num(t)
        elif ("bath" in kind or re.search(r"\bbath", t, re.I)) and l.baths is None:
            l.baths = num(t)
        elif re.search(r"acre", t, re.I) and l.acres is None:
            l.acres = num(t)
        elif re.search(r"sq\s*ft|sqft", t, re.I) and l.sqft is None:
            l.sqft = num(t)

    if l.ptype == LAND:
        l.beds = l.baths = None
        if l.acres is None:
            # Several lots only state the acreage in the title.
            m = re.search(r"(\d+(?:\.\d+)?)\s*(?:\+\s*)?acres?\b", l.title, re.I)
            if m:
                l.acres = float(m.group(1))
        if l.sqft is None and l.acres:
            l.sqft = round(l.acres * SQFT_PER_ACRE)
    if not l.image:
        og = soup.select_one("meta[property='og:image']")
        if og is not None and og.get("content"):
            l.image = urljoin(url, og["content"])   # recorded only - never fetched
    return l


def _index_cards(url: str) -> list[Listing]:
    soup = BeautifulSoup(_fetch(url).text, "lxml")
    out = []
    for card in soup.select("div.pro_wrap"):
        try:
            l = _parse_card(card, url)
        except Exception:
            continue
        if l and l.url:
            out.append(l)
    return out


def _rental_urls() -> set[str]:
    try:
        soup = BeautifulSoup(_fetch(RENT_URL).text, "lxml")
    except Exception:
        return set()
    return {urljoin(RENT_URL, a["href"].strip())
            for a in soup.select("div.pro_wrap a[href*='/property-detail/']")}


def _sitemap_urls() -> list[str]:
    try:
        xml = _fetch(SITEMAP_URL).text
    except Exception:
        return []
    return [u for u in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)
            if "/property-detail/" in u]


def fetch(max_pages: int = 1) -> list[Listing]:
    """H.A. Bodden's for-sale residential + land listings.

    /for-sale is not paginated, so `max_pages` only gates how much discovery we
    do: 1 reads /for-sale, >=2 adds the three category pages, >=3 also walks
    /sitemap.xml for detail URLs the index has dropped (most are sold, and the
    detail pages tell us so).  Detail fetches are capped at DETAIL_CAP."""
    pages = max(1, max_pages)
    listings: list[Listing] = []
    seen: set[str] = set()

    try:
        first = _index_cards(INDEX_URLS[0])
    except Exception as exc:
        raise RuntimeError(f"{SOURCE}: cannot read {INDEX_URLS[0]}: {exc}") from exc
    if not first:
        raise RuntimeError(f"{SOURCE}: {INDEX_URLS[0]} returned no listing cards "
                           f"- layout changed or listings withdrawn?")

    rentals = _rental_urls()
    for l in first:
        if l.url not in seen and l.url not in rentals:
            seen.add(l.url)
            listings.append(l)

    if pages >= 2:
        for url in INDEX_URLS[1:]:
            try:
                extra = _index_cards(url)
            except Exception:
                continue
            for l in extra:
                if l.url not in seen and l.url not in rentals:
                    seen.add(l.url)
                    listings.append(l)

    budget = DETAIL_CAP
    keep: list[Listing] = []
    for l in listings:
        if budget > 0:
            budget -= 1
            try:
                enriched = _parse_detail(l.url, l)
            except Exception:
                keep.append(l)
                continue
            if enriched is None:
                continue
            keep.append(enriched)
        else:
            keep.append(l)

    if pages >= 3:
        for url in _sitemap_urls():
            if budget <= 0:
                break
            if url in seen or url in rentals:
                continue
            seen.add(url)
            budget -= 1
            try:
                l = _parse_detail(url)
            except Exception:
                continue
            if l is not None:
                keep.append(l)

    return keep
