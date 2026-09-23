"""Property Cayman (propertycayman.com) scraper.

WordPress with a custom theme; listings are not in /wp-json/.  The /buy/ search
page loads results through admin-ajax (allowed by robots.txt):

    GET /wp-admin/admin-ajax.php?action=load_properties
        &filters[type]=properties&filters[page_path]=buy
        &filters[property_type]=Condo,House,Semi-detached,Land
        &filters[current_page]=N
    -> JSON {"properties": <card HTML>, "pagination": <html>, ...}

That search is the whole CIREBA MLS/LDX feed (~900+ residential listings,
11 per page; other brokers' listings say "LDX feed courtesy of ..." on
their detail pages).  The agency's own listings are shown on each agent's
profile page (/about/<agent>/), linked from /about/.

Default (own_only=True): scrape /about/ + every agent page (currently 18)
and de-dupe co-listed properties.  own_only=False: page through the full feed
via load_properties, up to `max_pages` pages.

Cards carry price with "CI$"/"US$", name, "<Type> [with a ... View] in
<District>", beds, baths, sqft or acres, MLS number, and a status label
("New", "Pending/Conditional", "Sold - 05/24").  The URL path
/buy/<house|condo|semi-detached|land|commercial>/... gives the type.
"""
from __future__ import annotations

import json
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from scraper.common import Listing, get, num, norm_type, HOME, CONDO, LAND

SOURCE = "Property Cayman"
BASE = "https://propertycayman.com"
AJAX = f"{BASE}/wp-admin/admin-ajax.php"
MAX_AGENT_PAGES = 30
SQFT_PER_ACRE = 43560.0
TYPE_MAP = {"house": HOME, "condo": CONDO, "semi-detached": CONDO, "land": LAND}


def _price(txt: str) -> tuple[float | None, str]:
    txt = " ".join((txt or "").split())
    cur = "KYD" if re.search(r"CI\s*\$|KYD", txt, re.I) else "USD"
    m = re.search(r"\d[\d,]*(?:\.\d+)?", txt)
    price = float(m.group(0).replace(",", "")) if m else None
    return (price or None), cur


def _parse_cards(html: str) -> list[Listing]:
    soup = BeautifulSoup(html, "lxml")
    out: list[Listing] = []
    for card in soup.select(".property-card"):
        try:
            a = card.select_one("a.text-holder[href]") or card.select_one("a[href*='/buy/']")
            if not a:
                continue
            url = urljoin(BASE, a["href"].split("#")[0].strip())
            path = urlsplit(url).path.strip("/").split("/")
            if len(path) < 3 or path[0] != "buy":
                continue
            ptype = TYPE_MAP.get(path[1].lower())
            if ptype is None:
                continue  # commercial, rentals, developments, ...

            label = card.select_one(".card-label")
            label = label.get_text(" ", strip=True) if label else ""
            if re.search(r"\bsold\b", label, re.I):
                continue

            pr = card.select_one(".price")
            price, cur = _price(pr.get_text(" ") if pr else "")
            if not price:
                continue

            name = card.select_one(".name")
            title = name.get_text(" ", strip=True) if name else ""
            desc = card.select_one(".description p")
            desc = desc.get_text(" ", strip=True) if desc else ""
            m = re.search(r".*\b(?:in|on)\s+(?:the\s+)?(.+)$", desc)
            location = m.group(1).strip() if m else ""

            beds = baths = sqft = acres = None
            mls = ""
            for li in card.select("ul.detail-list li"):
                icon = li.select_one(".icon")
                cls = " ".join(icon.get("class", [])) if icon else ""
                txt = li.get_text(" ", strip=True)
                if "MLS" in txt:
                    mm = re.search(r"MLS\s*#?:?\s*(\d+)", txt)
                    mls = mm.group(1) if mm else ""
                elif "icon-bed" in cls:
                    beds = num(txt)
                elif "icon-tub" in cls or "bath" in cls:
                    baths = num(txt)
                elif re.search(r"\bacr", txt, re.I):
                    acres = num(txt)
                elif re.search(r"sq\s*ft", txt, re.I):
                    sqft = num(txt)
            if acres is None:
                mm = re.search(r"(\d+(?:\.\d+)?)\s*acres?\b", title, re.I)
                if mm:
                    acres = float(mm.group(1))
            if ptype == LAND and sqft is None and acres:
                sqft = round(acres * SQFT_PER_ACRE)

            img = ""
            im = card.select_one(".image-holder img")
            if im:
                img = im.get("data-src") or im.get("src") or ""

            out.append(Listing(
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
                image=urljoin(BASE, img) if img else "",
                mls=mls,
                status=label if re.search(r"pending|offer|conditional|contract", label, re.I) else "For Sale",
            ))
        except Exception:
            continue
    return out


def _fetch_own() -> list[Listing]:
    try:
        about = get(f"{BASE}/about/").text
    except Exception as e:
        raise RuntimeError(f"Property Cayman: could not load /about/: {e}") from e
    agents = list(dict.fromkeys(
        re.findall(r"https://(?:www\.)?propertycayman\.com/about/[a-z0-9-]+/", about)))
    if not agents:
        raise RuntimeError("Property Cayman: no agent pages found on /about/ (layout changed?)")
    out: list[Listing] = []
    for u in agents[:MAX_AGENT_PAGES]:
        try:
            out.extend(_parse_cards(get(u).text))
        except Exception:
            continue
    return out


def _fetch_feed(max_pages: int) -> list[Listing]:
    out: list[Listing] = []
    for page in range(1, max_pages + 1):
        params = {
            "action": "load_properties",
            "filters[type]": "properties",
            "filters[page_path]": "buy",
            "filters[property_type]": "Condo,House,Semi-detached,Land",
            "filters[sort]": "most-recent",
            "filters[current_page]": page,
        }
        try:
            data = json.loads(get(AJAX, params=params).text)
        except Exception as e:
            if page == 1:
                raise RuntimeError(f"Property Cayman: load_properties failed: {e}") from e
            break
        cards = _parse_cards(data.get("properties") or "")
        out.extend(cards)
        if not data.get("properties") or f'data-page="{page + 1}"' not in (data.get("pagination") or ""):
            break
    return out


def fetch(max_pages: int = 5, own_only: bool = True) -> list[Listing]:
    """own_only=True (default): Property Cayman's own listings from its agent
    pages (one request per agent, `max_pages` not used).  own_only=False: the
    full MLS feed, `max_pages` pages of 11 listings."""
    raw = _fetch_own() if own_only else _fetch_feed(max_pages)
    results: list[Listing] = []
    seen: set[str] = set()
    for l in raw:
        key = l.mls or l.url
        if key in seen:
            continue
        seen.add(key)
        results.append(l)
    return results
