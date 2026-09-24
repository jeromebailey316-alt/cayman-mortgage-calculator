`update-listings.yml` runs every 4 hours: it scrapes the agency websites, commits the
refreshed `data/listings.json`, builds `site/` and publishes it to GitHub Pages.

If a website is down or blocks the runner, that source keeps its last good listings from
`data/raw/`, and the page shows it as "from <date>". The run only stops short of publishing
if fewer than 100 properties survive, which would mean something broke more widely.

Sites that refuse GitHub's datacenter addresses (ERA, Property Cayman and MOD Realty
return 403) fall back to their cached listings, and the page shows their date.
