# Button

One primary action per view, in navy-700; everything else is secondary (outlined), ghost (text) or onDark (white on navy). Labels are verbs — "Calculate", "See listings" — and an `iconRight` arrow marks the action that moves to another page.

- Never two primaries side by side; pair primary + secondary ("Calculate" / "Reset").
- `size="sm"` only inside the header and card footers.
- Pass `href` to get an `<a>` with button styling; keep `<button>` for in-page actions.
