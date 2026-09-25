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

def head(canonical: str = "") -> str:
    return (
        '<!doctype html><html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        f"<title>{TITLE}</title>"
        f'<meta name="description" content="{DESCRIPTION}">'
        '<meta name="color-scheme" content="light dark">'
        '<meta name="theme-color" content="#0E2A47">'
        # Brand favicon set: .ico for older browsers, .svg where supported.
        '<link rel="icon" href="favicon.ico" sizes="48x48">'
        '<link rel="icon" href="favicon.svg" type="image/svg+xml">'
        '<link rel="apple-touch-icon" href="apple-touch-icon.png">'
        '<link rel="manifest" href="site.webmanifest">'
        f'<meta property="og:title" content="{TITLE}">'
        f'<meta property="og:description" content="{DESCRIPTION}">'
        '<meta property="og:type" content="website">'
        + (f'<meta property="og:image" content="{canonical.rstrip("/")}/assets/og-image.png">'
           '<meta name="twitter:card" content="summary_large_image">' if canonical else "")
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
