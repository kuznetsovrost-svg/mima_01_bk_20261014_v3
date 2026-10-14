# Working example — /tmp/figma_v5/ (504-595 / Report 5)

Annotated walkthrough of the **complete end-to-end bridge** that ran on 2026-08-21, capturing the lessons from `v5 → v6`. This is the canonical shape to copy when starting a new `/tmp/figma_<stage>/` workspace.

## Timeline

| Date | Event | File | Key change |
|------|-------|------|------------|
| 2026-08-07 | v1: `figma_report.html` (Anima-style JSON spec) | `/tmp/figma_html_report_template.json` | First export attempt |
| 2026-08-08 | v2: HTML with `{{TOKEN}}` placeholders | `report_504-595_v2.html` | User uploads via html.to.design → `Report 3 TEST` |
| 2026-08-08 | v3: Auto-layout, fixed indigo header | `report_504-595_v2.html` (rev 2) | User uploads to `Report 4` (file renamed) |
| 2026-08-21 | v5: User manually creates 5 `COMPONENT_SET`s in Figma | `report_504-595_v5.html` | Hermes extracts structure, regenerates HTML with placeholders |
| 2026-08-21 | v6: User manually renamed all properties to `State`; shrank TBL3 head to 5 cols | `report_504-595_v6.html` | Hermes recalibrates widths, substitutes real 504-595 data, removes `app-header` |

## Layout in /tmp/figma_v5/

```
figma_v5/
├── html/
│   ├── report_504-595_v5.html       # ← v5 deliverable (after first extraction)
│   └── report_504-595_v6.html       # ← v6 deliverable (after user iteration)
├── scripts/
│   ├── extract_tables.py            # one-shot extractor used to build tables.json
│   └── build_html_v6.py             # the v6 generator
└── api_responses/
    ├── file.json                    # raw get_file() — 1.9 MB
    ├── nodes.json                   # targeted get_nodes() for variant components
    ├── tables.json                  # parsed: {table_name: {summary, head, row}}
    └── tables_v6.json               # v6: widths recalibrated per table
```

## Key data shapes

### `tables.json` — extracted from Figma

```json
{
  "TBL3": {
    "head": ["#", "Цвет", "Статус", "Код", "Наименование", "План", "Прогноз", "Факт", "Исполнитель"],
    "row":  ["{{S3_R1_NUM}}", ..., "{{S3_R1_OWNER}}"],
    "summary": "{{S3_SUMMARY}}"
  },
  ...
}
```

### `tables_v6.json` — after user iteration

```json
{
  "TBL3": {
    "head": ["#", "Код", "Наименование", "План", "Прогноз"],
    "row":  ["1", "104-719", "...", "2025-07-08", "2025-07-21"],
    "summary": "Замечания по срокам:  Требует внимания — 2 критических, 1 существенное, 0 информационных",
    "widths": [40, 90, 952, 240, 240]   // ← recalibrated to sum=1562
  },
  ...
}
```

The structure of `tables.json` is **identical** between v5 and v6 — only the **values** change, and in v6 the widths array is added per-table.

## Recalibration formula (P12)

```
canvas_width = 1562 (always)
fixed_columns = {#: 40, Код: 90, План: 240, Прогноз: 240, Дней: 100, ...}
flex_column = "Наименование" or "Детализация" or "Показатель"
flex_width = canvas_width - sum(fixed_columns for this table)
```

Examples from v6:
- TBL3 (5 cols): `[40, 90, 952, 240, 240]` — flex=952, sum=1562 ✓
- TBL4 (4 cols): `[40, 380, 120, 1022]` — flex=1022 (Детализация), sum=1562 ✓
- TBL5 (6 cols): `[40, 90, 712, 240, 240, 240]` — flex=712 (Название), sum=1562 ✓
- TBL6 (3 cols): `[40, 760, 762]` — flex split 760+762, sum=1562 ✓
- TBL7 (3 cols): `[40, 600, 922]` — flex=600+922, sum=1562 ✓

Always assert `sum(widths) == 1562` before emitting HTML.

## Indicator variant mapping (P9, P11, P15)

```python
# In Figma, the user's report Frame contains:
#   div#indicator (FRAME)                    ← wrapper, no componentProperties
#     INSTANCE "div#indicator" (9:515)        ← chosen variant = "substantial"
#       TEXT "ПРОЕКТ\nТРЕБУЕТ\nВНИМАНИЯ"

# Extractor reads:
#   wrapper.componentProperties = None      ← DO NOT use this
#   wrapper.children[0].componentProperties = {"State": {"value": "substantial"}}
#   wrapper.children[0].children[0].characters = ""  ← empty, not "ПРОЕКТ..."
#
# To get the actual text:
#   1. Read instance.componentProperties.State.value
#   2. Find the COMPONENT_SET's variant matching this value
#   3. Read the variant's TEXT child's characters
#
# For the COLOUR: read the wrapper FRAME's `fills`, not the variant's
```

Three variants of `div#indicator` exist:
- `State=critical` → "Проект болен"
- `State=substantial` → "ПРОЕКТ\nТРЕБУЕТ\nВНИМАНИЯ"
- `State=normal` → "ПРОЕКТ ЗДОРОВ"

## The cardinal-sin recovery protocol (P16)

After EACH iteration, run:
```bash
git -C ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health diff --stat
```
Should be empty. If anything modified, undo with `git checkout`.

In practice, fst-project-health is not git-managed in `/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health/`. The alternative is to spot-check by listing files and grepping for new FIGMA mentions:

```bash
grep -ri "figma" /root/.hermes/profiles/fst-control/skills/productivity/fst-project-health/
# Should return nothing
```

## Lessons captured in SKILL.md

| # | Lesson | Source event |
|---|--------|--------------|
| P11 | Read variant TEXT, not instance TEXT | v6 — `componentProperties.State="substantial"` + wrapper |
| P12 | Recalibrate widths after column-count changes | v6 — TBL3 went from 9 cols to 5 cols |
| P13 | Wrappers around INSTANCE shift the fill layer | v6 — `div#indicator` is a FRAME wrapper |
| P14 | User may delete layers between iterations | v6 — user deleted `div#app-header` |
| P15 | Property name case-sensitivity | v6 — "Expanded"/"expanded"/"Collapsed"/"collapsed" all coexist |
| P16 | The cardinal sin (recap with teeth) | 2026-08-21 — first recorded violation |
| P17 | Section names in Figma leak source skill | cosmetic |
| P18 | Image-эталон overrides Figma variant state | 2026-08-21 — `State=substantial` but etalon wanted red |
| P19 | Default section state = collapsed for TBL4–7 | 2026-08-21 — compact report view |
| P20 | Standard summary text vocabulary (Здоров/Требует внимания/Болен/Нейтральный) | 2026-08-21 — text labels, no emoji |
| P21 | Indicator radial gradient for critical | 2026-08-21 — `radial-gradient(circle at center, #fca5a5 0%, #ef4444 60%, #b91c1c 100%)` |
| P22 | Title text convention "Общая оценка здоровья проекта" | 2026-08-21 — generic title covers all sections |
| P23 | The cardinal sin V2 (with full user-stated rule) | 2026-08-21 — «Ни в коем случае не меняй скиллы и отчеты по скиллу fst-project-health» |

## Re-running this pipeline

For a new project (e.g. 503-152):
1. Copy `/tmp/figma_v5/` → `/tmp/figma_503-152/`
2. Update `scripts/build_html_v6.py` → `DATA_504_595` dict with 503-152 data
3. Re-run `extract_tables.py` against 503-152 Figma file
4. Re-run `build_html_v6.py`
5. Deliver as MEDIA:

The pipeline is **data-only** — if the Figma file structure stays the same (same COMPONENT_SETs, same variant names), only the data dict needs updating.

## Image-эталон convergence (the v6 inflection point)

The 2026-08-21 v5 → v6 iteration added a **third input source** that wasn't in the original v5 plan: the user's image-эталон (screenshot of the desired output). The Figma file said `State=substantial` for the indicator, but the etalon said "ПРОЕКТ БОЛЕН in a red gradient circle". The etalon won.

How to handle a three-way conflict (Figma state + tables.json + etalon):

1. **Structural facts** (column count, header names, presence of layer) → take from Figma, not the etalon. The etalon might compress or simplify the structure.
2. **Visual facts** (colors, text content, indicator gradient) → take from the etalon, not Figma state. The etalon is the design intent.
3. **Data facts** (real project data) → take from the live project (PMForesight MCP / `build_report_header.py`).
4. **Presentation facts** (which sections expanded vs collapsed, summary vocabulary) → take from the etalon.

The etalon can be a screenshot, a PDF, a hand-drawn sketch, or a verbal description. What matters is: **the etalon represents what the user wants to see**; Figma state represents what the user **made**; data represents what the project **is**. When these three diverge, the etalon wins for presentation, Figma wins for structure, data wins for content.

### Diagnostic when given an etalon

When the user attaches an image-эталон:

```bash
# 1. List all visual claims in the etalon:
#    - Title text and font size
#    - Indicator color, text, position
#    - Which sections are expanded vs collapsed
#    - Color tokens for row backgrounds
#    - Status vocabulary (Здоров / Требует внимания / Болен)
# 2. Compare each claim against current Figma state + tables.json
# 3. If they disagree, prefer the etalon (P18)
# 4. After emitting HTML, do a self-check pass:
#    - No emoji (P20)
#    - All widths sum to 1562 (P2, P12)
#    - Indicator gradient matches state (P21)
#    - Title text matches "Общая оценка..." convention (P22)
```