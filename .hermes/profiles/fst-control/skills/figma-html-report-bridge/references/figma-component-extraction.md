# Direction B: Figma → Hermes (extract structure)

Detailed procedure for reading COMPONENT_SETs and INSTANCES back from a Figma file and re-emitting HTML.

## When to use

Direction B applies when:

- The user says "extract from Figma" and provides a file URL
- The user has hand-authored `COMPONENT_SET`s with variants in Figma (after Direction A)
- The user wants to regenerate HTML with **real** data substituted into the Figma-defined shape

## Step 1 — parse the Figma URL

```python
import re

def parse_figma_url(url):
    # https://www.figma.com/design/FILEKEY/Name?node-id=NODEID
    m = re.match(r'figma\.com/(?:file|design)/([A-Za-z0-9]+)/[^?]+(?:\?.*node-id=([^&]+))?', url)
    if not m:
        raise ValueError(f"Can't parse Figma URL: {url}")
    file_key = m.group(1)
    node_id = m.group(2).replace('-', ':')  # 0-1 → 0:1
    return file_key, node_id
```

## Step 2 — fetch the document tree

```python
from figma_client import FigmaClient
client = FigmaClient()

file_data = client.get_file(file_key)
nodes = client.get_nodes(file_key, [node_id])
```

`get_file` returns the full tree; `get_nodes` returns only the requested subtree. For extraction, `get_file` is enough.

## Step 3 — walk for COMPONENT_SETs

`get_components` endpoint frequently returns 0 — do NOT rely on it. Walk the tree yourself:

```python
def walk_components(node, found):
    if node.get('type') in ('COMPONENT_SET', 'COMPONENT'):
        found.append(node)
    for child in node.get('children', []):
        walk_components(child, found)

components = walk_components(file_data['document'], [])
```

For each COMPONENT_SET, extract:

- `id`, `name` (e.g. `"TBL3"`)
- `componentPropertyDefinitions` — all variant properties and their `variantOptions`
- `children` — each child is a COMPONENT (one per variant option)

For each COMPONENT variant, extract:

- `id`, `name` (e.g. `"State=Expanded"`)
- `children` — the structure (summary, head, row)
- For each TEXT node: `characters` (the literal text content, which is `{{TOKEN}}` placeholder)
- For each layer: `fills[0].color` in `r/g/b` 0-1 range → convert to `#rrggbb`

## Step 4 — locate the target Frame

If the user said "extract from `Report_5_01`", find it by name within the document:

```python
def find_frame_by_name(node, target_name):
    if node.get('name', '').strip() == target_name:
        return node
    for child in node.get('children', []):
        r = find_frame_by_name(child, target_name)
        if r: return r
    return None
```

## Step 5 — extract INSTANCES

Inside the target Frame, find all INSTANCES:

```python
def walk_instances(node, found):
    if node.get('type') == 'INSTANCE':
        found.append(node)
    for child in node.get('children', []):
        walk_instances(child, found)
```

For each INSTANCE, extract:

- `id`, `name` (e.g. `"TBL3"`)
- `componentProperties` — the user's chosen variant values, e.g. `{"State": {"value": "Collapsed"}}`
- `children` — usually just the summary (because Collapsed doesn't show rows)

**If `State.value == "Collapsed"`, warn the user** — they need to switch to Expanded in Figma before the next extraction pass, otherwise you can't read row data.

## Step 6 — normalise property names

User feedback 2026-08-21: Property names vary across components. Normalise:

- `State` — unified by user after first extraction pass
- `Property 1`, `Property 2` — Figma's default names; tell the user to rename
- `Status`, `Severity` — user-chosen names from other conventions

Best practice: instruct the user once to rename every variant property to `State` (or `Severity`). Once done, all subsequent extractions are uniform.

## Step 7 — emit the components.json

Save the full snapshot:

```json
{
  "file_key": "nZGrueTh7EigAsJ0zCzG0B",
  "frame_id": "1:226",
  "frame_name": "Report_5_01",
  "components": {
    "TBL3": {
      "id": "5:53",
      "property": "State",
      "options": ["Expanded", "Collapsed"],
      "variants": {
        "Expanded": {
          "id": "5:52",
          "summary": "{{S3_SUMMARY}}",
          "summary_color": "#FEF3C7",
          "head_cells": ["#", "Код", "Наименование", "План", "Прогноз"],
          "head_widths": [40, 90, 320, 140, 140],
          "row_color": "#FEE2E2",
          "row_count": 3
        },
        "Collapsed": {
          "id": "5:51",
          "summary": "{{S3_SUMMARY}}",
          "summary_color": "#FEF3C7"
        }
      }
    }
  },
  "instances": [
    {
      "id": "5:95",
      "component": "TBL3",
      "properties": {"State": "Collapsed"}
    }
  ]
}
```

## Step 8 — build the HTML

For each component, build a `<table>` from the **Expanded** variant. Use:

- `head_cells` for `<th>` content
- `head_widths` for `<th style="width: Npx;">`
- `row_color` for `<tr class="critical|warning|healthy|neutral">`
- `summary_color` for the summary `<tr class="table-summary">`

If a cell width is unknown, distribute the leftover pixels to the widest column.

## Real working example

`/tmp/figma_v5/scripts/build_html_v6.py` — already implements everything in this reference. Read it for a complete Python reference implementation.

## Checklist before shipping HTML back to user

- [ ] Every `<tr>` cell widths sum to 1562
- [ ] Property names normalised to `State`
- [ ] Headings match what the user defined in Figma component
- [ ] `row_color` matches Figma's `div.table-row` fill
- [ ] Hand off as MEDIA: file
- [ ] Tell the user "if you want to push back to Figma, delete the old SECTION first" (P10)