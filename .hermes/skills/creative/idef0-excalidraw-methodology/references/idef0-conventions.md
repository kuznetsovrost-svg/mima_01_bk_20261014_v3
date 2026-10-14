# IDEF0 conventions reference

Detailed ICOM notation, catalogue schema, node description
template, and verification recipes. Companion to
`SKILL.md` of `idef0-excalidraw-methodology`.

---

## 1. ICOM codes on diagram boundaries

Each child diagram Frame carries ICOM codes as text labels
positioned on its four outer edges. Convention:

| Frame edge | ICOM role | Sample labels |
|------------|-----------|---------------|
| Left       | Inputs    | "I1", "I2", "I3" |
| Top        | Controls  | "C1", "C2" |
| Right      | Outputs   | "O1", "O2" |
| Bottom     | Mechanisms | "M1", "M2", "M3", "M4" |

Place each label as a text element with no `frameId` (it sits
on the Frame's edge but is not contained by the Frame, so the
agent can read it without filtering by frameId).

```json
{"type": "text", "id": "icom-label-I1",
 "x": 105, "y": 300, "text": "I1", "fontSize": 12}
```

Use the `( X)` parent annotation in the child Frame name to
declare which parent block this Frame decomposes:

```json
{"type": "frame", "id": "frame-A2",
 "name": "A2 Проверка заявки (parent: A0-2)",
 "x": 100, "y": 100, "width": 800, "height": 600}
```

## 2. Arrow catalogue schema

Recommended JSON shape for the catalogue inside the
"Arrow Catalogue" Frame:

```json
{
  "frame": "frame-A2",
  "arrows": [
    {
      "id": "arrow-I1",
      "name": "Заявка клиента",
      "from": "Граница",
      "to": "block-A2-1",
      "type": "I",
      "tunneled": false
    },
    {
      "id": "arrow-C1",
      "name": "Правила работы",
      "from": "Граница",
      "to": "block-A2-1",
      "type": "C",
      "tunneled": false
    },
    {
      "id": "arrow-arrow-O1",
      "name": "Заявка проверенная",
      "from": "block-A2-1",
      "to": "block-A2-2",
      "type": "—",
      "tunneled": false
    },
    {
      "id": "arrow-M1",
      "name": "Менеджер",
      "from": "Граница",
      "to": "block-A2-1",
      "type": "M",
      "tunneled": false
    }
  ]
}
```

The "Граница" literal is the canonical marker for arrows that
touch the outer edge of the diagram Frame. The agent must match
"Граница" to actual arrows whose free end lies on the Frame
edge — never invent catalogue entries that have no arrow.

## 3. Tunneling conventions

### Visual

The IDEF0 visual mark for a tunnel is a pair of round brackets
`( )` drawn around the arrow's binding point on the block.
Either side may be tunneled:

```
Без туннеля:                 С туннелем:
  ┌──────────┐                 ┌──────────┐
  │   A2     │                 │   A2     │
  └──────────┘                 └──────────┘
       ↑                            ↑
       │                            │
     (I1)                         (I1)
                              ┌ ( ┘   ┘ )
                              │( туннель)
```

### Encoding in Excalidraw

When you cannot draw the brackets visually, encode the tunnel
in the arrow's `text` field:

| Format in `text` | Meaning |
|------------------|---------|
| `"I1 ..."` | regular arrow |
| `"( I1 ..."` | arrow tunneled at the block end (the end that touches the block) |
| `"I1 ... )"` | arrow tunneled at the free end (outside the block) |
| `"( I1 ... )"` | both ends tunneled (external coupling) |

`(` and `)` at the start or end of the text field are the
markers. Brackets in the middle of the text (e.g. `"функция
(А)"`) are part of the object name, not tunnel markers.

### What a tunneled arrow looks like in the child diagram

Tunneled arrows do NOT enter any specific block of the child
diagram. They appear as boundary arrows on the same side of the
child Frame as they appeared on the parent block:

- Parent block A2 has a tunneled `I1` on its left
- Child Frame A2 (decomposing A2) must have a `I1` arrow whose
  free end touches its left edge

The child catalogue must list the tunneled arrow with
`"from": "Граница"` (or `"to": "Граница"`) — not naming any
specific block.

## 4. ICOM consistency check (recipe)

Use this pseudocode to validate parent↔child ICOM.

### Step 1: extract parent ICOM from the parent block

```python
def extract_parent_icom(parent_block_id, all_arrows):
    icom = {"input": [], "control": [],
            "output": [], "mechanism": []}
    for arrow in all_arrows:
        if not arrow.binds_to(parent_block_id):
            continue
        side = arrow.attached_side(parent_block_id)  # top/right/bottom/left
        role = {"top": "control",
                "right": "output",
                "bottom": "mechanism",
                "left": "input"}[side]
        icom[role].append(arrow.name)
    return icom
```

### Step 2: extract child ICOM from the child diagram Frame

```python
def extract_child_icom(child_frame, all_arrows):
    icom = {"input": [], "control": [],
            "output": [], "mechanism": []}
    for arrow in all_arrows:
        free_end = arrow.free_end()  # the end without a binding
        if free_end is None:
            continue  # arrow fully bound inside diagram, skip
        edge = nearest_frame_edge(free_end, child_frame)
        role = {"left": "input",
                "top": "control",
                "right": "output",
                "bottom": "mechanism"}[edge]
        icom[role].append(arrow.name)
    return icom
```

### Step 3: compare sets per role

```python
def check_consistency(parent_icom, child_icom,
                      tunnels={"input": set(),
                               "control": set(),
                               "output": set(),
                               "mechanism": set()}):
    errors = []
    for role in ["input", "control", "output", "mechanism"]:
        p = set(parent_icom[role])
        c = set(child_icom[role])
        for name in p - c:
            is_tunnel = name in tunnels[role]
            errors.append({
                "severity": "high" if not is_tunnel else "info",
                "role": role,
                "name": name,
                "problem": ("tunneled but missing on child boundary"
                            if is_tunnel else
                            "lost during decomposition")
            })
        for name in c - p:
            errors.append({
                "severity": "high",
                "role": role,
                "name": name,
                "problem": "appears on child but not on parent"
            })
    return errors
```

### Step 4: report

Output a list of discrepancies with severity, role, name, and
a short problem description. Show:

- Errors that break consistency (severity high)
- Tunneled arrows that landed on the wrong side (severity
  medium — they exist but in the wrong role)
- Tunneled arrows correctly placed (severity info / OK)

## 5. Node description template

Standard FIPS 183 walk-through for one block:

```
Блок {N}. {Имя блока}.
На основании {Controls — sorted left-to-right by start_x},
получает {Inputs — sorted top-to-bottom by start_y},
выдаёт {Outputs — sorted top-to-bottom by start_y},
опираясь на {Mechanisms — sorted left-to-right by start_x}.
```

When a side has no arrows, use one of these conventions:

| Style | Example |
|-------|---------|
| Explicit empty | "получает ничего" |
| Omit the side | "выдаёт X, опираясь на Y" |

Pick one style for the whole diagram and stay consistent.
Mixing "получает ничего" with omitted sides in the same
document reads as inconsistency.

For multiple arrows on the same side, list them comma-separated
with "и" before the last:

```
получает "Заявка клиента", "Заявка с сайта" и "Заявка по почте"
```

For two arrows:

```
получает "Заявка клиента" и "Заявка с сайта"
```

For one arrow:

```
получает "Заявка клиента"
```

## 6. Worked example: A2 with one block, tunneled Input

A minimal valid A2:

```json
{
  "elements": [
    {"type": "frame", "id": "frame-A2",
     "name": "A2 Обработка (parent: A0-2)",
     "x": 100, "y": 100, "width": 600, "height": 400},

    {"type": "rectangle", "id": "block-A2-1",
     "x": 250, "y": 200, "width": 200, "height": 100,
     "groupIds": ["group-A2-1"]},
    {"type": "text", "id": "func-A2-1",
     "x": 270, "y": 240, "text": "Обработка заявки",
     "textAlign": "center", "fontSize": 18,
     "groupIds": ["group-A2-1"]},
    {"type": "text", "id": "num-A2-1",
     "x": 255, "y": 278, "text": "A2.1",
     "textAlign": "left", "fontSize": 12,
     "groupIds": ["group-A2-1"]},

    {"type": "arrow", "id": "arrow-I1",
     "text": "( I1 Заявка клиента",
     "startBinding": {"elementId": "frame-A2",
                      "fixedPoint": [0, 0.5]},
     "endBinding": {"elementId": "block-A2-1",
                    "fixedPoint": [0, 0.5]},
     "endArrowhead": "arrow",
     "points": [[0, 0], [150, 0]]},

    {"type": "arrow", "id": "arrow-O1",
     "text": "O1 Результат",
     "startBinding": {"elementId": "block-A2-1",
                      "fixedPoint": [1, 0.5]},
     "endBinding": {"elementId": "frame-A2",
                    "fixedPoint": [1, 0.5]},
     "endArrowhead": "arrow",
     "points": [[0, 0], [150, 0]]}
  ]
}
```

Notes:

- `I1` is tunneled (encoded by leading `(`). Its free end is on
  the left edge of `frame-A2`, so it is captured as a child Input.
- `O1` is not tunneled (no brackets). Its free end is on the
  right edge of `frame-A2`.
- The block is one `groupIds` shared by three elements
  (rectangle, name text, number text).

## 7. Variant: heavy arrow catalogue

For large diagrams, render the catalogue as a real table inside
its child Frame:

```json
{"type": "rectangle", "id": "cat-A2-bg",
 "x": 850, "y": 100, "width": 400, "height": 350,
 "strokeStyle": "solid", "fillStyle": "hachure"},
{"type": "text", "id": "cat-A2-title",
 "x": 870, "y": 110, "text": "Arrow Catalogue A2",
 "fontWeight": "bold", "fontSize": 16},
{"type": "text", "id": "cat-A2-row1",
 "x": 870, "y": 140, "text":
   "I1 Заявка клиента | Граница | Блок 1 | I"},
{"type": "text", "id": "cat-A2-row2",
 "x": 870, "y": 165, "text":
   "O1 Результат | Блок 1 | Граница | O"}
```

Each row is one text element. Adjust line height (about 22-26px
for 14-16px font) so rows do not overlap.

## 8. Variant: ICOM codes only (no full catalogue)

For minimal diagrams, skip the catalogue Frame entirely and
only place ICOM codes as text labels on the child Frame edges.
The agent can still run ICOM consistency by comparing parent
block ICOM against the codes on the child Frame.

## 9. Common mistakes

- Tunneled arrows entered into a specific block of the child
  diagram. Tunneled arrows must have a free end on the child
  Frame edge, never an `endBinding` to a child block.
- Number text inside the rectangle rather than at its
  bottom-left. The canonical visual has the number outside the
  rectangle at the bottom-left corner. Place number text with
  `x` slightly to the left of the rectangle's `x`.
- Mixing `Граница` and `frame-A2` as source/target labels. Pick
  one: `Граница` is canonical; the Frame name is acceptable as a
  fallback only.
- Free end not actually on the edge. An arrow whose free end is
  5px inside the Frame is not "boundary" — push it out to the
  edge or it will be missed by the consistency check.
- Arrow `text` with parentheses in the object name confused for
  tunneling marker. Only parentheses at the very start or very
  end of `text` count as tunnel markers.