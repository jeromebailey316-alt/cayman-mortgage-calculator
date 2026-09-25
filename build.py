"""Build a single self-contained HTML file for publishing (e.g. as a Claude artifact).

    .venv/bin/python build.py              # uses data/listings.json
    .venv/bin/python build.py --scrape     # scrape first

Published pages can't load images from other websites, so each listing photo is
shrunk to a small WebP and embedded in the file. Thumbnails are cached in data/thumbs/.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from PIL import Image

import page
from scraper import run as scrape_run
from scraper.common import UA

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "web" / "static"
OUT = ROOT / "dist" / "cayman-mortgage.html"
THUMBS = ROOT / "data" / "thumbs"
THUMB_W, THUMB_H, QUALITY = 270, 180, 38


def thumb(url: str) -> str:
    """Return a data: URI for a small WebP of `url`, or '' if it can't be fetched."""
    if not url or any(h in url for h in scrape_run.NO_THUMB_HOSTS):
        return ""
    THUMBS.mkdir(parents=True, exist_ok=True)
    f = THUMBS / (hashlib.sha1(url.encode()).hexdigest() + ".webp")
    if not f.exists():
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content)).convert("RGB")
            # cover-crop to 3:2 then shrink
            w, h = im.size
            tw = min(w, int(h * THUMB_W / THUMB_H))
            th = min(h, int(w * THUMB_H / THUMB_W))
            left, top = (w - tw) // 2, (h - th) // 2
            im = im.crop((left, top, left + tw, top + th)).resize((THUMB_W, THUMB_H), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, "WEBP", quality=QUALITY, method=6)
            f.write_bytes(buf.getvalue())
        except Exception as e:
            print(f"  no thumbnail for {url[:80]}: {e}")
            return ""
    return "data:image/webp;base64," + base64.b64encode(f.read_bytes()).decode()


def build(data: dict) -> Path:
    ls = data["listings"]
    # a few parallel workers; images are static files spread over several hosts
    with ThreadPoolExecutor(max_workers=6) as ex:
        uris = list(ex.map(lambda l: thumb(l.get("image", "")), ls))
    for l, u in zip(ls, uris):
        l["image"] = u
        l.pop("scraped_at", None)
    html = page.render(dict(data, local=False))
    # The single-file build can't fetch separate files, so the logos travel inline.
    for name in ("cmc-secondary-color.svg", "cmc-secondary-reversed.svg"):
        svg = (STATIC / "assets" / name).read_bytes()
        uri = "data:image/svg+xml;base64," + base64.b64encode(svg).decode()
        html = html.replace(f"assets/{name}", uri)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)
    return OUT


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scrape", action="store_true", help="scrape the sites before building")
    a = ap.parse_args()
    if a.scrape:
        scrape_run.save(scrape_run.scrape())
    d = scrape_run.load()
    if not d:
        raise SystemExit("No data/listings.json yet. Run with --scrape first.")
    out = build(d)
    print(f"Wrote {out.relative_to(ROOT)} ({out.stat().st_size / 1e6:.1f} MB, {len(d['listings'])} listings)")
