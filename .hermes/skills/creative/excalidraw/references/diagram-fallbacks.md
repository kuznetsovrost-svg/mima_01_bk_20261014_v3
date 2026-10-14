# Diagram fallbacks for non-Latin scripts

Use this when the diagram must contain Cyrillic (Russian, Ukrainian, Bulgarian, etc.), CJK, Arabic, Hebrew, or any non-Latin script and you need a rasterized PNG/SVG deliverable. Excalidraw's headless renderer cannot serve these scripts — see the pitfall in `SKILL.md`.

## The reliable path: SVG + system fonts + headless chromium

The Linux server has `DejaVu Sans`, `Liberation Sans`, and `FreeSans` with full Cyrillic, CJK, and Arabic coverage. Wrap a hand-written SVG in a minimal HTML page and let chromium render it.

### SVG template (system-font, viewBox-driven, no JS)

```python
# Save as scripts/svg_diagram.py — produces SVG + PNG
import sys, subprocess, os
from pathlib import Path

svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1000" width="1600" height="1000">
<style>
  text { font-family: "DejaVu Sans", "Liberation Sans", sans-serif; fill: #1e1e1e; }
  .title { font-size: 28px; font-weight: bold; }
  .subtitle { font-size: 16px; fill: #666; }
  .label { font-size: 14px; }
  .node-name { font-size: 16px; font-weight: bold; text-anchor: middle; }
</style>
<rect width="100%" height="100%" fill="#ffffff"/>

<text class="title" x="800" y="35" text-anchor="middle">Заголовок диаграммы (кириллица ОК)</text>

<!-- Group of colored nodes with Russian labels -->
<rect x="200" y="120" width="200" height="80" fill="#a5d8ff" stroke="#4a9eed" stroke-width="2" rx="6"/>
<text class="node-name" x="300" y="155">Узел 1</text>
<text class="label" x="300" y="180" text-anchor="middle">описание</text>

<!-- ... more nodes ... -->
</svg>'''

out_svg = Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/diagram.svg')
out_svg.write_text(svg, encoding='utf-8')

# Wrap in HTML for headless rendering
html_path = Path(str(out_svg) + '.html')
html_path.write_text(
    f'<!DOCTYPE html><html><head><meta charset="utf-8">'
    f'<style>body{{margin:0;padding:0}}</style></head>'
    f'<body>{svg}</body></html>',
    encoding='utf-8'
)

# Render with headless chromium
chromium = '/root/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome'
out_png = Path(str(out_svg).replace('.svg', '.png'))
subprocess.run([
    chromium,
    '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars',
    '--window-size=1600,1000', '--virtual-time-budget=3000',
    f'--screenshot={out_png}',
    f'file://{html_path}',
], check=True, timeout=60)
print(f'OK: {out_svg} ({out_svg.stat().st_size} B) and {out_png} ({out_png.stat().st_size} B)')
```

Run: `python3 scripts/svg_diagram.py /tmp/my-diagram.svg` — produces both `.svg` (vector, edit-friendly) and `.png` (raster, ready to send).

## When to use which approach

| Need | Approach | Why |
|---|---|---|
| Interactive editing later (user opens at excalidraw.com) | `.excalidraw` file as primary | only format Excalidraw can edit |
| Headless PNG/SVG with Cyrillic or CJK text | **SVG + system fonts + chromium** | Excalidraw's font subset fails non-Latin in headless |
| Web-embeddable interactive diagram | Excalidraw + full runtime | needs JS bundle |
| Static report / Telegram attachment | **SVG + PNG** | universal, no dependencies |
| Multi-language diagram in same image | **SVG** | one file, multiple scripts |

## Why this isn't in the main SKILL.md

`SKILL.md` covers Excalidraw JSON construction. This file is the fallback when the user needs a non-Latin PNG deliverable and Excalidraw's runtime can't render it headless. Keep both — `.excalidraw` for the edit-format, `.svg`/`.png` for the deliverable.

## Headless chromium on this machine

- Path: `/root/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome`
- Auto-installed by Playwright (already on disk — do NOT reinstall)
- Supports `--screenshot=` for one-shot PNG
- `--virtual-time-budget=Nms` lets async JS settle before the screenshot fires
- For multi-page output, use Playwright/Puppeteer (not installed by default — only escalate if `--screenshot` is insufficient)
