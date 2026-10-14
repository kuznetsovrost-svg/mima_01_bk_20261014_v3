# Direction A: Hermes → Figma (HTML with placeholders)

Detailed procedure for generating HTML that survives the round-trip through `html.to.design` (or Anima / Builder.io).

## When to use

Direction A applies when:

- The user has Python data (parsed from MD report, MCP response, or JSON dump) and wants to hand it off to a designer in Figma
- The designer will manually convert each section into a `COMPONENT_SET` with `State=Expanded|Collapsed` variants
- The designer wants placeholder text (e.g. `{{S3_R1_NAME}}`) so they can see the shape without committing to copy yet

## HTML structure that survives html.to.design

`html.to.design` (free version) imposes these constraints — learn them or the import will silently break:

| Constraint | Reason | Workaround |
|-----------|--------|------------|
| No CSS variables (`--bg: #2563EB`) | Plugin's CSS parser doesn't resolve custom properties | Use literal hex (`#2563EB`) |
| No `position: absolute` for layering | Plugin reinterprets as flex child → stretches to parent width | Use `inline-flex` with explicit `width`/`height`/`flex-shrink: 0` |
| No `display: grid` for column layouts | Plugin collapses to flex | Use `display: flex` + explicit `width` on each cell |
| No `<table>` for layout (use it for tabular data) | Plugin handles `<table>` correctly if you want real borders/headers | OK in body, but layers don't survive `Auto-layout` |
| No emoji glyphs in text content | Plugin renders tofu (□) on import | Use text labels (e.g. `🔴 Красный` becomes `[red] Красный`) |
| No HTML comments in critical positions | Plugin may strip or keep; non-deterministic | Move comments above/outside `<body>` |

## Canvas calibration

**Default canvas width: 1562px** for the project-health report.

Rule: every `<tr>`>'s cells must sum exactly to 1562. Add a self-check before handing off.

### Quick calibration

```python
def calibrate_row(row):
    widths = re.findall(r'width:\s*(\d+)px', row)
    total = sum(int(w) for w in widths)
    return total == 1562
```

If a row fails, redistribute the leftover pixels to the widest column.

## Indicator placement

The round verdict indicator (160×160 circle) MUST be a flex sibling of the title block, not absolutely positioned.

```html
<!-- ❌ breaks: -->
<div class="report-header" style="position: relative;">
  <div class="indicator" style="position: absolute; right: 24px; top: 20px;">...</div>
</div>

<!-- ✅ survives: -->
<div class="report-header" style="display: flex; align-items: center; gap: 24px;">
  <div class="report-header-text" style="flex-grow: 1;">title + project + meta</div>
  <div class="indicator" style="width: 160px; height: 160px; flex-shrink: 0;">{{INDICATOR_TEXT}}</div>
</div>
```

## Color palette (Figma-aligned)

```
--bg-appbar:       #2563EB
--bg-header-light: #DBEAFE   (table summary default — NOT for top header)
--bg-summary-grey: #F3F4F6   (use this for table summaries that should be neutral)
--bg-summary-sick: #FCA5A5
--bg-summary-warn: #FEF3C7
--bg-row-critical:  #FEE2E2
--bg-row-warning:  #FEF3C7
--bg-row-healthy:  #DCFCE7
--bg-row-neutral:  #F9FAFB
--text-on-appbar:  #FFFFFF
--text-critical:   #991B1B
--text-warning:    #92400E
--text-healthy:    #166534
--text-neutral:    #232326
--border:          #D1CFD7
```

## Table summary — pick one

User feedback 2026-08-21: "Заголовки таблиц (summary) должны быть серыми, а не синими." So:

- Default summary: `background: #F3F4F6; color: #4B5563`
- Use `sick` summary (`#FCA5A5`) ONLY for the financial section (Section 6)
- Avoid the yellow summary (`#FEF3C7`) — it conflicts with row background for warnings

## Real working example: `/tmp/figma_v5/`

```
/tmp/figma_v5/
├── html/
│   └── report_504-595_v6.html   ← 13.8 KB, 5 tables, sum=1562 verified
├── scripts/
│   └── build_html_v6.py         ← generator with calibrate_widths() inline
└── api_responses/
    ├── tables_v6.json          ← extracted table data
    └── nodes_v6.json           ← raw Figma snapshot
```

## Checklist before shipping HTML to user

- [ ] Every `<tr>`'s cell widths sum to 1562
- [ ] No `position: absolute`
- [ ] No CSS variables
- [ ] No emoji glyphs in table cells
- [ ] Indicator is `inline-flex` with explicit `width: 160px; height: 160px`
- [ ] All 7 table-summary rows are grey (`#F3F4F6`), except Section 6 which is sick-red
- [ ] Hand off as MEDIA: file (not the raw script)

## Known good template

`/tmp/figma_v5/html/report_504-595_v6.html` — the most recent stable version. Use it as a reference if you're unsure about any structural decision.