"""Build the static website into site/ — what GitHub Pages publishes.

    .venv/bin/python build_site.py                      # uses data/listings.json
    .venv/bin/python build_site.py --scrape             # scrape first
    .venv/bin/python build_site.py --domain caymanmortgagecalculator.com
    .venv/bin/python build_site.py --url https://me.github.io/cayman-mortgage/

The page fetches listings.json from beside itself, so a refresh of the data is
just a new listings.json — the HTML doesn't change. Photos are hotlinked from
the agency websites (unlike build.py, which embeds copies for publishing as a
single file).
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import home
import page
from scraper import run as scrape_run

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
STATIC = ROOT / "web" / "static"     # favicons, manifest, logos — copied to the site root

def robots(base: str) -> str:
    lines = ["User-agent: *", "Allow: /"]
    if base:
        lines.append(f"Sitemap: {base}sitemap.xml")
    return "\n".join(lines) + "\n"


def sitemap(base: str, lastmod: str) -> str:
    """Every page, newest data first. lastmod is the day the listings were refreshed:
    the pages are rebuilt each time, so that is genuinely when they last changed."""
    urls = [("", "1.0"), ("calculator/", "0.9"), ("equity/", "0.8"), ("rent-vs-buy/", "0.8")]
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, priority in urls:
        out += ["  <url>", f"    <loc>{base}{path}</loc>",
                f"    <lastmod>{lastmod}</lastmod>",
                "    <changefreq>daily</changefreq>",
                f"    <priority>{priority}</priority>", "  </url>"]
    out.append("</urlset>")
    return "\n".join(out) + "\n"


def build(data: dict, canonical: str = "", domain: str = "") -> Path:
    if SITE.exists():
        shutil.rmtree(SITE)
    shutil.copytree(STATIC, SITE)
    base = canonical.rstrip("/") + "/" if canonical else ""
    # front page
    (SITE / "index.html").write_text(page.render_home(home.render(data, page.HOME_FRAGMENT.read_text()), base))
    # calculator (fetches listings.json from beside itself)
    calc = SITE / "calculator"; calc.mkdir()
    (calc / "index.html").write_text(page.render_app(None, base + "calculator/" if base else ""))
    rent = SITE / "rent-vs-buy"; rent.mkdir()
    (rent / "index.html").write_text(page.render_rent(base + "rent-vs-buy/" if base else ""))
    equity = SITE / "equity"; equity.mkdir()
    (equity / "index.html").write_text(page.render_equity(base + "equity/" if base else ""))
    (SITE / "assets" / "app.css").write_text(page.CSS.read_text())
    (SITE / "assets" / "core.js").write_text(page.CORE.read_text())
    (SITE / "listings.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    (calc / "listings.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    (SITE / "robots.txt").write_text(robots(base or page.SITE_URL + "/"))
    lastmod = (data.get("generated_at") or "")[:10] or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (SITE / "sitemap.xml").write_text(sitemap(base or page.SITE_URL + "/", lastmod))
    (SITE / ".nojekyll").write_text("")      # GitHub Pages: serve the files as they are
    if domain:
        # Deploys from Actions replace the whole site, so the custom domain has to ship
        # with it — without this file GitHub Pages drops the domain on the next deploy.
        (SITE / "CNAME").write_text(domain + "\n")
    return SITE


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scrape", action="store_true", help="scrape the sites before building")
    ap.add_argument("--url", default="", help="the site's address, for the canonical link")
    ap.add_argument("--domain", default="", help="custom domain: writes site/CNAME and sets the canonical link")
    a = ap.parse_args()
    if a.scrape:
        scrape_run.save(scrape_run.scrape())
    d = scrape_run.load()
    if not d:
        raise SystemExit("No data/listings.json yet. Run with --scrape first.")
    canonical = f"https://{a.domain}/" if a.domain else a.url
    out = build(d, canonical, a.domain)
    kb = (out / "listings.json").stat().st_size / 1e3
    where = f" at https://{a.domain}/" if a.domain else ""
    print(f"Wrote {out.relative_to(ROOT)}/{where} — {len(d['listings'])} listings, listings.json {kb:.0f} KB")
