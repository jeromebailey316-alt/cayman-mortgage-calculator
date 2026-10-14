# Input

A labelled text control with optional `prefix` ("CI$") and `suffix` ("%") rendered inside the border so money and percentages read as one unit. Focus is a teal-600 border with a teal-100 ring.

`Select` shares the same frame and adds a chevron; pass `options` as strings or `{value,label}` pairs.

- Labels are nouns, 12px semibold, above the control; hints and errors go below in 12px.
- Errors keep the text dark (`ink-900`) and the border `ink-700` — no red in this system.
- Use `type="number"` with `inputMode="decimal"` for money and rates so phones show the right keyboard.
- `bind="price" | "deposit" | "rate" | "term"` makes the control a live two-way view of the site's shared inputs (`CMC.inputs`), so a price typed on the stamp duty page is the price the calculator shows. Add the hint "Synced with the calculator" the first time it appears on a page.
