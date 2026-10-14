# html.to.design render rules — live-probe notes

What html.to.design keeps, drops, and mangles. Captured during the 2026-08-08 / 2026-08-21 iterations against `Report 3 TEST`, `Report 4`, `Report 5`.

## What survives intact

| Input | Output |
|-------|--------|
| `<div class="..." id="...">` | Figma FRAME named `div#<id>` (P3) |
| `class="div-name"` only | Figma FRAME named `div.<classname>` |
| `<table>`, `<thead>`, `<tbody>`, `<th>`, `<tr>`, `<td>` | Real Figma TABLE node (variant 4 — contradicted earlier advice) |
| `<details>`, `<summary>` | Renders expanded by default; loses collapse logic |
| `style="width: Npx"` on `<td>` | Sets FRAME width on corresponding cell |
| `display: flex` with `flex-direction: row` | Sets Figma auto-layout `HORIZONTAL` |
| `display: flex` with `flex-direction: column` | Sets Figma auto-layout `VERTICAL` |
| `justify-content: space-between` | Sets `primaryAxisAlignItems: SPACE_BETWEEN` (sometimes collapses to CENTER — see P1) |
| `align-items: center` | Sets `counterAxisAlignItems: CENTER` |
| `border-right: 1px solid #...` on each cell | Sets STROKE on each corresponding cell |
| `background: #hex` on a layer | Sets fill on corresponding FRAME |
| Text content in TEXT nodes | Copies to Figma TEXT `characters` field |

## What html.to.design drops silently

| Input | What you get instead |
|-------|----------------------|
| CSS variables (`:root { --bg: #2563EB }`) | No fill on the layer |
| `position: absolute; top: 20px; right: 24px` | Becomes flex child that stretches |
| `display: grid` | Collapses to flex with original layer order |
| `<table>` with `colspan` on `<th>` | Sometimes loses header layout |
| Nested `<details>` | Loses the nesting — both become expanded siblings |
| Comments `<!-- ... -->` | Stripped or kept non-deterministically |
| Inline `<style>` blocks | Stripped from the import (CSS is read but discarded for layout decisions) |
| Emoji glyphs 🔴🟡🟢 | Render as tofu `□` — must use text labels instead |
| SVG inline `<svg>` | Sometimes kept as IMAGE, sometimes lost |
| `<input>`, `<button>` | Becomes empty TEXT nodes |

## What html.to.design mangles (interprets differently from browser)

| Input | Browser | html.to.design |
|-------|---------|----------------|
| `<div class="report-header-text" style="display: flex; flex-direction: column;">` | Vertical stack | HORIZONTAL if no explicit flex-direction interpreted |
| `flex-shrink: 0` on indicator | Holds size | Often ignored — indicator stretches |
| `text-align: center` on `<th>` | Center text | Center text — works |
| `border-collapse: collapse` on `<table>` | Merged borders | Renders borders per cell — you see double borders |

## Loss budget (per round-trip)

Direction A → Direction B round-trip loses approximately:

| Element | Loss rate |
|---------|-----------|
| Layer hierarchy (groupings) | ~10% — wrapper divs may be merged |
| Sizes (width/height) | ~80% — most sizes become 0×0 unless inline-flex |
| Colors | ~95% preserved |
| Text content | ~100% preserved |
| Layer names | ~80% preserved (P3 caveat) |
| Auto-layout properties | ~60% preserved |

This is acceptable for **structural extraction** (sections, head cells, row count, color tokens) but NOT for **pixel-perfect re-render**. If the user wants pixel-perfect, switch to a different bridge (e.g. export the Figma file as image and inspect with vision tools).

## Plugin alternatives

| Plugin | Quality vs free html.to.design | Cost |
|--------|-------------------------------|------|
| **html.to.design** (free) | Baseline — drops sizes, mangling frequent | Free |
| **html.to.design** (paid) | Better size preservation, watermark removed | $$ |
| **Anima** | Better auto-layout, better size handling | $$ |
| **Builder.io** | Best HTML→Figma fidelity (paid) | $$ |

If pixel-perfect matters, recommend **Builder.io** or **Anima** paid. For our project-health reports with explicit inline widths, **free html.to.design** is acceptable.

## Tested against

- Report 3 TEST (file_key `vlv7GHSxXgQ04vz9Mk14tg`) — first bridge attempt, learned about COMPONENT_SET creation by user manually
- Report 4 (file_key `nZGrueTh7EigAsJ0zCzG0B`) — second attempt, refined placeholder strategy
- Report 5 (file_key `nZGrueTh7EigAsJ0zCzG0B`) — third attempt, user authored COMPONENT_SETs, full extraction

The user-author iteration loop (2026-08-21) yielded the most stable result: 5 table components + 1 indicator component, all with `State` variant, all with explicit Expanded/Collapsed options.