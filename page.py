"""Assembles the pages: shared head, shared header/nav, and the page's own body.

Fragments live in web/ (home.html, index.html). The stylesheet is web/app.css,
linked on the website and inlined for the single-file build.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
APP_FRAGMENT = WEB / "index.html"
HOME_FRAGMENT = WEB / "home.html"
RENT_FRAGMENT = WEB / "rent.html"
EQUITY_FRAGMENT = WEB / "equity.html"
CSS = WEB / "app.css"
CORE = WEB / "core.js"

SITE_NAME = "Cayman Mortgage Calculator"
SITE_URL = "https://caymanmortgagecalculator.com"
def _stamp(path: Path) -> str:
    """Short content hash. A changed stylesheet or engine must not be served from a
    browser cache holding the previous deploy — that mixes old code with new pages."""
    return hashlib.sha1(path.read_bytes()).hexdigest()[:8]


CSS_HREF = "/assets/app.css"

# Cloudflare Web Analytics: cookieless, so no consent banner is needed. Paste the
# token from the Cloudflare dashboard (Analytics -> Web Analytics) to switch it on.
CF_ANALYTICS_TOKEN = "b24be8194698467584c89adf2b99a705"
# Only needed if Search Console is verified by meta tag instead of a DNS record.
GOOGLE_SITE_VERIFICATION = ""
CORE_HREF = "/assets/core.js"

# Questions and answers shown on the front page and repeated as FAQ structured data.
# Both must stay in step: Google treats FAQ markup that is not visible as a violation.
FAQ = [
    ("How much is stamp duty when buying property in the Cayman Islands?",
     "Stamp duty on a transfer is 7.5% of the dutiable value, or 10% of the whole value once the price reaches "
     "CI$2,000,000. A Caymanian buying a first property pays nothing up to CI$550,000 on a home, then 3.75% on the "
     "next CI$100,000; buying jointly, two to ten Caymanians have a CI$600,000 threshold."),
    ("Is there property tax in the Cayman Islands?",
     "No. There is no annual property tax, no income tax and no capital gains tax in the Cayman Islands. The costs "
     "to plan for are the one-off duty and fees when you buy, and then strata fees, insurance and upkeep."),
    ("Is stamp duty charged on the mortgage as well?",
     "Yes. Mortgage stamp duty is 1% of the sum secured up to CI$300,000, and 1.5% of the whole sum above that. It "
     "is charged on the charge document, so it applies to a new mortgage and to further borrowing."),
    ("When does stamp duty have to be paid?",
     "Within 45 days of the documents being executed. After that, interest accrues on the unpaid duty."),
    ("Can a foreigner buy property in the Cayman Islands?",
     "Yes. There are no restrictions on foreign ownership of residential property and no licence is needed for a "
     "normal purchase, though a land holding licence can apply to large acreage or business use. Title is "
     "registered and guaranteed by the government."),
    ("How much deposit do Cayman banks ask for?",
     "Commonly 10% to 15% on a primary home for Caymanians and residents, and more from non-residents, where "
     "financing is generally available up to about 70% of value over shorter terms. Raw land usually needs around "
     "50% down. Each bank sets its own criteria."),
]

PAGES = {
    "home": {
        "path": "",
        "title": f"{SITE_NAME}: stamp duty and closing costs",
        "description": ("What buying in the Cayman Islands really costs: stamp duty, mortgage duty, registry, legal "
                        "and bank fees — plus the homes for sale that fit your budget."),
    },
    "rent": {
        "path": "rent-vs-buy/",
        "title": "Rent or buy in Cayman: the break-even year",
        "description": ("Renting against buying in Cayman: mortgage, strata, insurance, upkeep and duty versus rent "
                        "and rent rises, with the year buying pulls ahead."),
    },
    "equity": {
        "path": "equity/",
        "title": "Cayman home equity calculator: how much can you release?",
        "description": ("How much equity is in your Cayman property, how much a bank would lend against it at 90, 80 "
                        "or 70% loan-to-value, and what releasing it would cost."),
    },
    "404": {
        "path": "404.html",
        "title": f"Page not found — {SITE_NAME}",
        "description": "That page doesn't exist. The calculators and listings are a click away.",
    },
    "calculator": {
        "path": "calculator/",
        "title": "Cayman mortgage and stamp duty calculator",
        "description": ("Work out your monthly payment and the real cash to close in the Cayman Islands, then see the "
                        "listings that fit, priced through your own rate, term and deposit."),
    },
}

# The one piece that has to run before first paint: put a saved light/dark choice on
# <html> so the page never flashes the wrong theme. Kept tiny because it blocks.
THEME_PREPAINT = ("(function(){try{var t=localStorage.getItem('caymanMortgage.theme');"
                  "if(t==='dark'||t==='light')document.documentElement.setAttribute('data-theme',t);}catch(e){}})();")

# Everything else the shared header needs (the light/dark button, the sideways nav on
# a phone) loads deferred from /assets/site.js.
SITE_JS = WEB / "site.js"
SITE_JS_HREF = "/assets/site.js"


ICONS = ('<link rel="icon" href="/favicon.ico" sizes="48x48">'
         '<link rel="icon" href="/favicon.svg" type="image/svg+xml">'
         '<link rel="apple-touch-icon" href="/apple-touch-icon.png">'
         '<link rel="manifest" href="/site.webmanifest">')


def nav(active: str, root: str = "/") -> str:
    """The header every page shares: logo, links, light/dark button."""
    def link(key, label, href=None):
        here = ' aria-current="page"' if key == active else ""
        return f'<a href="{href or root + PAGES[key]["path"]}"{here}>{label}</a>'
    return (
        '<a class="skip-link" href="#main">Skip to content</a>'
        '<header class="site">'
        f'<a class="brand" href="{root}" aria-label="{SITE_NAME}, home">'
        f'<img class="logo light-only" src="{root}assets/cmc-secondary-color.svg" width="594" height="128" alt="{SITE_NAME}">'
        f'<img class="logo dark-only" src="{root}assets/cmc-secondary-reversed.svg" width="594" height="128" alt="" aria-hidden="true">'
        '</a>'
        '<nav class="site-nav" aria-label="Site">'
        + link("home", "Home")
        + link("calculator", "Mortgage Calculator")
        + link("equity", "Equity Calculator")
        + f'<a href="{root}calculator/#listings">Listings</a>'
        + link("rent", "Rent vs Buy")
        + '</nav>'
        '<div class="site-tools">'
        '<button class="btn icon" id="themeBtn" type="button" aria-label="Switch to dark mode" title="Switch to dark mode"></button>'
        '</div>'
        '</header>'
    )


def json_ld(page: str) -> str:
    """Structured data. The FAQ answers repeat what the front page says in visible
    text — Google requires the two to match."""
    site = {"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "url": SITE_URL + "/"}
    blocks = [site]
    APP_NAMES = {
        "calculator": "Cayman mortgage and stamp duty calculator",
        "equity": "Cayman home equity calculator",
        "rent": "Cayman rent versus buy calculator",
    }
    if page in APP_NAMES:
        blocks.append({
            "@context": "https://schema.org", "@type": "WebApplication",
            "name": APP_NAMES[page],
            "url": f"{SITE_URL}/{PAGES[page]['path']}",
            "applicationCategory": "FinanceApplication",
            "operatingSystem": "Any",
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "KYD"},
            "description": PAGES[page]["description"],
        })
    if page == "home":
        blocks.append({
            "@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q,
                            "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ],
        })
    return "".join(f'<script type="application/ld+json">{json.dumps(b, ensure_ascii=False)}</script>' for b in blocks)


def head(page: str, canonical: str = "", inline_css: bool = False) -> str:
    meta = PAGES[page]
    css = (f"<style>{CSS.read_text()}</style>" if inline_css
           else f'<link rel="stylesheet" href="{CSS_HREF}?v={_stamp(CSS)}">')
    og_image = (f'<meta property="og:image" content="{canonical.rstrip("/")}/assets/og-image.png">'
                '<meta name="twitter:card" content="summary_large_image">') if canonical else ""
    return (
        '<!doctype html><html lang="en"><head>'
        '<meta charset="utf-8">'
        + ("" if inline_css else CSP_SLOT)
        + '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        f'<title>{meta["title"]}</title>'
        f'<meta name="description" content="{meta["description"]}">'
        '<meta name="color-scheme" content="light dark">'
        '<meta name="theme-color" content="#0E2A47">'
        + ("" if inline_css else ICONS)
        + f'<meta property="og:title" content="{meta["title"]}">'
        f'<meta property="og:description" content="{meta["description"]}">'
        '<meta property="og:type" content="website">'
        f'<meta property="og:site_name" content="{SITE_NAME}">'
        + og_image
        + (f'<link rel="canonical" href="{canonical}">' if canonical else "")
        + '<link rel="preconnect" href="https://fonts.googleapis.com">'
          '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        + '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=Instrument+Sans:wght@400..600&display=swap">'
        + '<style>:root{box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
          'body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>'
        + ("" if inline_css else json_ld(page))
        + (f'<meta name="google-site-verification" content="{GOOGLE_SITE_VERIFICATION}">'
           if GOOGLE_SITE_VERIFICATION and not inline_css else "")
        + (f"<script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' "
           f'data-cf-beacon=\'{{"token": "{CF_ANALYTICS_TOKEN}"}}\'></script>'
           if CF_ANALYTICS_TOKEN and not inline_css else "")
        + css
        + f"<script>{THEME_PREPAINT}</script>"
        # Deferred: fetched in parallel, run in order once the HTML is parsed. The page
        # scripts wait for DOMContentLoaded, which fires after both have run.
        + (f"<script>{CORE.read_text()}</script><script>{SITE_JS.read_text()}</script>" if inline_css
           else f'<script defer src="{CORE_HREF}?v={_stamp(CORE)}"></script>'
                f'<script defer src="{SITE_JS_HREF}?v={_stamp(SITE_JS)}"></script>')
        + "</head><body>"
    )


TAIL = "</body></html>"

# Content Security Policy. GitHub Pages cannot send response headers, so it goes in a
# <meta> tag, filled in last by finish() once the page is assembled: every inline
# script that runs is allowed by its exact SHA-256 hash, so editing a script can never
# leave it blocked. Data blocks (JSON-LD, the listings JSON) don't execute and need none.
CSP_SLOT = "<!--CSP-->"
CSP_BASE = {
    "default-src": ["'self'"],
    "script-src": ["'self'", "https://static.cloudflareinsights.com"],
    # inline style="" attributes are used throughout; styles can't run code
    "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
    "font-src": ["'self'", "https://fonts.gstatic.com"],
    # listing photos are hotlinked from the agencies' own websites
    "img-src": ["'self'", "https:", "data:"],
    "connect-src": ["'self'", "https://cloudflareinsights.com"],
    "manifest-src": ["'self'"],
    "object-src": ["'none'"],
    "base-uri": ["'self'"],
    "form-action": ["'self'"],
}
_INLINE_SCRIPT = re.compile(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", re.S)


def _runs(attrs: str) -> bool:
    """True for a script block the browser executes (no src, a JavaScript type)."""
    if "src=" in attrs:
        return False
    m = re.search(r"""type=["']?([^"' >]+)""", attrs)
    return not m or m.group(1).lower() in ("text/javascript", "module", "application/javascript")


def finish(html: str) -> str:
    hashes = []
    for m in _INLINE_SCRIPT.finditer(html):
        if _runs(m.group("attrs")):
            digest = base64.b64encode(hashlib.sha256(m.group("body").encode("utf-8")).digest()).decode()
            hashes.append(f"'sha256-{digest}'")
    policy = {k: list(v) for k, v in CSP_BASE.items()}
    policy["script-src"] += sorted(set(hashes))
    value = "; ".join(f"{k} {' '.join(v)}" for k, v in policy.items())
    return html.replace(CSP_SLOT, f'<meta http-equiv="Content-Security-Policy" content="{value}">', 1)


def render_app(data: dict | None, canonical: str = "", inline_css: bool = False, root: str = "/") -> str:
    """The calculator page. `data` None means it fetches listings.json beside itself."""
    slot = "null" if data is None else json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    body = APP_FRAGMENT.read_text().replace("__LISTINGS_JSON__", slot).replace("__NAV__", nav("calculator", root))
    return finish(head("calculator", canonical, inline_css) + body + TAIL)


def render_home(body: str, canonical: str = "") -> str:
    return finish(head("home", canonical) + body.replace("__NAV__", nav("home")) + TAIL)


def render_rent(canonical: str = "") -> str:
    return finish(head("rent", canonical) + RENT_FRAGMENT.read_text().replace("__NAV__", nav("rent")) + TAIL)


def render_equity(canonical: str = "") -> str:
    return finish(head("equity", canonical) + EQUITY_FRAGMENT.read_text().replace("__NAV__", nav("equity")) + TAIL)


NOT_FOUND_BODY = """<div class="wrap">
  __NAV__
  <main id="main" tabindex="-1">
    <section class="hero-band">
      <div>
        <h1>That page isn't here</h1>
        <p class="lede">The address may have a typo, or the page has moved. Everything on the site is one click
          away from the links below.</p>
        <div class="hero-cta">
          <a class="go" href="/calculator/">Mortgage calculator</a>
          <a class="alt" href="/calculator/#listings">Browse listings</a>
          <a class="alt" href="/">Home</a>
        </div>
      </div>
    </section>
  </main>
</div>"""


def render_404() -> str:
    """GitHub Pages serves /404.html for any address that doesn't exist. Absolute links
    throughout, because it can be shown at any depth; noindex so it never ranks."""
    html = head("404").replace("<meta name=\"color-scheme\"",
                               '<meta name="robots" content="noindex"><meta name="color-scheme"', 1)
    return finish(html + NOT_FOUND_BODY.replace("__NAV__", nav("404")) + TAIL)


# Kept so older calls (build.py) keep working.
def render(data: dict | None, canonical: str = "") -> str:
    return render_app(data, canonical)
