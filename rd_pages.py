"""Redesigned pages, ported from the boards in cmc-redesign/pages/.

Each function takes the scraped data and returns a page body. The boards carry
their layout as inline styles; HANDOFF section 4 says those may move into
stylesheets as long as the result is visually identical, so the repeating
helpers live in web/rd.css and the one-off layout stays inline here, which keeps
each section recognisably the board it came from.
"""
from __future__ import annotations

import redesign as rd
from redesign import e, icon, button, listing_card, fmt_money

# The planning figures the boards quote. One place so they stay in step.
RATE = 7.75
TERM = 25
DEPOSIT_PCT = 10
PRIME_NOTE = ("KYD prime is 7.00%, raised from 6.75% on 18 September 2026 "
              "(Cayman National notice, checked 1 October 2026). A primary residence "
              "usually prices at prime plus 0.5-1%, so 7.75% is a planning figure, "
              "not a quote. Enter the rate your bank quoted.")


def payment(principal: float, annual_rate: float = RATE, years: int = TERM) -> float:
    r = annual_rate / 100 / 12
    n = years * 12
    return principal * r / (1 - (1 + r) ** -n) if r else principal / n


TAKEN = __import__("re").compile(r"under offer|pending|conditional|sold|contract", __import__("re").I)


def _agency_of(l: dict) -> str:
    return (l.get("sources") or [l.get("source")])[0] or ""


def _day_index(data: dict) -> int:
    """Days since the epoch, from the scrape date so a rebuild on the same day
    picks the same listings. Four builds a day must not reshuffle the page."""
    from datetime import date, datetime, timezone
    stamp = (data.get("generated_at") or "")[:10]
    try:
        d = date.fromisoformat(stamp)
    except ValueError:
        d = datetime.now(timezone.utc).date()
    return d.toordinal()


def _featured(data: dict, n: int = 4) -> list[dict]:
    """Four listings a day, from four different agencies, rotating.

    Sampling listings at random would hand the homepage to whoever has the most
    stock: CIREBA carries 472 of the 873 and would take roughly half the slots
    for ever, while an agency with one listing would appear about once a year.
    So the rotation is over agencies, not listings. Each day the window moves on
    by four, and because four and the number of agencies share no common factor
    the window visits every agency before any repeats: with 21 agencies that is
    a 21 day cycle in which each appears exactly four times.

    Within the chosen agency the listing also moves with the day, so an agency
    does not show the same property every time its turn comes round.
    """
    ls = [l for l in data.get("listings", []) if l.get("price_kyd")]
    if not ls:
        return []

    by_agency: dict[str, list[dict]] = {}
    for l in ls:
        by_agency.setdefault(_agency_of(l), []).append(l)

    # A fixed arbitrary order, not alphabetical: alphabetical would always pair
    # the same neighbours, so the same agencies would keep sharing a day.
    import hashlib
    agencies = sorted(by_agency, key=lambda a: hashlib.sha1(a.encode()).hexdigest())
    if not agencies:
        return []

    day = _day_index(data)
    picked, used_areas = [], set()
    # Walk from today's offset; take the first listing that adds something new.
    for step in range(len(agencies)):
        if len(picked) == n:
            break
        agency = agencies[(day * n + step) % len(agencies)]
        rows = by_agency[agency]
        # Within the agency: a photo, still available, a home rather than a bare
        # lot since the section is headed "Homes", and an area not already used.
        # An agency that only sells land still shows land, which is honest.
        ordered = sorted(
            rows,
            key=lambda l: (not l.get("image"),
                           bool(TAKEN.search(l.get("status") or "")),
                           l.get("ptype") == "land",
                           (l.get("location") or "") in used_areas))
        offset = day % len(ordered)
        choice = ordered[offset % len(ordered)]
        picked.append(choice)
        if choice.get("location"):
            used_areas.add(choice["location"])

    return picked[:n]


def _step(num: int, title: str, sub: str) -> str:
    return (
        '<li style="display:flex;gap:16px;align-items:center;padding:16px 20px;'
        'border:1px solid rgba(255,255,255,.14);border-radius:12px">'
        '<span style="width:40px;height:40px;border-radius:999px;background:var(--teal-600);'
        'color:var(--on-teal);display:flex;align-items:center;justify-content:center;'
        f'font-weight:700;flex:none">{num}</span>'
        '<span style="display:flex;flex-direction:column">'
        f'<strong style="font-size:16px;line-height:24px">{e(title)}</strong>'
        '<span style="font-size:14px;line-height:22px;color:var(--on-dark-muted)">'
        f"{e(sub)}</span></span></li>")


def _feature(icon_name: str, tone: str, title: str, sub: str) -> str:
    bg = "var(--teal-100)" if tone == "teal" else "var(--navy-100)"
    fg = "var(--teal-600)" if tone == "teal" else "var(--navy-700)"
    return (
        '<div style="display:flex;gap:16px;align-items:flex-start">'
        f'<span style="width:48px;height:48px;border-radius:999px;background:{bg};color:{fg};'
        f'display:flex;align-items:center;justify-content:center;flex:none">{icon(icon_name)}</span>'
        '<span style="display:flex;flex-direction:column;gap:4px">'
        f'<strong style="font-size:18px;line-height:24px">{e(title)}</strong>'
        f'<span style="font-size:14px;line-height:22px;color:var(--ink-500)">{e(sub)}</span>'
        "</span></div>")


def _guide_card(href: str, icon_name: str, title: str, sub: str) -> str:
    return (
        f'<a href="{e(href)}" style="display:flex;flex-direction:column;gap:16px;padding:24px;'
        'border-radius:16px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);'
        'color:var(--on-dark);text-decoration:none">'
        '<span style="width:48px;height:48px;border-radius:999px;background:var(--teal-600);'
        'color:var(--on-teal);display:flex;align-items:center;justify-content:center">'
        f"{icon(icon_name)}</span>"
        f'<strong style="font-size:18px;line-height:24px">{e(title)}</strong>'
        f'<span style="font-size:14px;line-height:22px;color:var(--on-dark-muted)">{e(sub)}</span>'
        '<span style="display:inline-flex;align-items:center;gap:8px;font-size:14px;'
        f'font-weight:600;color:var(--teal-300)">Read the guide {icon("arrow-right", 16)}</span></a>')


def home(data: dict) -> str:
    """Ported from cmc-redesign/pages/Main.dc.html."""
    feats = _featured(data)
    cards = []
    for l in feats:
        price = l["price_kyd"]
        loan = price * (100 - DEPOSIT_PCT) / 100
        cards.append(listing_card(
            price=price,
            address=l.get("title") or "Property for sale",
            locality=l.get("location"),
            beds=l.get("beds"), baths=l.get("baths"), sqft=l.get("sqft"),
            image=l.get("image"), image_alt="",
            badge_text="For sale", badge_tone="navy",
            monthly=payment(loan),
            agency=(l.get("sources") or [l.get("source")])[0],
            href=l.get("url"),
        ))
    assume = f"{DEPOSIT_PCT}% down, {RATE}% over {TERM} years"

    return (
        '<section aria-label="Intro" class="r-hero r-pad" style="background:var(--navy-900);'
        'color:var(--on-dark);padding:64px 24px 120px">'
        '<div class="r-grid" style="max-width:1200px;margin:0 auto;display:grid;'
        'grid-template-columns:repeat(2,minmax(0,1fr));gap:48px;align-items:center">'
        '<div style="display:flex;flex-direction:column;gap:24px;min-width:0">'
        '<span style="font-size:12px;line-height:16px;font-weight:700;letter-spacing:.08em;'
        'text-transform:uppercase;color:var(--teal-300)">Free · Cayman Islands · No sign-up</span>'
        '<h1 class="r-h1" style="margin:0;font-size:56px;line-height:60px;font-weight:700;'
        'letter-spacing:-.02em">Plan your home.<br>Know your '
        '<span style="color:var(--teal-300)">numbers</span>.</h1>'
        '<p style="margin:0;font-size:18px;line-height:28px;color:var(--on-dark-muted);'
        'max-width:44ch">See what a Cayman mortgage really costs each month, with stamp duty, '
        'fees and closing costs included, before you make an offer.</p>'
        '<div style="display:flex;gap:16px;flex-wrap:wrap;align-items:center">'
        + button("Run the numbers", href="/calculator/", variant="onDark", icon_right="arrow-right")
        + "</div></div>"
        '<ol style="list-style:none;margin:0;padding:0;display:flex;flex-direction:column;'
        'gap:12px;min-width:0">'
        + _step(1, "Enter the price and your deposit", "Any property, any district.")
        + _step(2, "Set a rate and term", "Try the figures lenders have quoted you.")
        + _step(3, "See the full cost of buying",
                "Monthly payment, stamp duty and closing costs, side by side.")
        + "</ol></div></section>"

        # The board floats the panel over the hero's lower edge.
        '<div class="r-pad" style="max-width:1200px;margin:-72px auto 0;padding:0 24px;'
        'width:100%;box-sizing:border-box;position:relative">'
        + rd.calculator_panel(
            href="/calculator/", cta_label="See full breakdown",
            note="Estimates use the standard amortising formula at KYD prime 7.00% + 0.75%. "
                 "Your lender's rate, fees and insurance will differ.")
        + "</div>"

        '<section id="how" aria-label="Why use it" style="padding:64px 24px 48px">'
        '<div class="r-grid" style="max-width:1200px;margin:0 auto;display:grid;'
        'grid-template-columns:repeat(4,minmax(0,1fr));gap:24px">'
        + _feature("shield-check", "navy", "Free, no account",
                   "No sign-up, no newsletter, nothing to unsubscribe from.")
        + _feature("receipt", "teal", "Cayman costs built in",
                   "Stamp duty, legal fees and closing costs; not a generic US calculator.")
        + _feature("house", "navy", "Real local listings",
                   "Shown with each agency's permission, linking back to the original listing.")
        + _feature("landmark", "navy", "Lender-ready figures",
                   "Walk into the bank knowing your deposit, payment and total cost.")
        + "</div></section>"

        '<section aria-label="Featured properties" class="r-pad" style="padding:24px 24px 64px">'
        '<div style="max-width:1200px;margin:0 auto;display:flex;flex-direction:column;gap:24px">'
        '<div style="display:flex;justify-content:space-between;align-items:flex-end;gap:24px;'
        'flex-wrap:wrap"><div style="display:flex;flex-direction:column;gap:12px">'
        '<span style="font-size:12px;line-height:16px;font-weight:700;letter-spacing:.08em;'
        'text-transform:uppercase;color:var(--navy-700)">Featured properties</span>'
        '<h2 style="margin:0;font-size:32px;line-height:40px;font-weight:700;letter-spacing:-.01em">'
        "Homes with the monthly already worked out</h2></div>"
        + button("View all listings", href="/listings/", variant="ghost", icon_right="arrow-right")
        + "</div>"
        '<div class="r-grid" style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));'
        'gap:24px">' + "".join(cards) + "</div>"
        '<p style="margin:0;font-size:12px;line-height:16px;color:var(--ink-500)">'
        f"Monthly figures are this site's estimates at {e(assume)}, not the agent's. "
        "Each tile opens the listing on the agent's own site, where the photo is hosted."
        "</p></div></section>"

        '<section aria-label="Guides" class="r-pad" style="background:var(--navy-900);'
        'color:var(--on-dark);padding:64px 24px">'
        '<div style="max-width:1200px;margin:0 auto;display:flex;flex-direction:column;gap:32px">'
        '<div style="display:flex;flex-direction:column;gap:12px;max-width:60ch">'
        '<span style="font-size:12px;line-height:16px;font-weight:700;letter-spacing:.08em;'
        'text-transform:uppercase;color:var(--teal-300)">Know the full cost</span>'
        '<h2 style="margin:0;font-size:32px;line-height:40px;font-weight:700;letter-spacing:-.01em">'
        "The monthly payment is only part of it</h2>"
        '<p style="margin:0;font-size:16px;line-height:26px;color:var(--on-dark-muted)">'
        "Three short guides on the costs that surprise first-time buyers in Cayman.</p></div>"
        '<div class="r-grid" style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));'
        'gap:24px">'
        + _guide_card("/guides/stamp-duty/", "file-text", "Stamp duty explained",
                      "The standard rate, who qualifies for first-time Caymanian relief, "
                      "and how it is paid.")
        + _guide_card("/guides/closing-costs/", "receipt", "Closing costs checklist",
                      "Legal fees, valuation, insurance and the other line items between "
                      "offer and keys.")
        + _guide_card("/affordability/", "percent", "What can you afford",
                      "Work back from your income and savings to the price you can carry.")
        + "</div></div></section>")


DISTRICTS = ["George Town", "Seven Mile Beach", "West Bay", "Bodden Town",
             "East End", "North Side", "Cayman Brac", "Little Cayman"]
TYPES = [("", "Any type"), ("house", "House"), ("condo", "Condo or townhouse"), ("land", "Land")]
SORTS = [("new", "Newest"), ("price-asc", "Price, low to high"),
         ("price-desc", "Price, high to low"), ("size", "Largest")]


def listings(data: dict) -> str:
    """Ported from cmc-redesign/pages/Listings.dc.html.

    The grid is rendered by rd-listings.js from listings.json: 873 listings is
    far too much markup to ship, and the filters, sort, paging and compare all
    need to work on the client anyway.
    """
    district_opts = [("", "Any district")] + [(d, d) for d in DISTRICTS]
    bed_opts = [("", "Any")] + [(str(n), f"{n}+") for n in (1, 2, 3, 4, 5)]

    filters = (
        '<form id="rdFilters" aria-label="Filter listings" style="display:flex;'
        'flex-direction:column;gap:16px;background:var(--surface-0);'
        'border:1px solid var(--line-100);border-radius:12px;box-shadow:var(--shadow-sm);'
        'padding:20px 24px">'
        # No pill bar: the board has Buy and Rent, but the scraper carries no
        # rentals, and a single tab is not a choice. It returns with the data.
        + '<div class="r-grid-2" style="display:grid;grid-template-columns:repeat(6,minmax(0,1fr));'
          'gap:16px;align-items:end">'
        + rd.select_field("District", district_opts, id="fDistrict")
        + rd.select_field("Property type", TYPES, id="fType")
        + rd.input_field("Min price", prefix="CI$", placeholder="No min", id="fMin", value=None, money=True)
        + rd.input_field("Max price", prefix="CI$", placeholder="No max", id="fMax", value=None, money=True)
        + rd.select_field("Beds", bed_opts, id="fBeds")
        + rd.button("Search", icon_left="search", type="submit")
        + "</div></form>")

    return (
        '<section aria-label="Search" class="r-pad" style="background:var(--navy-100);'
        'padding:40px 24px">'
        '<div style="max-width:1200px;margin:0 auto;display:flex;flex-direction:column;gap:24px">'
        '<div style="display:flex;flex-direction:column;gap:12px">'
        '<nav aria-label="Breadcrumb" style="font-size:12px;line-height:16px;font-weight:500;'
        'color:var(--ink-500)"><a href="/" style="color:var(--ink-500);text-decoration:none">Home</a>'
        ' › Listings</nav>'
        '<h1 style="margin:0;font-size:40px;line-height:48px;font-weight:700;letter-spacing:-.02em">'
        "Homes for sale in the Cayman Islands</h1>"
        '<p style="margin:0;font-size:16px;line-height:26px;color:var(--ink-700);max-width:70ch">'
        "Gathered from the agencies' own websites every four hours, each one priced through "
        "your deposit, rate and term. Every tile opens the listing on the agent's own site.</p>"
        "</div>" + filters + "</div></section>"

        '<section aria-label="Results" class="r-pad" style="padding:40px 24px 64px">'
        '<div style="max-width:1200px;margin:0 auto;display:flex;flex-direction:column;gap:24px">'
        '<div style="display:flex;justify-content:space-between;align-items:center;gap:16px;'
        'flex-wrap:wrap">'
        '<p id="rdCount" style="margin:0;font-size:14px;line-height:22px;color:var(--ink-700)" '
        'role="status">Loading listings</p>'
        '<div style="display:flex;gap:12px;align-items:end;flex-wrap:wrap">'
        + rd.select_field("Sort by", SORTS, id="fSort")
        + rd.button("Set my rate and deposit", href="/calculator/", variant="secondary",
                    size="sm", icon_left="calculator")
        + "</div></div>"
        '<div id="rdGrid" class="r-grid" style="display:grid;'
        'grid-template-columns:repeat(4,minmax(0,1fr));gap:24px"></div>'
        '<div id="rdMoreWrap" style="display:flex;justify-content:center;padding-top:8px">'
        + rd.button("Show more", id="rdMore", variant="secondary", icon_right="arrow-right")
        + "</div>"
        '<p style="margin:0;font-size:12px;line-height:16px;color:var(--ink-500)">'
        "Monthly figures are this site's estimates from your deposit, rate and term, not the "
        "agent's. Prices are what sellers are asking today, not what buyers paid.</p>"
        '<section aria-label="Compare listings" id="compare" hidden style="flex-direction:column;'
        'gap:16px;padding:24px;border:1px solid var(--line-100);border-radius:12px;'
        'box-shadow:var(--shadow-md);background:var(--surface-0)">'
        '<div style="display:flex;justify-content:space-between;align-items:center;gap:16px;'
        'flex-wrap:wrap"><h2 style="margin:0;font-size:24px;line-height:32px;font-weight:700">'
        "Side by side</h2><div style=\"display:flex;gap:8px\">"
        + rd.button("Change deposit, rate or term", href="/calculator/", variant="secondary",
                    size="sm", icon_left="calculator")
        + rd.button("Clear", id="rdCmpClear", variant="ghost", size="sm")
        + "</div></div>"
        # .cmc-swipe is the hint itself, shown only below 860px; the scrolling
        # wrapper and the table are ours.
        '<div class="rd-scroll"><table id="rdCmpTable" class="rd-table"></table></div>'
        '<p class="cmc-swipe">Swipe sideways to see every column.</p>'
        "</section></div></section>"

        '<div id="rdCmpBar" class="rd-cmpbar" hidden role="status">'
        '<span id="rdCmpCount">0 selected</span>'
        + rd.button("Compare", href="#compare", variant="onDark", size="sm", icon_right="arrow-right")
        + f'<button type="button" id="rdCmpClose" class="rd-cmpbar__x" aria-label="Clear comparison">'
          f'{rd.icon("x", 16)}</button></div>')


def _fieldset(legend: str, body: str, aria: str, collapsible: bool = False,
              open_: bool = True) -> str:
    """A form section. The board makes the two detail-heavy groups <details>, so
    the page opens at a readable length rather than as one long wall."""
    if collapsible:
        return (f'<details class="sec" aria-label="{e(aria)}"{" open" if open_ else ""}>'
                f"<summary>{e(legend)}</summary>{body}</details>")
    return (f'<fieldset class="sec" aria-label="{e(aria)}" style="border:0;margin:0">'
            f"<legend>{e(legend)}</legend>{body}</fieldset>")


def _grid(*cells, cols: int = 2) -> str:
    return (f'<div class="r-grid-2" style="display:grid;'
            f'grid-template-columns:repeat({cols},minmax(0,1fr));gap:16px">'
            + "".join(cells) + "</div>")


def _stat(label: str, el_id: str, sub_id: str = "") -> str:
    return ('<div style="display:flex;flex-direction:column;gap:4px;padding:16px 20px;'
            'border:1px solid var(--line-100);border-radius:12px;background:var(--surface-0)">'
            f'<span style="font-size:12px;line-height:16px;font-weight:700;letter-spacing:.06em;'
            f'text-transform:uppercase;color:var(--ink-500)">{e(label)}</span>'
            f'<span id="{e(el_id)}" class="rd-stat__v" style="line-height:32px;'
            'font-weight:700;font-variant-numeric:tabular-nums;color:var(--ink-900)">CI$0</span>'
            + (f'<span id="{e(sub_id)}" style="font-size:12px;line-height:16px;'
               'color:var(--ink-500)"></span>' if sub_id else "")
            + "</div>")


def calculator(data: dict) -> str:
    """Ported from cmc-redesign/pages/Calculator.dc.html.

    The board carries its own duty arithmetic, which omits the 10% band at
    CI$2,000,000 and ignores the island it asks the visitor to choose. This page
    uses core.js instead, which has both and is covered by the existing tests.
    See REDESIGN-PLAN.md section 4.1.
    """
    islands = [("grand", "Grand Cayman"), ("brac", "Cayman Brac"), ("little", "Little Cayman")]
    ptypes = [("home", "House or condo"), ("land", "Raw land")]
    statuses = [("first", "Caymanian, first property"), ("second", "Caymanian, second property"),
                ("standard", "Standard rate, 7.5%")]
    buyers = [("single", "One buyer"), ("joint", "Two to ten Caymanians jointly")]
    terms = [(15, "15 years"), (20, "20 years"), (25, "25 years"), (30, "30 years")]

    inputs = (
        rd.currency_toggle()
        + _fieldset("Property", _grid(
            rd.input_field("Purchase price", bind="price", value=650000, prefix="CI$", step=1000, min_=0, money=True),
            rd.input_field("Government valuation, if higher", id="cValuation", prefix="CI$",
                           placeholder="Same as price", step=1000, min_=0, value=None, money=True),
            rd.select_field("Island", islands, id="cIsland", value="grand"),
            rd.select_field("Property type", ptypes, id="cPtype", value="home"),
        ), "Property")
        + _fieldset("Buyer", _grid(
            rd.select_field("Stamp duty status", statuses, id="cStatus", value="first"),
            rd.select_field("Buyers", buyers, id="cBuyer", value="single"),
        ), "Buyer")
        + _fieldset("Mortgage", _grid(
            rd.input_field("Deposit", bind="deposit", value=10, suffix="%", step=0.5, min_=0, max_=100),
            rd.input_field("Interest rate", bind="rate", value=7.75, suffix="%", step=0.05, min_=0),
            rd.select_field("Term", terms, bind="term", value=25),
            rd.input_field("Extra each month", id="cExtra", prefix="CI$", placeholder="0",
                           step=50, min_=0, value=None, money=True),
            rd.input_field("Gross monthly income", id="cIncome", prefix="CI$", placeholder="Optional",
                           step=100, min_=0, value=None, money=True),
            rd.input_field("Cash available", id="cCash", prefix="CI$", placeholder="Optional",
                           step=1000, min_=0, value=None, money=True),
        ), "Mortgage")
        + _fieldset("Your household in detail", _grid(
            rd.input_field("Strata fees each month", id="cStrata", prefix="CI$",
                           placeholder="Not known", step=25, min_=0, value=None, money=True),
            rd.input_field("Life insurance each month", id="cLife", prefix="CI$", placeholder="0",
                           step=10, min_=0, value=None, money=True),
            rd.input_field("Building insurance", id="cBldg", suffix="%/yr",
                           hint="of the purchase price", value=1, step=0.1, min_=0),
            rd.input_field("Maintenance allowance", id="cMaint", suffix="%/yr",
                           hint="of the purchase price", value=1, step=0.1, min_=0),
        ) + '<label style="display:flex;gap:12px;align-items:center;font-size:14px;'
            'line-height:22px;color:var(--ink-700)">'
            '<input type="checkbox" id="cBldgInStrata"> '
            "The strata covers building insurance</label>",
          "Your household in detail", collapsible=True, open_=True)
        + _fieldset("Fee assumptions", _grid(
            rd.input_field("Legal fees", id="cLegal", suffix="%", hint="of the price", value=1, step=0.1, min_=0),
            rd.input_field("Bank fee", id="cBank", suffix="%", hint="of the loan", value=1, step=0.1, min_=0),
            rd.input_field("Valuation", id="cValFee", prefix="CI$", value=600, step=50, min_=0, money=True),
            rd.input_field("Mortgage stamp duty", id="cMortDuty", prefix="CI$", value=None,
                           readonly=True, inputmode=None, type_="text", money=True),
        ), "Fee assumptions", collapsible=True, open_=False)
    )

    results = (
        '<div style="display:flex;flex-direction:column;gap:12px;padding:24px;border-radius:16px;'
        'background:var(--navy-900);color:var(--on-dark)">'
        '<span style="font-size:12px;line-height:16px;font-weight:700;letter-spacing:.08em;'
        'text-transform:uppercase;color:var(--teal-300)">Estimated monthly payment</span>'
        '<span id="rMonthly" class="r-big" style="font-size:48px;line-height:52px;font-weight:700;'
        'letter-spacing:-.02em;font-variant-numeric:tabular-nums">CI$0</span>'
        '<span id="rMonthlySub" style="font-size:14px;line-height:22px;color:var(--on-dark-muted)">'
        "</span>"
        '<div style="padding-top:8px">'
        + rd.button("See homes that fit these numbers", href="/listings/", variant="onDark",
                    size="sm", icon_right="arrow-right", id="rFitLink")
        + "</div></div>"

        + ('<div class="rd-stats">'
           + _stat("Loan amount", "rLoan") + _stat("Deposit", "rDown", "rDownSub")
           + _stat("Total interest", "rInterest", "rInterestSub")
           + _stat("Cash to close", "rCash", "rCashSub") + "</div>")

        + '<section aria-label="Monthly cost of owning" style="display:flex;flex-direction:column;'
          'gap:12px;padding:24px;border:1px solid var(--line-100);border-radius:12px">'
          '<h2 style="margin:0;font-size:20px;line-height:28px;font-weight:700">'
          "Monthly cost of owning</h2>"
          '<p style="margin:0;font-size:13px;line-height:20px;color:var(--ink-500)">'
          "The mortgage payment above, plus everything else that falls due each "
          "month.</p>"
          '<div class="rd-scroll"><table class="rd-table" id="rOwnTable"></table></div>'
          '<p id="rOwnNote" style="margin:0;font-size:12px;line-height:16px;color:var(--ink-500)">'
          "</p></section>"

        + '<section aria-label="Cash you need at closing" style="display:flex;'
          'flex-direction:column;gap:12px;padding:24px;border:1px solid var(--line-100);'
          'border-radius:12px">'
          '<h2 style="margin:0;font-size:20px;line-height:28px;font-weight:700">'
          "Cash you need at closing</h2>"
          '<div class="rd-scroll"><table class="rd-table" id="rCashTable"></table></div>'
          '<p id="rCashNote" style="margin:0;font-size:12px;line-height:16px;color:var(--ink-500)">'
          "</p></section>"

        + '<section aria-label="Stamp duty" style="display:flex;flex-direction:column;gap:8px;'
          'padding:24px;border-radius:12px;background:var(--teal-100)">'
          '<h2 style="margin:0;font-size:20px;line-height:28px;font-weight:700">Stamp duty</h2>'
          '<p id="rDuty" style="margin:0;font-size:32px;line-height:40px;font-weight:700;'
          'font-variant-numeric:tabular-nums;color:var(--ink-900)">CI$0</p>'
          '<p id="rDutyWhy" style="margin:0;font-size:14px;line-height:22px;color:var(--ink-700)">'
          "</p></section>"

        + '<section id="rAffordWrap" aria-label="Affordability check" hidden '
          'style="display:flex;flex-direction:column;gap:8px;padding:24px;'
          'border:1px solid var(--line-100);border-radius:12px">'
          '<h2 style="margin:0;font-size:20px;line-height:28px;font-weight:700">'
          "Affordability check</h2>"
          '<p id="rAfford" style="margin:0;font-size:14px;line-height:22px;color:var(--ink-700)">'
          "</p></section>"

        + '<section aria-label="Year by year" style="display:flex;flex-direction:column;gap:12px;'
          'padding:24px;border:1px solid var(--line-100);border-radius:12px">'
          '<h2 style="margin:0;font-size:20px;line-height:28px;font-weight:700">Year by year</h2>'
          '<div class="rd-scroll"><table class="rd-table" id="rYears"></table></div>'
          '<p class="cmc-swipe">Swipe sideways to see every column.</p>'
        + '<div style="display:flex;gap:8px;flex-wrap:wrap;padding-top:8px">'
        + rd.button("Download full schedule", id="rXlsx", variant="secondary", size="sm",
                    icon_left="file-text")
        + "</div></section>"

        + '<section aria-label="Summary" id="rSummary" style="display:flex;'
          'flex-direction:column;gap:12px;padding:24px;border:1px solid var(--line-100);'
          'border-radius:12px">'
          '<h2 style="margin:0;font-size:20px;line-height:28px;font-weight:700">'
          "Take this with you</h2>"
          '<p style="margin:0;font-size:14px;line-height:22px;color:var(--ink-700)">'
          "A one page summary of these figures, with the assumptions behind them, to read "
          "away from the screen or take to a lender.</p>"
          '<div class="rd-no-print" style="display:flex;gap:8px;flex-wrap:wrap">'
        + rd.button("Save as PDF", id="rPdf", icon_left="file-text")
        + rd.button("Print", id="rPrint", variant="secondary", icon_left="receipt")
        + "</div>"
          '<p id="rExportNote" role="status" style="margin:0;font-size:12px;line-height:16px;'
          'color:var(--ink-500)"></p></section>')

    return (
        '<section aria-label="Page title" class="r-pad" style="background:var(--navy-100);'
        'padding:40px 24px">'
        '<div style="max-width:1200px;margin:0 auto;display:flex;flex-direction:column;gap:12px">'
        '<nav aria-label="Breadcrumb" style="font-size:12px;line-height:16px;font-weight:500;'
        'color:var(--ink-500)"><a href="/" style="color:var(--ink-500);text-decoration:none">Home</a>'
        ' › Mortgage calculator</nav>'
        '<h1 style="margin:0;font-size:32px;line-height:40px;font-weight:700;letter-spacing:-.02em">'
        "Cayman mortgage calculator</h1>"
        '<p style="margin:0;font-size:16px;line-height:26px;color:var(--ink-700);max-width:70ch">'
        "Your monthly payment and the cash you need on the day, with Cayman stamp duty, "
        "legal fees and bank charges included. Every figure is an estimate.</p></div></section>"

        '<section aria-label="Inputs" class="r-pad" style="padding:40px 24px 64px">'
        '<div class="r-grid" style="max-width:1200px;margin:0 auto;display:grid;'
        'grid-template-columns:minmax(0,5fr) minmax(0,7fr);gap:32px;align-items:start">'
        f'<form id="rdCalc" class="rd-form-panel">{inputs}</form>'
        '<div aria-label="Results" style="display:flex;flex-direction:column;gap:24px">'
        f"{results}</div></div></section>" + sources_block())


SOURCES = [
    ("Stamp Duty Act (2019 Revision)",
     "https://www.caymanlandinfo.ky/docs/default-source/laws-and-regulations/stamp-duty/"
     "stamp-duty-act_2019-revision.pdf?sfvrsn=dd960e84_5",
     "The transfer and mortgage duty rates, and the 45 day deadline"),
    ("Ministry of Finance: Caymanian concession application",
     "https://www.caymanlandinfo.ky/docs/default-source/laws-and-regulations/stamp-duty/"
     "application-concession-form-for-caymanian-property-buyers.pdf?sfvrsn=a01a6f6d_1",
     "The first property and second property bands, single and joint"),
    ("Lands and Survey: stamp duty concessions in Cayman Brac",
     "https://www.caymanlandinfo.ky/docs/default-source/laws-and-regulations/stamp-duty/"
     "stamp-duty-rates-cayman-brac-(2025).pdf",
     "0% on undeveloped land and 3% on developed property under CI$2,000,000, "
     "and 10% at or above it"),
    ("Cayman Islands Government: 10% duty at CI$2M and over",
     "https://gov.ky/w/legislation-passed-to-increase-stamp-duty-on-properties-worth-2m-and-over",
     "The rate on the whole value once the price reaches CI$2,000,000"),
    ("Lands and Survey: registry fees",
     "https://www.caymanlandinfo.ky/services/land-registry/registry-fees",
     "The CI$50 to register a transfer and CI$50 for a charge"),
]

BYLINE = {"author": "Jerome Bailey", "reviewer": "Janique Bailey",
          "checked": "14 October 2026", "updated": "14 October 2026"}


def sources_block(note: str = "") -> str:
    """The numbered Sources block and Byline that HANDOFF 5.7 asks every guide
    and calculator to end with."""
    items = "".join(
        f'<li style="margin-bottom:8px"><a href="{e(url)}" target="_blank" rel="noopener">'
        f"{e(title)}</a><br>"
        f'<span style="font-size:12px;line-height:16px;color:var(--ink-500)">{e(what)}</span>'
        "</li>"
        for title, url, what in SOURCES)
    return (
        '<section aria-label="Sources" class="r-pad" style="padding:0 24px 64px">'
        '<div style="max-width:1200px;margin:0 auto;display:flex;flex-direction:column;'
        'gap:16px;padding:24px;border:1px solid var(--line-100);border-radius:12px">'
        '<h2 style="margin:0;font-size:20px;line-height:28px;font-weight:700">Sources</h2>'
        f'<ol style="margin:0;padding-left:20px;font-size:14px;line-height:22px">{items}</ol>'
        + rd_board.byline(note=note or "Estimates only, not financial or legal advice. "
                          "Confirm every figure with your attorney and lender before you commit.",
                          **BYLINE)
        + "</div></section>")


def _page_head(crumb: str, title: str, lede: str) -> str:
    return ('<section aria-label="Page title" class="r-pad" style="background:var(--navy-100);'
            'padding:40px 24px">'
            '<div style="max-width:1200px;margin:0 auto;display:flex;flex-direction:column;gap:12px">'
            '<nav aria-label="Breadcrumb" style="font-size:12px;line-height:16px;font-weight:500;'
            'color:var(--ink-500)"><a href="/" style="color:var(--ink-500);text-decoration:none">'
            f"Home</a> › {e(crumb)}</nav>"
            '<h1 style="margin:0;font-size:32px;line-height:40px;font-weight:700;'
            f'letter-spacing:-.02em">{e(title)}</h1>'
            '<p style="margin:0;font-size:16px;line-height:26px;color:var(--ink-700);max-width:70ch">'
            f"{e(lede)}</p></div></section>")


def _two_col(form: str, results: str) -> str:
    return ('<section aria-label="Inputs" class="r-pad" style="padding:40px 24px 64px">'
            '<div class="r-grid" style="max-width:1200px;margin:0 auto;display:grid;'
            'grid-template-columns:minmax(0,5fr) minmax(0,7fr);gap:32px;align-items:start">'
            f"{form}"
            '<div aria-label="Results" style="display:flex;flex-direction:column;gap:24px">'
            f"{results}</div></div></section>")


def _answer(label_id: str, value_id: str, note_id: str, tone: str = "navy") -> str:
    bg = "var(--navy-900)" if tone == "navy" else "var(--teal-100)"
    fg = "var(--on-dark)" if tone == "navy" else "var(--ink-900)"
    muted = "var(--on-dark-muted)" if tone == "navy" else "var(--ink-700)"
    accent = "var(--teal-300)" if tone == "navy" else "var(--teal-600)"
    return ('<div style="display:flex;flex-direction:column;gap:12px;padding:24px;'
            f'border-radius:16px;background:{bg};color:{fg}">'
            f'<span id="{e(label_id)}" style="font-size:12px;line-height:16px;font-weight:700;'
            f'letter-spacing:.08em;text-transform:uppercase;color:{accent}"></span>'
            f'<span id="{e(value_id)}" class="r-big" style="font-size:48px;line-height:52px;'
            'font-weight:700;letter-spacing:-.02em;font-variant-numeric:tabular-nums">CI$0</span>'
            f'<span id="{e(note_id)}" style="font-size:14px;line-height:22px;color:{muted}">'
            "</span></div>")


def affordability(data: dict) -> str:
    """Ported from cmc-redesign/pages/Affordability.dc.html.

    Two limits, per HANDOFF 5.3: what your income will carry and what your cash
    will cover. The cash limit is solved with Core.maxPrice, which steps through
    the duty thresholds rather than bisecting past them.
    """
    statuses = [("first", "Caymanian, first property"), ("second", "Caymanian, second property"),
                ("standard", "Standard rate, 7.5%")]
    form = (
        '<form id="rdAfford" class="rd-form-panel">'
        + rd.currency_toggle()
        + _fieldset("What you earn and owe", _grid(
            rd.input_field("Gross monthly income", id="aIncome", prefix="CI$", value=9000,
                           step=100, min_=0, money=True),
            rd.input_field("Other monthly debts", id="aDebts", prefix="CI$", value=0,
                           step=50, min_=0, money=True),
            rd.input_field("Debt service ceiling", id="aCeiling", suffix="%",
                           hint="of gross income", value=40, step=1, min_=1, max_=100),
            rd.input_field("Cash available", id="aCash", prefix="CI$", value=120000,
                           step=1000, min_=0, money=True),
        ), "Income and cash")
        + _fieldset("The purchase", _grid(
            rd.input_field("Deposit", bind="deposit", value=10, suffix="%", step=0.5, min_=0, max_=100),
            rd.input_field("Interest rate", bind="rate", value=7.75, suffix="%", step=0.05, min_=0),
            rd.select_field("Term", [(15, "15 years"), (20, "20 years"), (25, "25 years"),
                                     (30, "30 years")], bind="term", value=25),
            rd.select_field("Stamp duty status", statuses, id="aStatus", value="first"),
        ), "The purchase")
        + "</form>")

    results = (
        _answer("aVerdictLabel", "aMax", "aVerdictNote")
        + '<div style="padding:0">'
        + rd.button("Run this price in the mortgage calculator", id="aRun",
                    icon_right="arrow-right") + "</div>"
        + '<section aria-label="The two limits" style="display:flex;flex-direction:column;'
          'gap:12px;padding:24px;border:1px solid var(--line-100);border-radius:12px">'
          '<h2 style="margin:0;font-size:20px;line-height:28px;font-weight:700">'
          "The two limits</h2>"
          '<div class="rd-scroll"><table class="rd-table" id="aTable"></table></div>'
          '<p style="margin:0;font-size:12px;line-height:16px;color:var(--ink-500)">'
          "The lower of the two is what you can actually buy. Lenders also apply their own "
          "criteria, so treat this as a planning figure.</p></section>")

    return (_page_head("Affordability", "What can you afford?",
                       "Two things decide it: what your income will carry each month, and what "
                       "your cash will cover on the day. This works out both and tells you "
                       "which one is binding.")
            + _two_col(form, results) + sources_block())


def equity(data: dict) -> str:
    """Ported from cmc-redesign/pages/Equity.dc.html (HANDOFF 5.4)."""
    form = (
        '<form id="rdEquity" style="display:flex;flex-direction:column;gap:24px">'
        + _fieldset("Your property", _grid(
            rd.input_field("What it is worth now", id="eValue", prefix="CI$", value=800000,
                           step=5000, min_=0, money=True),
            rd.input_field("Mortgage balance", id="eBalance", prefix="CI$", value=400000,
                           step=5000, min_=0, money=True),
            rd.input_field("Other secured loans", id="eOther", prefix="CI$", value=0,
                           step=1000, min_=0, money=True),
            rd.input_field("Maximum loan to value", id="eLtv", suffix="%", value=80,
                           hint="90% Caymanian, 80% resident, 70% non-resident",
                           step=1, min_=1, max_=100),
        ), "Your property")
        + "</form>")

    results = (
        _answer("eLabel", "eAvailable", "eNote", tone="teal")
        + '<section aria-label="How it is worked out" style="display:flex;flex-direction:column;'
          'gap:12px;padding:24px;border:1px solid var(--line-100);border-radius:12px">'
          '<h2 style="margin:0;font-size:20px;line-height:28px;font-weight:700">'
          "How it is worked out</h2>"
          '<div class="rd-scroll"><table class="rd-table" id="eTable"></table></div></section>'
        + '<p style="margin:0;font-size:14px;line-height:22px;color:var(--ink-700)">'
          'Releasing equity means a new or larger charge on the property, which carries its own '
          'stamp duty. The <a href="/guides/refinancing/">refinancing guide</a> works out '
          "whether a new rate pays for itself.</p>")

    return (_page_head("Equity", "How much equity do you have?",
                       "What your property is worth, less what is secured against it, and how "
                       "much of that a lender would let you borrow.")
            + _two_col(form, results) + sources_block())


# ---------------------------------------------------------------------------
# Boards with no live arithmetic are translated straight from the design files
# rather than retyped: the copy is approved and already dash-clean.
import rd_board
from pathlib import Path as _Path

_BOARDS = _Path(__file__).resolve().parent / "cmc-redesign" / "pages"


def from_board(name: str, vals: dict | None = None):
    def build(data, _n=name, _v=vals):
        return rd_board.translate(_BOARDS / f"{_n}.dc.html", _v)
    return build


# The agents page shows one illustrative card captioned "Your agency": it
# demonstrates the format to an agency rather than listing a real property.
AGENT_SAMPLE = {"price": 850000, "beds": 3, "baths": 2, "sqft": 2100, "monthly": 4800}


BRAC_SECTION = """
<section aria-label="Cayman Brac" class="r-pad" style="padding:0 24px 40px">
  <div style="max-width:1200px;margin:0 auto;display:flex;flex-direction:column;gap:16px">
    <h2 style="margin:0;font-size:24px;line-height:32px;font-weight:700;color:var(--ink-900)">
      Buying on Cayman Brac: a separate set of rates</h2>
    <p style="margin:0">Cayman Brac has its own rates, in force since 1 January 2026. They turn
      on the consideration, meaning the purchase price or the market value, whichever is higher,
      and on whether the property is developed. They are open to anyone, Caymanian or not.</p>
    <div class="rd-scroll"><table class="rd-table">
      <thead><tr><th>Rate</th><th>Applies to</th></tr></thead>
      <tbody>
        <tr><th>0%</th><td>Undeveloped land under CI$2,000,000, subject to the conditions
          below</td></tr>
        <tr><th>3%</th><td>Developed property under CI$2,000,000</td></tr>
        <tr><th>10%</th><td>Anything at CI$2,000,000 or more, developed or not</td></tr>
      </tbody>
    </table></div>
    <p style="margin:0"><strong style="color:var(--ink-900)">The 0% is a waiver with conditions
      attached, not a simple exemption.</strong> The property must be developed within two years
      of the waiver being granted, with a building that requires planning approval and a
      Certificate of Occupancy to occupy. If that is not done, the applicant may ask the Minister
      for Finance and Economic Development for an extension of up to two further years. If it is
      still not developed, the duty that was waived becomes payable in full plus a penalty of 10%.
      A restriction is placed on the property prohibiting transfer until every condition is met.
      Developed means certified fit to occupy, evidenced by a Certificate of Occupancy from the
      Department of Planning.</p>
    <p style="margin:0">The calculator applies these rates automatically when you choose Cayman
      Brac. Little Cayman is not part of this scheme and follows the ordinary rates.</p>
  </div>
</section>
"""


def stamp_duty_guide(data: dict) -> str:
    """Ported from StampDuty.dc.html.

    The board's own Cayman Brac section described the concession as waiving duty
    entirely on any value. The published sheet (Lands & Survey, effective
    1 January 2026) does not: the waiver is for undeveloped land under
    CI$2,000,000 only, developed property under that figure pays 3%, and anything
    at CI$2,000,000 or more pays 10%. The board's section is replaced with one
    written from the sheet, which is also what core.js applies.
    """
    src = (_BOARDS / "StampDuty.dc.html").read_text()
    i = src.find("Buying in Cayman Brac")
    if i > 0:
        start = src.rfind("<section", 0, i)
        end = src.find("</section>", i) + len("</section>")
        src = src[:start] + src[end:]

    # the standard-rate figure the quick estimate opens with; rd-guides.js keeps
    # it live, including the step to 10% at CI$2,000,000
    body = rd_board.translate_source(src, {"duty": "CI$48,750"})
    # the board hard-codes the rate label, which is only true below CI$2M
    body = body.replace("Standard rate · 7.5%",
                        '<span id="gdRateLabel">Standard rate · 7.5%</span>')
    body = body.replace('<span style="font-size: 32px; line-height: 40px; font-weight: 700">CI$48,750</span>',
                        '<span id="gdDuty" style="font-size: 32px; line-height: 40px; '
                        'font-weight: 700">CI$48,750</span>')
    # the Brac section, written from the published sheet, before the sources
    marker = '<section aria-label="Sources"'
    i = body.find(marker)
    return body[:i] + BRAC_SECTION + body[i:] if i > 0 else body + BRAC_SECTION


def _panel(title: str, inner: str, aria: str) -> str:
    return (f'<section aria-label="{e(aria)}" class="r-pad" style="padding:40px 24px">'
            '<div style="max-width:1200px;margin:0 auto;display:flex;flex-direction:column;'
            'gap:16px;padding:24px;border:1px solid var(--line-100);border-radius:12px;'
            'box-shadow:var(--shadow-sm);background:var(--surface-0)">'
            f'<h2 style="margin:0;font-size:24px;line-height:32px;font-weight:700">{e(title)}</h2>'
            f"{inner}</div></section>")


def refinancing_guide(data: dict) -> str:
    """Ported from Refinancing.dc.html. The board wires its inputs through setter
    callbacks, which leave nothing to bind to, so the break-even panel is built
    here and dropped in where the board's panel was."""
    src = (_BOARDS / "Refinancing.dc.html").read_text()
    body = rd_board.translate_source(rd_board.without_section(src, "Break-even calculator"))

    panel = _panel("Will a new rate pay for itself?",
        '<form id="rdRefi" style="display:flex;flex-direction:column;gap:16px">'
        + _grid(
            rd.input_field("Current balance", id="fBal", prefix="CI$", value=430000, step=5000, min_=0, money=True),
            rd.input_field("Current rate", id="fCur", suffix="%", value=8.25, step=0.05, min_=0),
            rd.input_field("Years left", id="fYears", value=20, step=1, min_=1),
            rd.input_field("New rate", id="fNew", suffix="%", value=7.5, step=0.05, min_=0),
            rd.input_field("New term", id="fTerm", suffix="years", value=20, step=1, min_=1),
            rd.input_field("Early repayment charge", id="fErc", prefix="CI$", value=0,
                           step=500, min_=0, money=True),
            rd.input_field("Legal", id="fLegal", prefix="CI$", value=2500, step=100, min_=0, money=True),
            rd.input_field("Valuation", id="fVal", prefix="CI$", value=600, step=50, min_=0, money=True),
            rd.input_field("Bank fee", id="fBank", suffix="%", hint="of the balance",
                           value=0.5, step=0.1, min_=0),
            cols=3)
        + '<label style="display:flex;gap:12px;align-items:center;font-size:14px;'
          'line-height:22px;color:var(--ink-700)">'
          '<input type="checkbox" id="fCharge" checked> New lender, so a new legal charge '
          "and its stamp duty</label></form>"
        + '<div style="display:flex;flex-direction:column;gap:8px;padding:20px;'
          'border-radius:12px;background:var(--teal-100)">'
          '<span id="fVerdictLabel" style="font-size:12px;line-height:16px;font-weight:700;'
          'letter-spacing:.08em;text-transform:uppercase;color:var(--teal-600)">Break-even</span>'
          '<span id="fVerdict" style="font-size:32px;line-height:40px;font-weight:700;'
          'font-variant-numeric:tabular-nums">0 months</span>'
          '<span id="fNote" style="font-size:14px;line-height:22px;color:var(--ink-700)">'
          "</span></div>"
        + '<div class="rd-scroll"><table class="rd-table" id="fTable"></table></div>',
        "Break-even calculator")

    # back where the board had it: after the opening section, before the sources
    marker = '<section aria-label="Sources"'
    i = body.find(marker)
    return body[:i] + panel + body[i:] if i > 0 else body + panel


def _closing_items() -> list[dict]:
    """The closing-cost lines at the shared defaults, from the same rules the
    calculator applies. Amounts are illustrative until the visitor sets a price."""
    price, deposit = 650000, 10
    loan = price * (1 - deposit / 100)
    duty_first_excess = max(0, price - 550000) * 0.0375
    mortgage_duty = loan * (0.015 if loan > 300000 else 0.01)
    rows = [
        ("Stamp duty on the transfer", duty_first_excess,
         "3.75% on the part above CI$550,000 for a Caymanian first property",
         "Stamp Duty Act (2019 Revision)"),
        ("Stamp duty on the mortgage", mortgage_duty,
         "1% up to CI$300,000, then 1.5% of the whole sum", "Stamp Duty Act, Schedule: Mortgage"),
        ("Land Registry fees", 100.0, "CI$50 to register the transfer, CI$50 for the charge",
         "Lands and Survey registry fees"),
        ("Legal fees", price * 0.01, "Commonly around 1% of the price; get this quoted",
         "Quoted by your attorney"),
        ("Bank arrangement fee", loan * 0.01, "Commonly around 1% of the loan",
         "Quoted by your lender"),
        ("Valuation", 600.0, "Required by the lender before it will advance",
         "Quoted by the valuer"),
    ]
    return [{"title": t, "amount": fmt_money(a), "note": n, "source": src_, "done": False,
             "toggle": ""} for t, a, n, src_ in rows]


def _closing_vals() -> dict:
    """The Assumptions block's figures, from the same defaults as the checklist."""
    price, deposit_pct = 650000, 10
    loan = price * (1 - deposit_pct / 100)
    stamp = max(0, price - 550000) * 0.0375
    mduty = loan * (0.015 if loan > 300000 else 0.01)
    legal = price * 0.01
    other = legal + loan * 0.01 + 600 + 100
    total = stamp + mduty + other
    return {
        "deposit": fmt_money(price * deposit_pct / 100),
        "stampDuty": fmt_money(stamp),
        "mortgageDuty": fmt_money(mduty),
        "mortgageDutyRate": "1.5%",
        "legal": fmt_money(legal),
        "legalRate": "1%",
        "bankRate": "1%",
        "valuationRaw": "600",
        "insuranceRaw": "",
        "other": fmt_money(other),
        "total": fmt_money(total),
        "totalPct": f"{total / price * 100:.1f}%",
    }


def closing_costs_guide(data: dict) -> str:
    """Ported from ClosingCosts.dc.html, with the cash-at-closing panel rebuilt
    on core.js so it matches the calculator line for line."""
    src = (_BOARDS / "ClosingCosts.dc.html").read_text()
    # The checklist is server-rendered from the same core.js itemisation the
    # calculator uses, then kept live by rd-guides.js. Ticking a line is runtime
    # state, so the initial render just shows every line unticked.
    items = _closing_items()
    body = rd_board.translate_source(
        rd_board.without_section(src, "Cash at closing"),
        dict({"items": items, "ticked": 0, "count": len(items)}, **_closing_vals()))

    panel = _panel("What you need on the day",
        '<form id="rdClosing" style="display:flex;flex-direction:column;gap:16px">'
        + _grid(
            rd.input_field("Purchase price", bind="price", value=650000, prefix="CI$",
                           step=1000, min_=0, money=True),
            rd.input_field("Deposit", bind="deposit", value=10, suffix="%", step=0.5,
                           min_=0, max_=100),
            rd.select_field("Stamp duty status",
                            [("first", "Caymanian, first property"),
                             ("second", "Caymanian, second property"),
                             ("standard", "Standard rate, 7.5%")],
                            id="ccStatus", value="first"),
            cols=3)
        + "</form>"
        + '<div class="rd-scroll"><table class="rd-table" id="ccTable"></table></div>'
        + '<p id="ccNote" style="margin:0;font-size:12px;line-height:16px;color:var(--ink-500)">'
          "</p>",
        "Cash at closing")

    marker = '<section aria-label="Sources"'
    i = body.find(marker)
    return body[:i] + panel + body[i:] if i > 0 else body + panel


def rent_vs_buy(data: dict) -> str:
    """Kept at the owner's request on 14 October; the hand-off's site map omits
    it. There is no board for this page, so it is built from the same parts as
    the other calculators: the shared page head, the two-column layout, the
    answer block and a table.
    """
    form = (
        '<form id="rdRent" style="display:flex;flex-direction:column;gap:24px">'
        + _fieldset("Renting", _grid(
            rd.input_field("Rent each month", id="vRent", prefix="CI$", value=3200,
                           step=50, min_=0, money=True),
            rd.input_field("Rent rises", id="vRentRise", suffix="%/yr", value=3,
                           step=0.5, min_=0),
        ), "Renting")
        + _fieldset("Buying", _grid(
            rd.input_field("Purchase price", bind="price", value=650000, prefix="CI$",
                           step=1000, min_=0, money=True),
            rd.input_field("Deposit", bind="deposit", value=10, suffix="%", step=0.5,
                           min_=0, max_=100),
            rd.input_field("Interest rate", bind="rate", value=7.75, suffix="%",
                           step=0.05, min_=0),
            rd.select_field("Term", [(15, "15 years"), (20, "20 years"), (25, "25 years"),
                                     (30, "30 years")], bind="term", value=25),
            rd.select_field("Stamp duty status",
                            [("first", "Caymanian, first property"),
                             ("second", "Caymanian, second property"),
                             ("standard", "Standard rate, 7.5%")],
                            id="vStatus", value="first"),
            rd.input_field("Prices rise", id="vGrowth", suffix="%/yr", value=3,
                           step=0.5, min_=0),
        ), "Buying")
        + _fieldset("How long you stay", _grid(
            rd.input_field("Years", id="vYears", value=10, step=1, min_=1, max_=40),
            rd.input_field("Selling costs", id="vSell", suffix="%", hint="of the sale price",
                           value=4, step=0.5, min_=0),
        ), "How long you stay")
        + "</form>")

    results = (
        _answer("vLabel", "vVerdict", "vNote")
        + '<section aria-label="Over your horizon" style="display:flex;flex-direction:column;'
          'gap:12px;padding:24px;border:1px solid var(--line-100);border-radius:12px">'
          '<h2 style="margin:0;font-size:20px;line-height:28px;font-weight:700">'
          "Over the years you stay</h2>"
          '<div class="rd-scroll"><table class="rd-table" id="vTable"></table></div>'
          '<p style="margin:0;font-size:12px;line-height:16px;color:var(--ink-500)">'
          "Buying is compared on what you are left with: the equity in the property after "
          "selling costs, less everything you paid in. Renting is compared on what you paid "
          "and the deposit you still have. Neither side assumes you invest the "
          "difference.</p></section>")

    return (_page_head("Rent vs Buy", "Rent or buy in Cayman?",
                       "Buying costs more at the start and less later. This works out the "
                       "year the two cross over, for the length of time you actually plan "
                       "to stay.")
            + _two_col(form, results) + sources_block())


def not_found(data: dict) -> str:
    """Served by GitHub Pages for any address that does not exist, at any depth,
    so every link here is absolute."""
    cards = [
        ("/calculator/", "calculator", "Mortgage calculator",
         "Your monthly payment and the cash you need on the day."),
        ("/listings/", "house", "Listings",
         "Every home and lot for sale, priced through your own numbers."),
        ("/affordability/", "percent", "What can you afford",
         "Work back from your income and savings to a price."),
        ("/guides/stamp-duty/", "receipt", "Stamp duty",
         "Rates, bands and the Caymanian concession."),
    ]
    tiles = "".join(
        f'<a href="{e(href)}" style="display:flex;flex-direction:column;gap:12px;padding:24px;'
        'border:1px solid var(--line-100);border-radius:12px;text-decoration:none;'
        'color:var(--ink-900);background:var(--surface-0)">'
        '<span style="width:40px;height:40px;border-radius:999px;background:var(--navy-100);'
        f'color:var(--navy-700);display:flex;align-items:center;justify-content:center">'
        f"{rd.icon(ic, 20)}</span>"
        f'<strong style="font-size:16px;line-height:24px">{e(title)}</strong>'
        f'<span style="font-size:14px;line-height:22px;color:var(--ink-500)">{e(sub)}</span></a>'
        for href, ic, title, sub in cards)

    return (
        _page_head("Page not found", "That page is not here",
                   "The address may have a typo in it, or the page may have moved. "
                   "Everything below still works.")
        + '<section aria-label="Where to go" class="r-pad" style="padding:40px 24px 64px">'
          '<div style="max-width:1200px;margin:0 auto;display:flex;flex-direction:column;gap:24px">'
          '<p style="margin:0;font-size:16px;line-height:26px;color:var(--ink-700);max-width:70ch">'
          "If you followed a link to a property: listings are read from the agencies' own "
          "websites every four hours, and one that has sold or been withdrawn drops off this "
          "site with it. The listing itself lives on the agent's website, and this site only "
          "ever links to it, so a saved link that has stopped working usually means the place "
          "has gone.</p>"
          '<div class="r-grid" style="display:grid;'
          'grid-template-columns:repeat(4,minmax(0,1fr));gap:24px">'
        + tiles + "</div></div></section>")
