# Header

Logo left (`cmc-secondary-color.svg` at 40px tall; the reversed file when `dark`), nav links centred-right in the `nav` style with a 2px navy underline on the active page, and one primary `cta`. The optional `utility` bar above is `navy-900` with 12px items (phone, "Free to use", "Listings shown with agents' permission").

- Nav order: Home, Calculators ▾, Listings, Guides ▾, Agents, About. `homeHref` sets where the logo links (the homepage). An item may carry a `menu` (Calculators: Mortgage, Equity, Affordability; Guides: Stamp duty, Closing costs, Refinancing). The label is a link to the section's first page; the chevron beside it is a separate button that expands or collapses the dropdown (click again, click elsewhere or press Escape to close). Hover still previews the menu on desktop. `open: true` on an item pins its dropdown open when the page loads; the visitor can still collapse it.
- `logoHeight` enlarges the lockup within the same 72px row (max 64); the row never grows.
- The CTA is the calculator ("Run the numbers"), not a sign-up.
- The header is sticky (`position: sticky; top: 0`) on every width so the menu is always reachable.
- Below 860px the utility bar is hidden, the row drops to 60px with the logo capped at 36px, the nav and CTA collapse behind a menu button that opens a full-width drawer: every link, groups expanded with their icons, the CTA as a block button at the bottom. Escape or any link closes it.
