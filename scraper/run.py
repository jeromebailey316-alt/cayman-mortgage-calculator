"""Scrape every source, merge duplicates and write data/listings.json.

    .venv/bin/python -m scraper.run            # default page depth
    .venv/bin/python -m scraper.run --pages 2  # quick run
"""
from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "listings.json"
RAW = ROOT / "data" / "raw"          # last good result per source, used when a site is down

# module name -> default max_pages (each module documents what a "page" means for its site)
SOURCES = {
    "cireba": 6,          # the MLS: houses, condos, land, newest first (30 per page per category)
    "remax": 8,           # 6 per page per type
    "bovell": 5,          # the Bovell team's own RE/MAX listings (overlap remax, merged by MLS)
    "williams2": 2,       # 20 per page; only the newest 40 get prices (detail pages)
    "trident": 1,         # 1 = Trident's own listings only; more pages add its copy of the MLS feed,
                          # which duplicates CIREBA without MLS numbers to merge on
    "era": 1,             # ERA's own listings, one page
    "propertycayman": 1,  # own listings via agent pages (max_pages not used)
    "mod": 6,             # 8 per page, own listings only, no MLS numbers
    "theagency": 1,       # "Agency listings" via the site's JSON API
    "shoreline": 1,       # "Our listings"
    "myrealtor": 1,       # all on one page, no MLS numbers
    "irg": 1,             # own listings + up to 40 detail pages
    "provenance": 1,      # own listings from the site's JSON API
    "rainbow": 3,         # own listings, per category
    "bhhs": 5,            # own listings via the agents API
}

# Modules that exist but are not run by default, with the reason shown on the page.
DISABLED = {
    "century21": ("Century 21", "Turned off: the site blocks repeated requests, and it only shows "
                                "the CIREBA feed, which is already covered."),
    "engelvoelkers": ("Engel & Völkers", "Turned off: the site's robots.txt asks AI agents not to read "
                                         "its listing pages. Run with --include engelvoelkers to scrape it yourself."),
}

# Hosts whose robots.txt disallows the image paths: build.py won't download these,
# and merge() prefers another source's photo when one exists.
NO_THUMB_HOSTS = ("tridentproperties.ky",)

FIELDS = ("title", "price", "location", "beds", "baths", "sqft", "acres", "image", "mls", "status")


def _cache_path(mod_name: str) -> Path:
    return RAW / f"{mod_name}.json"


def _save_raw(mod_name: str, name: str, listings: list[dict]) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    _cache_path(mod_name).write_text(json.dumps(
        {"name": name, "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "listings": listings},
        ensure_ascii=False))


def _load_raw(mod_name: str) -> dict | None:
    try:
        return json.loads(_cache_path(mod_name).read_text())
    except (OSError, ValueError):
        return None


def _fallback(mod_name: str, name: str, error: str) -> dict:
    """A site that failed this run keeps showing its last good listings, marked stale."""
    cached = _load_raw(mod_name)
    if not cached or not cached.get("listings"):
        return {"name": name, "ok": False, "count": 0, "error": error, "listings": []}
    return {"name": name, "ok": False, "stale": True, "as_of": cached.get("fetched_at"),
            "count": len(cached["listings"]), "error": error, "listings": cached["listings"]}


def _run_source(mod_name: str, pages: int) -> dict:
    try:
        mod = importlib.import_module(f"scraper.sources.{mod_name}")
    except Exception as e:  # module missing or broken
        return _fallback(mod_name, mod_name, f"Not available: {e}")
    name = getattr(mod, "SOURCE", mod_name)
    try:
        ls = [l.to_dict() for l in mod.fetch(pages)]
        ls = [l for l in ls if l.get("url") and l.get("price_kyd")]
        if not ls:
            return _fallback(mod_name, name, "No listings found")
        _save_raw(mod_name, name, ls)
        return {"name": name, "ok": True, "count": len(ls), "error": "", "listings": ls}
    except Exception as e:
        traceback.print_exc()
        return _fallback(mod_name, name, f"{type(e).__name__}: {e}"[:300])


def _richness(l: dict) -> int:
    return sum(1 for f in FIELDS if l.get(f))


def _key(l: dict) -> str:
    mls = re.sub(r"\D", "", str(l.get("mls") or ""))
    if mls:
        return "mls:" + mls
    title = re.sub(r"[^a-z0-9]", "", (l.get("title") or "").lower())
    return f"tp:{title}:{round(l.get('price_kyd') or 0, -3)}"


def merge(all_listings: list[dict]) -> list[dict]:
    """One record per property. The same MLS number can appear on CIREBA and on the
    listing agency's own site; keep the fuller record and remember the other links."""
    groups: dict[str, list[dict]] = {}
    for l in all_listings:
        groups.setdefault(_key(l), []).append(l)
    out = []
    for group in groups.values():
        group.sort(key=_richness, reverse=True)
        best = dict(group[0])
        for other in group[1:]:
            for f in FIELDS:
                if not best.get(f) and other.get(f):
                    best[f] = other[f]
        seen, sources, also = set(), [], []
        for l in group:
            if l["source"] not in seen:
                seen.add(l["source"])
                sources.append(l["source"])
                if l is not group[0]:
                    also.append({"source": l["source"], "url": l["url"]})
        imgs = [l["image"] for l in group if l.get("image")]
        ok = [i for i in imgs if not any(h in i for h in NO_THUMB_HOSTS)]
        best["image"] = (ok or imgs or [""])[0]
        best["sources"] = sources
        best["also"] = also
        out.append(best)
    out.sort(key=lambda l: l.get("price_kyd") or 0)
    return out


def scrape(pages: int | None = None, log=print, include: tuple[str, ...] = ()) -> dict:
    jobs = {m: (pages or p) for m, p in SOURCES.items()}
    for m in include:
        jobs[m] = pages or 5
    with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
        results = list(ex.map(lambda kv: _run_source(*kv), jobs.items()))
    raw = []
    for r in results:
        mark = "ok " if r["ok"] else ("old" if r.get("stale") else "ERR")
        log(f"  {r['name']:<10} {mark} {r['count']:>4} listings {r['error']}")
        raw.extend(r.pop("listings"))
    for m, (name, why) in DISABLED.items():
        if m not in jobs:
            results.append({"name": name, "ok": False, "count": 0, "error": why})
    merged = merge(raw)
    log(f"  {len(raw)} scraped -> {len(merged)} after merging duplicates")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": results,
        "listings": merged,
    }


def save(data: dict, path: Path = OUT) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    tmp.replace(path)


def load(path: Path = OUT) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pages", type=int, default=None, help="max pages per source (overrides defaults)")
    ap.add_argument("--include", action="append", default=[], metavar="MODULE",
                    help="also run a turned-off source, e.g. --include century21")
    a = ap.parse_args()
    print("Scraping Cayman listing sites…")
    d = scrape(a.pages, include=tuple(a.include))
    save(d)
    print(f"Wrote {OUT.relative_to(ROOT)}")
    sys.exit(0 if d["listings"] else 1)
