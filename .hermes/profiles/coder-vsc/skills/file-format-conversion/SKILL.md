---
name: file-format-conversion
description: "Convert files between formats. Confirm target first."
version: 1.0.0
author: Hermes Agent + Nous Research
license: MIT
metadata:
  hermes:
    tags: [conversion, files, visual, pdf, document, image, excalidraw, ffmpeg, pandoc]
---

# File Format Conversion

Convert a file from one format to another (e.g. `.excalidraw` → PDF, `.docx` → `.md`, `.svg` → `.png`). This class of task is unusually failure-prone in headless / sandboxed environments because most reliable renderers (Chromium for canvas-based diagrams, LibreOffice for documents, ImageMagick for raster ops) need to be installed and verified to actually work — and silent failures (empty output, blank page, wrong file) are common.

## Procedure

1. **Identify the input format precisely.** `.excalidraw` (JSON) ≠ `.excalidraw.png` (image with metadata) ≠ `.excalidraw.svg`. Confirm before doing anything else.
2. **Confirm the target format and the deliverable shape** with the user before running anything. Visual conversions have many plausible paths; the user has a preference and you will not guess it. Ask one question, with named options, instead of trying several approaches and getting corrected mid-stream.
3. **Probe the environment** for the likely-needed toolchain with a single `which` / `command -v` batch (e.g. `which node npm npx chromium chromium-browser google-chrome libreoffice ffmpeg magick convert pandoc`). Do NOT install anything yet — only inventory.
4. **Decide the path** based on (2) and (3). If the target is PDF and the renderer relies on a browser canvas, headless Chromium + screenshot + `pdf-lib` is the most reliable; if it relies on document rendering, `libreoffice --headless --convert-to pdf`; for SVG/raster, `magick` / `rsvg-convert`. State the chosen path to the user in one line.
5. **Execute once, then VERIFY the output** (file size sanity check, `pdfinfo` page count, `identify` dimensions, or a `vision_analyze` call on a rasterized page). A PDF that is 10 KB and 1 page is almost certainly empty — catch it before reporting success.
6. **Report result with handle**: absolute path, file size, page count (for PDFs), and a one-line note of how the user can re-open it.

## Load-this-skill gate (READ FIRST, before any tool call)

If the user's request matches any of these, **load this skill via `skill_view name="file-format-conversion"` before the first `terminal`, `write_file`, or browser navigation** — not after you've already started building a renderer:

- "convert X to Y", "X в Y", "сделай из X Y", "преврати X в Y" where X is `.docx`, `.pdf`, `.md`, `.svg`, `.png`, `.jpg`, `.excalidraw`, `.pptx`, `.xlsx`, `.odt`, `.heic`, `.mov`, `.mp4`, `.gif`, `.wav`, `.mp3`
- Any request mentioning Excalidraw, Figma, draw.io / diagrams.net, mermaid
- "transcribe / extract text from PDF / image"
- "PDF из этого", "Word из markdown", "картинку из SVG"

Why: this skill encodes the failure modes (multi-canvas screenshots, empty PDFs from `page.pdf()`, `waitForFunction` timeouts, silent installation of 300 MB Chromium) that waste 5–15 minutes per attempt when hit cold. The skill is the *first* thing that should be on screen, not the *autopsy* of what went wrong.

## Hard rules

- **Never silently swap the deliverable.** If you produced an intermediate PNG because `page.pdf` failed, that's a different artifact than what was asked. The user has the right to refuse the substitution; do not present it as a feature.
- **Never iterate past the second failed approach without asking.** Two strategies that failed is the threshold for re-checking with the user, not for trying a third variation. The user is paying the latency, not you.
- **Never claim success on a suspiciously small output file.** PDFs of 10–30 KB from a multi-element source are almost always empty canvases / blank pages. Always verify size + page count + visual sample.
- **If no reliable path exists on this environment, say "I don't have a working method"** — not "let me try one more thing." Honest no is better than presenting an untested guess as best practice.
- **If the user says "не нужен [intermediate format]" or "стоп"** — stop immediately and clean up any scratch files you created. Do not leave failed output artifacts in shared directories.

## Pitfalls

- **Headless Chromium does not print canvas content via `Page.printToPDF` reliably.** Excalidraw, Figma-rendered SVG, canvas-based diagrams all hit "Printing failed" or produce blank PDFs. Use `page.screenshot()` → embed PNG into a `pdf-lib` document, not `page.pdf()`.
- **`page.screenshot()` on Excalidraw screenshots the LARGEST canvas by default — but the right one is the visible `document.body` region, not a single `<canvas>`.** Excalidraw stacks 3-4 canvases (background grid, scene, interactive layer, UI overlay). `page.screenshot()` clips to the viewport (which works), but if you try to read pixels via `getImageData` on a *single* canvas you will pick the wrong layer (background grid = mostly white, scene = actual content, interactive = null until interaction). Always screenshot the whole page via `page.screenshot({ clip: { x, y, width, height } })` matching the document size you set in the viewport — never rely on per-canvas pixel sampling to decide readiness.
- **Excalidraw's `viewModeEnabled: true` hides the toolbar visually but `zenModeEnabled: true` and `gridModeEnabled: false` interact non-trivially with `initialData` timing.** If `initialData.elements` is set but `appState` is missing or empty, Excalidraw may reset zoom/pan to default, hiding the content off-screen. Always pass a non-empty `appState` object alongside `elements`, and screenshot the full viewport (not just the first 200×200 region) to catch content rendered off-screen.
- **Waiting for canvas render by `waitForTimeout` is fragile.** Use `waitForFunction` that polls `getImageData` for non-white pixels in the central region. UI chrome alone can fool a 1.5-second `setTimeout`-based readiness signal.
- **Excalidraw does NOT auto-render to the topmost canvas.** It uses multiple stacked canvases (background, scene, interactive, UI overlay). Screenshot the document via the visible page region, not via `getImageData` on a single canvas — that picks the wrong layer.
- **Excalidraw in `viewModeEnabled: true` still draws UI overlays** ("Canvas actions", zoom controls, help icon). Hide them via `display:none` on `.layer-ui__*`, `.Island`, `[class*="zoom"]`, `[class*="zen"]` BEFORE screenshotting, or the screenshot will include the toolbar chrome.
- **Installing Playwright + Chromium = ~300 MB download.** If the user just asked to convert a single file, propose the install BEFORE doing it; this is a long-lived change to the environment, not an ephemeral scratch.
- **`pdf-lib` only embeds images; it does not render SVG or HTML.** If your source renders to SVG (e.g. via `exportToCanvas` / `exportToSvg`), you still need a raster step (e.g. `resvg` or headless Chrome) to get to a bitmap for embedding.
- **Never claim "I have a working method" based on a path you merely proposed.** Only confirm after `verify`-step passes (file size, page count, vision check).

## Decision table: which tool for which source

| Source | Target | Best path on Linux | Fallback |
|---|---|---|---|
| `.excalidraw` (JSON) | PDF | Playwright + headless Chromium → render in `react-dom`, screenshot, embed with `pdf-lib` | `@excalidraw/excalidraw` + `exportToSvg` → resvg/Chrome → pdf-lib |
| `.docx` / `.odt` | PDF | `libreoffice --headless --convert-to pdf` | `pandoc` (limited layout fidelity) |
| `.md` | PDF | `pandoc` + `wkhtmltopdf` or `weasyprint` | `pandoc` → `latex` → `pdflatex` |
| `.svg` | PNG/PDF | `rsvg-convert` / `magick` / `resvg` | Chrome headless `page.pdf()` (works for SVG, unlike canvas) |
| Image (PNG/JPG) | PDF | `magick` or `img2pdf` (img2pdf preserves quality, no re-encode) | `pdf-lib` (embed image) |
| Video → frames / GIF | image | `ffmpeg` (already ubiquitous) | n/a |
| HTML → PDF | PDF | Chrome headless `page.pdf()` (works here) | `weasyprint` |
| `.excalidraw.png` | elements (reverse) | Decode `excalidraw` payload from PNG metadata | — (not common) |

## Quick environment probe (paste as-is)

```bash
which node npm npx chromium chromium-browser google-chrome \
      libreoffice soffice ffmpeg magick convert pandoc \
      rsvg-convert resvg wkhtmltopdf weasyprint \
      python3 pip 2>&1
```

If everything is missing for a Chromium-canvas task, **stop and ask** — installing a 300 MB dependency for a one-shot conversion is a user decision, not yours to make silently.

## When to give up honestly

- Two different render strategies both produced wrong/empty output → stop, tell the user you have no working method, suggest the user run the conversion in their own GUI tool or via a hosted service.
- The conversion requires a browser feature that headless Chromium does not implement → say so specifically (e.g. "this needs WebGPU, which headless Chromium 153 does not support"). Don't bury the limitation in a generic "it didn't work."
- The file is malformed in a way that no renderer can recover from → say "the file is not parseable as <format>" and ask whether the user has an alternative source.
