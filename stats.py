"""Market figures for the front page, worked out from the listings we already hold.

Everything here is derived from data/listings.json, so the banner is as current as
the last scrape. Nothing is hand-typed, and nothing claims to be a sold-price index:
these are asking prices for what is on the market right now.
"""
from __future__ import annotations

import statistics
import re
from datetime import datetime, timezone

# The planning defaults the calculator itself opens with, used for the "payment on
# the median home" figure so the banner and the calculator agree.
DOWN_PCT, RATE, TERM_YEARS = 15, 7.25, 25

HOME_TYPES = ("house", "condo")


def _median(values) -> float | None:
    vals = [v for v in values if v]
    return statistics.median(vals) if vals else None


def payment(loan: float, annual_rate: float = RATE, years: int = TERM_YEARS) -> float:
    r, n = annual_rate / 100 / 12, years * 12
    return loan * r / (1 - (1 + r) ** -n) if r else loan / n


def summarise(data: dict) -> dict:
    ls = [l for l in data.get("listings", []) if l.get("price_kyd")]
    homes = [l for l in ls if l["ptype"] in HOME_TYPES]

    def med_price(t):
        return _median([l["price_kyd"] for l in ls if l["ptype"] == t])

    def med_psf(t):
        return _median([l["price_kyd"] / l["sqft"] for l in ls
                        if l["ptype"] == t and l.get("sqft") and l["sqft"] > 200])

    med_home = _median([l["price_kyd"] for l in homes])
    out = {
        "count": len(ls),
        "generated_at": data.get("generated_at"),
        "sources_ok": sum(1 for s in data.get("sources", []) if s.get("ok")),
        "sources_total": len(data.get("sources", [])),
        "median": {t: med_price(t) for t in ("house", "condo", "land")},
        "psf": {t: med_psf(t) for t in HOME_TYPES},
        "under_1m": sum(1 for l in ls if l["price_kyd"] < 1_000_000),
        "luxury_duty": sum(1 for l in ls if l["price_kyd"] >= 2_000_000),
        "first_time_band": sum(1 for l in homes if l["price_kyd"] <= 550_000),
        "median_home": med_home,
        "median_home_payment": payment(med_home * (100 - DOWN_PCT) / 100) if med_home else None,
        "down_pct": DOWN_PCT, "rate": RATE, "term": TERM_YEARS,
    }
    out["under_1m_pct"] = round(out["under_1m"] / len(ls) * 100) if ls else 0

    # by district, using the same grouping the listings filter uses
    districts: dict[str, list] = {}
    for l in ls:
        districts.setdefault(district_of(l.get("location", "")), []).append(l)
    out["districts"] = sorted(
        ({"name": d,
          "count": len(v),
          "median": _median([x["price_kyd"] for x in v]),
          "homes": sum(1 for x in v if x["ptype"] in HOME_TYPES),
          "land": sum(1 for x in v if x["ptype"] == "land")}
         for d, v in districts.items() if d != "Elsewhere"),
        key=lambda d: -d["count"])
    return out


DISTRICT_RULES = [
    ("Little Cayman", ("little cayman",)),
    ("Cayman Brac", ("cayman brac", "brac")),
    ("Seven Mile Beach", ("seven mile", "w bay bch", "w bay beach", "west bay beach", "governor")),
    ("West Bay", ("west bay", "w bay")),
    ("George Town", ("george town", "south sound", "prospect", "spotts", "red bay")),
    ("Bodden Town", ("bodden town", "savannah", "lower valley", "newlands", "breakers", "midland", "pedro")),
    ("East End", ("east end", "high rock", "colliers", "east interior", "n.e. coast", "north east coast")),
    ("North Side", ("north side", "northside", "rum point", "cayman kai", "kaibo")),
]


def district_of(area: str) -> str:
    a = (area or "").lower()
    for name, needles in DISTRICT_RULES:
        if any(n in a for n in needles):
            return name
    return "Elsewhere"


# Investment stock reads badly on a front page aimed at buyers, and its price per
# square foot makes the "below the median" line meaningless.
NOT_A_HOME = re.compile(
    r"four[- ]?plex|tri[- ]?plex|multi[- ]?unit|multi[- ]?family|apartment building|"
    r"commercial|income[- ]?producing|\broi\b|zoning|development site|投资", re.I)


def featured(data: dict, n: int = 6) -> list[dict]:
    """A mixed half-dozen: the newest listings, plus the best value per square foot,
    never two from the same area, and nothing without a photo."""
    ls = [l for l in data.get("listings", [])
          if l.get("price_kyd") and l.get("image") and not NOT_A_HOME.search(l.get("title") or "")]
    picked, seen_areas, seen_urls = [], set(), set()

    def take(candidates):
        for l in candidates:
            if len(picked) >= n:
                return
            area = l.get("location", "")
            if l["url"] in seen_urls or (area and area in seen_areas):
                continue
            picked.append(l)
            seen_urls.add(l["url"])
            if area:
                seen_areas.add(area)

    homes = [l for l in ls if l["ptype"] in HOME_TYPES]
    value = sorted((l for l in homes if l.get("sqft") and l["sqft"] > 400),
                   key=lambda l: l["price_kyd"] / l["sqft"])
    newest = sorted(ls, key=lambda l: l.get("scraped_at") or "", reverse=True)
    affordable = sorted((l for l in homes if l["price_kyd"] <= 550_000),
                        key=lambda l: l["price_kyd"])

    take(value[:12])          # best value per sq ft
    take(affordable[:12])     # within the first-time buyer band
    take(newest[:40])         # and whatever came in most recently
    take(ls)                  # backstop
    return picked[:n]


def as_of(data: dict) -> str:
    try:
        t = datetime.fromisoformat(data["generated_at"]).astimezone(timezone.utc)
        return t.strftime("%-d %B %Y, %H:%M UTC")
    except Exception:
        return ""
