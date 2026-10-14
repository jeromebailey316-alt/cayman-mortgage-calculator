# CalculatorPanel

The site's signature element: a white panel (`radius-md`, `shadow-md`) that floats over the bottom of the hero and answers "what would this cost a month?" before the visitor scrolls. Four inputs — price, deposit %, rate, term — a live result and one primary button to the full breakdown.

- Its four values are the site's shared inputs (`CMC.inputs`): typing here updates every other page that shows a price, deposit, rate or term, and the panel opens with whatever the visitor last entered. `defaults` only apply when nothing has been entered yet. It follows the shared `currency` too: in US$ mode the price field and results convert at the fixed peg while the stored value stays in CI$.
- Computation is the standard amortising formula (`payment()` is exported); results round to the dollar and are labelled "Estimated".
- `tabLinks` maps the Refinancing and "What can I afford?" tabs to their pages (`{ refi, afford }`), so the tabs navigate instead of switching in place.
- `compact` stacks it to two columns for the calculator page sidebar and phones.
- `note` is for the rate source and date ("Rates from Cayman lenders, updated Oct 2026"); keep it one line.
- It never captures an email: the button goes to the breakdown page, nothing else.
