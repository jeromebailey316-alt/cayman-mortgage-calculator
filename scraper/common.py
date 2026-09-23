"""Shared helpers for the Cayman listing scrapers.

Every source module exposes:

    SOURCE = "CIREBA"                       # display name
    def fetch(max_pages: int = 5) -> list[Listing]

and should be polite: one request at a time, via `get()` (which sleeps between
calls and sends an honest User-Agent).
"""
from __future__ import annotations

import re
import threading
import time
from urllib.parse import urlparse
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

import requests

KYD_PER_USD = 0.82
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36 CaymanMortgageCalc/1.0")
DELAY = 1.0  # seconds between requests to the same site

_session = requests.Session()
_session.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
_last: dict[str, float] = {}      # per-host time of last request
_lock = threading.Lock()


def _throttle(url: str) -> None:
    """Keep at least DELAY seconds between requests to the same host.
    Different sites can be scraped in parallel threads."""
    host = urlparse(url).netloc
    while True:
        with _lock:
            wait = DELAY - (time.time() - _last.get(host, 0.0))
            if wait <= 0:
                _last[host] = time.time()
                return
        time.sleep(wait)


RETRIES = 2  # extra attempts after a timeout, dropped connection or 5xx


def _request(method: str, url: str, **kw) -> requests.Response:
    kw.setdefault("timeout", (10, 25))
    for attempt in range(RETRIES + 1):
        _throttle(url)
        try:
            r = _session.request(method, url, **kw)
            if r.status_code >= 500 and attempt < RETRIES:
                time.sleep(3 * (attempt + 1))
                continue
            r.raise_for_status()
            return r
        except (requests.Timeout, requests.ConnectionError):
            if attempt == RETRIES:
                raise
            time.sleep(3 * (attempt + 1))
    raise RuntimeError("unreachable")


def get(url: str, **kw) -> requests.Response:
    """Rate-limited GET with a couple of retries. Raises for HTTP errors."""
    return _request("GET", url, **kw)


def post(url: str, **kw) -> requests.Response:
    return _request("POST", url, **kw)


# Property types the calculator understands.
HOME, CONDO, LAND, OTHER = "house", "condo", "land", "other"


def norm_type(text: str | None) -> str:
    t = (text or "").lower()
    if any(k in t for k in ("land", "lot", "acre", "parcel")):
        return LAND
    if any(k in t for k in ("condo", "apartment", "townhouse", "townhome", "villa", "duplex", "strata")):
        return CONDO
    if any(k in t for k in ("house", "home", "residential", "single family", "bungalow", "estate")):
        return HOME
    return OTHER


def parse_price(text) -> tuple[float | None, str]:
    """'US$1,250,000' -> (1250000.0, 'USD'); 'CI$ 500K' -> (500000.0, 'KYD')."""
    if text is None:
        return None, "USD"
    if isinstance(text, (int, float)):
        return float(text) or None, "USD"
    s = str(text)
    cur = "KYD" if re.search(r"CI\$|KYD|CI \$", s, re.I) else "USD"
    m = re.search(r"([\d][\d,]*(?:\.\d+)?)\s*(?:([kKmM])(?![A-Za-z]))?", s.replace(" ", ""))
    if not m:
        return None, cur
    v = float(m.group(1).replace(",", ""))
    if m.group(2):
        v *= 1e3 if m.group(2).lower() == "k" else 1e6
    return (v or None), cur


def num(text) -> float | None:
    if text is None:
        return None
    m = re.search(r"\d[\d,]*(?:\.\d+)?", str(text))
    return float(m.group(0).replace(",", "")) if m else None


@dataclass
class Listing:
    source: str                 # "CIREBA", "RE/MAX", ...
    url: str                    # absolute link to the listing page
    title: str
    price: float | None         # asking price in `currency`
    currency: str = "USD"       # "USD" or "KYD" as advertised
    ptype: str = OTHER          # house | condo | land | other
    location: str = ""          # district / area, e.g. "Seven Mile Beach"
    beds: float | None = None
    baths: float | None = None
    sqft: float | None = None   # interior sq ft (or lot sq ft for land)
    acres: float | None = None
    image: str = ""             # absolute URL of the main photo
    mls: str = ""               # CIREBA MLS number when shown (used to de-dupe)
    status: str = ""            # e.g. "For Sale", "Under Offer"
    scraped_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    @property
    def price_kyd(self) -> float | None:
        if self.price is None:
            return None
        return self.price if self.currency == "KYD" else round(self.price * KYD_PER_USD)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["price_kyd"] = self.price_kyd
        return d
