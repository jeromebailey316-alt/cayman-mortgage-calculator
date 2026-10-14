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

    No photos: the board's own caption says they appear once agencies confirm
    permission, and that confirmation is still outstanding for all but two
    agencies. See REDESIGN-PLAN.md section 4.2.
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
        "Each tile opens the listing on the agent's own site. Photos appear once agencies "
        "confirm permission.</p></div></section>"

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
