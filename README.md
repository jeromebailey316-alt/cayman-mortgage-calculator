# Cayman Mortgage Calculator

Works out the monthly payment and the real cash needed to buy in the Cayman Islands
(stamp duty, mortgage duty, Land Registry, legal and bank fees). It then shows homes and
land for sale right now, priced through the same settings.

Listings are read from the public websites of:

| Source | What's read | Notes |
|---|---|---|
| CIREBA (`cireba.com`) | Houses, condos and land, newest first | The MLS. Most properties from every agency appear here |
| RE/MAX (`remax.ky`) | Homes, condos and land | Uses the site's own map-search JSON |
| Williams2 (`williams2realestate.com`) | The agency's newest 40 listings | Prices come from each listing page, so the scraper stops at 40 |
| Trident (`tridentproperties.ky`) | The agency's own listings | Its copy of the MLS feed is skipped (it duplicates CIREBA) |
| Bovell RE/MAX (`bovell.ky`) | The Bovell team's listings | Also on remax.ky; merged by MLS number |
| ERA (`eracayman.com`) | ERA's own listings page | |
| Property Cayman (`propertycayman.com`) | Listings on each agent's page | The site's search is the full MLS feed |
| MOD Realty (`modrealtycayman.com`) | For-sale listings | No MLS numbers, so these can't be merged with other sites |
| The Agency (`theagencyre.ky`) | "Agency listings" via the site's JSON API | |
| Shoreline (`shoreline.ky`) | "Our listings" | House vs condo is guessed from the title |
| MyRealtor (`myrealtor.agency`) | The sales page | No MLS numbers |
| IRG (`irgcayman.com`) | IRG's own listings | Up to 40 listing pages for type and area |
| Provenance (`provenanceproperties.com`) | Own listings from the site's JSON API | |
| Rainbow Realty (`rainbowrealty.ky`) | Own residential and land listings | House vs condo is guessed from the title |
| Berkshire Hathaway HomeServices (`bhhscaymanislands.com`) | Listings on each agent's profile | bhhscayman.com is a parked domain |

Two more modules exist but are **off by default** (the page shows them as unavailable, with the reason):

- **Century 21** (`century21cayman.com`): its firewall blocks after about 8 requests, and it only shows the CIREBA feed.
- **Engel & Völkers** (`evrealestate.com`): its robots.txt asks AI agents such as ClaudeBot not to read its listing
  pages, so Claude doesn't run it. You can run it yourself with `.venv/bin/python -m scraper.run --include engelvoelkers`.

Most agency sites also carry the whole CIREBA feed. The scrapers read only each agency's own listings, because
CIREBA already covers the rest. A property listed on several sites under the same MLS number is shown once,
with links to the other sites.

## Publish it as a website

The site is static: `index.html` plus `listings.json` beside it. A GitHub Action
(`.github/workflows/update-listings.yml`) scrapes every 4 hours, commits the refreshed
listings and republishes to GitHub Pages. Nothing needs to run on your Mac.

1. Create an **empty public repository** on GitHub (no README, no .gitignore), for example `cayman-mortgage`.
2. Push this folder to it:
   ```bash
   git remote add origin https://github.com/<you>/cayman-mortgage.git
   git branch -M main
   git push -u origin main
   ```
3. In the repository: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
4. In **Settings → Actions → General → Workflow permissions**, choose **Read and write permissions**
   (the workflow commits the refreshed listings).
5. Run it once by hand: **Actions → Update listings and publish → Run workflow**.

The site is then at `https://<you>.github.io/cayman-mortgage/`, and refreshes at
01:07, 05:07, 09:07, 13:07, 17:07 and 21:07 UTC (that's 20:07, 00:07, 04:07, 08:07,
12:07 and 16:07 in Cayman). To use your own domain, add it under Settings → Pages.

**If a website is down or blocks the runner**, that source keeps its last good listings
(cached in `data/raw/`) and the page marks it "from &lt;date&gt;" instead of dropping it. The
workflow only refuses to publish if fewer than 100 properties survive a run.

### Topping up from your Mac

ERA, Property Cayman and MOD Realty answer 403 to GitHub's datacenter addresses but are
fine from a home connection, so those three run from cache on the hosted schedule. To
refresh them, run a scrape here and push it — that republishes the site too:

```bash
.venv/bin/python -m scraper.run && git add data && git commit -m "Listings from a local run" && git push
```

**Changing the schedule:** edit the `cron` line in the workflow. GitHub runs scheduled jobs
on a best-effort basis, so a run can start a few minutes late, or be skipped when GitHub is busy.

## Run it locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python server.py
```

This opens http://127.0.0.1:8787. If the saved listings are missing or more than 4 hours old,
the server scrapes the sites in the background. Use **Refresh listings** on the page to scrape again.

## Other commands

```bash
.venv/bin/python -m scraper.run            # scrape and write data/listings.json
.venv/bin/python -m scraper.run --pages 2  # quicker, shallower scrape
.venv/bin/python build_site.py             # build the website into site/
.venv/bin/python build_site.py --scrape    # scrape first, then build
.venv/bin/python build.py                  # one self-contained HTML file in dist/ (photos embedded)
```

Preview the built site with `.venv/bin/python -m http.server 8788 --directory site`.

`build.py` embeds small copies of the listing photos, because a published page can't load
images from other websites.

## Layout

```
web/index.html        the app (calculator + listings); listing data goes in the __LISTINGS_JSON__ slot
page.py               the HTML head shared by the server, the site and the single-file build
build_site.py         builds site/ (index.html + listings.json) for GitHub Pages
server.py             local server: page, /api/listings, /api/status, POST /api/refresh
build.py              single-file build with photos embedded, for publishing as one HTML file
scraper/common.py     Listing record, polite rate-limited HTTP (1 request/sec per site), parsers
scraper/sources/*.py  one module per website: SOURCE name + fetch(max_pages) -> [Listing]
scraper/run.py        runs every source in parallel, merges duplicates, writes data/listings.json
data/listings.json    the merged listings the site serves
data/raw/<source>.json  each source's last good result, used when that site is down
.github/workflows/    the 4-hourly scrape-and-publish action
```

The page gets its listings either injected into the HTML (local server and single-file build)
or fetched from `listings.json` beside it (the website).

To add a site, drop a module in `scraper/sources/` with `SOURCE` and `fetch()`, then add it to
`SOURCES` in `scraper/run.py`.

## Being a good citizen

The scrapers make one request per second per site, keep to robots.txt, and read listing
index pages rather than every detail page. Scrapers depend on each site's current HTML, so
a redesign can break one. The page shows any source that failed, and the other sources still load.
Listing data belongs to the agencies. Always check prices and availability on the agent's own page.
