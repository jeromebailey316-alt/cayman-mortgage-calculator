"""Paradise Realty & Property Management, Cayman Brac (paradiserealtycyb.com).

A hand-built Wix site (not a Wix CMS collection, not Wix Stores), so there is
no JSON feed: `wix-warmup-data` on these pages holds only component metadata.
Everything is rendered server-side as text, which is all we need -- one GET of
the list page carries every listing in full:

    /property-for-sale-1   ("Cayman Brac Listings")   ~17 cards

Each card's facts live in a single rich-text component shaped like

    Cayman Brac West Bluff, Cayman Brac
    96E381 | Inland Lot | 0.36 of an Acre
    $59,000.00 CI

i.e. location, block & parcel, lot kind, acreage and the CI$ price. Detail
pages add nothing: /96e381 restates the same figures plus "Block & Parcel:-
96E381", so we never fetch them.

Layout caveat: the page is absolutely positioned, so there is no per-card
container to parse. The newer rows wrap each card in its own component, the two
oldest 3-up rows do not -- their info blocks and their buttons are flat
siblings in document order (3 info blocks, then 3 "ARRANGE A VIEWING" /
"MORE INFORMATION" pairs). We therefore walk the document in order and pair the
Nth pending info block with the Nth "MORE INFORMATION" link, which holds for
both layouts.

Detail URLs are the parcel code -- /96e381, or /copy-of-96e239 where the agent
duplicated a page -- so the code is the natural de-duplication key and goes in
`mls` (the site shows no CIREBA MLS numbers). Cards whose "MORE INFORMATION"
button still points at the home page have no detail URL and are skipped.

Status: the site keeps sold and under-offer stock on the page, flagged only by
a free-standing "UNDER CONTRACT" / "SOLD" badge component that cannot be tied
to a card by DOM position. So we cross-check parcel codes against the separate
/sold-properties page (one extra GET, best-effort) and drop any match.

Everything here is Cayman Brac, so `location` is always suffixed with the
island -- downstream stamp-duty code needs the island, and the Brac has its own
rates. Prices are quoted in CI$ (KYD). Stock is land/lots only in practice.

robots.txt: "Allow: /", with Crawl-delay only for dotbot and AhrefsBot and
"Disallow: *?lightbox=" (we never request those). common.py still throttles
this host to 10s between requests, so a run takes ~20 seconds.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from scraper.common import Listing, get, num, norm_type, LAND

SOURCE = "Paradise Realty Brac"
BASE = "https://www.paradiserealtycyb.com"
LIST_URL = BASE + "/property-for-sale-1"
SOLD_URL = BASE + "/sold-properties"
ISLAND = "Cayman Brac"

# "96E381", "102A379", "99A135": block letter-and-number, then the parcel.
CODE = re.compile(r"\b(\d{2,3}[A-Z]\d{1,4})\b")
PRICE = re.compile(r"\$\s*[\d,]+(?:\.\d+)?\s*CI\b", re.I)
ACRES = re.compile(r"(\d+(?:\.\d+)?)\s*(?:of\s+an?\s+)?acres?\b", re.I)
SOLD_WORDS = re.compile(r"\bsold\b|\bunder\s+(contract|offer)\b|\bpending\b", re.I)


def _clean(s: str | None) -> str:
    return re.sub(r"[\s​\xa0]+", " ", s or "").strip()


def _code(text: str | None) -> str:
    m = CODE.search((text or "").upper())
    return m.group(1) if m else ""


def _full_image(src: str) -> str:
    """Wix serves a blurred lazy-load thumbnail in the markup
    (".../<id>~mv2.png/v1/fill/w_69,h_48,...,blur_2/<id>~mv2.png").
    Keep just the media id, which is the full-size original."""
    if not src:
        return ""
    src = urljoin(BASE, src)
    m = re.match(r"(https://static\.wixstatic\.com/media/[^/]+)", src)
    return m.group(1) if m else src


def _code_from_url(url: str) -> str:
    """/96e381 and /copy-of-96e239 -> "96E381" / "96E239"."""
    slug = urlparse(url).path.strip("/")
    slug = re.sub(r"^(?:copy-of-)+", "", slug, flags=re.I)
    return _code(slug)


def _is_info_block(text: str) -> bool:
    """A card's facts component: a CI$ price plus an acreage on its own lines."""
    return bool(PRICE.search(text) and ACRES.search(text) and len(text) < 400)


def _sold_codes() -> set[str]:
    """Parcel codes shown on /sold-properties. Best-effort: an error here just
    means we fall back to the for-sale page's own badges."""
    try:
        soup = BeautifulSoup(get(SOLD_URL).text, "lxml")
    except Exception as e:
        print(f"[{SOURCE}] sold-properties unavailable, skipping cross-check: {e}")
        return set()
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    return {m.group(1) for m in CODE.finditer(_clean(soup.get_text(" ")).upper())}


def _parse_info(text: str) -> dict:
    """Pull location / code / lot kind / acres / price out of a facts block."""
    lines = [_clean(l) for l in text.split("\n")]
    lines = [l for l in lines if l]

    price_line = next((l for l in lines if PRICE.search(l)), "")
    # The price sits on its own line; the line above it carries code | kind | acres.
    fact_line = next((l for l in lines if ACRES.search(l) and not PRICE.search(l)), "")
    if not fact_line and price_line:
        fact_line = price_line
    # Location is the first line that is neither the price nor the facts line.
    location = next((l for l in lines if l not in (price_line, fact_line)), "")

    acres = None
    m = ACRES.search(fact_line) or ACRES.search(text)
    if m:
        acres = float(m.group(1))

    # "Inland Lot", "Corner Lot", ... -> the lot kind, used for ptype.
    kind = ""
    for part in fact_line.split("|"):
        part = _clean(part)
        if re.search(r"\blot\b|\bland\b|\bhouse\b|\bhome\b|\bcondo\b", part, re.I):
            kind = part
            break

    return {
        "location": location,
        "code": _code(fact_line),
        "kind": kind,
        "acres": acres,
        "price_text": _clean(price_line) or _clean(text),
    }


def _price_kyd(text: str) -> float | None:
    """"$59,000.00 CI" -> 59000.0. Prices on this site are always CI$."""
    m = PRICE.search(text)
    return num(m.group(0)) if m else None


def fetch(max_pages: int = 1) -> list[Listing]:
    """Every Paradise Realty Cayman Brac listing.

    The site has no pagination -- all stock is on /property-for-sale-1 -- so
    `max_pages` is accepted for interface compatibility and ignored beyond
    deciding whether to run at all. Costs 2 requests (list + sold cross-check).
    """
    if max_pages < 1:
        return []

    soup = BeautifulSoup(get(LIST_URL).text, "lxml")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()

    # Candidate facts components, in document order. The rows that wrap a card
    # in its own component match too (a wrapper holds exactly one price), so
    # keep only the innermost matches -- a wrapper always contains the real
    # facts block, never the other way round.
    candidates = [el for el in soup.find_all(["div", "p", "section"])
                  if str(el.get("id") or "").startswith("comp-")
                  and _is_info_block(el.get_text("\n"))]
    inner = [el for el in candidates
             if not any(other is not el and other in el.descendants for other in candidates)]
    blocks = {id(el): _parse_info(el.get_text("\n")) for el in inner}

    # Walk the page in document order, pairing each facts block with the
    # "MORE INFORMATION" link that follows it (see module docstring).
    pending: list[dict] = []
    cards: list[tuple[dict, str]] = []

    for el in soup.find_all(["div", "p", "section", "a"]):
        if el.name == "a":
            if not re.search(r"MORE\s+INFORMATION", el.get_text(" "), re.I):
                continue
            if pending:
                cards.append((pending.pop(0), el.get("href") or ""))
            continue
        info = blocks.get(id(el))
        if info is not None:
            pending.append(info)

    # Image per parcel code, from the gallery <img alt="96E381"> tags.
    images: dict[str, str] = {}
    for img in soup.select("img[src]"):
        code = _code(img.get("alt"))
        if code and code not in images:
            images[code] = _full_image(img["src"])

    # Only worth the second request if we actually found something to check.
    sold = _sold_codes() if cards else set()

    out: list[Listing] = []
    seen: set[str] = set()
    for info, href in cards:
        try:
            url = urljoin(BASE, href)
            # Cards still wired to the home page have no detail page yet.
            if not urlparse(url).path.strip("/"):
                continue

            code = info["code"] or _code_from_url(url)
            if code and code in sold:
                continue

            price = _price_kyd(info["price_text"])
            if not price:
                continue

            # The parcel code de-dupes the agent's duplicated pages
            # (/96e239 and /copy-of-96e239 are the same lot).
            key = code or url
            if key in seen:
                continue
            seen.add(key)

            location = info["location"]
            if ISLAND.lower() not in location.lower():
                location = f"{location}, {ISLAND}".strip(", ")

            title = " - ".join(p for p in (code, info["kind"] or "Land", location) if p)

            out.append(Listing(
                source=SOURCE,
                url=url,
                title=title,
                price=price,
                currency="KYD",
                ptype=norm_type(info["kind"]) if info["kind"] else LAND,
                location=location,
                beds=None,
                baths=None,
                sqft=None,
                acres=info["acres"],
                image=images.get(code, ""),
                mls=code,
                status="For Sale",
            ))
        except Exception as e:
            print(f"[{SOURCE}] card parse error: {e}")
            continue

    return out
