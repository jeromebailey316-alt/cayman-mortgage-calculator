"""Build the redesigned site into site-rd/.

Separate from build_site.py on purpose: the live build keeps working untouched
while the redesign is assembled page by page. The two are merged once every
route in HANDOFF section 3 exists.

    .venv/bin/python build_redesign.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import redesign as rd
import rd_pages
from scraper import run as scrape_run

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "site-rd"
BRAND = ROOT / "cmc-redesign" / "brand"

# Routes built so far. The rest of HANDOFF section 3 lands here as each is ported.
PAGES = {
    "": {
        "title": "Cayman Mortgage Calculator: what a Cayman home really costs",
        "description": ("Work out a Cayman mortgage with stamp duty, legal fees and closing "
                        "costs included, then see the homes for sale that fit."),
        "build": lambda data: rd_pages.home(data),
        "active": "/",
    },
    "calculator": {
        "title": "Cayman mortgage calculator: payment, stamp duty and closing costs",
        "description": ("Work out a Cayman mortgage: the monthly payment, the stamp duty at "
                        "your buyer status, and the cash you need on the day you buy."),
        "build": lambda data: rd_pages.calculator(data),
        "active": "/calculator/",
        "scripts": ["/assets/core.js", "/assets/rd-calculator.js"],
    },
    "affordability": {
        "title": "What can you afford? A Cayman affordability calculator",
        "description": ("The most you can buy in the Cayman Islands, from what your income "
                        "carries each month and what your cash covers on the day."),
        "build": lambda data: rd_pages.affordability(data),
        "active": "/affordability/",
        "scripts": ["/assets/core.js", "/assets/rd-afford.js"],
    },
    "equity": {
        "title": "Cayman home equity calculator: how much could you release?",
        "description": ("What your Cayman property is worth less what is secured against it, "
                        "and how much of that a lender would advance."),
        "build": lambda data: rd_pages.equity(data),
        "active": "/equity/",
        "scripts": ["/assets/core.js", "/assets/rd-afford.js"],
    },
    "about": {
        "title": "About the Cayman Mortgage Calculator",
        "description": "Who runs this free Cayman Islands mortgage calculator, and why.",
        "build": rd_pages.from_board("About"), "active": "/about/",
    },
    "contact": {
        "title": "Contact the Cayman Mortgage Calculator",
        "description": "How to reach us: one inbox and an Instagram account, no forms.",
        "build": rd_pages.from_board("Contact"), "active": "/contact/",
    },
    "agents": {
        "title": "For real-estate agents and agencies in the Cayman Islands",
        "description": ("How Cayman agencies can have their listings shown to buyers who "
                        "already know their numbers."),
        "build": rd_pages.from_board("Agents", {"sample": rd_pages.AGENT_SAMPLE}),
        "active": "/agents/",
    },
    "privacy": {
        "title": "Privacy: Cayman Mortgage Calculator",
        "description": "What this site stores, what it measures, and what it never collects.",
        "build": rd_pages.from_board("Privacy"), "active": "/privacy/",
    },
    "terms": {
        "title": "Terms of use: Cayman Mortgage Calculator",
        "description": "The terms on which this free Cayman mortgage calculator is offered.",
        "build": rd_pages.from_board("Terms"), "active": "/terms/",
    },
    "guides/stamp-duty": {
        "title": "Cayman Islands stamp duty: rates, bands and concessions",
        "description": ("What stamp duty costs when you buy in the Cayman Islands, who "
                        "qualifies for the Caymanian concession, and when it is paid."),
        "build": lambda data: rd_pages.stamp_duty_guide(data),
        "active": "/guides/stamp-duty/",
        "scripts": ["/assets/core.js", "/assets/rd-guides.js"],
    },
    "guides/closing-costs": {
        "title": "Closing costs in the Cayman Islands: the full checklist",
        "description": ("Every cost between offer and keys in the Cayman Islands, which are "
                        "fixed by law and which you should get quoted."),
        "build": lambda data: rd_pages.closing_costs_guide(data),
        "active": "/guides/closing-costs/",
        "scripts": ["/assets/core.js", "/assets/rd-guides.js"],
    },
    "guides/refinancing": {
        "title": "Refinancing a Cayman mortgage: does a new rate pay for itself?",
        "description": ("Work out the break-even on refinancing in the Cayman Islands, with "
                        "the stamp duty on a new charge included."),
        "build": lambda data: rd_pages.refinancing_guide(data),
        "active": "/guides/refinancing/",
        "scripts": ["/assets/core.js", "/assets/rd-guides.js"],
    },
    "rent-vs-buy": {
        "title": "Rent or buy in the Cayman Islands: the break-even year",
        "description": ("Renting against buying in Cayman, with stamp duty, fees and upkeep "
                        "included, and the year buying pulls ahead."),
        "build": lambda data: rd_pages.rent_vs_buy(data),
        "active": "/rent-vs-buy/",
        "scripts": ["/assets/core.js", "/assets/rd-rent.js"],
    },
    "listings": {
        "title": "Homes for sale in the Cayman Islands: priced for your mortgage",
        "description": ("Every listing from the Cayman agencies, priced through your own "
                        "deposit, rate and term, with stamp duty and the monthly worked out."),
        "build": lambda data: rd_pages.listings(data),
        "active": "/listings/",
        # core.js supplies stamp duty in the comparison, the same engine the
        # calculator uses, so the two figures cannot disagree.
        "scripts": ["/assets/core.js", "/assets/rd-listings.js"],
        "icons_for_js": True,
    },
}


def build(data: dict, canonical: str = "") -> Path:
    if OUT.exists():
        shutil.rmtree(OUT)
    assets = OUT / "assets"
    assets.mkdir(parents=True)

    css = rd.stylesheet()
    (assets / "rd.css").write_text(css)
    stamp = hashlib.sha1(css.encode()).hexdigest()[:8]
    href = f"/assets/rd.css?v={stamp}"

    for js in ("rd-inputs.js", "rd-listings.js", "rd-calculator.js", "rd-afford.js", "rd-guides.js", "rd-rent.js", "core.js"):
        shutil.copy(ROOT / "web" / js, assets / js)
    for logo in ("cmc-secondary-color.svg", "cmc-secondary-reversed.svg"):
        shutil.copy(BRAND / "logos" / logo, assets / logo)
    for ico in ("favicon.svg", "favicon.ico"):
        src = BRAND / "icons" / ico
        if src.exists():
            shutil.copy(src, OUT / ico)

    base = canonical.rstrip("/") + "/" if canonical else ""
    for path, meta in PAGES.items():
        body = meta["build"](data)
        html = rd.page(meta["title"], meta["description"], body,
                       active=meta["active"], canonical=base + path if base else "",
                       css_href=href, scripts=meta.get("scripts", ()),
                       icons_for_js=meta.get("icons_for_js", False))
        target = OUT / path / "index.html" if path else OUT / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html)

    (OUT / "listings.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    (OUT / ".nojekyll").write_text("")
    return OUT


if __name__ == "__main__":
    d = scrape_run.load()
    if not d:
        raise SystemExit("No data/listings.json yet.")
    out = build(d)
    pages = sum(1 for _ in out.rglob("index.html"))
    print(f"Wrote {out.relative_to(ROOT)}/ - {pages} page(s), {len(d['listings'])} listings")
