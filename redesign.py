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


def island_of(area: str) -> str:
    """Which island a listing sits on, from the area the agency wrote.
    Duty differs by island, so this travels with the price into the calculator."""
    import re as _re
    a = (area or "").lower()
    if "little cayman" in a:
        return "little"
    if "cayman brac" in a or _re.search(r"\bbrac\b", a):
        return "brac"
    return "grand"


def use_in_calculator(price, location=None, ptype=None) -> str:
    """The action that carries a listing into the calculator.

    It sits inside the card's anchor, as the favourite and compare controls
    already do in the delivered component, so its handler must stop the click
    reaching the link: otherwise the visitor is sent to the agency's website
    instead of the calculator.
    """
    return (
        '<div class="rd-listing-actions">'
        '<button type="button" class="cmc-btn cmc-btn--secondary cmc-btn--sm rd-use-calc"'
        + attrs(data_use_price=int(round(price or 0)),
                data_use_island=island_of(location),
                data_use_ptype="land" if ptype == "land" else "home")
        + f">{icon('calculator', 16)}<span>Use in calculator</span></button></div>")


def clean_title(t: str) -> str:
    """Tidy a scraper title for display without rewriting the agent's words.

    Agencies type these by hand: "New 2Bed|2Bath in Prime Location in West
    Bay(END UNIT)". Pipes become commas, a bracket gets the space it is missing,
    and doubled spaces collapse. Nothing else is touched.
    """
    import re as _re
    t = (t or "").strip()
    # Agencies type en and em dashes into their titles, and the brief rules them
    # out of rendered text. A plain hyphen matches the " - " most of the other
    # titles already use, and keeps the agent's wording recognisable.
    t = t.replace("\u2014", " - ").replace("\u2013", " - ")
    t = t.replace("|", ", ")
    t = _re.sub(r"\s*\(", " (", t)
    t = _re.sub(r"\s{2,}", " ", t)
    t = _re.sub(r"\s+,", ",", t)
    return t.strip()


def fmt_money(v, currency="KYD") -> str:
    """CI$ by default; whole dollars, grouped. Matches fmtMoney in the bundle."""
    sym = "US$" if currency == "USD" else "CI$"
    r = round(v)
    return f"{'-' if r < 0 else ''}{sym}{abs(r):,}"


def listing_card(price, address, locality=None, beds=None, baths=None, sqft=None,
                 image=None, image_alt="", badge_text=None, badge_tone="navy",
                 monthly=None, agency=None, href=None, currency="KYD",
                 ptype_for_calc=None) -> str:
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
    # clean first: the label was being built from the raw scraper string, so a
    # title cleaned for display still reached screen readers with its own dashes
    address = clean_title(address)
    locality = clean_title(locality) if locality else locality
    label = f"{address}: view on the agent's site" if external and address else None
    return (f'<{tag} class="cmc-listing"'
            + attrs(href=href, target="_blank" if external else None,
                    rel="noopener" if external else None, aria_label=label)
            + f'><div class="cmc-listing__media">{media}</div>'
            f'<div class="cmc-listing__body">'
            f'<div class="cmc-listing__price">{e(fmt_money(price, currency))}</div>'
            f'<div class="cmc-listing__address">{e(address)}</div>'
            + (f'<div class="cmc-listing__locality">{e(locality)}</div>' if locality else "")
            + monthly_html + "</div>" + meta_html + agency_html
            + use_in_calculator(price, locality, ptype_for_calc) + f"</{tag}>")


def field(control: str, label=None, prefix=None, suffix=None, hint=None,
          error=None, chevron=False, cls="") -> str:
    """Port of CMC.Field: the label wraps the control, affixes sit inside."""
    return (f'<label class="{cx("cmc-field", "cmc-field--error" if error else "", cls)}">'
            + (f'<span class="cmc-field__label">{e(label)}</span>' if label else "")
            + '<span class="cmc-field__control">'
            + (f'<span class="cmc-field__affix">{e(prefix)}</span>' if prefix else "")
            + control
            + (f'<span class="cmc-field__affix">{e(suffix)}</span>' if suffix else "")
            + (icon("chevron-down", 16, "cmc-field__chevron") if chevron else "")
            + "</span>"
            + (f'<span class="cmc-field__hint cmc-field__hint--error">{e(error)}</span>' if error
               else f'<span class="cmc-field__hint">{e(hint)}</span>' if hint else "")
            + "</label>")


def input_field(label, bind=None, value=None, type_="number", prefix=None, suffix=None,
                hint=None, step=None, min_=None, max_=None, inputmode="decimal",
                money=False, **kw) -> str:
    """bundle.css styles .cmc-field__input, not a bare input: without the class a
    control falls back to the browser's own box.

    `money` renders a text field that carries thousands separators. A number
    input cannot show them, and 650000 is materially harder to read at a glance
    than 650,000 when the figure is someone's house.
    """
    if money:
        type_, step, min_, max_ = "text", None, None, None
        if value is not None:
            value = f"{round(float(value)):,}"
        kw["data_cmc_money"] = True
    control = "<input" + attrs(class_="cmc-field__input", type=type_, value=value, step=step,
                               min=min_, max=max_, inputmode=inputmode,
                               data_cmc_bind=bind, **kw) + ">"
    return field(control, label=label, prefix=prefix, suffix=suffix, hint=hint)


def select_field(label, options, value=None, bind=None, hint=None, **kw) -> str:
    opts = "".join(
        f"<option{attrs(value=v, selected=(str(v) == str(value)) or None)}>{e(t)}</option>"
        for v, t in options)
    control = ("<select" + attrs(class_="cmc-field__input cmc-field__input--select",
                                 data_cmc_bind=bind, **kw) + f">{opts}</select>")
    return field(control, label=label, hint=hint, chevron=True)


def pill_tabs(items, value=None, cls="") -> str:
    """Port of CMC.PillTabs. Each tab is a link, so it works without JavaScript."""
    out = []
    for v, label, href in items:
        on = v == value
        out.append(f'<a class="{cx("cmc-pill", "cmc-pill--active" if on else "")}"'
                   f'{attrs(href=href, aria_current="page" if on else None)}>{e(label)}</a>')
    return f'<div class="{cx("cmc-pills", cls)}" role="tablist">' + "".join(out) + "</div>"


def currency_toggle() -> str:
    """CI$ / US$, bound to the shared currency. All arithmetic stays in CI$;
    this converts what is displayed and entered, at the fixed peg."""
    return (
        '<div class="sec" style="flex-direction:row;align-items:center;'
        'justify-content:space-between;gap:12px;flex-wrap:wrap">'
        '<span style="font-size:14px;line-height:22px;font-weight:600;color:var(--ink-900)">'
        "Show figures in</span>"
        '<div class="cmc-pills" role="group" aria-label="Currency">'
        '<button type="button" class="cmc-pill cmc-pill--active" data-cmc-currency="KYD"'
        ' aria-pressed="true">CI$</button>'
        '<button type="button" class="cmc-pill" data-cmc-currency="USD"'
        ' aria-pressed="false">US$</button>'
        "</div></div>")


def calculator_panel(href="/calculator/", cta_label="See full breakdown", note=None,
                     tabs=True, tab="buy", compact=False) -> str:
    """Port of CMC.CalculatorPanel. Renders with the shared defaults already in
    place; rd-inputs.js then binds the controls and keeps the result in step."""
    d = {"price": 650000, "deposit": 10, "rate": 7.75, "term": 25}
    loan = d["price"] * (1 - d["deposit"] / 100)
    r = d["rate"] / 100 / 12
    n = d["term"] * 12
    monthly = loan * r / (1 - (1 + r) ** -n)
    tabs_html = ""
    if tabs:
        tabs_html = pill_tabs([("buy", "Buying", "/calculator/"),
                               ("refi", "Refinancing", "/guides/refinancing/"),
                               ("afford", "What can I afford?", "/affordability/")],
                              value=tab, cls="cmc-calc__tabs")
    return (
        f'<section class="{cx("cmc-calc", "cmc-calc--compact" if compact else "")}"'
        ' aria-label="Mortgage calculator">' + tabs_html
        + '<div class="cmc-calc__grid">'
        + input_field("Purchase price", bind="price", value=d["price"], prefix="CI$",
                      money=True)
        + input_field("Deposit", bind="deposit", value=d["deposit"], suffix="%", step=0.5, min_=0, max_=100)
        + input_field("Interest rate", bind="rate", value=d["rate"], suffix="%", step=0.05, min_=0)
        + select_field("Term", [(15, "15 years"), (20, "20 years"), (25, "25 years"), (30, "30 years")],
                       value=d["term"], bind="term")
        + '<div class="cmc-calc__result">'
          '<span class="cmc-calc__result-label">Estimated monthly</span>'
          f'<span class="cmc-calc__result-value" data-cmc-result>{e(fmt_money(monthly))}</span>'
          f'<span class="cmc-calc__result-sub" data-cmc-result-sub>'
          f'on {e(fmt_money(loan))} over {d["term"]} yrs</span></div>'
        + button(cta_label, href=href, icon_right="arrow-right", cls="cmc-calc__cta")
        + "</div>"
        + (f'<p class="cmc-calc__note">{icon("info", 14)}{e(note)}</p>' if note else "")
        + "</section>")


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
    {"icon": "house", "text": "Listings shown with agents' permission"},
]
UTILITY_RIGHT = "Grand Cayman, Cayman Islands"


def header(active: str = "", utility=True) -> str:
    """`active` is matched against each item's href.

    The logo is sized in rd.css, not here: it has to step down between the
    drawer handover and 1024px, where the nav and CTA need the width back.

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
                f'<div class="cmc-utility__items">{items}</div>'
                f'<span class="cmc-utility__right">{e(UTILITY_RIGHT)}</span>'
                "</div></div>")

    links = []
    for n, it in enumerate(NAV):
        on = is_on(it)
        link_cls = cx("cmc-header__link", "cmc-header__link--active" if on else "")
        if not it.get("menu"):
            links.append('<div class="cmc-header__item">'
                         f'<a class="{link_cls}"'
                         f'{attrs(href=it["href"], aria_current="page" if on else None)}>'
                         f'{e(it["label"])}</a></div>')
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
            '<div class="cmc-header__item cmc-header__item--menu">'
            '<span class="cmc-header__link-group">'
            f'<a class="{link_cls}"{attrs(href=it["href"], aria_current="page" if on else None)}>'
            f'{e(it["label"])}</a>'
            f'<button class="cmc-header__toggle" type="button" aria-expanded="false"'
            f' aria-controls="{did}" aria-label="Show {e(it["label"])} menu">'
            f'{icon("chevron-down", 16)}</button></span>'
            f'<ul class="cmc-header__dropdown" id="{did}">{rows}</ul></div>')

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
        # No inline height: the lockup is sized in rd.css, which has to step it
        # down between the drawer handover and 1024px. An inline declaration,
        # even of a custom property, would beat those media queries.
        '<img src="/assets/cmc-secondary-color.svg" alt=""></a>'
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


# The Privacy page describes what this measures.
GA_MEASUREMENT_ID = "G-B7WJ51P8MN"

ORG_JSONLD = {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": SITE_NAME,
    "url": "https://caymanmortgagecalculator.com/",
    "logo": "https://caymanmortgagecalculator.com/icon-512.png",
    "email": EMAIL,
    "sameAs": [INSTAGRAM],
    "founder": [
        {"@type": "Person", "name": "Jerome Bailey"},
        {"@type": "Person", "name": "Janique Bailey"},
    ],
}

SITE_JSONLD = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": SITE_NAME,
    "url": "https://caymanmortgagecalculator.com/",
}


def software_jsonld(name: str, url: str, description: str) -> dict:
    return {
        "@context": "https://schema.org", "@type": "SoftwareApplication",
        "name": name, "url": url, "description": description,
        "applicationCategory": "FinanceApplication",
        "operatingSystem": "Any web browser",
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "KYD"},
    }


def faq_jsonld(pairs) -> dict:
    return {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in pairs],
    }


def breadcrumb_jsonld(crumb: str, url: str) -> dict:
    return {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home",
             "item": "https://caymanmortgagecalculator.com/"},
            {"@type": "ListItem", "position": 2, "name": crumb, "item": url},
        ],
    }


ICON_LINKS = (
    '<link rel="icon" href="/favicon.ico" sizes="48x48">'
    '<link rel="icon" href="/favicon.svg" type="image/svg+xml">'
    '<link rel="apple-touch-icon" href="/apple-touch-icon.png">'
    '<link rel="manifest" href="/site.webmanifest">'
)


def head(title: str, description: str, canonical: str = "", css_href: str = "/assets/rd.css",
         jsonld=(), og_image: str = "") -> str:
    blocks = "".join(
        f'<script type="application/ld+json">{json.dumps(b, separators=(",", ":"))}</script>'
        for b in jsonld)
    og = ""
    if og_image:
        og = (f'<meta property="og:image" content="{e(og_image)}">'
              '<meta name="twitter:card" content="summary_large_image">')
    ga = ""
    if GA_MEASUREMENT_ID:
        ga = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={e(GA_MEASUREMENT_ID)}">'
              "</script><script>window.dataLayer=window.dataLayer||[];"
              "function gtag(){dataLayer.push(arguments);}gtag('js',new Date());"
              f"gtag('config','{e(GA_MEASUREMENT_ID)}',{{anonymize_ip:true}});</script>")
    return (
        '<!doctype html><html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        f"<title>{e(title)}</title>"
        f'<meta name="description" content="{e(description)}">'
        # The live site carries a policy and the redesign should not lose it.
        # cdnjs is listed because the spreadsheet and PDF builders are fetched
        # from there on first use; img-src allows https generally because the
        # listing photos come from about twenty agency domains.
        '<meta http-equiv="Content-Security-Policy" content="'
        "default-src 'self'; "
        "img-src 'self' https: data:; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com "
        "https://www.googletagmanager.com; "
        "connect-src 'self' https://*.google-analytics.com https://*.analytics.google.com "
        "https://*.googletagmanager.com; "
        "object-src 'none'; base-uri 'self'; form-action 'none'"
        '">'
        + ga
        + '<meta name="color-scheme" content="light dark">'
        '<meta name="theme-color" content="#011533">'
        + (f'<link rel="canonical" href="{e(canonical)}">' if canonical else "")
        + f'<meta property="og:title" content="{e(title)}">'
          f'<meta property="og:description" content="{e(description)}">'
          '<meta property="og:type" content="website">'
          f'<meta property="og:site_name" content="{e(SITE_NAME)}">'
        + (f'<meta property="og:url" content="{e(canonical)}">' if canonical else "")
        + og + ICON_LINKS
        + '<link rel="preconnect" href="https://fonts.googleapis.com">'
          '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
          f'<link rel="stylesheet" href="{FONT_HREF}">'
          f'<link rel="stylesheet" href="{e(css_href)}">'
        + blocks
        + "</head><body>")


def tail(scripts=(), icons_for_js=False) -> str:
    """Scripts are page-specific and load after the shared ones, in order."""
    out = ""
    if icons_for_js:
        # Cards built on the client need the same Lucide paths the server uses.
        out += f"<script>window.RD_ICON_PATHS={json.dumps(ICONS, separators=(',', ':'))};</script>"
    out += '<script src="/assets/rd-inputs.js"></script>'
    for src in scripts:
        out += f'<script src="{e(src)}"></script>'
    return out + f"<script>{RD_JS}</script></body></html>"


TAIL = tail()


def page(title: str, description: str, body: str, active: str = "",
         canonical: str = "", css_href: str = "/assets/rd.css",
         scripts=(), icons_for_js: bool = False, jsonld=(), og_image: str = "") -> str:
    return (head(title, description, canonical, css_href, jsonld, og_image)
            + '<a class="rd-skip" href="#main">Skip to content</a>'
            + header(active=active)
            + f'<main id="main">{body}</main>'
            + footer() + back_to_top() + tail(scripts, icons_for_js))


def stylesheet() -> str:
    """One stylesheet, in three clearly separated sections.

    Sections 1 and 2 are the delivered design system, byte for byte. Nothing in
    them is edited; anything missing is added as an override in section 3.
    """
    bar = "/* " + "=" * 74 + " */\n"
    return (
        bar + "/* 1. tokens.css, as delivered. Do not edit here. */\n" + bar
        + TOKENS.read_text().rstrip() + "\n\n"
        + bar + "/* 2. components/bundle.css, as delivered. Do not edit here. */\n" + bar
        + BUNDLE_CSS.read_text().rstrip() + "\n\n"
        + bar + "/* 3. Site overrides and page-level styles, added by this repo.\n"
                "      Everything below is ours; the two sections above are not. */\n" + bar
        + (ROOT / "web" / "rd.css").read_text().rstrip() + "\n")
