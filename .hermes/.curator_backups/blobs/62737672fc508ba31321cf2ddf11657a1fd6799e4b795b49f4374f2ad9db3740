# BPMN → DrawIO via DI-preserving custom converter (verified 2026-07-08)

This is the **fallback when `bpmn2drawio` (the community skill)
breaks on collaboration diagrams** — even with `--layout preserve`
or `--layout graphviz`, the auto-layout still misaligns pools, lanes,
and tasks on Camunda collaboration diagrams with multiple pools and
message flows. Verified on a 7-pool Camunda file: this converter
produces a DrawIO where every element sits at its original
source-tool coordinates, with orthogonal routing on every edge
that matches the BPMN DI waypoints exactly.

## When to use this instead of `bpmn2drawio`

Use this when:

- The source BPMN is a **collaboration diagram** (multiple
  `<bpmn:participant>` pools, `<bpmn:messageFlow>` between them).
- The user says "blocks misaligned" or "edges don't connect
  properly" after a `bpmn2drawio` run.
- The user explicitly wants the source geometry preserved
  (not re-laid-out) — e.g. they're cross-checking with another
  viewer like bpmn.io.
- pip is unavailable and you can't `pip install lxml networkx
  pyyaml` for the community skill. This converter uses
  `xml.etree.ElementTree` (stdlib only).

Don't use this when:

- The source BPMN has **no BPMN DI section** (no coordinates).
  In that case `bpmn2drawio --layout graphviz` is the right tool,
  because we need Graphviz to invent positions that don't exist.
- The user wants a themed/colored output. `bpmn2drawio` themes
  (`default / blueprint / monochrome / high_contrast`) are more
  polished than the raw `mxgraph.bpmn.*` style strings this
  converter emits.

## The technique

Three structural decisions that make the output faithful:

### 1. Coordinates come from BPMN DI, not from Graphviz

`bpmndi:BPMNShape/bpmndi:BPMNBounds/dc:Bounds` carries the
`x`/`y`/`width`/`height` of every element — pools, lanes, tasks,
events, gateways, data objects, text annotations. Parse them all
and use them as-is for the `<mxGeometry x="..." y="..." width="..." height="..." />` of the corresponding `mxCell`.

`bpmn2drawio --layout graphviz` ignores these (rebuilds from
edges). `bpmn2drawio --layout preserve` does use them, but
the surrounding pool/lane containers are repositioned to fit,
which is what causes the "blocks misaligned" complaint.

### 2. Edge routing comes from BPMNEdge waypoints

A `<bpmndi:BPMNEdge>` has a sequence of `<di:waypoint x=".."
y=".." />` children — the literal routing points the source tool
drew. Render them as `<mxPoint as="sourcePoint"/>` /
`as="targetPoint"` and intermediate `<mxPoint as="points"/>`
inside an `<mxGeometry relative="1">` block on the edge
`<mxCell>`:

```xml
<mxCell id="..." style="edgeStyle=orthogonalEdgeStyle;..."
        edge="1" parent="1" source="..." target="...">
  <mxGeometry relative="1" as="geometry">
    <mxPoint x="290" y="270" as="sourcePoint" />
    <mxPoint x="488" y="270" as="targetPoint" />
    <mxPoint x="488" y="310" as="points" />
  </mxGeometry>
</mxCell>
```

This is the bit that gives true orthogonal routing. Without
it, the edge takes a straight line between source and target,
ignoring the BPMN source tool's bends.

### 3. mxCell id counter starts at 2

`mxGraphModel` always reserves `id="0"` (document root) and
`id="1"` (first-level container with `parent="0"`). User
elements start at `id="2"`. A converter that starts at `1`
produces `Duplicate ID '1'` and diagrams.net refuses to open
the file. (See the main SKILL.md "DrawIO mxCell id reservation"
pitfall — same lesson, this converter respects it.)

## The script

The verified converter is ~9.7 KB of stdlib-only Python. Drop-in
replacement for `bpmn2drawio` when the latter breaks:

```python
# /root/bpmn_to_drawio_v2.py
# (See templates/bpmn_to_drawio_di_preserve.py for the full file.)
# Usage:
#   python3 /root/bpmn_to_drawio_v2.py input.bpmn output.drawio
```

What it does, top to bottom:

- Parses BPMN DI `<BPMNShape>` for `x/y/width/height`.
- Parses BPMN DI `<BPMNEdge>` for waypoints.
- Iterates `<bpmn:participant>` for pools.
- Iterates the union of `<bpmn:task>`, `<bpmn:userTask>`,
  `<bpmn:serviceTask>`, etc. for flow nodes; classifies each
  by type → maps to the right `mxgraph.bpmn.*` style.
- Iterates `<bpmn:dataObjectReference>`, `<bpmn:dataStoreReference>`,
  `<bpmn:textAnnotation>` for artifacts (notes).
- Iterates `<bpmn:sequenceFlow>`, `<bpmn:messageFlow>`,
  `<bpmn:association>` for edges.
- Emits `<mxCell>` for each, with `vertex="1"` for boxes /
  `edge="1"` for flows, and `parent="1"` for all of them
  (top-level — pools do NOT contain their children in this
  converter, which is the right call when absolute coords are
  already correct).
- mxCell id counter starts at 2 (root 0/1 reserved).

## Verified output on a 7-pool Camunda collaboration

```
input.bpmn       →  64 KB
output.drawio    →  38 KB (105 cells: 63 vertices, 40 edges, 0 duplicates)
```

Coordinates of selected elements (verified against the source
BPMN, ±0 px):

| Element                     | BPMN DI      | DrawIO mxGeometry |
|-----------------------------|--------------|-------------------|
| Pool «Сотрудники, …»        | x=132 y=50   | x=132 y=50        |
| Task «10. Фиксация новых…»  | x=292 y=190  | x=292 y=190       |
| Task «20. Анализ и…»        | x=290 y=489  | x=290 y=489       |
| Task «30. КОМ.ДИР: …»       | x=973 y=820  | x=973 y=820       |

The user opens the output in https://app.diagrams.net/ via
File → Open from Device and the layout matches the source
1:1 — same as what Camunda Modeler showed.

## When this still falls short

- **No DI in source**: Graphviz is still required for invented
  positions. The converter just emits every element at (0, 0)
  with default 120×80 if its DI bounds are missing — useless.
- **Lane geometry inside pools**: this converter emits pools
  as plain boxes; lanes inside them are NOT separate `mxCell`s
  but visually appear as inner borders drawn by DrawIO's
  `mxgraph.bpmn.pool` style. If the user needs to edit
  individual lanes (e.g. to add a task into one lane), they
  have to manually split the pool into a pool + N lane
  `mxCell`s. `bpmn2drawio` does this correctly; this
  converter trades that for coordinate fidelity.
- **Cycle of fixes**: if the user re-saves the output in
  DrawIO and then re-exports to BPMN, the new BPMN's DI may
  differ from the original (DrawIO uses different grid
  snapping). Treat the conversion as one-shot, not iterative.

## Style mapping (mirrors main SKILL.md table)

| BPMN element              | DrawIO style |
|---------------------------|--------------|
| `bpmn:task`               | `shape=mxgraph.bpmn.task;taskMarker=abstract;fillColor=#dae8fc;` |
| `bpmn:userTask`           | `shape=mxgraph.bpmn.task;taskMarker=user;` |
| `bpmn:serviceTask`        | `shape=mxgraph.bpmn.task;taskMarker=service;fillColor=#d5e8d4;` |
| `bpmn:startEvent`         | `shape=mxgraph.bpmn.event;fillColor=#d5e8d4;` |
| `bpmn:endEvent`           | `shape=mxgraph.bpmn.event;fillColor=#f8cecc;` |
| `bpmn:intermediateThrowEvent` | `shape=mxgraph.bpmn.event;fillColor=#dae8fc;` |
| `bpmn:exclusiveGateway`   | `shape=mxgraph.bpmn.gateway2;fillColor=#fff2cc;` |
| `bpmn:parallelGateway`    | `shape=mxgraph.bpmn.gateway_plus;fillColor=#fff2cc;` |
| `bpmn:inclusiveGateway`   | `shape=mxgraph.bpmn.gateway_or;fillColor=#fff2cc;` |
| `bpmn:eventBasedGateway`  | `shape=mxgraph.bpmn.gateway_event;` |
| `bpmn:participant` (pool) | `shape=mxgraph.bpmn.pool;fillColor=#ffffff;` |
| `bpmn:dataObjectReference`| `shape=note;background=#ffe6cc;` |
| `bpmn:textAnnotation`     | `shape=note;background=#ffffcc;` |

## Edge styles (same as main SKILL.md)

| BPMN edge            | DrawIO style |
|----------------------|--------------|
| `bpmn:sequenceFlow`  | `edgeStyle=orthogonalEdgeStyle;endArrow=classic;` |
| `bpmn:messageFlow`   | `edgeStyle=orthogonalEdgeStyle;dashed=1;startArrow=oval;endArrow=open;startFill=0;` |
| `bpmn:association`   | `edgeStyle=none;dashed=1;endArrow=open;` |

## Pre-flight verification (run before declaring done)

```python
import xml.etree.ElementTree as ET
import re

t = ET.parse('/root/diagram.drawio')
cells = t.findall('.//mxCell')
ids = [c.get('id') for c in cells]
dupes = [x for x in set(ids) if ids.count(x) > 1]
assert not dupes, f'Duplicate IDs: {dupes}'
assert '0' in ids and '1' in ids, 'Root cells 0 and 1 missing'
user_ids = [i for i in ids if int(i) >= 2]
assert len(user_ids) == len(set(user_ids)), 'Duplicate user-cell IDs'
print(f'OK: {len(cells)} cells, {len([c for c in cells if c.get("vertex")=="1"])} vertices, {len([c for c in cells if c.get("edge")=="1"])} edges')
```

Then open in https://app.diagrams.net/ via File → Open from Device
and visually confirm the layout matches the source BPMN.

## See also

- `templates/bpmn_to_drawio_di_preserve.py` — the full, runnable converter (~9.7 KB, stdlib-only).
- `references/bpmn-to-drawio-skill.md` — the community `bpmn2drawio` skill (the right tool when DI coordinates don't exist).
- The main SKILL.md pitfall "bpmn2drawio Graphviz layout ignores collaboration structure" — for the problem this converter solves.