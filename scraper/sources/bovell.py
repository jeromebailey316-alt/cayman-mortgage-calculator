"""Bovell team at RE/MAX Cayman Islands (www.bovell.ky) scraper.

bovell.ky is a WordPress site running a clone of the remax.ky listings theme.
Its "properties for sale" archive shows the *whole RE/MAX Cayman office
inventory* (~317 listings, same as remax.ky -- not the full CIREBA MLS), but
the default sort puts listings assigned to a Bovell-site agent (James Bovell,
Samiran Saha, Mabel McMillan, ...) first; those cards show an agent block,
the rest of the office's listings don't.  We keep only the agent-assigned
("team") listings and stop paging at the first card without an agent.

    list view  /cayman-island-properties-for-sale/[page/N/]?type=Home
               10 cards/page: price+currency, title, beds, baths, sqft, image,
               status badge ("New", "Pending/Conditional"), agent name.
    map JSON   same URL + &show-map=1&ajax=1 -> {"listings": [...], "html"}
               12/page in the same order; adds `location` (district).
    detail     /cayman-island-properties-for-sale/<slug>/ -> "MLS: 421137"
               (the only place the CIREBA MLS number appears; capped at 40).

Rentals only appear with `lease=1`, so the default archive is for sale.  We
query per type (Home, Condominium, Land); Commercial / Business / Multi-Unit
are skipped.  robots.txt allows everything.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from scraper.common import Listing, get, num, HOME, CONDO, LAND

SOURCE = "Bovell RE/MAX"
BASE = "https://www.bovell.ky"
ARCHIVE = "/cayman-island-properties-for-sale/"
TYPES = [("Home", HOME), ("Condominium", CONDO), ("Land", LAND)]
SQFT_PER_ACRE = 43560.0
MAX_DETAIL = 40


def _clean_url(u: str) -> str:
    p = urlsplit(urljoin(BASE, (u or "").strip()))
    return urlunsplit((p.scheme, p.netloc, p.path, "", ""))


def _page_url(type_name: str, page: int, ajax: bool = False) -> str:
    path = ARCHIVE if page == 1 else f"{ARCHIVE}page/{page}/"
    q = f"?type={type_name}" + ("&show-map=1&ajax=1" if ajax else "")
    return BASE + path + q


def _price(txt: str) -> tuple[float | None, str]:
    # Strip the currency code before parsing ("KYD" would read as a K suffix).
    cur = "KYD" if re.search(r"KYD|CI\s*\$|\bCI\b", txt or "", re.I) else "USD"
    m = re.search(r"\d[\d,]*(?:\.\d+)?", txt or "")
    v = float(m.group(0).replace(",", "")) if m else None
    return (v or None), cur


def _acres(title: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*[- ]?\s*(?:acres?|ac)\b", title or "", re.I)
    return float(m.group(1)) if m else None


def _list_cards(html: str) -> list[dict]:
    """Parse list-view cards in page order; `agent` is '' for non-team cards."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for c in soup.select("div.overflow-hidden.rounded-lg.bg-white.flex"):
        try:
            links = [a for a in c.select("a[href]") if ARCHIVE in a["href"]]
            if not links:
                continue
            d: dict = {"url": _clean_url(links[0]["href"])}
            t = next((a for a in links if a.get_text(strip=True)), None)
            d["title"] = t.get_text(" ", strip=True) if t else ""
            pr = c.select_one("p.text-sm.font-semibold")
            d["price_txt"] = pr.get_text(" ", strip=True) if pr else ""
            ag = c.select_one("strong")
            d["agent"] = ag.get_text(strip=True) if ag else ""
            badge = c.select_one("p.rounded-md")
            d["badge"] = badge.get_text(" ", strip=True) if badge else ""
            for pill in c.select("div.inline-flex"):
                icon = pill.select_one("img[src]")
                val = pill.select_one("span")
                if not icon or not val:
                    continue
                for k in ("bed", "bath", "sqft"):
                    if f"/{k}.svg" in icon["src"]:
                        d[k] = num(val.get_text())
            img = c.select_one("img.object-cover[src]")
            if img:
                d["img"] = urljoin(BASE, img["src"].strip())
            out.append(d)
        except Exception:
            continue
    return out


def _locations(type_name: str, pages: int) -> dict[str, str]:
    """URL -> district from the map-view JSON (12 per page, same order)."""
    locs: dict[str, str] = {}
    for page in range(1, pages + 1):
        try:
            data = get(_page_url(type_name, page, ajax=True),
                       headers={"Accept": "application/json"}).json()
        except Exception:
            break
        items = data.get("listings") or []
        if not items:
            break
        for it in items:
            try:
                locs[_clean_url(it.get("link", ""))] = BeautifulSoup(
                    it.get("location") or "", "lxml").get_text(" ", strip=True)
            except Exception:
                continue
    return locs


def _mls(url: str) -> str:
    try:
        m = re.search(r"MLS:?\s*#?\s*(\d{4,})", get(url).text)
        return m.group(1) if m else ""
    except Exception:
        return ""


def fetch(max_pages: int = 5) -> list[Listing]:
    """Fetch the Bovell team's for-sale listings. `max_pages` caps the list
    pages *per property type* (10 listings each); paging stops as soon as the
    team listings run out (usually 1-4 pages per type)."""
    results: list[Listing] = []
    seen: set[str] = set()
    details = 0

    for type_name, ptype in TYPES:
        team: list[dict] = []
        for page in range(1, max_pages + 1):
            try:
                html = get(_page_url(type_name, page)).text
            except Exception:
                break  # 404 past the last page
            cards = _list_cards(html)
            if not cards:
                break
            team += [c for c in cards if c.get("agent")]
            if any(not c.get("agent") for c in cards):
                break  # reached the rest of the RE/MAX office inventory
            if f"{ARCHIVE}page/{page + 1}/" not in html:
                break
        if not team:
            continue

        locs = _locations(type_name, -(-len(team) // 12))  # ceil(n/12) map pages

        for c in team:
            try:
                url = c["url"]
                if url in seen or url.rstrip("/").endswith(ARCHIVE.rstrip("/")):
                    continue
                price, cur = _price(c.get("price_txt", ""))
                badge = c.get("badge", "")
                if not price or re.search(r"\bsold\b|\blease|rent", badge, re.I):
                    continue
                status = badge if re.search(r"pending|conditional|offer", badge, re.I) else "For Sale"
                title = c.get("title", "")
                sqft = c.get("sqft")
                acres = _acres(title)
                if ptype == LAND and acres is None and sqft:
                    acres = round(sqft / SQFT_PER_ACRE, 3)
                mls = ""
                if details < MAX_DETAIL:
                    details += 1
                    mls = _mls(url)
                results.append(Listing(
                    source=SOURCE,
                    url=url,
                    title=title,
                    price=price,
                    currency=cur,
                    ptype=ptype,
                    location=locs.get(url, ""),
                    beds=c.get("bed"),
                    baths=c.get("bath"),
                    sqft=sqft,
                    acres=acres,
                    image=c.get("img", ""),
                    mls=mls,
                    status=status,
                ))
                seen.add(url)
            except Exception:
                continue
    return results
