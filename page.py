"""Assembles the pages: shared head, shared header/nav, and the page's own body.

Fragments live in web/ (home.html, index.html). The stylesheet is web/app.css,
linked on the website and inlined for the single-file build.
"""
from __future__ import annotations

import json
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
CSS_HREF = "/assets/app.css"

# Cloudflare Web Analytics: cookieless, so no consent banner is needed. Paste the
# token from the Cloudflare dashboard (Analytics -> Web Analytics) to switch it on.
CF_ANALYTICS_TOKEN = ""
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
    "calculator": {
        "path": "calculator/",
        "title": "Cayman mortgage and stamp duty calculator",
        "description": ("Work out your monthly payment and the real cash to close in the Cayman Islands, then see the "
                        "listings that fit, priced through your own rate, term and deposit."),
    },
}

# Applied before first paint on every page, and binds the light/dark button.
THEME_JS = """
(function () {
  var KEY = 'caymanMortgage.theme';
  var SUN = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2.2M12 19.3v2.2M4.3 4.3l1.6 1.6M18.1 18.1l1.6 1.6M2.5 12h2.2M19.3 12h2.2M4.3 19.7l1.6-1.6M18.1 5.9l1.6-1.6"/></svg>';
  var MOON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.5 14.3A8.5 8.5 0 0 1 9.7 3.5a8.5 8.5 0 1 0 10.8 10.8z"/></svg>';
  function saved() { try { var t = localStorage.getItem(KEY); return t === 'dark' || t === 'light' ? t : null; } catch (e) { return null; } }
  function systemDark() { return !!(window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches); }
  var t = saved();
  if (t) document.documentElement.setAttribute('data-theme', t);   // before paint: no flash
  function apply(choice) {
    var root = document.documentElement;
    if (choice) root.setAttribute('data-theme', choice); else root.removeAttribute('data-theme');
    var dark = choice ? choice === 'dark' : systemDark(), btn = document.getElementById('themeBtn');
    if (!btn) return;
    btn.innerHTML = dark ? SUN : MOON;
    var label = dark ? 'Switch to light mode' : 'Switch to dark mode';
    btn.setAttribute('aria-label', label); btn.title = label;
  }
  function start() {
    apply(saved());
    var btn = document.getElementById('themeBtn');
    if (btn) btn.addEventListener('click', function () {
      var next = (saved() ? saved() === 'dark' : systemDark()) ? 'light' : 'dark';
      try { localStorage.setItem(KEY, next); } catch (e) { /* ignore */ }
      apply(next);
    });
    if (window.matchMedia) {
      var mq = matchMedia('(prefers-color-scheme: dark)');
      var onChange = function () { if (!saved()) apply(null); };
      if (mq.addEventListener) mq.addEventListener('change', onChange);
      else if (mq.addListener) mq.addListener(onChange);
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();

  // On a phone the nav scrolls sideways: bring the current page's tab into view,
  // and fade the right edge while there is more to see.
  function navScroll() {
    var nav = document.querySelector('.site-nav');
    if (!nav) return;
    var here = nav.querySelector('a[aria-current="page"]');
    if (here && here.scrollIntoView) {
      try { here.scrollIntoView({ inline: 'center', block: 'nearest' }); } catch (e) { /* ignore */ }
    }
    var mark = function () {
      var more = nav.scrollWidth - nav.clientWidth - nav.scrollLeft > 8;
      nav.classList.toggle('more', more);
    };
    mark();
    nav.addEventListener('scroll', mark, { passive: true });
    window.addEventListener('resize', mark);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', navScroll); else navScroll();
})();
"""

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
    if page == "calculator":
        blocks.append({
            "@context": "https://schema.org", "@type": "WebApplication",
            "name": "Cayman mortgage and stamp duty calculator",
            "url": f"{SITE_URL}/calculator/",
            "applicationCategory": "FinanceApplication",
            "operatingSystem": "Any",
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "KYD"},
            "description": PAGES["calculator"]["description"],
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
    css = f"<style>{CSS.read_text()}</style>" if inline_css else f'<link rel="stylesheet" href="{CSS_HREF}">'
    og_image = (f'<meta property="og:image" content="{canonical.rstrip("/")}/assets/og-image.png">'
                '<meta name="twitter:card" content="summary_large_image">') if canonical else ""
    return (
        '<!doctype html><html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
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
        + '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=Instrument+Sans:wght@400..600&display=swap">'
        + '<style>:root{box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
          'body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>'
        + ("" if inline_css else json_ld(page))
        + (f'<meta name="google-site-verification" content="{GOOGLE_SITE_VERIFICATION}">'
           if GOOGLE_SITE_VERIFICATION and not inline_css else "")
        + (f"<script defer src='https://static.cloudflareinsights.com/beacon.min.js' "
           f'data-cf-beacon=\'{{"token": "{CF_ANALYTICS_TOKEN}"}}\'></script>'
           if CF_ANALYTICS_TOKEN and not inline_css else "")
        + css
        + (f"<script>{CORE.read_text()}</script>" if inline_css else f'<script src="{CORE_HREF}"></script>')
        + f"<script>{THEME_JS}</script>"
        + "</head><body>"
    )


TAIL = "</body></html>"


def render_app(data: dict | None, canonical: str = "", inline_css: bool = False, root: str = "/") -> str:
    """The calculator page. `data` None means it fetches listings.json beside itself."""
    slot = "null" if data is None else json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    body = APP_FRAGMENT.read_text().replace("__LISTINGS_JSON__", slot).replace("__NAV__", nav("calculator", root))
    return head("calculator", canonical, inline_css) + body + TAIL


def render_home(body: str, canonical: str = "") -> str:
    return head("home", canonical) + body.replace("__NAV__", nav("home")) + TAIL


def render_rent(canonical: str = "") -> str:
    return head("rent", canonical) + RENT_FRAGMENT.read_text().replace("__NAV__", nav("rent")) + TAIL


def render_equity(canonical: str = "") -> str:
    return head("equity", canonical) + EQUITY_FRAGMENT.read_text().replace("__NAV__", nav("equity")) + TAIL


# Kept so older calls (build.py) keep working.
def render(data: dict | None, canonical: str = "") -> str:
    return render_app(data, canonical)
