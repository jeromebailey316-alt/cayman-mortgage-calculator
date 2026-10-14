"""The redesigned site: components and page shell.

Ports the reference components in cmc-redesign/design-system/components/bundle.js
to plain Python string builders. They emit exactly the class names bundle.css
expects, so the stylesheet is used as delivered rather than reimplemented.

Why not the React bundle: see REDESIGN-PLAN.md section 2. The pages are documents
with a few interactive panels, and React plus ReactDOM would roughly treble the
site's JavaScript for markup that is almost all static.

Interactivity that the React components provided with state (the nav dropdowns,
the mobile drawer, back-to-top) is supplied by RD_JS at the bottom of this file.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RD = ROOT / "cmc-redesign"
DS = RD / "design-system"
TOKENS = DS / "tokens.css"
BUNDLE_CSS = DS / "components" / "bundle.css"
ICONS = json.loads((ROOT / "web" / "rd-icons.json").read_text())

SITE_NAME = "Cayman Mortgage Calculator"
EMAIL = "caymanmortgagecalculator@gmail.com"
INSTAGRAM = "https://www.instagram.com/caymanmortgagecalc"

# Inter only, per HANDOFF section 2.
FONT_HREF = ("https://fonts.googleapis.com/css2?"
             "family=Inter:wght@400;500;600;700&display=swap")


def e(s) -> str:
    """Escape text for HTML. Everything user- or data-derived goes through this."""
    return html.escape(str(s if s is not None else ""), quote=True)


def attrs(**kw) -> str:
    """Render attributes, skipping None and False, rendering True as bare."""
    out = []
    for k, v in kw.items():
        if v is None or v is False:
            continue
        k = k.rstrip("_").replace("_", "-")
        out.append(f" {k}" if v is True else f' {k}="{e(v)}"')
    return "".join(out)


def cx(*names) -> str:
    return " ".join(n for n in names if n)


# --------------------------------------------------------------------- icons

def icon(name: str, size: int = 24, cls: str = "") -> str:
    """Lucide, stroke width 1.5, as in the bundle. Unknown names render nothing
    rather than a broken glyph, and are reported by check_icons()."""
    paths = ICONS.get(name)
    if not paths:
        return ""
    d = "".join(f'<path d="{e(p)}"/>' for p in paths)
    return (f'<svg class="{cx("cmc-icon", cls)}" width="{size}" height="{size}" '
            'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{d}</svg>')


def check_icons(*names) -> list[str]:
    return [n for n in names if n and n not in ICONS]


# ------------------------------------------------------------------- button

def button(label, href=None, variant="primary", size="md", icon_left=None,
           icon_right=None, block=False, cls="", **kw) -> str:
    tag = "a" if href else "button"
    klass = cx("cmc-btn", f"cmc-btn--{variant}", f"cmc-btn--{size}",
               "cmc-btn--block" if block else "", cls)
    isz = 16 if size == "sm" else 18
    extra = attrs(href=href, **kw)
    if not href and "type" not in kw:
        extra += ' type="button"'
    return (f'<{tag} class="{klass}"{extra}>'
            f'{icon(icon_left, isz) if icon_left else ""}'
            f"<span>{e(label)}</span>"
            f'{icon(icon_right, isz) if icon_right else ""}'
            f"</{tag}>")


def badge(label, tone="neutral", tint=False) -> str:
    return (f'<span class="{cx("cmc-badge", f"cmc-badge--{tone}", "cmc-badge--tint" if tint else "")}">'
            f"{e(label)}</span>")


def fmt_money(v, currency="KYD") -> str:
    """CI$ by default; whole dollars, grouped. Matches fmtMoney in the bundle."""
    sym = "US$" if currency == "USD" else "CI$"
    return f"{sym}{round(v):,}"


def listing_card(price, address, locality=None, beds=None, baths=None, sqft=None,
                 image=None, image_alt="", badge_text=None, badge_tone="navy",
                 monthly=None, agency=None, href=None, currency="KYD") -> str:
    """Port of CMC.ListingCard. Values that are unknown are omitted rather than
    shown as zero, which is how the rest of this site treats missing data."""
    external = bool(href) and href.lower().startswith(("http://", "https://"))
    tag = "a" if href else "article"
    media = (f'<img src="{e(image)}" alt="{e(image_alt)}" loading="lazy" referrerpolicy="no-referrer">'
             if image else
             f'<div class="cmc-listing__placeholder">{icon("house", 32)}</div>')
    if badge_text:
        media += (f'<span class="{cx("cmc-badge", f"cmc-badge--{badge_tone}", "cmc-listing__badge")}">'
                  f"{e(badge_text)}</span>")
    meta = []
    if beds is not None:
        meta.append((("bed-double"), f"{beds:g} Bed" + ("" if beds == 1 else "s")))
    if baths is not None:
        meta.append(("bath", f"{baths:g} Bath" + ("" if baths == 1 else "s")))
    if sqft is not None:
        meta.append(("ruler", f"{round(sqft):,} Sq Ft"))
    meta_html = ""
    if meta:
        meta_html = ('<div class="cmc-listing__meta">'
                     + "".join(f"<span>{icon(i, 14)}{e(t)}</span>" for i, t in meta)
                     + "</div>")
    agency_html = ""
    if agency or external:
        agency_html = ('<div class="cmc-listing__agency">'
                       + (f"<span>Listed by {e(agency)}</span>" if agency else "")
                       + (f'<span class="cmc-listing__ext">View on agent\'s site{icon("external-link", 12)}</span>'
                          if external else "")
                       + "</div>")
    monthly_html = ""
    if monthly is not None:
        monthly_html = (f'<div class="cmc-listing__monthly">{icon("calculator", 14)}From '
                        f"<strong>{e(fmt_money(monthly, currency))}</strong>/mo</div>")
    label = f"{address}: view on the agent's site" if external and address else None
    return (f'<{tag} class="cmc-listing"'
            + attrs(href=href, target="_blank" if external else None,
                    rel="noopener" if external else None, aria_label=label)
            + f'><div class="cmc-listing__media">{media}</div>'
            f'<div class="cmc-listing__body">'
            f'<div class="cmc-listing__price">{e(fmt_money(price, currency))}</div>'
            f'<div class="cmc-listing__address">{e(address)}</div>'
            + (f'<div class="cmc-listing__locality">{e(locality)}</div>' if locality else "")
            + monthly_html + "</div>" + meta_html + agency_html + f"</{tag}>")


# ------------------------------------------------------------------- header

NAV = [
    {"label": "Home", "href": "/"},
    {"label": "Calculators", "href": "/calculator/", "menu": [
        {"label": "Mortgage", "href": "/calculator/", "icon": "calculator",
         "description": "Monthly payment and cash to close"},
        {"label": "Equity", "href": "/equity/", "icon": "trending-up",
         "description": "What you could release"},
        {"label": "Affordability", "href": "/affordability/", "icon": "percent",
         "description": "The most you can borrow"},
        {"label": "Rent vs buy", "href": "/rent-vs-buy/", "icon": "house",
         "description": "The year buying pulls ahead"},
    ]},
    {"label": "Listings", "href": "/listings/"},
    {"label": "Guides", "href": "/guides/stamp-duty/", "menu": [
        {"label": "Stamp duty", "href": "/guides/stamp-duty/", "icon": "receipt",
         "description": "Rates, bands and concessions"},
        {"label": "Closing costs", "href": "/guides/closing-costs/", "icon": "file-text",
         "description": "What you need on the day"},
        {"label": "Refinancing", "href": "/guides/refinancing/", "icon": "landmark",
         "description": "Whether a new rate pays for itself"},
    ]},
    {"label": "Agents", "href": "/agents/"},
    {"label": "About", "href": "/about/"},
]

UTILITY = [
    {"icon": "shield-check", "text": "Free to use"},
    {"icon": "check", "text": "No sign-up"},
]


def header(active: str = "", logo_height: int = 40, utility=True) -> str:
    """`active` is matched against each item's href.

    Emits the class names bundle.css actually defines: __toggle not __chevron,
    __dropdown not __menu (__menu is the burger), __actions around the burger,
    and __link-group wrapping the label and its toggle.
    """
    def is_on(it):
        if it.get("href") and it["href"] == active:
            return True
        return any(m.get("href") == active for m in it.get("menu") or [])

    util = ""
    if utility:
        items = "".join(f"<span>{icon(i['icon'], 14)}{e(i['text'])}</span>" for i in UTILITY)
        util = ('<div class="cmc-utility"><div class="cmc-container cmc-utility__row">'
                f'<div class="cmc-utility__items">{items}</div></div></div>')

    links = []
    for n, it in enumerate(NAV):
        on = is_on(it)
        link_cls = cx("cmc-header__link", "cmc-header__link--active" if on else "")
        if not it.get("menu"):
            links.append(f'<a class="{link_cls}"'
                         f'{attrs(href=it["href"], aria_current="page" if on else None)}>'
                         f'{e(it["label"])}</a>')
            continue
        did = f"navmenu{n}"
        rows = "".join(
            '<li><a class="{cls}"{a}>{ic}<span class="cmc-header__dropdown-text">'
            '<span>{lab}</span>{desc}</span></a></li>'.format(
                cls=cx("cmc-header__dropdown-link",
                       "cmc-header__dropdown-link--active" if m.get("href") == active else ""),
                a=attrs(href=m["href"], aria_current="page" if m.get("href") == active else None),
                ic=icon(m.get("icon"), 18), lab=e(m["label"]),
                desc=(f'<span class="cmc-header__dropdown-desc">{e(m["description"])}</span>'
                      if m.get("description") else ""))
            for m in it["menu"])
        # The label links to the section's first page; the toggle beside it is a
        # separate button, so the section is reachable without opening the menu.
        links.append(
            '<span class="cmc-header__item cmc-header__item--menu">'
            '<span class="cmc-header__link-group">'
            f'<a class="{link_cls}"{attrs(href=it["href"], aria_current="page" if on else None)}>'
            f'{e(it["label"])}</a>'
            f'<button class="cmc-header__toggle" type="button" aria-expanded="false"'
            f' aria-controls="{did}" aria-label="Show {e(it["label"])} menu">'
            f'{icon("chevron-down", 16)}</button></span>'
            f'<ul class="cmc-header__dropdown" id="{did}">{rows}</ul></span>')

    drawer = []
    for it in NAV:
        on = is_on(it)
        drawer.append('<div class="cmc-header__drawer-group">'
                      f'<a class="{cx("cmc-header__drawer-link", "cmc-header__drawer-link--active" if on else "")}"'
                      f'{attrs(href=it["href"])}>{e(it["label"])}</a>')
        if it.get("menu"):
            subs = "".join(
                f'<a class="{cx("cmc-header__drawer-sublink", "cmc-header__drawer-sublink--active" if m.get("href") == active else "")}"'
                f'{attrs(href=m["href"])}>{icon(m.get("icon"), 18)}<span>{e(m["label"])}</span></a>'
                for m in it["menu"])
            drawer.append(f'<div class="cmc-header__drawer-sub">{subs}</div>')
        drawer.append("</div>")

    return (
        '<header class="cmc-header">' + util +
        '<div class="cmc-container cmc-header__row">'
        f'<a class="cmc-header__logo" href="/" aria-label="{e(SITE_NAME)}: home">'
        f'<img src="/assets/cmc-secondary-color.svg" alt="" style="height:{logo_height}px"></a>'
        f'<nav class="cmc-header__nav" aria-label="Main">{"".join(links)}</nav>'
        '<div class="cmc-header__cta">'
        + button("Run the numbers", href="/calculator/", icon_right="arrow-right") +
        '</div>'
        '<div class="cmc-header__actions">'
        '<button class="cmc-header__menu" type="button" aria-expanded="false"'
        f' aria-controls="rdDrawer" aria-label="Open menu">{icon("menu", 22)}</button>'
        '</div></div>'
        f'<div class="cmc-header__drawer" id="rdDrawer" hidden>{"".join(drawer)}'
        '<div class="cmc-header__drawer-cta">'
        + button("Run the numbers", href="/calculator/", icon_right="arrow-right", block=True) +
        '</div></div></header>')


# ------------------------------------------------------------------- footer

FOOTER_COLS = [
    ("Calculators", [("Mortgage", "/calculator/"), ("Equity", "/equity/"),
                     ("Affordability", "/affordability/"), ("Rent vs buy", "/rent-vs-buy/")]),
    ("Guides", [("Stamp duty", "/guides/stamp-duty/"), ("Closing costs", "/guides/closing-costs/"),
                ("Refinancing", "/guides/refinancing/")]),
    ("Listings", [("Buy", "/listings/"), ("For agents", "/agents/")]),
    ("About", [("About the site", "/about/"), ("Contact", "/contact/"),
               ("Privacy", "/privacy/"), ("Terms", "/terms/")]),
]


def footer(year: int = 2026) -> str:
    # h4 is what bundle.css styles inside a footer column; keeping it matches the
    # delivered design, at the cost of a heading-level skip noted in REDESIGN-PLAN.
    cols = "".join(
        f'<div class="cmc-footer__col"><h4>{e(title)}</h4><ul>' +
        "".join(f'<li><a{attrs(href=href)}>{e(label)}</a></li>' for label, href in links) +
        "</ul></div>"
        for title, links in FOOTER_COLS)
    return (
        '<footer class="cmc-footer"><div class="cmc-container cmc-footer__grid">'
        '<div class="cmc-footer__brand">'
        '<img src="/assets/cmc-secondary-reversed.svg" alt="">'
        '<p>What buying in the Cayman Islands actually costs, worked out before you make '
        'an offer. Free to use, no sign-up.</p>'
        f'<p class="rd-footer-contact">{icon("mail", 16)}'
        f'<a href="mailto:{e(EMAIL)}">{e(EMAIL)}</a></p>'
        f'<p class="rd-footer-contact">{icon("external-link", 16)}'
        f'<a href="{e(INSTAGRAM)}" target="_blank" rel="noopener">Instagram</a></p>'
        '</div>' + cols + '</div>'
        '<div class="cmc-container cmc-footer__legal">'
        f'<span>© {year} {e(SITE_NAME)}. Estimates only, not financial or legal advice.</span>'
        '<span class="cmc-footer__legal-links"><a href="/privacy/">Privacy</a>'
        '<a href="/terms/">Terms</a></span>'
        '</div></footer>')


def back_to_top() -> str:
    # bundle.css reveals this with .cmc-totop--show, not the hidden attribute.
    return ('<button class="cmc-totop" id="rdTop" type="button" '
            f'aria-label="Back to top">{icon("arrow-up", 20)}</button>')


# --------------------------------------------------------------------- shell

RD_JS = """
(function () {
  'use strict';
  // Every page opens at the top unless the URL carries a hash (HANDOFF 3).
  if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
  function toTop() { if (!location.hash) window.scrollTo(0, 0); }
  window.addEventListener('pageshow', toTop);
  toTop();

  // Nav dropdowns. bundle.css reveals a dropdown on hover, on focus-within, or
  // when the item carries --open, so the toggle sets that class rather than
  // touching [hidden], which would fight the stylesheet.
  var items = [].slice.call(document.querySelectorAll('.cmc-header__item--menu'));
  function close(it) {
    it.classList.remove('cmc-header__item--open');
    var b = it.querySelector('.cmc-header__toggle');
    if (b) { b.classList.remove('cmc-header__toggle--open'); b.setAttribute('aria-expanded', 'false'); }
  }
  function closeAll(except) {
    items.forEach(function (it) { if (it !== except) close(it); });
  }
  items.forEach(function (it) {
    var b = it.querySelector('.cmc-header__toggle');
    if (!b) return;
    b.addEventListener('click', function (ev) {
      ev.preventDefault(); ev.stopPropagation();
      var open = it.classList.contains('cmc-header__item--open');
      closeAll(it);
      if (open) { close(it); return; }
      it.classList.add('cmc-header__item--open');
      b.classList.add('cmc-header__toggle--open');
      b.setAttribute('aria-expanded', 'true');
    });
  });
  document.addEventListener('click', function (ev) {
    if (!ev.target.closest || !ev.target.closest('.cmc-header__item--menu')) closeAll();
  });

  // Mobile drawer.
  var burger = document.querySelector('.cmc-header__menu');
  var drawer = document.getElementById('rdDrawer');
  function setDrawer(open) {
    if (!burger || !drawer) return;
    burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    burger.classList.toggle('cmc-header__menu--open', open);
    burger.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    drawer.hidden = !open;
  }
  if (burger) burger.addEventListener('click', function () {
    setDrawer(burger.getAttribute('aria-expanded') !== 'true');
  });
  if (drawer) drawer.addEventListener('click', function (ev) {
    if (ev.target.closest('a')) setDrawer(false);
  });
  document.addEventListener('keydown', function (ev) {
    if (ev.key !== 'Escape') return;
    closeAll(); setDrawer(false);
  });

  // Back to top, after 400px, revealed with the class bundle.css animates.
  var top = document.getElementById('rdTop');
  if (top) {
    var queued = false;
    function mark() { top.classList.toggle('cmc-totop--show', (window.pageYOffset || 0) >= 400); }
    window.addEventListener('scroll', function () {
      if (queued) return; queued = true;
      requestAnimationFrame(function () { queued = false; mark(); });
    }, { passive: true });
    top.addEventListener('click', function () {
      var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (reduce) window.scrollTo(0, 0); else window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    mark();
  }
})();
"""


def head(title: str, description: str, canonical: str = "", css_href: str = "/assets/rd.css") -> str:
    return (
        '<!doctype html><html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        f"<title>{e(title)}</title>"
        f'<meta name="description" content="{e(description)}">'
        '<meta name="color-scheme" content="light dark">'
        '<meta name="theme-color" content="#011533">'
        + (f'<link rel="canonical" href="{e(canonical)}">' if canonical else "")
        + '<link rel="preconnect" href="https://fonts.googleapis.com">'
          '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
          f'<link rel="stylesheet" href="{FONT_HREF}">'
          f'<link rel="stylesheet" href="{e(css_href)}">'
          "</head><body>")


TAIL = f"<script>{RD_JS}</script></body></html>"


def page(title: str, description: str, body: str, active: str = "",
         canonical: str = "", css_href: str = "/assets/rd.css") -> str:
    return (head(title, description, canonical, css_href)
            + '<a class="rd-skip" href="#main">Skip to content</a>'
            + header(active=active)
            + f'<main id="main">{body}</main>'
            + footer() + back_to_top() + TAIL)


def stylesheet() -> str:
    """tokens, then the component bundle as delivered, then page-level styles."""
    parts = [
        "/* tokens.css, as delivered */", TOKENS.read_text(),
        "/* components/bundle.css, as delivered */", BUNDLE_CSS.read_text(),
        "/* page-level styles for the redesign */", (ROOT / "web" / "rd.css").read_text(),
    ]
    return "\n".join(parts)
