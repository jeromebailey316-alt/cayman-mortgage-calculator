"""Renders the front page body: statistics banner, featured listings, district table.

Built at publish time rather than in the browser, so the figures are in the HTML
itself — visible immediately and readable by search engines.
"""
from __future__ import annotations

import html
from urllib.parse import quote

import stats

TYPE_LABEL = {"house": "House", "condo": "Condo", "land": "Land", "other": "Property"}


def money(v: float | None, dp: int = 0) -> str:
    return "—" if v is None else "CI$" + f"{v:,.{dp}f}"


def compact(v: float | None) -> str:
    if v is None:
        return "—"
    if v >= 1_000_000:
        return "CI$" + f"{v / 1_000_000:.2f}".rstrip("0").rstrip(".") + "M"
    if v >= 1_000:
        return "CI$" + f"{v / 1_000:.0f}K"
    return money(v)


def stat_tiles(s: dict) -> str:
    # The first two lead: how much is out there, and what the middle of the market
    # costs you a month. The rest is supporting detail and is sized that way.
    tiles = [
        ("Homes for sale", f"{s['count']:,}", f"across {s['sources_ok']} agency websites", True, ""),
        ("Payment on the median home", money(s["median_home_payment"]),
         f"{compact(s['median_home'])} at {s['down_pct']}% down, {s['rate']}% over {s['term']} yrs", True, ""),
        ("Median house", compact(s["median"]["house"]),
         f"{money(s['psf']['house'])} per sq ft" if s["psf"]["house"] else "", False, ""),
        ("Median condo", compact(s["median"]["condo"]),
         f"{money(s['psf']['condo'])} per sq ft" if s["psf"]["condo"] else "", False, ""),
        ("Median land", compact(s["median"]["land"]), "lots and parcels", False, ""),
        ("Under CI$1M", f"{s['under_1m']:,}", f"{s['under_1m_pct']}% of what is listed", False, ""),
        ("First-time buyer band", f"{s['first_time_band']:,}",
         f"homes at or under {money(stats.FIRST_TIME_CAP)}, where a Caymanian first-time buyer pays no duty",
         False, first_time_link()),
        ("At the 10% duty line", f"{s['luxury_duty']:,}", "listed at CI$2M or more", False, ""),
    ]
    out = []
    for k, v, sub, lead, link in tiles:
        out.append('<div class="stat%s"><span class="k">%s</span><span class="v">%s</span>%s%s</div>'
                   % (" lead" if lead else "", html.escape(k), html.escape(v),
                      f'<span class="s">{html.escape(sub)}</span>' if sub else "", link))
    return "".join(out)


def first_time_link() -> str:
    """Opens the calculator already set to the band this tile counted: a home at the
    threshold, first-time Caymanian status, and a deposit, rate and term a buyer in
    that band would actually be quoted. `range=under` then lists everything up to it,
    so the listings shown are the ones behind the number."""
    pl = stats.FIRST_TIME_PLAN
    q = (f"price={stats.FIRST_TIME_CAP}&ptype=home&status=first"
         f"&down={pl['down_pct']}&rate={pl['rate']}&term={pl['term']}&range=under")
    return (f'<a class="stat-link" href="/calculator/?{q}#listings">View Listings'
            '<span aria-hidden="true"> →</span></a>')


def _why(l: dict, s: dict) -> str:
    """One short reason this listing is worth a look."""
    if l["ptype"] in stats.HOME_TYPES and l["price_kyd"] <= 550_000:
        return "No duty for a first-time Caymanian buyer"
    psf = s["psf"].get(l["ptype"])
    if psf and l.get("sqft") and l["sqft"] > 400:
        own = l["price_kyd"] / l["sqft"]
        if own < psf * 0.8:
            return f"{money(own)}/sq ft, below the {TYPE_LABEL[l['ptype']].lower()} median"
    return "Newly listed"


def featured_cards(data: dict, s: dict) -> str:
    cards = []
    for l in stats.featured(data):
        pay = stats.payment(l["price_kyd"] * (100 - s["down_pct"]) / 100)
        facts = []
        if l.get("beds"):
            facts.append(f"{l['beds']:g} bed")
        if l.get("baths"):
            facts.append(f"{l['baths']:g} bath")
        if l.get("sqft") and l["ptype"] != "land":
            facts.append(f"{l['sqft']:,.0f} sq ft")
        elif l.get("acres"):
            facts.append(f"{l['acres']:g} acres")
        meta = " · ".join(filter(None, [html.escape(l.get("location") or ""), " ".join(facts)]))
        cards.append(
            '<a class="feat" href="/calculator/?price={price:.0f}&ptype={pt}#listings">'
            '<span class="shot"><img src="{img}" alt="" loading="lazy" referrerpolicy="no-referrer">'
            '<span class="tag">{src}</span><span class="why">{why}</span></span>'
            '<span class="body">'
            '<span class="price">{money}</span>'
            '<span class="t">{title}</span>'
            '<span class="meta">{meta}</span>'
            '<span class="pay">About <b>{pay}</b> a month at {down}% down</span>'
            '</span></a>'.format(
                price=l["price_kyd"], pt="land" if l["ptype"] == "land" else "home",
                img=html.escape(l.get("image") or ""),
                src=html.escape((l.get("sources") or [l.get("source", "")])[0]),
                why=html.escape(_why(l, s)),
                money=money(l["price_kyd"]),
                title=html.escape(l.get("title") or TYPE_LABEL.get(l["ptype"], "Property")),
                meta=meta, pay=money(pay), down=s["down_pct"]))
    return "".join(cards)


def _cell(stat: dict) -> str:
    """Median with its sample size, because a median of three listings is not a market."""
    if not stat["n"]:
        return '<span class="none">none listed</span>'
    size = f'<span class="n">{stat["n"]}</span>'
    if stat["n"] < 5:
        return f'{money(stat["median"])} {size}<span class="thin"> few</span>'
    return f'{money(stat["median"])} {size}'


def district_rows(s: dict) -> str:
    rows = []
    for d in s["districts"]:
        rows.append(
            '<tr><th scope="row">{name}</th><td>{house}</td><td>{condo}</td><td>{land}</td>'
            '<td><a href="/calculator/?district={slug}#listings">See {count} →</a></td></tr>'.format(
                slug=quote(d["name"]), name=html.escape(d["name"]),
                house=_cell(d["house"]), condo=_cell(d["condo"]), land=_cell(d["land"]),
                count=f"{d['count']:,}"))
    return "".join(rows)


def render(data: dict, template: str) -> str:
    s = stats.summarise(data)
    return (template
            .replace("__STATS__", stat_tiles(s))
            .replace("__FEATURED__", featured_cards(data, s))
            .replace("__DISTRICTS__", district_rows(s))
            .replace("__COUNT__", f"{s['count']:,}")
            .replace("__SOURCES_OK__", str(s["sources_ok"]))
            .replace("__UPDATED__", stats.as_of(data))
            .replace("__DOWN_PCT__", str(s["down_pct"]))
            .replace("__RATE__", str(s["rate"]))
            .replace("__TERM__", str(s["term"])))
