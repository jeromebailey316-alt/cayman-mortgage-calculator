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


def _featured(data: dict, n: int = 4) -> list[dict]:
    """The newest listings with a price, one per area, as the board's four tiles.

    Photos are hotlinked from the agency, as the live site already does: the
    owner confirmed on 14 October that "listings only with permission" means
    attribution and linking, not gating. See REDESIGN-PLAN.md section 4.2.
    """
    ls = [l for l in data.get("listings", []) if l.get("price_kyd")]
    ls.sort(key=lambda l: l.get("scraped_at") or "", reverse=True)
    out, seen = [], set()
    for l in ls:
        area = l.get("location") or ""
        if area and area in seen:
            continue
        seen.add(area)
        out.append(l)
        if len(out) == n:
            break
    return out


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
        + rd.pill_tabs([("buy", "Buy", "/listings/")], value="buy")
        + '<div class="r-grid-2" style="display:grid;grid-template-columns:repeat(6,minmax(0,1fr));'
          'gap:16px;align-items:end">'
        + rd.select_field("District", district_opts, id="fDistrict")
        + rd.select_field("Property type", TYPES, id="fType")
        + rd.input_field("Min price", prefix="CI$", placeholder="No min", id="fMin", value=None)
        + rd.input_field("Max price", prefix="CI$", placeholder="No max", id="fMax", value=None)
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


def _fieldset(legend: str, body: str, aria: str) -> str:
    return (f'<fieldset aria-label="{e(aria)}" style="border:0;margin:0;padding:0;'
            'display:flex;flex-direction:column;gap:16px">'
            f'<legend style="padding:0;font-size:18px;line-height:24px;font-weight:700;'
            f'color:var(--ink-900)">{e(legend)}</legend>{body}</fieldset>')


def _grid(*cells, cols: int = 2) -> str:
    return (f'<div class="r-grid-2" style="display:grid;'
            f'grid-template-columns:repeat({cols},minmax(0,1fr));gap:16px">'
            + "".join(cells) + "</div>")


def _stat(label: str, el_id: str, sub_id: str = "") -> str:
    return ('<div style="display:flex;flex-direction:column;gap:4px;padding:16px 20px;'
            'border:1px solid var(--line-100);border-radius:12px;background:var(--surface-0)">'
            f'<span style="font-size:12px;line-height:16px;font-weight:700;letter-spacing:.06em;'
            f'text-transform:uppercase;color:var(--ink-500)">{e(label)}</span>'
            f'<span id="{e(el_id)}" style="font-size:24px;line-height:32px;font-weight:700;'
            'font-variant-numeric:tabular-nums;color:var(--ink-900)">CI$0</span>'
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
        _fieldset("Property", _grid(
            rd.input_field("Purchase price", bind="price", value=650000, prefix="CI$", step=1000, min_=0),
            rd.input_field("Government valuation, if higher", id="cValuation", prefix="CI$",
                           placeholder="Same as price", step=1000, min_=0, value=None),
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
                           step=50, min_=0, value=None),
            rd.input_field("Gross monthly income", id="cIncome", prefix="CI$", placeholder="Optional",
                           step=100, min_=0, value=None),
            rd.input_field("Cash available", id="cCash", prefix="CI$", placeholder="Optional",
                           step=1000, min_=0, value=None),
        ), "Mortgage")
        + _fieldset("Your household in detail", _grid(
            rd.input_field("Strata fees each month", id="cStrata", prefix="CI$",
                           placeholder="Not known", step=25, min_=0, value=None),
            rd.input_field("Life insurance each month", id="cLife", prefix="CI$", placeholder="0",
                           step=10, min_=0, value=None),
            rd.input_field("Building insurance", id="cBldg", suffix="%/yr",
                           hint="of the purchase price", value=1, step=0.1, min_=0),
            rd.input_field("Maintenance allowance", id="cMaint", suffix="%/yr",
                           hint="of the purchase price", value=1, step=0.1, min_=0),
        ), "Your household in detail")
        + '<label style="display:flex;gap:12px;align-items:center;font-size:14px;'
          'line-height:22px;color:var(--ink-700)">'
          '<input type="checkbox" id="cBldgInStrata"> The strata covers building insurance</label>'
        + _fieldset("Fee assumptions", _grid(
            rd.input_field("Legal fees", id="cLegal", suffix="%", hint="of the price", value=1, step=0.1, min_=0),
            rd.input_field("Bank fee", id="cBank", suffix="%", hint="of the loan", value=1, step=0.1, min_=0),
            rd.input_field("Valuation", id="cValFee", prefix="CI$", value=600, step=50, min_=0),
            rd.input_field("Mortgage stamp duty", id="cMortDuty", prefix="CI$", value=None,
                           readonly=True, inputmode=None, type_="text"),
        ), "Fee assumptions")
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

        + _grid(_stat("Loan amount", "rLoan"), _stat("Deposit", "rDown", "rDownSub"),
                _stat("Total interest", "rInterest", "rInterestSub"),
                _stat("Cash to close", "rCash", "rCashSub"), cols=4)

        + '<section aria-label="Monthly cost of owning" style="display:flex;flex-direction:column;'
          'gap:12px;padding:24px;border:1px solid var(--line-100);border-radius:12px">'
          '<h2 style="margin:0;font-size:20px;line-height:28px;font-weight:700">'
          "Monthly cost of owning</h2>"
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
          '<p class="cmc-swipe">Swipe sideways to see every column.</p></section>')

    return (
        '<section aria-label="Page title" class="r-pad" style="background:var(--navy-100);'
        'padding:40px 24px">'
        '<div style="max-width:1200px;margin:0 auto;display:flex;flex-direction:column;gap:12px">'
        '<nav aria-label="Breadcrumb" style="font-size:12px;line-height:16px;font-weight:500;'
        'color:var(--ink-500)"><a href="/" style="color:var(--ink-500);text-decoration:none">Home</a>'
        ' › Mortgage calculator</nav>'
        '<h1 style="margin:0;font-size:40px;line-height:48px;font-weight:700;letter-spacing:-.02em">'
        "Cayman mortgage calculator</h1>"
        '<p style="margin:0;font-size:16px;line-height:26px;color:var(--ink-700);max-width:70ch">'
        "Your monthly payment and the cash you need on the day, with Cayman stamp duty, "
        "legal fees and bank charges included. Every figure is an estimate.</p></div></section>"

        '<section aria-label="Inputs" class="r-pad" style="padding:40px 24px 64px">'
        '<div class="r-grid" style="max-width:1200px;margin:0 auto;display:grid;'
        'grid-template-columns:minmax(0,5fr) minmax(0,7fr);gap:32px;align-items:start">'
        f'<form id="rdCalc" style="display:flex;flex-direction:column;gap:24px">{inputs}</form>'
        '<div aria-label="Results" style="display:flex;flex-direction:column;gap:24px">'
        f"{results}</div></div></section>")


def _page_head(crumb: str, title: str, lede: str) -> str:
    return ('<section aria-label="Page title" class="r-pad" style="background:var(--navy-100);'
            'padding:40px 24px">'
            '<div style="max-width:1200px;margin:0 auto;display:flex;flex-direction:column;gap:12px">'
            '<nav aria-label="Breadcrumb" style="font-size:12px;line-height:16px;font-weight:500;'
            'color:var(--ink-500)"><a href="/" style="color:var(--ink-500);text-decoration:none">'
            f"Home</a> › {e(crumb)}</nav>"
            '<h1 style="margin:0;font-size:40px;line-height:48px;font-weight:700;'
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
        '<form id="rdAfford" style="display:flex;flex-direction:column;gap:24px">'
        + _fieldset("What you earn and owe", _grid(
            rd.input_field("Gross monthly income", id="aIncome", prefix="CI$", value=9000,
                           step=100, min_=0),
            rd.input_field("Other monthly debts", id="aDebts", prefix="CI$", value=0,
                           step=50, min_=0),
            rd.input_field("Debt service ceiling", id="aCeiling", suffix="%",
                           hint="of gross income", value=40, step=1, min_=1, max_=100),
            rd.input_field("Cash available", id="aCash", prefix="CI$", value=120000,
                           step=1000, min_=0),
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
            + _two_col(form, results))


def equity(data: dict) -> str:
    """Ported from cmc-redesign/pages/Equity.dc.html (HANDOFF 5.4)."""
    form = (
        '<form id="rdEquity" style="display:flex;flex-direction:column;gap:24px">'
        + _fieldset("Your property", _grid(
            rd.input_field("What it is worth now", id="eValue", prefix="CI$", value=800000,
                           step=5000, min_=0),
            rd.input_field("Mortgage balance", id="eBalance", prefix="CI$", value=400000,
                           step=5000, min_=0),
            rd.input_field("Other secured loans", id="eOther", prefix="CI$", value=0,
                           step=1000, min_=0),
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
            + _two_col(form, results))


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
