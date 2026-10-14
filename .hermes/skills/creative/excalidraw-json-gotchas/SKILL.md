---
name: excalidraw-json-gotchas
description: |
  Sub-skill reference for the excalidraw umbrella. Common pitfalls when
  building tools (parsers, validators, generators) that read or write
  .excalidraw JSON. Covers camelCase key conventions on disk, snake_case
  in-memory output, factory-API design traps (input params ≠ on-disk keys),
  arrow binding coordinate semantics, geometry tolerance for side detection,
  Excalidraw's auto-recalculated text bbox, Frame name parsing (incl. Russian),
  group text classification priority, hash-stripping for cross-frame matchers,
  bbox-center frame membership, longest-text-wins for descriptions, and
  leading-zero NNN normalization. Use when writing excalidraw_parser,
  block_extractor, side_detector, grid_parser, cell_extractor, or any
  module that touches element JSON.
version: 0.1.0
author: Hermes Agent
metadata:
  hermes:
    tags: [excalidraw, json, parser, pitfall, tooling]
    category: creative
    related_skills: [excalidraw, idef0-excalidraw]
---

# Excalidraw JSON — Gotchas for Tool Builders

Hard-won patterns from writing parsers, validators, and generators that
read or write `.excalidraw` files. Read this before building any module
that touches element JSON.

## 1. On-disk keys are camelCase. In-memory keys are snake_case.

Excalidraw's JSON format uses **camelCase**:

```
startBinding, endBinding, boundElements, containerId,
frameId, groupIds, originalText, autoResize,
fixedPoint, fontFamily, fontSize, textAlign,
verticalAlign, backgroundColor, strokeColor,
fillStyle, strokeStyle, strokeWidth, endArrowhead,
startArrowhead, roundness, seed, version, ...
```

When you build a wrapper class that returns extracted/normalized dicts
for downstream consumers, the convention in this skill library is to
**convert to snake_case in the output**:

```python
# Output dict (what consumers see)
{
    "start_binding": elem.get("startBinding"),
    "end_binding": elem.get("endBinding"),
    "frame_id": elem.get("frameId"),
    ...
}
```

This avoids clashing with Python conventions downstream (e.g. when you
add logic that references these keys in many places). But it creates a
trap when writing tests or factory functions.

## 2. Factory/wrapper API trap

If you write a factory function `make_arrow(end_binding=..., start_binding=...)`,
the **parameter names** should be snake_case (Python convention), but the
**values written into the dict** must be camelCase (Excalidraw format):

```python
def make_arrow(..., end_binding=None, start_binding=None, ...):
    return {
        ...
        "startBinding": start_binding,   # camelCase on disk
        "endBinding": end_binding,        # camelCase on disk
        ...
    }
```

If a downstream module then reads the output dict and looks up
`arrow.get("end_binding")` (snake_case, expecting extractor output), it
will silently get `None` and you'll spend 30 minutes debugging why
"nothing binds". Always trace: input → on-disk format → in-memory format
→ consumer expectations.

## 3. arrow binding coordinate semantics

When an arrow has `endBinding: { elementId: "r1", focus: 0, gap: 1 }`,
the arrow's last `points` entry is **relative to the arrow's x/y**, not
absolute. To get the actual end coordinate:

```python
end_x = arrow["x"] + arrow["points"][-1][0]
end_y = arrow["y"] + arrow["points"][-1][1]
```

Same for `startBinding`. Forgetting this offset makes every side-detection
result wrong by the arrow's `x`/`y`.

## 4. `block_id` lookup mismatch — the classic bug

`block_extractor` returns dicts keyed by `rectangle_id` / `group_id` /
`num_text_id` / `func_text_id` (semantic, not raw). But `side_detector`
or other modules often write `block.get("id")` expecting the raw
Excalidraw `id` field. This silently returns `None`, and
`_find_attached_end` always returns `(None, None)` — meaning **side
detection fails for 100% of arrows** even though the code looks correct.

Always use a fallback chain:

```python
block_id = (
    block.get("id")
    or block.get("rectangle_id")
    or block.get("group_id")
)
```

Apply the same defensive lookup to anything matching arrow bindings to
blocks.

## 5. `fixedPoint` vs `points` for arrow anchor

`startBinding`/`endBinding` can carry `fixedPoint: [0.5, 0.5]` (normalized
0..1 within the target shape). But the arrow's own anchor is determined
by its `points` array, not by `fixedPoint`. If you're computing "which
side of the block does this arrow touch?", **use the arrow's points**,
not the binding's fixedPoint.

## 6. Geometry tolerance for side detection

When detecting which side of a block an arrow touches (left/right/top/
bottom), use a tolerance of ~20 px to account for Excalidraw's hand-drawn
rendering offset and rough.js jitter. Strict equality will miss arrows
that visually attach but have a 1-3 px offset due to roughness. Test
cases must place the arrow's end within tolerance of the block edge.

## 7. Text bbox is auto-recalculated

When you set `containerId`, Excalidraw **ignores** your `x`/`y`/`width`/
`height` for the text and recalculates them on load to center inside the
container. Don't rely on text bbox in tests that use container binding —
test the binding relationship, not the coordinates.

## 8. IDEF0/FIPS-183 number formats — regex pitfall

When parsing function-block numbers (`A0.1`, `A1.2`, `A-0.1`, `2.3a`),
naive regex like `^[A-]?\.?\d+[a-z]?$` **fails for the standard IDEF0
form**. A correct regex:

```python
r"^[A]-?\d*\.?\d*[a-z]?$|^[A]-?\d+[a-z]?$|^\d+\.?\d*[a-z]?$"
```

Or break it up: optional `A` prefix, optional `-` separator, optional
`<n>`, optional `.<m>`, optional `[a-z]` suffix.

## 9. Tunnel notation: round brackets, NOT double

Tunnel arrows in IDEF0 use single round brackets at the binding point:
`( I1 ...` or `... I1 )` or `( I1 ... )`. **NOT** `(( ))` (that's a
different convention, e.g. for "callout" in some diagram styles).

## 10. Arrow name extraction strips parens

When extracting the ICOM-code from arrow text like `( I1 входной
документ`, strip the parens **first**, then take the first whitespace-
delimited token. Otherwise you'll get `(` or empty string as the name.

## 11. Frame name parsing — Russian `х` + spaces around `x`

When parsing dimension-style Frame names like `"Таблица 500x300"`,
naive regex `r'Таблица\s+(\d+)[xх](\d+)'` fails for:

- Russian lowercase `х` (U+0445) — needs `[xхХX]` set, not just `[xх]`
- Spaces around the separator: `"Таблица 500 x 300"`, `"500X300"`, `"500 Х 300"`

Working pattern (allows optional whitespace around `x`/X/х/Х):
```python
TABLE_FRAME_NAME_PATTERN = re.compile(
    r'^Таблица\s+(\d+)\s*[xхХX]\s*(\d+)\s*$',
    re.IGNORECASE
)
```

When you design your own "named Frame" convention, prefer the same shape:
`<prefix> <value><sep><value>` with `[sep]` being a char class that
includes both Latin and Cyrillic variants, plus optional surrounding
whitespace.

## 12. Group classification by text content — priority order matters

When a group contains multiple text elements (e.g. `##001`, `#Name`,
`Описание...`), **classification order matters** — and `#NNN` must
not collide with `#Name`. The convention from `excalidraw-grid-analyzer`:

1. Text matches `^#+\s*(\d+)\s*$` → it's a **number** (`##001`, `#42`)
2. Text starts with `#` but is NOT just `##NNN` → it's a **name** (`#Git`)
3. Text does NOT start with `#` → it's a **description** (pick longest)

Apply this priority in one pass over the group's texts, marking each
text with its role and breaking on first match. Don't rely on element
order in the group — Excalidraw may reorder them between save and load.

## 13. Hash normalization in cross-frame lookups

When matching elements across different Frames (e.g. `##001` in table
Frame vs `#Name` in description Frame), the **leading `#` is structural,
not semantic**. Normalize before comparing:

```python
def normalize_name(name: str) -> str:
    name = name.strip()
    while name.startswith('#'):
        name = name[1:].lstrip()  # strip # AND following whitespace
    return ' '.join(name.lower().split())
```

Common bug: comparing `'#Git'` against `'Git'` returns `False` if you
just `.lower()` both — the `#` survives. Same applies to `##Name`
(double hash as a stylistic variant).

## 14. Position-based Frame membership — use group bbox center

When deciding whether a group belongs inside a Frame (table) or outside
(descriptions), check by the **center of the group's bounding box**,
not by the position of any single element. A group is the union of all
its elements; element 1 might be at (10, 10) while element 2 is at
(700, 500) — neither tells you where the group sits.

```python
def group_in_frame(group, frame):
    xs = [el.get('x', 0) for el in group]
    ys = [el.get('y', 0) for el in group]
    ws = [el.get('width', 0) for el in group]
    hs = [el.get('height', 0) for el in group]
    cx = (min(xs) + max(x + w for x, w in zip(xs, ws))) / 2
    cy = (min(ys) + max(y + h for y, h in zip(ys, hs))) / 2
    return frame_x <= cx <= frame_x + frame_w and frame_y <= cy <= frame_y + frame_h
```

Use ~10 px padding tolerance on the Frame edges to absorb hand-drawn jitter.

## 15. Longest-text-wins for descriptions

When a group contains multiple non-hash texts (e.g. a label "short" and
a body "this is a much longer description"), pick the **longest** as
the description. Designers often add short helper labels alongside the
real description — picking the first text silently grabs a label.

```python
candidates = [(el['text'], el['id']) for el in group
              if el['type'] == 'text' and not el['text'].startswith('#')]
candidates.sort(key=lambda x: len(x[0]), reverse=True)
description_text, text_id = candidates[0]
```

## 16. Leading zeros in NNN — normalize before matching

`##001`, `##01`, `##1` are visually distinct but semantically equal.
Match by `int(s)` (after stripping `#` and whitespace), not by string
equality:

```python
def normalize_nnn(nnn: str) -> str:
    if not nnn:
        return ''
    return str(int(nnn))  # "001" → "1", "01" → "1"
```

Failing to do this produces spurious "missing description" or "orphan"
errors whenever designers write `##01` in one place and `##1` in another.

## 17. Primary-key matching collapses secondary-key mismatches

When you index records by a primary key (NNN, ID, slug) and then look up
a foreign record by that key, the result is **binary**: found or not found.
Secondary mismatches (e.g. "found by NNN, but name doesn't match") DO happen,
but they only manifest if the foreign record's primary key DOES exist locally.

**Implications for `match()` functions:**

- `NNN_MISMATCH` (foreign NNN ≠ local NNN) **is impossible** if you index by
  NNN. Either the foreign NNN is in your index (then name can mismatch) or it
  isn't (then it's orphan/missing).
- `BOTH_MISMATCH` is similarly unreachable — once NNN matches the local index,
  the only axis left is name.
- The only realistic mismatch status when matching by primary key is
  `NAME_MISMATCH`.

**Don't design tests for impossible states.** If you find yourself writing
`assert both_mismatches == 1` for records with different primary keys, you're
describing the orphan/missing path, not a both-mismatch path.

Working pattern (index by primary key, classify secondary mismatches only):

```python
skill_idx = {normalize_nnn(s.nnn): s for s in skills}   # primary index
desc_idx = {normalize_nnn(d.nnn): d for d in descriptions}

matched_nnns = set()
for skill in skills:
    nnn = normalize_nnn(skill.nnn)
    desc = desc_idx.get(nnn)            # binary lookup
    if desc is None:
        missing.append(skill)           # foreign key not found
        continue
    if normalize_name(desc.name) != normalize_name(skill.name):
        name_mismatches.append((skill, desc))   # only this kind of mismatch
    else:
        matched.append((skill, desc))

for desc in descriptions:
    nnn = normalize_nnn(desc.nnn)
    if nnn not in skill_idx and nnn not in matched_nnns:
        orphans.append(desc)            # foreign key with no local counterpart
```

This pattern generalizes to any cross-record match (skill↔description,
person↔contact, issue↔assignee). The lesson is: pick a primary key,
index by it, then secondary mismatches are a function of "did the lookup
succeed at all".

## Test design checklist

When writing tests for Excalidraw JSON analysis tools:

- [ ] Factory functions take snake_case params, emit camelCase JSON
- [ ] Tests that consume `arrow_extractor` output reference **snake_case**
      keys (`start_binding`, `end_binding`, `frame_id`)
- [ ] Tests that pass raw Excalidraw elements directly reference
      **camelCase** keys (`startBinding`, etc.)
- [ ] For side detection tests, use `arrow_via_extractor(raw_arrow)` to
      normalize input
- [ ] Geometry tolerance ~20 px
- [ ] End-of-arrow coordinates include the `x`/`y` offset
- [ ] Standard IDEF0 number formats tested: `1`, `A1`, `A1.2`, `A-0.1`, `1.2a`
- [ ] Frame-name parser tested with Russian `х` AND space-padded `x`
- [ ] Group classification tested for text priority: `##NNN` → `#Name` → description
- [ ] Cross-frame matchers normalize leading `#` before comparing
- [ ] Frame-membership checks use **bbox center**, not single-element position
- [ ] Description-text picker uses longest-text-wins
- [ ] NNN matching tested with leading-zero variants (`##001` == `##1`)
- [ ] If matching by primary key, secondary-key mismatch tests only cover
      cases where the primary key DOES exist locally (don't test impossible
      `both_mismatch` / `nnn_mismatch` states)

## История версий

- 0.1.0 (2026-08-09): начальная версия (10 gotchas)
- 0.2.0 (2026-08-17): добавлены gotchas #11–16 из разработки
  `excalidraw-grid-analyzer` (Frame name regex, group text priority,
  hash normalization, bbox-center frame membership, longest-text-wins
  for descriptions, leading-zero NNN normalization)
- 0.3.0 (2026-08-17): добавлен gotcha #17 — primary-key matching collapses
  secondary-key mismatches (из рефакторинга `skill_matcher.match()` для
  `excalidraw-grid-analyzer`; тесты `test_both_mismatch` и
  `test_nnn_mismatch_with_same_name` сначала проверяли недостижимые
  состояния, потом были переписаны на проверку orphan/missing)
