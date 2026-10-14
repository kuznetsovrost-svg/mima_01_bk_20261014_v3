---
name: idef0-excalidraw-methodology
description: "Author and analyze IDEF0 functional diagrams in Excalidraw JSON — multi-level A-0/A0/A1 hierarchy via named Frames, ICOM arrow conventions (Inputs/Controls/Outputs/Mechanisms on block sides), canonical block layout (function name + numbered label as a group), tunneling notation (round brackets around binding point), and arrow catalogues. Use when the user says 'IDEF0', 'функциональная модель', 'A-0 / A0 / A1 диаграмма', 'ICOM стрелки', 'туннелирование в IDEF0', 'node tree description', or asks to draw/analyze hierarchical function decomposition with named inputs/outputs/controls/mechanisms. Covers FIPS 183 conventions, ICOM consistency check between parent and child frames, block group structure (rectangle + 2 texts + groupIds), and the standard node description template. NOT for IDEF3 (workflow/sequence — use BPMN), NOT for DFD (data flow — use data-flow-diagram), NOT for generic flowcharts without ICOM semantics (use plain excalidraw)."
version: 0.1.0
author: Hermes Agent
license: MIT
dependencies: []
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [IDEF0, Excalidraw, ICOM, Functional-Modeling, FIPS-183, Frame, Hierarchy, Diagram]
    category: creative
    related_skills: [diagram-format-conversion, vscode-integration]

---

# IDEF0 in Excalidraw — class-level methodology skill

Draw and analyze IDEF0 functional diagrams using Excalidraw JSON.
IDEF0 = Integration DEFinition for Function Modeling, FIPS 183.
Core notation: rectangles are Functions, arrows are ICOM objects
(Inputs/Controls/Outputs/Mechanisms) on the four sides of each block.

This skill owns the conventions for translating IDEF0 into
Excalidraw elements. The base `creative/excalidraw` skill
(bundled) covers raw element types — this skill adds
the IDEF0-specific patterns on top.

## When to use

Use this skill when the user:

- Draws an IDEF0 diagram and asks how to lay it out
- Asks to analyze an existing IDEF0 in Excalidraw
- Says "A-0", "A0", "A1", "ICOM", "функциональная модель",
  "IDEF0", "node tree", "FIPS 183"
- Mentions arrow catalogue, tunneling, or block numbering
- Wants parent↔child consistency check across diagram levels

Do NOT use for:

- IDEF3 (workflow/sequence) — use BPMN skill
- DFD (data flow) — different notation, use data-flow-diagram
- Plain flowcharts without ICOM semantics — use bundled excalidraw

## Core conventions (read these before drawing)

### 1. One Frame per diagram level

Each IDEF0 diagram (A-0, A0, A1, A2, ...) lives in its own
Frame element. Name the Frame with the level code so the agent
can extract hierarchy directly from `name`:

```json
{
  "type": "frame",
  "id": "frame-A0",
  "name": "A0 Производство (parent: A-0)",
  "x": 100, "y": 100,
  "width": 800, "height": 600
}
```

Naming convention: `"<code> <description> (parent: <parent-code>)"`.
The `(parent: X)` segment is what the agent parses to reconstruct
the hierarchy. Parent-level diagrams (A-0, A0) name themselves
without `parent:` or with their own parent. Child blocks inside
the Frame link back via `(parent: A0-2)` — the block number
from the parent diagram.

### 2. Block structure: rectangle + 2 texts, grouped

Each IDEF0 block is a Group of three elements:
- Rectangle (the function box)
- Center text (function name, e.g. "Разработка чертежей")
- Bottom-left text (block number, e.g. "A1.2")

All three share the same `groupIds` array:

```json
{
  "elements": [
    {"type": "rectangle", "id": "block-A1-2", "x": 100, "y": 100,
     "width": 200, "height": 100, "groupIds": ["group-A1-2"]},
    {"type": "text", "id": "func-A1-2", "x": 120, "y": 140,
     "text": "Разработка чертежей", "textAlign": "center",
     "fontSize": 18, "groupIds": ["group-A1-2"]},
    {"type": "text", "id": "num-A1-2", "x": 105, "y": 178,
     "text": "A1.2", "textAlign": "left",
     "fontSize": 12, "groupIds": ["group-A1-2"]}
  ]
}
```

ID conventions:
- `block-<code>` for rectangle
- `func-<code>` for name text
- `num-<code>` for number text
- `group-<code>` for the shared groupIds value

The agent finds a block's name by looking at the same `groupIds`
as its rectangle. Use `groupIds` (array), not `groupId`, because
Excalidraw supports multi-group membership — useful when the
same object needs to belong to both a topic and a stage group.

### 3. ICOM arrows on the four sides

Each arrow attaches to one of four sides of a block. Side is
detected from the coordinates of the arrow's bound endpoint
versus the rectangle's bounding box:

| Side | Detection |
|------|-----------|
| Top (Control) | `abs(end_y - block.y)` minimal |
| Right (Output) | `abs(end_x - (block.x + block.width))` minimal |
| Bottom (Mechanism) | `abs(end_y - (block.y + block.height))` minimal |
| Left (Input) | `abs(end_x - block.x)` minimal |

Arrow text (the ICOM code / object name) lives in the arrow's
own `text` field or in a `boundElements` text child.

### 4. Arrow Catalogue (FIPS 183 mandatory)

Every diagram must carry an Arrow Catalogue — a table of all
arrows with name, source, destination, ICOM type. Implement
as a child Frame inside the diagram Frame:

```json
{"type": "frame", "id": "cat-A2", "name": "Arrow Catalogue A2",
 "frameId": "frame-A2"}
```

Inside: rectangle as table background + text rows for each
arrow. Rows: `Имя стрелки | Источник | Получатель | Тип (I/C/O/M)`.
Use the literal string `"Граница"` for arrows that touch the
diagram's outer edge.

The agent can validate: every arrow on the diagram appears in
the catalogue, every catalogue entry corresponds to a real
arrow, sources/destinations either name a real block or are
`"Граница"`.

### 5. Tunneling notation

When an ICOM arrow should pass through every block of a child
diagram without being decomposed, mark it as tunneled:

- Canonical visual mark: a pair of round brackets `( )`
  surrounding the arrow's binding point on the block side
- Encode in JSON: include `( ` and/or ` )` around the arrow
  name in the arrow's `text` field

```json
{"type": "arrow", "id": "arrow-I1-tunnel",
 "text": "( I1 входной документ )",
 "startBinding": {"elementId": "frame-A1", "fixedPoint": [0, 0.5]},
 "endBinding": {"elementId": "block-A1-2", "fixedPoint": [0, 0.5]}}
```

Tunneled arrows in the parent diagram must appear as
boundary-touching free ends on the child diagram's Frame —
they do NOT enter any specific block of the child. The ICOM
consistency check treats them differently from regular
arrows (see next section).

### 6. No cross-page arrows

FIPS 183 does NOT allow arrows to cross between diagrams. Each
diagram is closed. Parent↔child linking is by:
- Block numbering (`A0-2` in parent = `A1` is its decomposition)
- ICOM codes on the boundary of the child Frame (text labels
  on the four sides of the child Frame listing the codes I1,
  C1, O1, M1 etc.)

If you see an arrow that appears to span two Frames in an IDEF0
diagram, it is a violation — flag it during analysis.

## ICOM consistency check

The agent can verify parent↔child decomposition by extracting
ICOM on both sides and comparing sets.

### Extract parent ICOM from a block

For every arrow bound to the block, classify by which side of
the block it touches. Collect names into:

```python
parent_icom = {
    "input": [],     # arrows on the LEFT side of the block
    "control": [],   # arrows on the TOP side
    "output": [],    # arrows on the RIGHT side
    "mechanism": []  # arrows on the BOTTOM side
}
```

### Extract child ICOM from a diagram Frame

For every arrow whose free end (the end without a
`startBinding` or `endBinding`) lies on the edge of the child
Frame, classify by which edge:

| Free end edge | ICOM role |
|---------------|-----------|
| Left edge of child Frame | Input of child |
| Top edge of child Frame | Control of child |
| Right edge of child Frame | Output of child |
| Bottom edge of child Frame | Mechanism of child |

### Compare and report

For each role, `set(parent_icom[role])` must equal
`set(child_icom[role])`. If not:
- `missing_in_child` = names in parent but not child → lost
  during decomposition
- `extra_in_child` = names in child but not parent → invented
  by mistake

Tunneled arrows are tracked separately: a tunneled arrow from
the parent must appear as a boundary arrow on the same side of
the child Frame (it doesn't enter any child block).

## Node description (FIPS 183 mandatory)

Every IDEF0 diagram must carry a natural-language description
following a standard template. Walk blocks in order (smallest
block number first, ties broken by top-left position). For each
block, walk its four sides in clockwise order starting from
the top:

```
Блок {N}. {Имя блока}.
На основании {Controls — top, sorted left-to-right},
получает {Inputs — left, sorted top-to-bottom},
выдаёт {Outputs — right, sorted top-to-bottom},
опираясь на {Mechanisms — bottom, sorted left-to-right}.
```

The agent can generate this description automatically given
the arrow catalogue and block groups. The output is one
paragraph per block; sections separated by blank lines.

Empty sides are noted as such ("получает ничего", "выдаёт
ничего") or omitted — pick one convention and stay consistent.

## Workflow when the user asks for an IDEF0 diagram

1. Confirm the level — A-0 (context), A0, A1, A2, ..., or
   custom.
2. List the blocks the user wants at this level. Get names and
   numbers.
3. For each block, list its ICOM: what controls it, what
   inputs it takes, what outputs it produces, what mechanisms
   it uses. Decide which arrows are tunneled.
4. Emit the JSON: one Frame per diagram level, blocks as
   groups of 3 elements, arrows bound to block sides, arrow
   text = ICOM code, arrow catalogue as a child Frame.
5. Verify: each block has exactly one rectangle, one name
   text, one number text, all sharing one groupIds value. Each
   arrow is bound to exactly one block or one Frame boundary.
6. Optionally run the ICOM consistency check against the
   parent diagram.

## Pitfalls / failure modes

- **`label` field on shapes is silently ignored** — labels
  require `boundElements` + a separate text element with
  `containerId`. This is from the base excalidraw skill but is
  especially easy to slip on IDEF0 blocks where you want a
  block label.
- **`groupId` (singular) is not a real Excalidraw field** — the
  field is `groupIds` (array). Use `["group-X"]`, not `"group-X"`.
- **One object can only be in one Frame** — code the parent
  relationship in the Frame `name`, not in the element's
  `frameId`. An object can be in many groups but only one Frame.
- **Arrow text vs label** — text inside `points[0]` or near the
  start of the arrow is shown inline; a separate text element
  bound to the arrow is shown above it. For ICOM codes prefer
  the arrow's own `text` field (compact).
- **Coordinates of arrows inside a Frame** — `arrow.x` and
  `arrow.y` are still absolute, not relative to the Frame. The
  ICOM boundary detection must use the child Frame's absolute
  bounding box.
- **FIPS 183 vs IDEF0+** — extensions exist (especially in
  Russian practice) that add cross-page arrows for feedback.
  The classic FIPS 183 forbids them; ask the user which
  dialect they follow before validating.

## Output checklist

When you finish an IDEF0 diagram, verify before delivery:

- [ ] Every diagram level has its own Frame with a clear name
- [ ] Every block is a group of exactly 3 elements sharing one
      groupIds value
- [ ] Every arrow is bound to exactly one block side or
      exactly one Frame edge
- [ ] Tunneled arrows are marked with `( )` in their text
- [ ] Arrow Catalogue Frame is present inside each diagram
      Frame
- [ ] ICOM codes on Frame boundary match parent's ICOM for the
      corresponding block
- [ ] No arrow spans two different Frames

## Related skills and references

- `references/idef0-conventions.md` — detailed ICOM codes,
  arrow catalogue schema, node description examples
- `references/IDEF0-in-Excalidraw-playbook-01.md` — full
  playbook with workflow examples, ICOM consistency recipes,
  node description templates, and skill architecture notes
- Bundled `creative/excalidraw` — base element format
- `software-development/diagram-format-conversion` — convert
  IDEF0 ↔ BPMN / Mermaid if needed

## CLI quick reference

The `scripts/` directory ships three reusable entry points.

### `validator.py` (top-level CLI)

```bash
python3 scripts/validator.py summary   <file.excalidraw>
python3 scripts/validator.py validate  <file.excalidraw>
python3 scripts/validator.py tunnels   <file.excalidraw>
python3 scripts/validator.py icom      <file.excalidraw> \
        --parent-block <block-id> --child-frame <frame-id>
python3 scripts/validator.py catalogue <file.excalidraw> [--frame-id <id>]
python3 scripts/validator.py description <file.excalidraw>
```

### `icom_consistency_check.py` (deep consistency)

Returns non-zero exit code (2) on consistency errors and prints
a per-role diff plus severity-tagged discrepancies. Use this
when you need a machine-readable verdict; use `validator.py icom`
when you only want the two ICOM dicts side-by-side.

### `tunnel_detector.py`

Lists every arrow whose `text` starts with `(` or ends with `)`,
reports `tunnel_side = start | end | both`, and prints a one-line
explanation per tunnel. Add `--json` for CI consumption.