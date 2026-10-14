---
name: diagram-format-conversion
description: Convert diagrams between formats — BPMN ↔ DrawIO, BPMN ↔ Mermaid, Mermaid ↔ DrawIO, SVG ↔ any, BPMN ↔ Camunda 7/8. Use when the user asks "конвертируй X в Y", "convert this diagram to <format>", "BPMN в drawio", "drawio в mermaid", or hands you a `.bpmn`/`.drawio`/`.mmd`/`.svg` file and asks for a specific target format. Captures format quirks (mxGraph root-cell id reservation, BPMN DI coordinates, namespace maps), the verified scripts, and the "no ready-made npm package exists for BPMN→DrawIO" reality that pushes you toward Python+xml.etree.
version: 0.4.0
author: Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [diagrams, bpmn, drawio, mermaid, conversion, mxgraph, camunda]
    related_skills: [architecture-diagram, excalidraw, guide-authoring-for-hermes]
---

# Diagram Format Conversion

Class: the user has a diagram in one format (BPMN, DrawIO, Mermaid, SVG) and wants the **same diagram** in another format. The class is "produce a faithful structural conversion" — not "design a new diagram" (use `architecture-diagram` or `excalidraw`) and not "explain what these formats are."

## When to Use

- User phrasings: "конвертируй .bpmn в .drawio", "convert this DrawIO file to Mermaid", "BPMN в mermaid", "переведи диаграмму из X в Y", "give me a Mermaid version of this BPMN".
- Hands you a `.bpmn`/`.bpmn`-shaped XML, a `.drawio`/`.xml` from diagrams.net, a `.mmd`/`.md` with mermaid blocks, or an `.svg`.
- Asks for a specific output format by name.

**Don't use for:** designing a new diagram from scratch (use `architecture-diagram` for SVG/HTML, `excalidraw` for hand-drawn), explaining what BPMN is, or generating images/PDFs of an existing diagram (use a renderer like `mermaid-cli` or Playwright).

## Verified Conversions (this host has working code)

| From → To | Status | Tool | Where |
|---|---|---|---|
| **BPMN 2.0 (.bpmn) → DrawIO (.drawio)** | ✅ Working | **`davistroy/bpmn2drawio`** (community skill, 24 .py modules, 260 KB) — see `references/bpmn-to-drawio-skill.md` for the install + run recipe | `/root/bpmn-skill/` |
| **BPMN 2.0 (.bpmn) → DrawIO (.drawio)** (DI-preserving fallback) | ✅ Working | Custom stdlib-only Python converter using BPMN DI coordinates + BPMNEdge waypoints. **Use this when the source is a collaboration diagram with multiple pools** — verified on a 7-pool Camunda file (105 cells, opens cleanly in diagrams.net, positions match source within ±0 px). | `templates/bpmn_to_drawio_di_preserve.py` |
| **BPMN 2.0 (.bpmn) → DrawIO (.drawio)** (no-deps fallback) | ✅ Working | Python `xml.etree` + custom converter | `scripts/bpmn_to_drawio.py` |
| **Mermaid → Camunda BPMN** | ✅ Covered | via `bpmn_форматы_01.txt` guide + Camunda Modeler manual | `/root/BPMN_форматы_01.txt` |
| DrawIO → BPMN | ❌ No ready tool | Would need reverse mxGraph parsing | — |
| Mermaid → DrawIO | ⚠️ Possible | via mermaid-cli SVG → mxGraph import | needs research |
| DrawIO → Mermaid | ⚠️ Possible | via mmdc CLI reverse | needs research |

**The first row is the canonical tool as of 2026-07-08** — see `references/bpmn-to-drawio-skill.md` for the verified install + run sequence (download from `davistroy/claude-marketplace`, install `lxml networkx pyyaml`, run with `--layout preserve` to keep BPMN DI coordinates). The custom converter in `templates/bpmn_to_drawio_di_preserve.py` is the right fallback when `bpmn2drawio` breaks on collaboration diagrams (see `references/bpmn-di-preserve-coords-converter.md`). The simpler converter in `scripts/bpmn_to_drawio.py` remains as a no-dependency fallback for hosts where pip isn't available.

## Critical Format Quirk: DrawIO `mxCell` id reservation (footgun)

**All DrawIO files start with these two root cells:**

```xml
<mxCell id="0" />
<mxCell id="1" parent="0" />
```

**`id="0"` is the document root. `id="1"` is the first-level container with `parent="0"`.** Every diagram element must have `id >= 2`. A converter that starts user-element IDs at 1 produces `Duplicate ID '1'` and diagrams.net refuses to open it.

**Verified failure (2026-07-08):** The first run of `bpmn_to_drawio.py` started its counter at `1` and the resulting `.drawio` failed with "Duplicate ID '1'" on open. Fix: start at `2`. The corrected converter is committed to `scripts/bpmn_to_drawio.py`. The new `templates/bpmn_to_drawio_di_preserve.py` starts at `2` by design.

**Rule:** any custom DrawIO converter must initialize its element-id counter at **2** (or higher). `0` and `1` are reserved for the root skeleton that `<mxGraphModel>` requires.

## BPMN 2.0 → DrawIO: the converter design

The verified Python converters (`scripts/bpmn_to_drawio.py` and `templates/bpmn_to_drawio_di_preserve.py`) handle the full standard BPMN 2.0 element set. The design choices that took non-trivial work to figure out:

### Namespace map

```python
NS = {
    'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
    'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
    'dc': 'http://www.omg.org/spec/DD/20100524/DC',
    'di': 'http://www.omg.org/spec/DD/20100524/DI',
}
```

`bpmn:` holds semantic elements (tasks, events, flows). `bpmndi:` holds the Diagram Interchange (DI) — that's where x/y/w/h come from. **Coordinates live in `bpmndi:BPMNShape/bpmndi:BPMNBounds/dc:Bounds`** (note the three-level nesting), not directly on the BPMN element. **Edges also have geometry in DI** — `bpmndi:BPMNEdge/di:waypoint` is a sequence of (x, y) routing points that produces the orthogonal routing when emitted as `<mxPoint as="sourcePoint"/>` / `as="targetPoint"` / `as="points"` inside an `<mxGeometry relative="1">` block on the edge `<mxCell>`.

### Element-to-style mapping (mxGraph BPMN shape library)

DrawIO has a built-in `mxgraph.bpmn.*` shape library that renders proper BPMN glyphs. The mapping that worked:

| BPMN element | DrawIO style |
|---|---|
| `bpmn:task` | `shape=mxgraph.bpmn.task;taskMarker=abstract;` |
| `bpmn:serviceTask` | `...taskMarker=service;fillColor=#d5e8d4;strokeColor=#82b366;` |
| `bpmn:userTask` | `...taskMarker=user;fillColor=#dae8fc;strokeColor=#6c8ebf;` |
| `bpmn:sendTask` / `receiveTask` | `...taskMarker=send/receive;fillColor=#f8cecc;...` |
| `bpmn:businessRuleTask` | `...taskMarker=businessRule;fillColor=#e1d5e7;...` |
| `bpmn:startEvent` / `endEvent` | `shape=mxgraph.flowchart.terminator;...` (NOT `mxgraph.bpmn.event`) |
| `bpmn:intermediateThrowEvent` / `CatchEvent` | `shape=mxgraph.flowchart.terminator;...` |
| `bpmn:exclusiveGateway` | `shape=mxgraph.bpmn.gateway2;...` (diamond with X) |
| `bpmn:parallelGateway` | `shape=mxgraph.bpmn.gateway_plus;...` (diamond with +) |
| `bpmn:inclusiveGateway` | `shape=mxgraph.bpmn.gateway_or;...` (diamond with O) |
| `bpmn:eventBasedGateway` | `shape=mxgraph.bpmn.gateway_event;...` |
| `bpmn:subProcess` | `shape=mxgraph.bpmn.subprocess;...` |
| `bpmn:callActivity` | `shape=mxgraph.bpmn.activity2;...` |
| `bpmn:participant` (pool) | `shape=mxgraph.bpmn.pool;...` |
| `bpmn:dataObjectReference` | `shape=mxgraph.bpmn.data_object;...` |
| `bpmn:dataStoreReference` | `shape=mxgraph.bpmn.datastore;...` |
| `bpmn:textAnnotation` | `shape=note;background=#ffff99;` |

The colour scheme follows BPMN 2.0 conventions: green for service, blue for user, red for messaging, yellow for manual, purple for business rule.

### Flow mapping

Three kinds of edges in BPMN, three edge styles in DrawIO:

| BPMN edge | DrawIO style | Notes |
|---|---|---|
| `bpmn:sequenceFlow` | `edgeStyle=orthogonalEdgeStyle;endArrow=classic;` | Standard arrow |
| `bpmn:messageFlow` | `edgeStyle=orthogonalEdgeStyle;dashed=1;startArrow=oval;endArrow=open;startFill=0;` | **Dashed**, between pools — the visual convention for cross-pool messaging |
| `bpmn:association` | `edgeStyle=orthogonalEdgeStyle;dashed=1;strokeColor=#666666;strokeWidth=1.5;endArrow=open;startArrow=none;` | For data-object / annotation links. **Must be orthogonal — see "Association edges must use orthogonalEdgeStyle" pitfall** |

### Text escaping in `<mxCell value="...">`

BPMN names frequently contain Cyrillic, quotes, ampersands. mxCell `value` is XML, so escape:

```python
def _escape_xml(self, s):
    if not s:
        return ''
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
             .replace('"', '&quot;').replace("'", '&apos;'))
```

Newlines in BPMN labels become `&#xa;` (HTML entity) for multi-line rendering inside DrawIO shapes.

### Text annotations: read from `<bpmn:text>`, not `@name`

`textAnnotation` elements put their content in a child `<bpmn:text>` element, not the `name` attribute. Handle separately:

```python
if tag_name == 'textAnnotation':
    text_elem = elem.find('{' + NS['bpmn'] + '}text')
    if text_elem is not None and text_elem.text:
        name = text_elem.text
```

## Recipe: BPMN → DrawIO on this host

```bash
# 1. Copy the converter
ls /root/bpmn_to_drawio.py  # exists; ~13 KB (no-deps fallback)

# 2a. Convert with the stdlib converter
python3 /root/bpmn_to_drawio.py /path/to/diagram.bpmn /root/diagram.drawio

# 2b. OR — if the source is a collaboration diagram (multiple pools,
#     message flows) and bpmn2drawio misbehaves — use the DI-preserving
#     converter for 1:1 source-tool fidelity. See
#     references/bpmn-di-preserve-coords-converter.md for the write-up.
cp templates/bpmn_to_drawio_di_preserve.py /root/bpmn_to_drawio_v2.py
python3 /root/bpmn_to_drawio_v2.py /path/to/diagram.bpmn /root/diagram.drawio

# 3. Verify XML is valid and IDs are unique
python3 -c "
import xml.etree.ElementTree as ET
t = ET.parse('/root/diagram.drawio')
cells = t.findall('.//mxCell')
ids = [c.get('id') for c in cells]
dupes = [x for x in set(ids) if ids.count(x) > 1]
print('cells:', len(cells), 'unique:', len(set(ids)), 'dupes:', dupes or 'none')
"

# 4. Deliver to user
#    Open in https://app.diagrams.net/ via File → Open from Device
```

**Typical output for a Camunda collaboration diagram with 7 pools:** ~100 cells, 36-40 KB `.drawio`, opens cleanly in diagrams.net. The DI-preserving converter produces exact source-tool positions (±0 px), while the `bpmn2drawio` community skill may shift things by a few px even with `--layout preserve`.

**If events render as rectangles in the output:** edit `STYLE_START` / `STYLE_END` / `STYLE_IEVENT` in `templates/bpmn_to_drawio_di_preserve.py` to use `shape=mxgraph.flowchart.terminator;` instead of `shape=mxgraph.bpmn.event;`. See "BPMN events render as rectangles" pitfall below.

**If association arrows are invisible:** edit `STYLE_ASSOC` to use `edgeStyle=orthogonalEdgeStyle;...;strokeWidth=1.5;` instead of `edgeStyle=none;`. See "Association edges must use orthogonalEdgeStyle" pitfall below.

## When NO ready-made tool exists

For BPMN→DrawIO specifically, the npm registry search returns nothing useful (verified 2026-07-08). The path is:

1. Don't waste time looking for a 1-line install.
2. Write a Python converter using `xml.etree.ElementTree` (stdlib).
3. Test on a real Camunda-exported file (they have rich DI data — better test than synthetic).
4. Validate the output by re-parsing it and checking for duplicate IDs before declaring done.
5. **If the diagram has pools and `bpmn2drawio`'s layout still misaligns them, use `templates/bpmn_to_drawio_di_preserve.py` instead** — the DI-preserving path is the right answer for collaboration diagrams.

For other pairs (DrawIO→Mermaid, Mermaid→DrawIO), the same rule applies: assume no ready tool, write a small converter, validate round-trip.

## Pitfalls

### BPMN `name` attribute can be empty (Camunda default)

When you author a task in Camunda Modeler without typing a name, `name=""` is set explicitly. The converter must default to empty string, not crash on `None`. Always use `elem.get('name', '')`, never `elem.get('name')`.

### Pools need a height, not just x/y

A `bpmn:participant` (pool) usually has a width spanning the whole diagram and a height covering all its lanes. The DI bounds carry this. **Don't default pools to 120×80 like tasks** — they need to read as containers. The converter passes through the DI height as-is.

### Message flows only exist in collaboration diagrams

`bpmn:messageFlow` only appears inside `bpmn:collaboration`, never inside a `bpmn:process`. If your converter sees no `messageFlow` elements, it means the source is a plain `bpmn:process` (no participants) — convert to a single-pool DrawIO diagram.

### DI is optional

Some BPMN files (especially hand-written ones, or exports from older tools) skip `bpmndi:BPMNShape` entirely. Without DI there are no coordinates — the converter falls back to a default 120×80 placement in a grid, which is ugly but doesn't fail. Flag this in your reply so the user knows they need to add layout in DrawIO manually. **When DI is missing, the DI-preserving converter (`templates/bpmn_to_drawio_di_preserve.py`) is useless** — use `bpmn2drawio --layout graphviz` instead.

### Camunda Cloud uses `zeebe:` namespace extensions

BPMN files exported from Camunda Cloud Modeler carry `<zeebe:...>` extensions for service-task bindings, form refs, etc. The converter ignores them (they don't affect layout), but if the user asks about preserving them, you'd need an explicit namespace handler. Not implemented in v1.

### `bpmn2drawio` Graphviz layout ignores collaboration structure (verified 2026-07-08)

**Symptom:** On a 7-pool Camunda collaboration diagram with message flows, both `--layout preserve` AND `--layout graphviz` produce a DrawIO where blocks visibly misalign. Tasks inside pools overlap each other, lanes collapse to default height, and message-flow arrows route through other pools.

**Cause:** `bpmn2drawio`'s Graphviz mode builds the layout graph from `sequenceFlow` edges only. It treats pools/lanes as `subgraph cluster_*` containers with **fixed coordinates from BPMN DI**, not as layout nodes — so the auto-layout positions tasks *without* resizing their parent pool to fit. Result: pools keep DI dimensions (which were designed for the source tool, not for the auto-laid-out children), and the children get squished inside.

**Fix paths (none perfect, pick by use case):**

1. **Use `--layout preserve`** — if the source BPMN already has DI coordinates (Camunda Modeler exports do), this keeps the source's hand-laid-out positions. Default to this. **Don't blindly switch to `--layout graphviz`** expecting better auto-layout — it's not better for collaboration diagrams with multiple pools.
2. **Use `templates/bpmn_to_drawio_di_preserve.py`** — the stdlib-only Python converter that reads BPMN DI coordinates directly and emits `<mxCell>` elements at exact source-tool positions, with BPMNEdge waypoints translated to `<mxPoint as="sourcePoint"/>` / `as="points"` / `as="targetPoint"/>` for orthogonal routing. Verified on a 7-pool Camunda file: positions match the source within ±0 px. **This is the right answer when source-fidelity matters.** See `references/bpmn-di-preserve-coords-converter.md` for the write-up.
3. **Manually adjust in DrawIO** — after import, drag pool boundaries to fit their contents. The original Camunda geometry is often close; a few minutes of drag-resize beats fighting the converter.
4. **Pre-process the BPMN** — strip pools/lanes, convert collaboration to a single-process `bpmn:process`, then `--layout graphviz`. Loses pool context but gives clean auto-layout. Only worth it for the very simplest diagrams.
5. **Use Mermaid instead** — `bpmn-to-mermaid` (and the `BPMN_форматы_01.txt` guide in this session) handles multi-pool diagrams with proper swimlane geometry via Mermaid's native `subgraph` blocks.

**Action when user reports "blocks misaligned after BPMN→DrawIO":** ask whether the BPMN is single-process or collaboration (multiple `bpmn:participant`). If collaboration + they want fidelity, jump straight to option 2 (`templates/bpmn_to_drawio_di_preserve.py`) — verified to produce 1:1 source-tool geometry without manual tweaking. If they want auto-layout (sacrificing fidelity), push back: explain that auto-layout in DrawIO is always manual tweaking for collaboration diagrams, regardless of converter. Save them an hour of "let me try a different converter" churn.

### `bpmn2drawio` emits unnamed artifact vertices (verified 2026-07-08)

**Symptom:** Output DrawIO contains dozens of `<mxCell>` vertices with empty `value=""` at suspicious positions:
- Coordinates `(32, 50)`, `(32, 120)`, `(32, 190)`, ..., `(32, 1170)` — left-margin column of 40×50 boxes
- Coordinates `(9, 11)`, `(15, 15)`, `(18, 14)` — tiny markers inside parent tasks
- Coordinates `(261, 1535)`, `(888, 875)`, `(701, 1685)`, `(1023, 1805)` — 50×50 boxes scattered mid-canvas

**Cause:** These are visual decorations that `bpmn2drawio` generates internally:
- The `(32, *)` boxes are **lane-header labels** (the vertical "АНАЛИТИК", "АРХИТЕКТОР" text on the left side of each lane in Camunda).
- The `(9, 11)` tiny markers are **task-type glyphs** (user-icon, gear-icon, etc.) that should render inside the parent task, but they're emitted with **relative coordinates and no `parent=` attribute**, so DrawIO renders them at the document root instead of inside the task.
- The mid-canvas 50×50 boxes are **gateway/event glyphs** that lost their label binding during the conversion.

**Practical impact:** Diagrams.net opens the file without error (no Duplicate ID), but the diagram looks "noisy" with extra boxes on the left margin and floating markers. Users will say "blocks misaligned" when really the blocks are fine — it's these artifacts that look broken.

**Workaround:** None from the converter side. Mitigation: open in DrawIO, delete the `(32, *)` lane-header column manually (they're decorative and the lane pool already has the name), and the floating markers will be cosmetic noise that doesn't block reading the diagram. **The DI-preserving converter (`templates/bpmn_to_drawio_di_preserve.py`) does not have this problem** — it only emits the source BPMN's actual elements, never internal decorations.

**Detection (run after every conversion):**

```python
import xml.etree.ElementTree as ET
import re
t = ET.parse('/root/diagram.drawio')
cells = re.findall(r'<mxCell id="(\d+)"[^>]*value="([^"]*)"[^>]*vertex="1"[^>]*>(.*?)</mxCell>',
                   ET.tostring(t.getroot(), encoding='unicode'))
artifacts = [(cid, geom) for cid, value, geom in cells if not value.strip()]
print(f'unnamed artifact vertices: {len(artifacts)}')
# Expected: 0 for DI-preserving converter, 5-50 for bpmn2drawio on collaboration diagrams
# > 50 = something went wrong in the conversion
```

### BPMN events render as rectangles, not circles, when sized 36x36 (verified 2026-07-08)

**Symptom:** Start events (green) and end events (red) appear as **small filled rectangles** in diagrams.net instead of circles. Tasks, gateways, and pools render correctly — only events are broken. The user sees "кружочки пропали, остались подписи" / "circles missing, only labels remain."

**Cause:** `shape=mxgraph.bpmn.event` in the DrawIO BPMN shape library renders an ellipse, but **at very small sizes (36×36 — typical for Camunda-exported events)** the shape's internal padding plus the label-text overflow make it collapse to a rectangle visually, and the label sits *inside* the cell where it overlaps the shape. The BPMN event shape also lacks `verticalLabelPosition` by default, so the label goes to the centre.

**Fix:** Use `shape=mxgraph.flowchart.terminator` instead. This shape is a generic ellipse/oval that renders correctly at any size, including 36×36. Verified on the 7-pool Camunda file: 14 events (7 start, 7 end) now render as proper circles.

```python
# Wrong — collapses to rectangle at 36x36:
STYLE_START = 'shape=mxgraph.bpmn.event;html=1;fillColor=#d5e8d4;strokeColor=#82b366;'

# Right — renders as a proper circle at any size:
STYLE_START = 'shape=mxgraph.flowchart.terminator;html=1;whiteSpace=wrap;fillColor=#d5e8d4;strokeColor=#82b366;'

# Also right — explicit BPMN event shape with full label-positioning control:
STYLE_START = 'shape=mxgraph.bpmn.event;html=1;verticalLabelPosition=bottom;verticalAlign=top;resizable=0;fillColor=#d5e8d4;strokeColor=#82b366;rounded=1;absoluteArcSize=1;arcSize=50;'
```

The last form (full BPMN-event style with `arcSize=50;verticalLabelPosition=bottom`) is what `bpmn2drawio` itself emits, and what renders correctly when the user wants the *actual* BPMN event glyph (not a generic oval). For maximum compatibility with diagram fidelity, use the full style. For maximum "circles always look right", use `flowchart.terminator`.

**Task-label fit:** Tasks have a similar label-overflow issue when the name is long. Add `verticalAlign=top;fontSize=10` to the task style — labels start at the top of the cell instead of vertically centred, which buys headroom for 2-3 lines of text without overflow.

### Association edges must use orthogonalEdgeStyle, not edgeStyle=none (verified 2026-07-08)

**Symptom:** After conversion, all the **dashed association arrows** between tasks and data objects / text annotations are invisible in diagrams.net — they just don't render. The user sees "пропали пунктирные стрелочки между элементами" / "dashed arrows between elements are missing." Sequence flows and message flows render fine.

**Cause:** `edgeStyle=none` produces straight lines. When the straight line from a task edge to a data-object edge passes through (or behind) a filled element on its way, diagrams.net can clip or hide the line, especially when both endpoints overlap with other shapes. Worse, `edgeStyle=none` does not respect `exitX`/`entryX` connection points — the line shoots straight from cell-centre to cell-centre, often through other elements.

**Fix:** Use `edgeStyle=orthogonalEdgeStyle` for association edges too, with high contrast and slightly thicker stroke. Verified on the 7-pool Camunda file: 8 associations all render as visible dashed orthogonal lines after this change.

```python
# Wrong — invisible / clipped / overlapping other elements:
STYLE_ASSOC = 'edgeStyle=none;html=1;dashed=1;endArrow=open;startArrow=none;'

# Right — orthogonal routing, visible, doesn't overlap:
STYLE_ASSOC = 'edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;dashed=1;endArrow=open;startArrow=none;strokeColor=#666666;strokeWidth=1.5;'
```

**Action when user reports "dashed lines missing":** Check the converter's `STYLE_ASSOC` constant. If it contains `edgeStyle=none`, change it to `edgeStyle=orthogonalEdgeStyle;strokeWidth=1.5;` before regenerating. This is a one-line fix that resolves 90% of "missing association arrows" reports.

### BPMN `dataInputAssociation` / `dataOutputAssociation` parsing gap (verified 2026-07-08)

**Symptom:** After conversion, the Camunda diagram is missing **dashed arrows between tasks and data objects** (`D10`, `D20`, `D30` and friends). The user sees "пунктирные ассоциации между задачами 50 и D30, D40, D25, D60 не видны" / "missing dashed links from task 50 to data objects."

**Cause:** Camunda-exported BPMN uses **three kinds of links**, not one:

| BPMN element | What it points from/to | Where parsed in the original template |
|---|---|---|
| `<bpmn:association>` | task ↔ text annotation | ✅ parsed |
| `<bpmn:messageFlow>` | pool ↔ pool (cross-pool signals) | ✅ parsed |
| `<bpmn:dataInputAssociation>` | task ↔ data object (input) | ❌ **silently dropped** |
| `<bpmn:dataOutputAssociation>` | task ↔ data object (output) | ❌ **silently dropped** |

`dataInputAssociation` / `dataOutputAssociation` are nested children of `<bpmn:task>`, not siblings of `<bpmn:association>`. Their `sourceRef` points to a `<bpmn:dataObjectReference>` (the visible data object on the diagram), and their `targetRef` points to a `Property_*` placeholder (`name="__targetRef_placeholder"` — Camunda's wire-format quirk). The visual association is `dataObject → parent_task` (or `parent_task → dataObject` for output).

**Verified failure (2026-07-08):** First v7 run on a 7-pool Camunda diagram produced only 40 edges (8 association, 5 message, 27 sequence). After adding dataInput/Output parsing the count went to 56 — the missing 16 edges were the dashed task↔data-object arrows the user had been asking for.

**Fix (already applied to `templates/bpmn_to_drawio_di_preserve.py` 2026-07-08):**

```python
# After parsing <bpmn:association>, add:
prop_to_ref = {}
for ref in self.root.iter('{' + NS_BPMN + '}dataObjectReference'):
    name = ref.get('name', '')
    if name.startswith('Property_'):
        prop_to_ref[name] = ref.get('id')

for tag_name in ('dataInputAssociation', 'dataOutputAssociation'):
    for assoc in self.root.iter('{' + NS_BPMN + '}' + tag_name):
        src_ref = tgt_ref = None
        for child in assoc:
            if child.tag.endswith('}sourceRef') and child.text:
                src_ref = child.text.strip()
            elif child.tag.endswith('}targetRef') and child.text:
                tgt_ref = child.text.strip()
        # Find parent task
        parent_id = None
        for parent in self.root.iter():
            for child in list(parent):
                if child is assoc:
                    parent_id = parent.get('id')
                    break
            if parent_id:
                break
        # Resolve Property_* placeholder to actual DataObjectReference
        if tgt_ref and tgt_ref.startswith('Property_'):
            tgt_ref = prop_to_ref.get(tgt_ref, tgt_ref)
        # Visual source/target decision
        if src_ref and src_ref.startswith('DataObjectReference_') and parent_id:
            self.assoc.append(('da_' + src_ref + '_' + parent_id, src_ref, parent_id))
        elif parent_id and tgt_ref:
            self.assoc.append(('da_' + parent_id + '_' + tgt_ref, parent_id, tgt_ref))
```

**Detection:** count `dataInputAssociation` + `dataOutputAssociation` in the source BPMN. If > 0 and your converter doesn't parse them, you'll lose that many arrows:

```bash
grep -cE "dataInputAssociation|dataOutputAssociation" /path/to/source.bpmn
```

Expected output from a complete conversion: number of association edges in the .drawio = number of `<bpmn:association>` in source + number of `dataInputAssociation` + number of `dataOutputAssociation`.

### `verticalLabelPosition=bottom` collapses 36x36 event circles (verified 2026-07-08)

**Symptom:** Events that were rendering as circles disappear (or shrink to invisible dots). The user sees "кружочки опять пропали" / "circles vanished again" — and they're right to be frustrated because the previous run *did* show circles.

**Cause:** The full BPMN-event style that `bpmn2drawio` emits includes `verticalLabelPosition=bottom;verticalAlign=top;...;arcSize=50;`. At the standard Camunda event size of **36×36 px**, this combination of properties is a trap: `verticalLabelPosition=bottom` reserves the bottom half of the bbox for the label, `verticalAlign=top` pins the shape to the top half, and the circle collapses into a ~18×18 region that is then visually dominated by the long Russian label rendered inside it. From the user's perspective the circle is gone — only the label remains, and it looks like a floating text node.

**Fix:** for elements **smaller than ~60×60 px**, **do not add `verticalLabelPosition=bottom` or `verticalAlign=top`**. Use plain `shape=mxgraph.flowchart.terminator;...;` and let the label sit inside the circle (overflow is acceptable for Camunda-style events; the long name is part of the source-tool output):

```python
# Wrong - collapses 36x36 circles:
STYLE_START = 'shape=mxgraph.bpmn.event;html=1;verticalLabelPosition=bottom;verticalAlign=top;resizable=0;fillColor=#d5e8d4;strokeColor=#82b366;rounded=1;arcSize=50;'

# Right - works at any size:
STYLE_START = 'shape=mxgraph.flowchart.terminator;html=1;whiteSpace=wrap;fillColor=#d5e8d4;strokeColor=#82b366;strokeWidth=2;'
```

**When `verticalLabelPosition=bottom` IS the right choice:** for **large events** (~80×80 or bigger), where the label has room to live below the circle without crowding. In BPMN, intermediate and end events are often large; start events are usually small.

**Recovery path:** if the user says "кружочки пропали / circles disappeared," check `STYLE_START` / `STYLE_END` / `STYLE_IEVENT`. If they contain `verticalLabelPosition=bottom` AND the source has 36×36 events, that's the trap. Strip the vertical-positioning directives; do NOT add bigger fonts as a workaround — that just makes the overflow worse.

### Don't install Graphviz for BPMN → DrawIO conversion (verified 2026-07-08)

**Symptom:** You `apt install graphviz libgraphviz-dev` + `pip install pygraphviz` to enable `bpmn2drawio --layout graphviz`, hoping auto-layout will fix a poorly-positioned output. The auto-laid-out output is **worse** than the original — pools misalign, tasks collapse to a column on the right side, lanes lose their proportional heights.

**Cause:** Graphviz sees a *flat graph* — it doesn't understand BPMN pool/lane containment. When `bpmn2drawio --layout graphviz` lays out the flow nodes, it positions them based on sequence-flow edges only, then places pools around them with their original DI dimensions (which were sized for the *source tool's* layout, not Graphviz's). Result: pools are too small to contain their auto-laid-out children.

**Don't do this:**

```bash
sudo apt-get install -y graphviz libgraphviz-dev
pip install pygraphviz
PYTHONPATH=src python3 -m bpmn2drawio input.bpmn output.drawio --layout graphviz
```

The output looks like this (verified on a 7-pool Camunda diagram):
- Pools: 7 thin rectangles stacked vertically on the **left edge** of the page.
- Tasks: all 11 gathered in a **single vertical column** on the right edge.
- Almost no overlap, but the layout is now wrong in a different way — the visual hierarchy from the source (which pool contains which task) is destroyed.

**Do this instead:**

```bash
# Use --layout preserve to keep Camunda's hand-laid-out positions
PYTHONPATH=src python3 -m bpmn2drawio input.bpmn output.drawio --layout preserve

# OR — drop bpmn2drawio entirely and use the DI-preserving converter:
python3 templates/bpmn_to_drawio_di_preserve.py input.bpmn output.drawio
```

The DI-preserving path reads BPMN DI coordinates directly and never invokes Graphviz. Layout matches the source 1:1. Verified on the same 7-pool file.

**Action when a user reports "blocks misaligned" after `bpmn2drawio`:** do NOT reach for Graphviz as a fix. The DI-preserving converter is the answer; it's the same path the skill recommends for collaboration diagrams.

### Cyrillic labels — preserved correctly via UTF-8

Verified: `Сотрудники, имеющие право фиксировать требования` and `АНАЛИТИК` come through verbatim into the `.drawio` and render correctly in diagrams.net. No transliteration, no encoding bugs. The Pitfall is reading the source as UTF-8 explicitly (`open(path, encoding='utf-8')`) — the default Python locale may pick up cp1251 on Windows hosts.

### Diagrams.net online editor quirk

After `sendDocument` delivers the file, opening it via https://app.diagrams.net/ → File → Open from Device works. Opening via URL import sometimes fails if the file has unusual XML namespace declarations. Local upload is reliable.

## Verification Checklist

- [ ] Source BPMN parsed without errors (check `xml.etree.ElementTree.ParseError`).
- [ ] All user mxCell IDs are unique AND ≥ 2 (root 0/1 reserved).
- [ ] Pools have meaningful height (≥ 200, not task default 80).
- [ ] Task marker styles match BPMN type (service/user/businessRule/script/...).
- [ ] Sequence flows are solid arrows; message flows are dashed.
- [ ] Labels with special chars (`<`, `>`, `&`, `'`) are XML-escaped.
- [ ] Cyrillic preserved (verify a Russian label).
- [ ] Output opens in diagrams.net without error.
- [ ] Visual fidelity: positions match source BPMN within ±5 px (or ±0 px if using the DI-preserving converter).
- [ ] Unnamed artifact vertices ≤ 50 (see `bpmn2drawio emits unnamed artifact vertices` pitfall). With the DI-preserving converter this should be 0.
- [ ] For collaboration diagrams: pools visibly contain their lanes; message flows cross pool boundaries.
- [ ] **Events render as circles, not rectangles** — start events green, end events red. If they're rectangles, see "BPMN events render as rectangles" pitfall.
- [ ] **Association arrows are visible** — dashed lines from tasks to data objects / text annotations. If they're missing, see "Association edges must use orthogonalEdgeStyle" pitfall.
- [ ] **DataInputAssociation / DataOutputAssociation arrows are visible** — dashed lines from tasks to data objects (`D10`, `D20`, `D30`...). If missing, see "BPMN dataInputAssociation / dataOutputAssociation parsing gap" pitfall. Quick check: `grep -cE "dataInputAssociation|dataOutputAssociation" source.bpmn` — if > 0, your converter must parse these.

## Files in This Skill

- `scripts/bpmn_to_drawio.py` — the verified stdlib-only converter (~13 KB). Use as a no-dependency fallback when `pip install` is unavailable.
- `scripts/verify_drawio.py` — post-conversion validator. Catches duplicate IDs, root-id collisions, and the unnamed-vertex artifact pattern from `bpmn2drawio`. Run this on every output before declaring the conversion done:
  ```bash
  python3 scripts/verify_drawio.py /root/diagram_<name>.drawio
  # Exit 0 = clean. Exit 1 = FAIL-class problem (duplicate IDs or > 50 artifacts).
  ```
- `templates/bpmn_to_drawio_di_preserve.py` — **the right fallback** when `bpmn2drawio` breaks on collaboration diagrams (multiple pools + message flows). Uses BPMN DI coordinates + BPMNEdge waypoints directly (no Graphviz), so the output geometry matches the source BPMN 1:1. Verified on a 7-pool Camunda collaboration diagram (105 cells, 0 duplicates, opens cleanly). See `references/bpmn-di-preserve-coords-converter.md` for the write-up.
- `references/bpmn-to-drawio-skill.md` — install + run recipe for the canonical `davistroy/bpmn2drawio` community skill (24 .py modules, 260 KB, 4 themes, optional Graphviz auto-layout, `--layout preserve` to keep Camunda DI coordinates). **Use this first** when you need a polished conversion.
- `references/bpmn-di-preserve-coords-converter.md` — write-up of the DI-preserving custom converter (`templates/bpmn_to_drawio_di_preserve.py`): when to use it instead of `bpmn2drawio`, how BPMNEdge waypoints become `<mxPoint as="sourcePoint"/>` etc., the BPMN DI namespace triple, and verified output for a 7-pool Camunda file.
- `references/bpmn-namespace-map.md` — full BPMN 2.0 namespace reference with examples.
- `references/mxgraph-style-catalog.md` — mxGraph BPMN shape library style reference (every supported BPMN glyph).

The user-facing conversational gpt-response in Telegram must mention "files in this skill" so the user knows where to look.