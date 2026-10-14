# Verified Bento Deck — Template Recipe

This is the **structure** of a 10-slide deck that worked end-to-end (verified:
opened in browser, all morph transitions played, PDF exported cleanly, file
~700 KB). Use as scaffolding — copy, rename slides, swap content.

The literal 10-slide demo lives at `/tmp/bento-slides-deep/deck.json`
(topics: Knowledge Garden) — usable but topic-specific. This template is
**structural** and survives any subject.

## Recipe: 10-slide Bento deck

```
slide 1   cover         morph-targets: headline, bar (kicker label)
slide 2   question      morph from s1 (headline moves up, bar becomes vertical line)
slide 3   comparison    HTML table with one row highlighted (Knowledge Garden row)
slide 4   anatomy       3 boxes side by side, each with title+body text
slide 5   chart         bar chart, plain-numbers data
slide 6   code-snippet  mono font, on dark rect background
slide 7   diagram       shapes-only composition (no real photos)
slide 8   STATE SLIDE   stateOf="s7", name="DETAIL", link back via dismiss rect
slide 9   roadmap       4 numbered phases, each w/ title + body
slide 10  CTA           morph back to cover motif
```

The morph **thread** runs through slides 1→2→10 (headline + bar ids stay
constant). Other transitions: `none` on interior slides, `fade` or `morph`
on section breaks.

## Theme stub (paste into `theme`)

Use this as the dark-pitch default. Swap `accent` to whatever brand color.

```json
{
  "background": "#0E1116",
  "color": "#E8E6DE",
  "accent": "#7A5CFF",
  "accent2": "#FF9E8A",
  "fontFamily": "system-ui, sans-serif"
}
```

## Canonical morph IDs (declare these on slides 1, 2, 10 at minimum)

```json
{"id": "kicker",   "type": "text", ...}     // small uppercase label on slide 1
{"id": "headline", "type": "text", ...}     // big title on slides 1, 2, 10
{"id": "bar",      "type": "shape", "shape": "rect", ...}  // accent bar
```

Keep `bar`'s `fill` the same color across slides (morph tweens size/position
but the fill tracks too). Width/height/rotation/opacity are the tweenable
properties.

## Element copy-paste blocks

**Cover kicker (top-left label)**

```json
{
  "id": "kicker",
  "type": "text",
  "x": 96, "y": 196, "w": 400, "h": 36,
  "html": "KNOWLEDGE GARDEN \u00b7 v1.0",
  "fontSize": 22, "fontFamily": "system-ui, sans-serif",
  "fontWeight": 600, "color": "#FF9E8A",
  "align": "left", "valign": "top",
  "letterSpacing": 2, "lineHeight": 1
}
```

**Headline (used on s1, s2, s10 — same id, three different layouts)**

```json
{
  "id": "headline",
  "type": "text",
  "x": 96, "y": 248, "w": 1088, "h": 200,
  "html": "Big claim here.",
  "fontSize": 120, "fontFamily": "system-ui, sans-serif",
  "fontWeight": 900, "color": "#E8E6DE",
  "align": "left", "valign": "top",
  "lineHeight": 1
}
```

On s2, keep id="headline" but move `y` up, lower `fontSize`, narrow `w`.
On s10, move it back to y:248 with full original geometry.

**Bar (the morph glue)**

```json
{
  "id": "bar",
  "type": "shape", "shape": "rect",
  "x": 96, "y": 470, "w": 320, "h": 6,
  "fill": "#7A5CFF", "stroke": "none", "strokeWidth": 0,
  "radius": 3, "rotation": 0, "opacity": 1,
  "fx": {"loop": {"type": "dash-march", "distance": 18, "duration": 1.4}}
}
```

`dash-march` makes the cover bar visibly animate. Requires
`strokeStyle: "dashed"` — and **note**: the skill's chart-inventory is
silent on this, but plain `rect` with dash-march needs `stroke` set to a
non-zero dash pattern; for visual safety use the snippet above (solid bar
+marching animation reads as motion even if the dash is invisible).

## Comparison table (slide 3)

```json
{
  "id": "tbl",
  "type": "table",
  "x": 96, "y": 230, "w": 1088, "h": 360,
  "header": true,
  "columns": [{"w": 1.5}, {"w": 2}, {"w": 1.5}, {"w": 1}],
  "rows": [
    {"cells": [
      {"html": "Option", "bold": true},
      {"html": "Works offline?", "bold": true},
      {"html": "Interactive?", "bold": true},
      {"html": "Self-contained?", "bold": true}
    ]},
    // ... more rows ...
    // The "winner" row gets {"color": "#7A5CFF", "bold": true} on its cells
  ],
  "style": {
    "headerBg": "#1A1F26",
    "headerColor": "#E8E6DE",
    "borderColor": "rgba(232,230,222,0.10)",
    "borderWidth": 1,
    "cellPadX": 16, "cellPadY": 14,
    "fontSize": 17, "color": "#94A3B8",
    "radius": 8,
    "zebra": "rgba(255,255,255,0.02)"
  }
}
```

## Bar chart (slide 5) — plain numbers, no ECharts-object syntax

```json
{
  "id": "chart",
  "type": "chart",
  "x": 96, "y": 250, "w": 1088, "h": 380,
  "rotation": 0, "opacity": 1,
  "preset": "bar",
  "option": {
    "xAxis": {"type": "category", "data": ["A", "B", "C"]},
    "yAxis": {"type": "value", "axisLabel": {"color": "#94A3B8"}},
    "grid": {"left": 60, "right": 30, "top": 20, "bottom": 30},
    "series": [{
      "type": "bar",
      "data": [12, 39, 87],
      "itemStyle": {
        "color": "#94A3B8",
        "borderRadius": [6, 6, 0, 0]
      },
      "barWidth": 120
    }],
    "tooltip": {"trigger": "item", "formatter": "{b}: {c}"}
  },
  "fx": {"enter": "fade-up"}
}
```

Wrong: `{"value": 12}` — chart engine coerces to 0. Use plain numbers only.

## Code-snippet rect (slide 6)

```json
{
  "id": "code-bg",
  "type": "shape", "shape": "rect",
  "x": 96, "y": 270, "w": 1088, "h": 200,
  "fill": "#1A1F26",
  "stroke": "rgba(232,230,222,0.10)", "strokeWidth": 1,
  "radius": 12, "rotation": 0, "opacity": 1
},
{
  "id": "code",
  "type": "text",
  "x": 128, "y": 304, "w": 1024, "h": 144,
  "html": "$ command --flag arg \n # comments",
  "fontSize": 22,
  "fontFamily": "ui-monospace, 'SF Mono', Monaco, Consolas, monospace",
  "fontWeight": 400, "color": "#E8E6DE",
  "align": "left", "valign": "top", "lineHeight": 1.5
}
```

## State-slide (slide 8) — drill-down from slide 7

The parent slide holds a clickable element with `link`:

```json
{"id":"node","type":"shape","shape":"ellipse","x":380,"y":320,"w":90,"h":90,
 "fill":"#e57373","stroke":"#7A5CFF","strokeWidth":3,
 "link":"state-detail"}
```

The state slide:

```json
{
  "id": "state-detail",
  "stateOf": "parent-slide-id",
  "transition": "morph",
  "name": "DETAIL",
  "elements": [
    // transparent dismiss rect that catches clicks to return
    {"id":"dismiss","type":"shape","shape":"rect","x":0,"y":0,"w":1280,"h":720,
     "fill":"rgba(0,0,0,0)","stroke":"none","strokeWidth":0,
     "radius":0,"rotation":0,"opacity":1,
     "link":"parent-slide-id"},

    // the actual detail content (kicker + headline + body + back hint)
    {"id":"kicker","type":"text","x":96,"y":96,"w":400,"h":36,
     "html":"NODE DETAIL","fontSize":20,"fontWeight":600,"color":"#FF9E8A",
     "letterSpacing":2},
    {"id":"headline","type":"text","x":96,"y":160,"w":1088,"h":120,
     "html":"Subject name","fontSize":96,"fontWeight":900,"color":"#E8E6DE",
     "lineHeight":1},
    {"id":"bar","type":"shape","shape":"rect","x":96,"y":300,"w":100,"h":4,
     "fill":"#7A5CFF","stroke":"none","strokeWidth":0,"radius":2},
    {"id":"body","type":"text","x":96,"y":340,"w":700,"h":200,
     "html":"Long body paragraph.","fontSize":22,"color":"#94A3B8",
     "lineHeight":1.6},
    {"id":"hint","type":"text","x":96,"y":640,"w":1088,"h":36,
     "html":"\u2190 Press Esc or click empty space to return",
     "fontSize":16,"color":"#7A5CFF"}
  ]
}
```

The shared `id` between parent and state (`headline`, `bar`) means morph
fires when entering the detail view.

## Step 1 → always do this before authoring

```python
import subprocess
# Cache the runtime file ONCE per session — don't re-download every slide.
subprocess.run(['curl', '-fsSL',
    'https://bento.page/releases/slides/Bento_Slides.bento.html',
    '-o', '/tmp/bento-runtime.bento.html'], check=True)
```

If the curl fails (offline), `/tmp/bento-runtime.bento.html` from a prior
session works. The runtime version rarely changes; if `format: bento/slides`
in the doc is current, the runtime will be compatible.

## Step 2 → write the JSON, escape, inject

Use the helpers in `scripts/bento_io.py`:

```python
import sys, json
sys.path.insert(0, '/root/.hermes/skills/creative/bento-slides-decks/scripts')
from bento_io import load_doc, save_doc

# If editing a fresh runtime:
doc = {
  "format": "bento/slides", "version": 1, "title": "Topic",
  "size": {"width": 1280, "height": 720},
  "theme": {...},
  "slides": [...]
}

# Compose path:
import shutil
shutil.copy('/tmp/bento-runtime.bento.html', '/tmp/output.bento.html')
save_doc('/tmp/output.bento.html', doc)
```

The helper handles `<` → `\u003c` escaping and the regex replacement. It
asserts exactly one `<bento-doc>` block was found and replaced.
