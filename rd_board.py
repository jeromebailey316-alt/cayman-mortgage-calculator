"""Translate a design board (pages/*.dc.html) into a page body.

HANDOFF section 4 describes the boards' template syntax. Translating mechanically
beats retyping the prose: the copy is already approved and already free of em and
en dashes, and transcription would risk losing a paragraph or reintroducing one.

Handled:
  <x-import component-from-global-scope="CMC.X" a-b="v">text</x-import>
      -> the ported component, kebab-case attribute to snake_case argument
  {{name}} in text or attributes -> looked up in `vals`
  *.dc.html hrefs -> the real routes
  /_blob/... -> the logo assets

Deliberately dropped: the <helmet> block, whose CSS already lives in web/rd.css,
and the Header, Footer and BackToTop imports, which the page shell provides.

Anything it cannot resolve raises, rather than emitting a half-translated page.
"""
from __future__ import annotations

import html
import re

import redesign as rd

# board file -> the route it becomes
ROUTES = {
    "Main.dc.html": "/",
    "Calculator.dc.html": "/calculator/",
    "Equity.dc.html": "/equity/",
    "Affordability.dc.html": "/affordability/",
    "Listings.dc.html": "/listings/",
    "StampDuty.dc.html": "/guides/stamp-duty/",
    "ClosingCosts.dc.html": "/guides/closing-costs/",
    "Refinancing.dc.html": "/guides/refinancing/",
    "Contact.dc.html": "/contact/",
    "About.dc.html": "/about/",
    "Agents.dc.html": "/agents/",
    "Privacy.dc.html": "/privacy/",
    "Terms.dc.html": "/terms/",
}

BLOBS = {
    "/_blob/3abd7386e93b1deaca8bb90d9dcd1590": "/assets/cmc-secondary-color.svg",
    "/_blob/c8bdb95aa36670eb38580872c9cb28be": "/assets/cmc-secondary-reversed.svg",
}

# components the shell already renders, so the board's copies are dropped
SHELL = {"CMC.Header", "CMC.Footer", "CMC.BackToTop"}

# plain numbers the boards pass as {{vars}} purely to satisfy the design tool
DEFAULT_VALS = {
    "twelve": 12, "fourteen": 14, "sixteen": 16, "eighteen": 18,
    "twenty": 20, "twentyFour": 24, "twentyEight": 28, "thirtyTwo": 32,
    "yes": True, "no": False,
}

_IMPORT = re.compile(
    r'<x-import\s+component-from-global-scope="(?P<name>CMC\.[A-Za-z]+)"'
    r'(?P<attrs>[^>]*?)>(?P<inner>.*?)</x-import>', re.S)
_ATTR = re.compile(r'([a-zA-Z-]+)="([^"]*)"')
_VAR = re.compile(r"\{\{([a-zA-Z0-9_.]+)\}\}")


def _resolve(text: str, vals: dict):
    """Substitute {{a.b}}. A whole-string match returns the value itself, so a
    number stays a number rather than becoming a string."""
    m = _VAR.fullmatch(text.strip())
    if m:
        return _lookup(m.group(1), vals)
    return _VAR.sub(lambda mm: html.escape(str(_lookup(mm.group(1), vals))), text)


def _lookup(path: str, vals: dict):
    cur = vals
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise KeyError(f"board referenced {{{{{path}}}}} but no value was supplied")
    return cur


def _href(v: str) -> str:
    if v in BLOBS:
        return BLOBS[v]
    if v == "#":
        return "/listings/"
    base = v.split("#")[0]
    if base in ROUTES:
        return ROUTES[base] + v[len(base):]
    return v


def _component(name: str, attrs: dict, inner: str) -> str:
    kind = name.split(".", 1)[1]
    if kind == "Icon":
        return rd.icon(attrs.get("name", ""), int(attrs.get("size") or 24))
    if kind == "Button":
        return rd.button(
            inner.strip(), href=attrs.get("href"),
            variant=attrs.get("variant", "primary"), size=attrs.get("size", "md"),
            icon_left=attrs.get("icon-left"), icon_right=attrs.get("icon-right"),
            block=attrs.get("block") in ("true", True),
            **({"target": attrs["target"], "rel": attrs.get("rel", "noopener")}
               if attrs.get("target") else {}))
    if kind == "Badge":
        return rd.badge(inner.strip(), tone=attrs.get("tone", "neutral"))
    if kind in ("Input", "Select"):
        # The board names a control; the page's own script gives it behaviour.
        # `bind` opts it into the shared inputs, `id` lets a page script find it.
        if kind == "Select":
            opts = attrs.get("options")
            items = opts if isinstance(opts, list) else []
            return rd.select_field(attrs.get("label"),
                                   [(o.get("value", o.get("label")), o.get("label"))
                                    if isinstance(o, dict) else (o, o) for o in items],
                                   value=attrs.get("default-value") or attrs.get("value"),
                                   id=attrs.get("id"), bind=attrs.get("bind"))
        return rd.input_field(
            attrs.get("label"), id=attrs.get("id"), bind=attrs.get("bind"),
            value=attrs.get("value"), type_=attrs.get("type", "number"),
            prefix=attrs.get("prefix"), suffix=attrs.get("suffix"),
            hint=attrs.get("hint"), placeholder=attrs.get("placeholder"),
            inputmode=attrs.get("input-mode", "decimal"),
            step=attrs.get("step"), min_=attrs.get("min"), max_=attrs.get("max"))
    if kind == "ListingCard":
        return rd.listing_card(
            price=float(attrs.get("price") or 0), address=attrs.get("address", ""),
            locality=attrs.get("locality"),
            beds=_opt_num(attrs.get("beds")), baths=_opt_num(attrs.get("baths")),
            sqft=_opt_num(attrs.get("sqft")),
            badge_text=attrs.get("badge"), badge_tone=attrs.get("badge-tone", "navy"),
            monthly=_opt_num(attrs.get("monthly")), agency=attrs.get("agency"),
            href=attrs.get("href"))
    if kind == "Byline":
        return byline(author=attrs.get("author"), reviewer=attrs.get("reviewer"),
                      checked=attrs.get("checked"), updated=attrs.get("updated"),
                      note=attrs.get("note"))
    raise ValueError(f"no port for {name}; add one before translating this board")


def _opt_num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def byline(author=None, reviewer=None, checked=None, updated=None, note=None) -> str:
    pairs = [("Written by", author), ("Reviewed by", reviewer),
             ("Sources checked", checked), ("Last updated", updated)]
    items = "".join(
        f'<span class="cmc-byline__item"><span class="cmc-byline__k">{rd.e(k)} </span>'
        f"<strong>{rd.e(v)}</strong></span>"
        for k, v in pairs if v)
    return ('<div class="cmc-byline">' + rd.icon("shield-check", 16) + items
            + (f'<span class="cmc-byline__note">{rd.e(note)}</span>' if note else "")
            + "</div>")


def translate_source(src: str, vals: dict | None = None) -> str:
    """translate(), for a board already read into memory (so a section can be
    held back before translation)."""
    return _translate(src, vals)


def translate(path, vals: dict | None = None) -> str:
    """Board file -> page body."""
    src = path.read_text() if hasattr(path, "read_text") else open(path).read()
    return _translate(src, vals)


def _translate(src: str, vals: dict | None = None) -> str:
    vals = dict(DEFAULT_VALS, **(vals or {}))
    body = src[src.index("<x-dc>") + len("<x-dc>"): src.index("</x-dc>")]
    # the helmet's styles are in web/rd.css already
    body = re.sub(r"<helmet>.*?</helmet>", "", body, flags=re.S)

    def swap(m):
        name = m.group("name")
        if name in SHELL:
            return ""
        attrs = {k: v for k, v in _ATTR.findall(m.group("attrs"))}
        resolved = {}
        for k, v in attrs.items():
            rv = _resolve(v, vals)
            if k == "href":
                rv = _href(str(rv))
            resolved[k] = rv
        return _component(name, resolved, _resolve(m.group("inner"), vals))

    body = _IMPORT.sub(swap, body)

    # plain links and images left in the markup
    body = re.sub(r'(href|src)="([^"]+)"',
                  lambda m: f'{m.group(1)}="{_href(m.group(2))}"', body)
    body = _VAR.sub(lambda m: html.escape(str(_lookup(m.group(1), vals))), body)

    leftover = re.search(r"<(x-import|sc-for|helmet)\b", body)
    if leftover:
        raise ValueError(f"board still contains <{leftover.group(1)}> after translation")
    return body.strip()
