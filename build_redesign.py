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
        # the panel's three modes run on the engine, so core.js comes with it
        "scripts": ["/assets/core.js", "/assets/rd-home.js"],
    },
    "calculator": {
        "title": "Cayman mortgage calculator: payment, stamp duty and closing costs",
        "description": ("Work out a Cayman mortgage: the monthly payment, the stamp duty at "
                        "your buyer status, and the cash you need on the day you buy."),
        "build": lambda data: rd_pages.calculator(data),
        "active": "/calculator/",
        "scripts": [
            # As the board loads them, so window.XLSX and window.jspdf are present
            # rather than appearing only after the first click. They sit at the end
            # of the body, so they do not block the first paint.
            "https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js",
            "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js",
            "/assets/core.js", "/assets/rd-calculator.js", "/assets/rd-export.js",
        ],
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
                        "how much a lender would advance, and what releasing it costs a month "
                        "and in stamp duty on the larger charge."),
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
        "build": lambda data: rd_pages.privacy(data), "active": "/privacy/",
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


SITE = "https://caymanmortgagecalculator.com"

CALCULATORS = {
    "calculator": ("Cayman mortgage calculator", "Monthly payment, stamp duty and cash to close."),
    "affordability": ("Cayman affordability calculator", "The most you can buy on your income and cash."),
    "equity": ("Cayman home equity calculator", "What you could release against your property."),
    "rent-vs-buy": ("Cayman rent versus buy calculator", "The year buying pulls ahead of renting."),
}

CRUMBS = {
    "calculator": "Mortgage calculator", "affordability": "Affordability", "equity": "Equity",
    "rent-vs-buy": "Rent vs Buy", "listings": "Listings",
    "guides/stamp-duty": "Stamp duty", "guides/closing-costs": "Closing costs",
    "guides/refinancing": "Refinancing", "about": "About", "contact": "Contact",
    "agents": "For agents", "privacy": "Privacy", "terms": "Terms",
}

# Drawn from each guide's own FAQ section, so the markup and the page agree.
FAQS = {
    "guides/stamp-duty": [
        ("How much is stamp duty when buying property in the Cayman Islands?",
         "Stamp duty on a transfer is 7.5% of the higher of the price and the Government "
         "valuation, rising to 10% of the whole value once the price reaches CI$2,000,000. "
         "A Caymanian buying a first property pays nothing up to CI$550,000 on a home and "
         "3.75% on the part up to CI$650,000."),
        ("When is stamp duty paid?",
         "Within 45 days of the documents being executed. After that, interest accrues on "
         "the unpaid duty."),
        ("Is stamp duty charged on the mortgage as well?",
         "Yes. Mortgage stamp duty is 1% of the sum secured up to CI$300,000 and 1.5% of "
         "the whole sum above that. It is charged on the charge document, so it applies to "
         "a new mortgage and to further borrowing."),
    ],
    "guides/refinancing": [
        ("Does refinancing a Cayman mortgage trigger stamp duty again?",
         "If the refinance creates a new legal charge, which it does when you move to a "
         "different lender, mortgage stamp duty is payable on the sum secured: 1% up to "
         "CI$300,000 and 1.5% of the whole sum above that."),
        ("How do I work out whether refinancing is worth it?",
         "Divide the total cost of switching by the monthly saving. That is the number of "
         "months before you are ahead. If you expect to keep the mortgage longer than that, "
         "it pays for itself."),
    ],
}


def _jsonld_for(path: str) -> list:
    out = [rd.SITE_JSONLD, rd.ORG_JSONLD]
    if path in CALCULATORS:
        name, desc = CALCULATORS[path]
        out.append(rd.software_jsonld(name, f"{SITE}/{path}/", desc))
    if path in FAQS:
        out.append(rd.faq_jsonld(FAQS[path]))
    if path in CRUMBS:
        out.append(rd.breadcrumb_jsonld(CRUMBS[path], f"{SITE}/{path}/"))
    return out


def manifest() -> str:
    return json.dumps({
        "name": rd.SITE_NAME,
        "short_name": "Cayman Mortgage",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#011533",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/icon-maskable-512.png", "sizes": "512x512", "type": "image/png",
             "purpose": "maskable"},
        ],
    }, indent=2)


def sitemap(base: str, lastmod: str) -> str:
    rows = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path in PAGES:
        pri = "1.0" if path == "" else "0.9" if path in CALCULATORS or path == "listings" else "0.7"
        rows += ["  <url>", f"    <loc>{base}{path}{'/' if path else ''}</loc>",
                 f"    <lastmod>{lastmod}</lastmod>",
                 f"    <priority>{pri}</priority>", "  </url>"]
    rows.append("</urlset>")
    return "\n".join(rows) + "\n"


DOMAIN = "caymanmortgagecalculator.com"


def build(data: dict, canonical: str = "") -> Path:
    if OUT.exists():
        shutil.rmtree(OUT)
    assets = OUT / "assets"
    assets.mkdir(parents=True)

    css = rd.stylesheet()
    (assets / "rd.css").write_text(css)
    stamp = hashlib.sha1(css.encode()).hexdigest()[:8]
    href = f"/assets/rd.css?v={stamp}"

    for js in ("rd-inputs.js", "rd-listings.js", "rd-calculator.js", "rd-afford.js", "rd-guides.js", "rd-rent.js", "rd-export.js", "rd-home.js", "core.js"):
        shutil.copy(ROOT / "web" / js, assets / js)
    for logo in ("cmc-secondary-color.svg", "cmc-secondary-reversed.svg"):
        shutil.copy(BRAND / "logos" / logo, assets / logo)
    for ico in ("favicon.svg", "favicon.ico", "icon-16.png", "icon-32.png", "icon-48.png",
                "apple-touch-icon.png", "icon-192.png", "icon-512.png",
                "icon-maskable-512.png", "og-image.png"):
        src = BRAND / "icons" / ico
        if src.exists():
            shutil.copy(src, OUT / ico)
    (OUT / "site.webmanifest").write_text(manifest())

    for path, meta in PAGES.items():
        body = meta["build"](data)
        url = f"{SITE}/{path}/" if path else f"{SITE}/"
        html = rd.page(meta["title"], meta["description"], body,
                       active=meta["active"], canonical=url,
                       css_href=href, scripts=meta.get("scripts", ()),
                       icons_for_js=meta.get("icons_for_js", False),
                       jsonld=_jsonld_for(path),
                       og_image=f"{SITE}/og-image.png")
        target = OUT / path / "index.html" if path else OUT / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html)

    (OUT / "listings.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    (OUT / ".nojekyll").write_text("")
    # Without this GitHub Pages drops the custom domain on the next deploy.
    (OUT / "CNAME").write_text(DOMAIN + "\n")
    # Served for any address that does not exist, at any depth.
    (OUT / "404.html").write_text(rd.page(
        "Page not found: " + rd.SITE_NAME,
        "That page is not here. The calculators and the current listings are all still available.",
        rd_pages.not_found(data), active="", canonical="", css_href=href,
        jsonld=[rd.SITE_JSONLD, rd.ORG_JSONLD]))
    lastmod = (data.get("generated_at") or "")[:10]
    (OUT / "sitemap.xml").write_text(sitemap(SITE + "/", lastmod))
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")

    # Without ads.txt at the root, AdSense treats unauthorised resellers as
    # unverified and buyers bid less or not at all. f08c47fec0942fa0 is
    # Google's own certification id, the same for every publisher.
    if rd.ADSENSE_CLIENT:
        pub = rd.ADSENSE_CLIENT.replace("ca-", "", 1)
        (OUT / "ads.txt").write_text(
            f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n")
    return OUT


if __name__ == "__main__":
    d = scrape_run.load()
    if not d:
        raise SystemExit("No data/listings.json yet.")
    out = build(d)
    pages = sum(1 for _ in out.rglob("index.html"))
    print(f"Wrote {out.relative_to(ROOT)}/ - {pages} page(s), {len(d['listings'])} listings")
