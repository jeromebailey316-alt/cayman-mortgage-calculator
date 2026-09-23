"""The HTML wrapper shared by the local server and the published website.

web/index.html holds the page itself (styles, markup, script) with a
__LISTINGS_JSON__ slot. This module wraps it in a document head.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "web" / "index.html"

TITLE = "Cayman Mortgage Calculator"
DESCRIPTION = ("Work out your monthly payment and the real cash needed to buy in the Cayman Islands "
               "— stamp duty, mortgage duty, Land Registry, legal and bank fees — then see the homes "
               "and land for sale that fit your numbers.")

# A house outline, drawn in the page's accent blue.
ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
        "%3Cpath d='M4 15 16 5l12 10v13H4z' fill='%230d5c99'/%3E"
        "%3Cpath d='M13 28v-8h6v8' fill='%23fff'/%3E%3C/svg%3E")


def head(canonical: str = "") -> str:
    return (
        '<!doctype html><html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        f"<title>{TITLE}</title>"
        f'<meta name="description" content="{DESCRIPTION}">'
        '<meta name="color-scheme" content="light dark">'
        '<meta name="theme-color" content="#0b3a5e" media="(prefers-color-scheme: dark)">'
        '<meta name="theme-color" content="#f1f5f7" media="(prefers-color-scheme: light)">'
        f'<link rel="icon" href="{ICON}">'
        f'<meta property="og:title" content="{TITLE}">'
        f'<meta property="og:description" content="{DESCRIPTION}">'
        '<meta property="og:type" content="website">'
        + (f'<link rel="canonical" href="{canonical}">' if canonical else "")
        + '<style>:root{box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
          'body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>'
          "</head><body>"
    )

TAIL = "</body></html>"


def render(data: dict | None, canonical: str = "") -> str:
    """Full HTML. `data` is embedded in the page; None means the page fetches
    listings.json from beside itself instead (the published website)."""
    slot = "null" if data is None else json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return head(canonical) + TEMPLATE.read_text().replace("__LISTINGS_JSON__", slot) + TAIL
