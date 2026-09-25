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
CSS_HREF = "/assets/app.css"
CORE_HREF = "/assets/core.js"

PAGES = {
    "home": {
        "path": "",
        "title": f"{SITE_NAME} — stamp duty, closing costs and listings",
        "description": ("What buying in the Cayman Islands really costs: stamp duty, mortgage duty, Land Registry, "
                        "legal and bank fees, plus the homes and land for sale that fit your budget."),
    },
    "rent": {
        "path": "rent-vs-buy/",
        "title": f"Rent or buy in Cayman — {SITE_NAME}",
        "description": ("Should you rent or buy in the Cayman Islands? Mortgage, strata, insurance, upkeep and stamp "
                        "duty against rent and rent rises, with the year buying pulls ahead."),
    },
    "equity": {
        "path": "equity/",
        "title": f"Equity calculator — {SITE_NAME}",
        "description": ("How much equity is in your Cayman property, and how much of it a bank would lend against — "
                        "with the loan-to-value ratios Cayman lenders publish for Caymanians, residents and "
                        "non-residents."),
    },
    "calculator": {
        "path": "calculator/",
        "title": f"Mortgage and stamp duty calculator — {SITE_NAME}",
        "description": ("Work out your monthly payment and the real cash needed to close in the Cayman Islands, then "
                        "see the listings that fit — priced through your own rate, term and deposit."),
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
