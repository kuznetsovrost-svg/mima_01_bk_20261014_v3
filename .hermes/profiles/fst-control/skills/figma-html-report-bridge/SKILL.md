---
name: figma-html-report-bridge
description: "Hermes↔Figma bridge for HTML reports. Direction A: data → HTML with {{TOKEN}} → user imports via html.to.design → user authors COMPONENT_SETs. Direction B: read COMPONENT_SETs + INSTANCES via Figma REST → re-emit HTML. Direction C: image-эталон («вот как должно быть» + screenshot) — emitter prefers visual over Figma state. Direction D: real-data iteration («нужны реальные данные») — substitute placeholders with concrete project dict. Pitfalls: html.to.design drops CSS vars; Figma renames by id (div#name); Property 1 default; INSTANCES in Collapsed hide data; get_components returns 0; Figma REST cannot write — Hermes never writes; default state = collapsed TBL4–7 / expanded TBL3; vocabulary = Здоров/Требует внимания/Болен/Нейтральный, no emoji; report-header-text MUST be flex-direction row; native <details> + CSS triangle for collapsed; thead #1D4ED8 darker than #2563EB; title 18px regular, project 30px bold. NEVER modify fst-project-health — use /tmp/figma_<stage>/. Author: ROSTISLAV KUZNETSOV."
version: 0.3.0
author: ROSTISLAV KUZNETSOV
metadata:
  hermes:
    tags: [figma, html, bridge, components, variants, round-trip, design, export, import, ru, image-etalon]
    category: productivity
    related_skills: [fst-project-health]
changelog:
  - "0.3.0 (2026-08-21): P25 + P19 — corrected: render full <thead>/<tbody> in DOM even for collapsed sections, let <details> open/closed state hide them. Previous advice to omit body broke the toggle. User feedback: «А где строки в таблицах при раскрытии? Есть только в одной (верхней)!»"
  - "0.2.0 (2026-08-21): Image-эталон workflow (Direction C), real-data iteration (Direction D), P18–P28."
---

# figma-html-report-bridge

Class-level workflow for the bidirectional **Hermes ↔ Figma** bridge used to author structured HTML reports and inspect them inside Figma. The four directions are deliberately separate:

- **Direction A — Hermes → Figma:** export data → placeholder HTML → user imports via html.to.design → user hand-authors Figma COMPONENT_SETs.
- **Direction B — Figma → Hermes:** read COMPONENT_SETs + INSTANCES via Figma REST → re-emit HTML with placeholders (or real data).
- **Direction C — Image-эталon:** user attaches screenshot/PDF saying «вот как должно быть». Emitter treats the image as the authoritative visual target, not the Figma state. Reconcile structural facts (column count, header names) from Figma, visual facts (colors, text, indicator gradient) from the image.
- **Direction D — Real-data iteration:** user says «нужны реальные данные» (or similar). Substitute placeholders in the regenerated HTML with concrete values from a hardcoded DATA dict or live MCP query. The structure (column count, summary format, row colors) stays the same; the data is what changes.

The skill is intentionally **read-write from Hermes, read-only from Figma**. Figma REST API cannot create nodes (POST `/v1/files/{key}/nodes` → 404); drawing in Figma requires a Plugin (e.g. html.to.design) or a human.

## When to load

Trigger phrases:

- «открой в figma», «выгрузи в figma», «сделай html для figma», «импорт в figma», «html.to.design», «anima»
- «вытащи из figma», «figma → html», «обратно из figma», «извлеки компоненты», «что в figma»
- «обнови figma», «re-emit», «перегенери html», «синхронизируй с figma»
- «вот как должно быть» (when screenshot/PDF attached) — image-эталон workflow
- «реальные данные», «нужны реальные данные», «подставь реальные», «как выглядит с реальными» — real-data iteration

Do **not** load for: simple Figma file inspection (use `figma-api-import`), or for general HTML generation unrelated to Figma.

## Hard rule — never modify the source skill

**Never** edit `fst-project-health` (or any other user-owned skill) while running FIGMA experiments. All scripts, templates, references, and outputs go into an isolated workspace:

```
/tmp/figma_<stage>/
├── html/             # generated HTML files (v1, v2, v3, ...)
├── scripts/          # per-stage Python (extract_*, build_html_*)
├── api_responses/    # raw + parsed Figma API JSON snapshots
└── references/       # stage-specific notes
```

`/tmp/project_<code>_report.{html,md,docx}` files produced by `fst-project-health` are NEVER touched during a FIGMA bridge run. Violating this rule was the lesson of 2026-08-21 (user caught FIGMA-bridge content creeping into `fst-project-health` `SKILL.md` description, removed it twice).

## Workflow: direction A — Hermes → Figma

```
1. Python data dict (e.g. parsed from MD report, MCP, JSON)
        ↓
2. build_html_with_placeholders.py (in scripts/)
   - Generates HTML with {{TOKEN}} placeholders for every dynamic value
   - Inline CSS, not CSS variables (html.to.design drops them)
   - inline-flex on indicators (not position: absolute)
   - Widths expressed as inline style="width: Npx" on each <td>
   - Sum of cell widths per row = canvas width (1562px)
        ↓
3. Hand off HTML to user as MEDIA: file
        ↓
4. User imports via Figma plugin (html.to.design / Anima / Builder.io)
        ↓
5. User manually converts each section into a COMPONENT_SET
   - Property name "State" with values [Expanded, Collapsed]
   - Property name "Severity" with values [critical, normal, substantial]
   - User must rename "Property 1" in Figma UI before extraction
        ↓
6. User assembles a Frame with INSTANCES of those components
        ↓
7. Stop — user owns the Figma file from here
```

## Workflow: direction B — Figma → Hermes

```
1. User says "extract from Figma" and provides a Figma file URL
        ↓
2. extract_figma_components.py (in scripts/)
   - get_file(file_key) → walk document recursively
   - get_nodes(file_key, [frame_id]) → get the user's Frame
   - For each INSTANCE inside the Frame:
     * Read componentProperties (e.g. {"State": {"value": "Collapsed"}})
     * If instance is Collapsed → warn user, suggest switch to Expanded (P5)
     * **Extract the text from the chosen variant's TEXT child, NOT from the instance** (P9, P11)
   - For each COMPONENT_SET in the document:
     * Read componentPropertyDefinitions → all variant options (P4)
     * For each variant (COMPONENT):
       - Walk children (table-summary, table-head, table-row)
       - Extract all_text_chars from each TEXT node
       - Extract fills_hex from each layer
     * Save to api_responses/components.json
        ↓
3. build_html_from_components.py (in scripts/)
   - Read components.json
   - Substitute real data into HTML template
   - **Widths MUST be recalibrated** if the number of head columns shrank vs. direction A template (P12)
   - Emit report_<code>_v<N>.html as MEDIA:
        ↓
4. Hand off regenerated HTML to user
        ↓
5. (Optional) User re-imports to Figma, repeating direction A
```

## Workflow: direction C — Hermes → real-data HTML → re-extract (loop)

The bridge is intentionally a **loop**, not a one-shot export. After the user converts their Frame into COMPONENT_SETs (direction B once), every subsequent data update skips Figma entirely:

```
1. New project data arrives (different project, updated values)
        ↓
2. Read the previously extracted api_responses/components.json
   - Use it as a TEMPLATE — same column layout, same color tokens
   - Skip re-extraction from Figma (Figma file hasn't changed)
        ↓
3. Substitute new data into build_html_from_components.py
   - Emit new report_<code>_v<N+1>.html
        ↓
4. User can either:
   (a) Browse the HTML locally — done, no Figma round-trip needed
   (b) Re-upload to Figma for a fresh export
        ↓
5. If (b) — user uploads, the iteration loop continues
```

This is the **economic payoff** of the bridge: once COMPONENT_SETs are authored (one-time, ~30 min human work), every subsequent report runs fully automated.

## Pitfalls — the non-obvious ones

### P1. html.to.design drops CSS variables and `position: absolute`

`<div style="--bg: #2563EB">` becomes a flat div with no fill. `<div class="indicator" style="position: absolute; right: 24px; top: 20px">` becomes a flex child that stretches to its parent's full width. **Always** use inline literal hex and inline-flex with explicit width/height instead.

### P2. Cell widths must sum to canvas width

Per-row cell widths must sum to canvas width (typically 1562px). If they don't, html.to.design shows the table correctly in Figma but loses the alignment when the user opens the COMPONENT for editing. Add a self-check: parse every `<tr>`, sum `style="width: Npx"`, assert == 1562.

### P3. Figma renames layers by HTML `id`, not `class`

`<div class="report-header" id="report-header">` becomes `div#report-header` in Figma's layer tree, **not** `div.report-header`. Search and inspection scripts MUST look for `div#<id>`. If two layers share an `id`, only the first survives — give each layer a unique id.

### P4. Property names default to "Property 1"

Figma names auto-created variant properties `Property 1`, `Property 2`, ... The user must rename them in Figma's component panel (`right sidebar → Component → Variant property → rename`). Until renamed, Figma API returns `"Property 1": {...}` and your extractor must tolerate any name. Best practice: instruct the user to rename before extraction.

### P5. INSTANCES in Collapsed variant don't expose data

When the user assembles a Frame with INSTANCES, each instance is in `Collapsed` by default. The Figma tree only contains the `div.table-summary` node, not the rows. **Before** extraction, ask the user to switch every instance to `Expanded` — or accept that you can only extract summary text.

### P6. `get_components` endpoint returns 0

`GET /v1/files/{key}/components` frequently returns `{"meta": {"components": []}}` even when the file contains many `COMPONENT_SET` nodes. **Always** walk `document` recursively looking for `type == "COMPONENT_SET"` and `type == "COMPONENT"`. The extractor script does this automatically.

### P7. Figma API cannot create nodes

`POST /v1/files/{key}/nodes` → 404. The bridge is therefore read-only from Figma's side. Hermes NEVER writes to Figma. The user is the only writer.

### P8. Instance overrides apply only to non-variant properties

`componentPropertyDefinitions` lists the variant properties; `componentProperties` on an instance lists the values the user picked. Don't confuse the two — the former defines what's possible, the latter records what's chosen.

### P9. INDICATOR text differs between variants

If the user makes the indicator a component with `State=critical|normal|substantial`, the variant carries the full text and color. The HTML extractor reads the text from the chosen variant's TEXT child and writes it as `{{INDICATOR_TEXT}}`. Don't read it from the instance — read from the variant.

### P10. Re-importing produces a fresh SECTION

When the user re-uploads the regenerated HTML to Figma via html.to.design, the plugin creates a new SECTION with the same name. The original SECTION is not overwritten. To avoid pile-up, instruct the user to delete the old SECTION before re-uploading, or use a different filename each time.

### P11. Read variant TEXT, not instance TEXT

When an instance carries variant text (e.g. indicator with `State=critical` shows "Проект болен" and `State=normal` shows "ПРОЕКТ ЗДОРОВ"), the text lives in the **variant COMPONENT** (`State=critical`) under its TEXT child, not in the INSTANCE. The instance has `componentProperties.State.value = "critical"` and a single TEXT child whose `characters` is the empty string — it just points to the variant. To get the actual rendered text, find the COMPONENT_SET, find the variant matching the instance's `State.value`, and read its TEXT children.

### P12. Recalibrate widths after column-count changes

When the user shrinks or grows the number of head columns between iterations (e.g. TBL3 went from 9 columns in `Report 4` to 5 columns in `Report 5` after you asked them to), the existing width array no longer sums to 1562px. Re-run the calibration per table:

```python
# For each table, set widths so they sum to canvas_width (typically 1562)
# Rule of thumb:
#   - # (index)        = 40
#   - Код / Цвет / etc = 90
#   - Наименование     = 320-952 (largest flex column)
#   - Date / small     = 100-240
# Adjust the long column to absorb the difference
assert sum(widths) == 1562, f"TBL3 widths sum to {sum(widths)}, not 1562"
```

Always run a self-check loop before emitting HTML.

### P13. Wrappers around INSTANCE shift the fill layer

The user may wrap an INSTANCE of `div#indicator` inside another FRAME (e.g. for padding or a background ring). In that case the fill lives on the WRAPPER, not on the INSTANCE, and `componentProperties` on the wrapper is empty. To find the indicator's actual visual color, walk wrapper → instance → component → variant.

**Symptom:** `componentProperties` is `None` on a node named `div#indicator`. Check whether it has a single INSTANCE child instead.

### P14. User may delete layers between iterations

Do not assume every layer in the canonical HTML structure (e.g. `div#app-header`) is present in the user's Frame. After each iteration, check the Frame's children by name and adapt:

- If `div#app-header` is absent → omit it from the regenerated HTML
- If a section's table component is absent → render the section as a placeholder
- Never error out on a missing expected layer; treat it as intentional simplification

### P15. Property name case-sensitivity

When extracting variants, the instance's `componentProperties.State.value` may be `"Collapsed"` while the COMPONENT_SET's `componentPropertyDefinitions.State.variantOptions` may contain `"expanded"` and `"collapsed"` (lowercase). Both `Expanded` and `expanded` exist in the wild. Normalize by lowercasing both sides before comparison:

```python
def match_variant(cs_definitions, instance_state_value):
    for option in cs_definitions["State"]["variantOptions"]:
        if option.lower() == instance_state_value.lower():
            return option  # return canonical case from definitions
    return None
```

### P16. The cardinal sin (recap with teeth)

**Editing `fst-project-health/SKILL.md` or its `scripts/`, `references/`, `templates/` directories from a FIGMA bridge session is the rule this skill was created to prevent.** First recorded violation: 2026-08-21 — I added a "FIGMA bridge" reference and pitfall to `fst-project-health/SKILL.md` description mid-session. User caught it and demanded a separate skill. **Always** verify by running:

```bash
diff <(git -C ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health diff SKILL.md) <(echo -n) \
  || echo "fst-project-health modified — undo immediately"
```

If you find yourself writing to that path, stop and use `/tmp/figma_<stage>/` instead.

### P17. Section names in Figma leak the source skill

html.to.design names the SECTION after the HTML file. If the source HTML was generated from `fst-project-health` output, the SECTION name may echo the original. This is metadata leakage, not data leakage — the SECTION name is visible in the Figma layer panel. Avoid generating HTML named after the source skill for any flow that ends up in Figma.

### P18. Image-etalon overrides Figma variant state

When the user attaches a **screenshot or PDF rendering** of the desired output, treat it as the **authoritative target**, not the Figma component state. Live example (2026-08-21 v6): user showed a screenshot of the report with `ПРОЕКТ БОЛЕН` text inside a **red** gradient circle. But the Figma instance carried `State=substantial` (yellow). I emitted yellow + multi-line text because I followed Figma. The user corrected: emit what the **screenshot shows**, regardless of variant state. Resolution rules:

- Figma state + user screenshot match → trust Figma
- Figma state + user screenshot disagree → **trust screenshot**, add a one-line comment to the script explaining the deviation
- No screenshot, only Figma → trust Figma but warn user about the conflict

### P19. Default collapsed state for compact sections

When emitting HTML from `tables.json`, **default sections 4–7 to collapsed** (only the summary bar visible). Section 3 (Замечания по срокам) is the exception — keep it expanded by default because it shows the КТ with concrete dates. Rationale: a user opening the report should see the highest-density table first, then click to expand detail sections.

```python
OPEN_TABLES = {"TBL3"}  # canonical default
# User can override per-iteration if a project needs different default
```

For the collapsed variant of a table, **render the full `<thead>` and `<tbody>`** — the browser hides them automatically when `<details>` is closed. Omitting the body entirely produces a "только в одной таблице есть данные" complaint when the user expands other tables. See P25 for the full pattern with CSS triangle.

### P20. Standard summary text vocabulary

Use these Russian terms consistently across all sections (no emoji in summary text):

| Status | When | Example suffix |
|--------|------|----------------|
| `Здоров` | All indicators pass | `Здоров — 0 критических, 0 существенных, 0 информационных, 0 «Неопределено»` |
| `Требует внимания` | Mix of critical + non-critical, OR 1–2 critical | `Требует внимания — 2 критических, 1 существенное, 0 информационных` |
| `Болен` | All indicators are critical | `Болен — все 3 показателя «Да» (критические)` |
| `Нейтральный` | Reference / informational only | `Нейтральный — справочная информация` |

Emoji glyphs (🔴🟡🟢) **break in html.to.design** — render as tofu `□`. Plain text only.

### P21. Indicator radial gradient for critical state

The critical indicator (red gradient) is built with:

```css
.indicator-critical {
    background: radial-gradient(circle at center, #fca5a5 0%, #ef4444 60%, #b91c1c 100%);
    color: #FFFFFF;
}
```

The substantial state uses flat `#FEF3C7` + `#92400E` text. The unknown/normal state uses `#D1D5DB` + `#9CA3AF`. **Never** apply the radial gradient to non-critical states — the visual contrast is what signals danger.

### P24. `.report-header-text` MUST be a horizontal flex container

The indicator must sit **to the right** of the title block, not below it. Common bug (encountered 2026-08-21 v6): accidentally writing `flex-direction: column` on `.report-header-text` makes the indicator wrap below the text, even though every individual block (`.report-header-left`, `.indicator`) is correctly styled. The fix is mechanical:

```css
.report-header-text {
    display: flex;
    flex-direction: row;       /* NOT column */
    align-items: center;        /* vertical centering */
    gap: 32px;
}
.report-header-left {
    display: flex;
    flex-direction: column;     /* title + project + meta stack vertically */
    gap: 6px;
    flex-grow: 1;               /* take available horizontal space */
}
.indicator {
    flex-shrink: 0;             /* do NOT let flexbox squeeze the circle */
}
```

Diagnostic when user complains "indicator moved under the title": `grep "flex-direction" *.css` — `.report-header-text` should be `row`, `.report-header-left` should be `column`. If they're swapped, that's the bug.

### P25. Use `<details>` for collapsed sections with a CSS-styled triangle

When TBL4–TBL7 are collapsed (default per P19), use native `<details>`/`<summary>` with a CSS-styled triangle marker. **Always render the full `<thead>` and `<tbody>` in the DOM** — the browser hides them automatically when `<details>` is closed. Emitting an empty table body breaks the `<details>` toggle and creates a "только в одной таблице есть данные" complaint from the user when they expand the others.

```html
<details class="table-details">
  <summary class="table-summary"><span class="triangle">▶</span><span class="summary-text">Section name:  Status — 0 critical, 0 substantial</span></summary>
  <table>
    <thead>
      <tr>
        <th>...</th>   <!-- head row rendered, hidden by details closed -->
      </tr>
    </thead>
    <tbody>
      <!-- FULL data rows rendered, hidden by details closed -->
      <tr class="critical"><td>1</td><td>...</td></tr>
      <tr class="warning"><td>2</td><td>...</td></tr>
    </tbody>
  </table>
</details>
```

CSS:

```css
.table-details > summary {
    list-style: none;     /* hide default ▶ marker */
    cursor: pointer;
    display: block;
    padding: 8px 24px;
    background: #F3F4F6;
    color: #4B5563;
    font-weight: 700;
    font-size: 12px;
}
.table-details > summary::-webkit-details-marker { display: none; }
.table-details > summary .triangle {
    display: inline-block;
    margin-right: 8px;
    font-size: 9px;
    transition: transform 0.2s;
}
.table-details[open] > summary .triangle { transform: rotate(90deg); }
```

The black triangle **is the `<details>` marker**. Don't try to fake it with a separate icon — the browser-native `<details>` is the right primitive.

For the **opened** section (TBL3 by default per P19), set `<details class="table-details" open>` — the triangle rotates 90° and shows ▼.

### P26. Image-эталon trigger phrases

User signals they want a re-emit against the visual target with phrases like:

- «вот как должно быть» (most common, after attaching a screenshot)
- «так должно быть»
- «эталон» / «image-эталон»
- Direct attachment of screenshot/PDF with no other text

When this signal fires, skip the Figma-extraction workflow (P18) and go straight to the etalon-matching flow. If both Figma state AND etalon are present, the etalon wins for presentation (P18). After emitting HTML, do the self-check pass listed in P23's `Diagnostic recipe`.

### P27. "Real data, not placeholders" iteration trigger

User often emits a "give me real numbers" signal mid-iteration. Trigger phrases:

- «нужны реальные данные»
- «как это выглядит с реальными данными»
- «на реальных данных»
- «подставь реальные»

When this signal fires, the placeholders in `tables.json` are intentional — the user wants to see the layout with concrete values from a specific project (e.g. 504-595). To answer: keep the structure (column count, row color logic, summary format) but substitute placeholder values with concrete data from a hardcoded DATA dict (or from MCP for live projects). The structure is the bridge; the data is the value.

In `/tmp/figma_v5/` this was `DATA_504_595` — a 100-line Python dict with every row's cell text, all summaries written in the standard vocabulary (P20). Always include at least one full project (header + all sections) in the script so the user can verify the layout.

### P28. Thead darker than report header

After `report-header` is established as `#2563EB`, the `thead` should be **darker** (`#1D4ED8`) to create visual hierarchy. Same applies to `<thead>`'s `border-right` color (`#1E3A8A` rather than `#1E40AF`). User feedback 2026-08-21 v6: «Строки заголовков темнее» — they want a darker blue for the table heads, not the same `#2563EB` as the header.

```css
thead th {
    background: #1D4ED8;
    border-right: 1px solid #1E3A8A;
}
```

If the user's image-эталon shows thead the same color as the header, fall back to `#2563EB`. Otherwise, default to `#1D4ED8` for visual separation.

### P23. The cardinal sin (recap with teeth) — V2

**Editing `fst-project-health/SKILL.md` or its `scripts/`, `references/`, `templates/` directories from a FIGMA bridge session is the rule this skill was created to prevent.** First recorded violation: 2026-08-21 — I added a "FIGMA bridge" reference and pitfall to `fst-project-health/SKILL.md` description mid-session. User caught it and demanded a separate skill. The user-stated rule: «Ни в коем случае не меняй скиллы и отчеты по скиллу fst-project-health. Мы продолжим работать с этим скиллом так, как будто всех наших экспериментов с FIGMA не было! Если нужно куда-то записывать, сделай отдельный SKILL для экспериментов с FIGMA, а в fst-project-health верни все как было до этого!»

**Always** verify before emitting any HTML:

```bash
# 1. Check fst-project-health wasn't modified
grep -ri "figma" /root/.hermes/profiles/fst-control/skills/productivity/fst-project-health/
# Should return nothing

# 2. Check the deliverable reports weren't touched
ls -la /tmp/project_504-595_report.{html,md,docx} 2>/dev/null
# Should show untouched mtimes from earlier sessions

# 3. Confirm the stage workspace is isolated
test -d /tmp/figma_<stage>/ && echo "Stage dir isolated — OK"
```

If any of these fail, stop and use `/tmp/figma_<stage>/` instead.

## Diagnostic recipe

When the user says "the Figma import looks wrong":

```bash
# 1. Get current state
python3 scripts/extract_figma_components.py --file-key=KEY --frame-id=ID

# 2. Compare emitted HTML against original data dict
diff <(python3 -c "import json; print(json.dumps(data, indent=2))" \
       < api_responses/data.json) \
     <(python3 -c "import json; print(json.dumps(data, indent=2))" \
       < api_responses/components.json)

# 3. Check for known pitfalls:
#    - P5: instances in Collapsed? → ask user to switch to Expanded
#    - P3: layer names start with `div#`, not `div.`
#    - P4: property names "Property 1"?
#    - P6: components.json empty? → check extract_figma_components.py walked the tree
```

When the user attaches an image-etalon (screenshot/PDF of the desired output):

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

## V6 convergence pattern (from 2026-08-21)

The v5 → v6 iteration with user feedback demonstrates the full convergence loop:

1. v5: emit HTML from extracted Figma structure (literal extraction, including Figma's quirks)
2. User iterates manually in Figma — renames properties, shrinks columns, deletes layers
3. Re-extract: get the new state (P13 wrapper detection, P15 case-insensitive variant match)
4. User provides **image-эталон** of desired output
5. v6: reconcile Figma extraction vs etalon:
   - Take column count + header names from Figma (user-driven structural change)
   - Take colors and texts from etalon (P18)
   - Recalibrate widths per table (P12)
   - Substitute real project data (no placeholders)
   - Default sections 4–7 to collapsed (P19)
6. Deliver `report_<code>_v6.html` as MEDIA
7. Verify `fst-project-health` untouched (P23)

## Scripts inventory

The skill ships reusable scripts (in `scripts/`) plus a working reference example at `/tmp/figma_v5/`:

| Script | Purpose |
|--------|---------|
| `extract_figma_components.py` | Walk Figma document, dump COMPONENT_SETs + INSTANCES to JSON |
| `build_html_with_placeholders.py` | Generate HTML with `{{TOKEN}}` placeholders from a Python data dict |
| `build_html_from_components.py` | Re-emit HTML from extracted components.json (substituting real data) |
| `calibrate_html_widths.py` | Self-check that row sums match canvas width |
| `inspect_figma_file.py` | One-shot dump of a Figma file: pages, top-level frames, COMPONENT_SETs + variant summaries — used to verify state before extraction (e.g. after the user reports a change) |
| `validate_html.py` | Pretty-print the structure of a generated HTML: tables, tbody rows, placeholder count, sum-of-widths per row, broken layout warnings |

## Reference files

| File | Purpose |
|------|---------|
| `references/figma-html-export.md` | Detailed direction A: HTML structure, widths, indicators, color tokens |
| `references/figma-component-extraction.md` | Detailed direction B: COMPONENT_SET walk, variant mapping, JSON shape |
| `references/figma-html-render-rules.md` | Live-probe notes: what html.to.design keeps / drops, plus loss budget |
| `references/working-example-figma-v5.md` | Annotated walkthrough of `/tmp/figma_v5/` — the working example from 504-595 / Report 5 |

## Templates

| File | Purpose |
|------|---------|
| `templates/report.html.j2` | Starter HTML template with all placeholders, inline-flex, sum-1562 layout |

## Working example — `/tmp/figma_v5/`

The living example from 2026-08-21. Use it as the canonical shape when starting a new `/tmp/figma_<stage>/` workspace:

```
/tmp/figma_v5/
├── html/
│   ├── report_504-595_v5.html    # direction A output: HTML with {{...}} placeholders
│   └── report_504-595_v6.html    # direction B/C output: real-data HTML after extraction
├── scripts/
│   ├── extract_tables.py         # one-shot extractor used to build tables.json
│   └── build_html_v6.py          # direction B: rebuild HTML from tables.json + DATA dict
├── api_responses/
│   ├── file.json                 # full get_file response (large; archive before re-running)
│   ├── nodes.json                # targeted get_nodes for variant components
│   ├── tables.json               # parsed table shape: {table_name: {summary, head, row}}
│   └── tables_v6.json            # v6: widths recalibrated after column-count change
└── README.md (or references/)   # local notes about this stage
```

## What this skill is NOT

- This is **not** a general Figma API tutorial. Use the `figma-api-import` skill (default profile) for that.
- It is **not** a `fst-project-health` extension. The source skill lives at `~/.hermes/profiles/fst-control/skills/productivity/fst-project-health/`. Modifying it from a FIGMA bridge session is the cardinal sin of this workflow.
- It does **not** create Plugin code. Figma Plugins use a different SDK and a separate auth flow — out of scope.

## Known limitations

- Cannot rename `Property 1` programmatically. User must rename in Figma UI.
- Cannot extract `fills` from `<g>` SVG groups (irrelevant for HTML reports but possible future need).
- Variant names are case-sensitive and depend on what the user typed in Figma. Extractor normalises `Expanded`/`expanded` and `Collapsed`/`collapsed` but not other variants.
- `width` and `height` set on layers in Figma are NOT propagated through componentPropertyDefinitions; only fills, stroke, text, and visibility survive the instance binding. To preserve sizes across instances, set them on the parent frame in Figma manually.