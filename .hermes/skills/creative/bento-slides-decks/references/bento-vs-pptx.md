# Bento vs PowerPoint — when to use which

This is the user's standing decision rule, not a generic comparison. Use
this whenever the deliverable could plausibly be either format.

## TL;DR

| Deliverable target | Use Bento | Use PPTX | Notes |
|---|---|---|---|
| Send to one colleague with modern browser | ✓ | | Self-contained, opens in any browser |
| Send to someone on an old OS or restricted browser | ✓ + PDF | | Email both files — `.bento.html` for the editor, `.pdf` as fallback |
| Send to "anyone who can open it" (mass) | ✓ + PDF | ✓ | Bento wins for editability, but **always include the PDF** for read-only recipients |
| Receive round-trip edits back | ✓ | ✓ | Bento edits are plain text diffs; PPTX edits are opaque XML |
| Print to paper | | ✓ | PDF export via browser works, but PDF-to-paper isn't directly supported in Bento |
| Speaker notes / handout mode | ✓ | ✓ | Both |
| Live demo with click-to-state drill-down | ✓ | | Bento's `stateOf` + `link` is much simpler than PPTX triggers |
| Long animations (morph, ken-burns, motion paths) | ✓ | ✓ | Bento gives the same result with declarative config instead of imperative triggers |
| Audit/archive (open in 5 years) | ✓ | | View-source readable JSON > opaque .pptx |

## The two-line decision

1. **Will the recipient open this in a browser at all?** Yes → Bento.
   No (only Microsoft Office) → PPTX.
2. **Is this an iterative process where LLM or text tools will edit the
   file?** Yes → Bento. PPTX edits through LLM tools are still painful
   even with python-pptx.

## What the user has explicitly said

- "ты в своих рассуждения не учел возможность генерить из BENTO файлы
  PDF. Это делается путем вывода на печать в формат PDF" — *when
  discussing Bento vs PPTX, always include the PDF fallback path*.
- PDF quality verified as "вполне приличное" by the user — no need to
  warn or qualify.

## Pitfall: don't recommend Bento where PPTX is the answer

If the deliverable target is a board deck sent to executives who use
PowerPoint, or a printed handout, **say so** before defaulting to Bento.
Bento's strength is editing and animation, not paper-print primitives.

## Pitfall: don't recommend PPTX where Bento wins cleanly

If the user wants animations, web-native delivery, or iterative edits,
PPTX is overhead. Switch to Bento and offer the PDF as the read-only
companion.

## Reference run: which format this user has been mixing

The user has, in this session alone, taken deliveries in **all three** forms:

- `Knowledge-Garden-Presentation.bento.html` — interactive demo deck
  (interactive deck for review)
- PDF of the same deck (via browser print) — read-only share
- Markdown playbooks (`*.md`) — reference doc

All three coexisted with no friction. That's the answer for what the
user actually wants in mixed workflows.
