"""Build the static website into site/ — what GitHub Pages publishes.

    .venv/bin/python build_site.py                      # uses data/listings.json
    .venv/bin/python build_site.py --scrape             # scrape first
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
from pathlib import Path

import page
from scraper import run as scrape_run

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"

ROBOTS = "User-agent: *\nAllow: /\n"


def build(data: dict, canonical: str = "") -> Path:
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir(parents=True)
    (SITE / "index.html").write_text(page.render(None, canonical))
    (SITE / "listings.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    (SITE / "robots.txt").write_text(ROBOTS)
    (SITE / ".nojekyll").write_text("")      # GitHub Pages: serve the files as they are
    return SITE


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scrape", action="store_true", help="scrape the sites before building")
    ap.add_argument("--url", default="", help="the site's address, for the canonical link")
    a = ap.parse_args()
    if a.scrape:
        scrape_run.save(scrape_run.scrape())
    d = scrape_run.load()
    if not d:
        raise SystemExit("No data/listings.json yet. Run with --scrape first.")
    out = build(d, a.url)
    kb = (out / "listings.json").stat().st_size / 1e3
    print(f"Wrote {out.relative_to(ROOT)}/ — {len(d['listings'])} listings, listings.json {kb:.0f} KB")
