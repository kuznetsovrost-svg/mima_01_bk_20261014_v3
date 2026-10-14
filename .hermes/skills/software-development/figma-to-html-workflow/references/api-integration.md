# Figma API integration (figma-api-import)

How the new `figma-api-import` skill connects to this workflow.

## The bridge

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  User designs   │───▶│  figma-api-import│───▶│  JSON of frame  │
│  in Figma       │    │  skill           │    │  + components   │
└─────────────────┘    └──────────────────┘    └────────┬────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Final HTML     │◀───│  figma-to-html   │◀───│  JSON template  │
│  in Telegram    │    │  workflow skill  │    │  fill-in        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## What figma-api-import gives us

1. **`frame.json`** — the Figma frame tree with all nodes, sizes, fills, strokes, text
2. **`components/<name>.json`** — for each main component, the full structure including `componentPropertyDefinitions` (Variants)
3. **`components/<name>/variants/state=collapsed.json`** — each variant as a separate file
4. **`styles.json`** — Figma Styles (Color, Text, Effect)
5. **`variables.json`** — Variables (Figma's newer design tokens)
6. **`summary.md`** — readable summary for the agent

## How to use the JSON in template generation

### From `frame.json` to HTML

The frame JSON has `node.type` (FRAME, GROUP, INSTANCE, TEXT, RECTANGLE, ...) and properties per type. Map:

| Figma node | HTML element | Notes |
|---|---|---|
| `FRAME` (auto-layout) | `<div>` with flex | Use `layoutMode`, `primaryAxisAlignItems`, `counterAxisAlignItems` |
| `RECTANGLE` (filled) | `<div>` with `background-color` | Map fill hex → CSS custom property |
| `TEXT` | `<span>` or `<h1>`/`<p>` | `characters` → text content; `style.fontSize/Weight/Family` → CSS |
| `INSTANCE` | Template render | `componentId` → look up in `components/` |
| `GROUP` | `<div>` (no semantic) | Use absolute positioning if no auto-layout |
| `ELLIPSE` | `<div>` with `border-radius: 50%` | |

### From Variants to runtime classes

If `cmp.status-badge` has variants `state=critical|attention|healthy|neutral`, the JSON looks like:

```json
{
  "name": "Status Badge",
  "componentPropertyDefinitions": {
    "state": {
      "type": "VARIANT",
      "variantOptions": ["critical", "attention", "healthy", "neutral"]
    }
  },
  "variants": [
    {"name": "state=critical", "fills": [{"color": "#FEE2E2"}], ...},
    {"name": "state=attention", "fills": [{"color": "#FEF3C7"}], ...},
    ...
  ]
}
```

**In the HTML template:**
```html
<span class="badge badge--{{ row.severity }}">{{ row.severity_label }}</span>
```

**The CSS** (from tokens):
```css
.badge--critical { background: var(--status-critical-bg); color: var(--status-critical-text); }
.badge--attention { background: var(--status-attention-bg); color: var(--status-attention-text); }
```

## Token bridge

The figma-api-import's `variables.json` can be **converted directly** to `figma-tokens.json` (the Tokens Studio format):

```python
# Pseudo-code for the conversion
for var_id, var_data in variables.json['meta']['variables'].items():
    name = var_data['name'].replace('/', '-')  # "Status/Critical/Bg" → "Status-Critical-Bg"
    value = var_data['valuesByMode'][mode_id]
    if var_data['resolvedType'] == 'COLOR':
        token = {"value": hex_to_rgb(value), "type": "color"}
    elif var_data['resolvedType'] == 'FLOAT':
        token = {"value": f"{value}px", "type": "spacing"}
    # ...etc
    output[name] = token
```

This means: design in Figma → push to API → get JSON tokens → use as CSS variables → no manual sync needed.

## When to use figma-api-import vs manual

| Use API | Use manual |
|---|---|
| User has a real Figma file with components | User asks "how should I structure this" (no file yet) |
| User wants consistent extraction across projects | User is prototyping, hasn't built the design yet |
| Component has 5+ Variants that are tedious to read by hand | Single one-off component, easy to describe in chat |
| The template will use the JSON programmatically | The template will be hand-coded from chat description |

## How this skill (figma-to-html-workflow) references the API skill

When a new request lands:

1. Check if the user has a Figma file URL → run `figma-api-import` → use the JSON
2. If not, fall back to the playbook recipes in this skill
3. If the request is genuinely new (not in the 8 playbooks), write a new playbook following the skeleton in `references/best-practices-from-sessions.md`

## Scripts that combine both

Future scripts (to write when needed):

- `figma-to-tokens.py` — extract Variables → Tokens Studio JSON
- `figma-to-css.py` — extract Styles → CSS custom properties
- `figma-to-jinja.py` — extract components → Jinja2 macros

These would live under `figma-api-import/scripts/` and produce artifacts that this skill consumes.
