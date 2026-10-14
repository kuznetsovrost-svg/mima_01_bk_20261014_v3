---
name: bento-slides-decks
description: "Author and edit single-file `.bento.html` slide decks in the Bento/Slides JSON format. Use when the user asks for a 'bento slides', 'bento deck', '.bento.html', 'single-file presentation', 'self-contained HTML deck', or wants to write into the `#bento-doc` JSON block of an existing Bento file (with `format: bento/slides`). Covers the document schema (slides[], elements, transitions), element types (text, shape, chart, table, image, media, svg, connector), the morph transition system (shared `id` or `morphId` + `transition: morph`), motion primitives (ken-burns, dash-march, motion-path, countUp, fade-up), hidden state slides (`stateOf` + `link`), UI strings, and the constraint that all runtime blocks must remain untouched. Includes a verified first deck template that worked end-to-end."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [bento, slides, presentations, single-file, html, json, deck]
    category: creative
    related_skills: [claude-design, powerpoint, excalidraw]
---

# Bento/Slides Decks

Author and edit `.bento.html` files — the format where one HTML file is the
document + viewer + editor + presenter. The author wrote the tool because
their team kept building decks as web frontends via Claude Code and hit a
loop on every small edit: the format is plain JSON living in one plaintext
block near the top, so any assistant that can read and write a file can
edit the deck. No plugin, no API, no MCP server — the file is the API.

## When this skill activates

Use this skill when the user asks for:

- "A bento slides deck", "a bento deck", "make a `.bento.html`"
- "Self-contained HTML presentation"
- "Generate a deck, then I'll open it in a browser"
- "Edit the JSON inside my .bento.html" / "add a slide about X to my existing bento"
- A deck that should animate between slides (morph), have inline charts, or
  do drill-down via click-to-state — features that pull their weight vs
  PowerPoint's overhead

Do NOT use for:

- `.pptx` deliverables → use `powerpoint`
- Markdown slide aesthetics (slidev, reveal.js from markdown) — wrong stack
- Decks the user wants to host on a real web server with auth — file-format
  is wrong fit, use the deck source in a repo and serve it

## What a .bento.html actually is

```html
<script type="application/bento+json" id="bento-doc">
  {"format": "bento/slides", ...}
</script>
<script id="bento-rt-css" type="bento/deflate-b64">…</script>
<script id="bento-rt" type="bento/deflate-b64">…</script>
```

- `<bento-doc>` — **the only block you ever edit**. JSON in a
  `<script type="application/bento+json">` block. The rest is read-only.
- `bento-rt-css` and `bento-rt` — compiled runtime, deflate-base64. **NEVER
  modify or re-encode** — opening a deck where these changed surfaces a
  user-confusing "broken" feel because the runtime version no longer matches
  the bento-doc format.
- Empty `<bento-doc>` is fine — opened in browser, the runtime mints a
  showcase deck to onboard a new user.
- **Escape every `<` in the JSON as `\u003c`** so the JSON block can't
  accidentally contain `</script>`. Re-emit the whole block when you save.

## Mandatory shape

A minimal valid document requires `size`, `theme.fontFamily`, and one slide.
Without these the app refuses to boot:

```json
{
  "format": "bento/slides",
  "version": 1,
  "title": "My deck",
  "size": {"width": 1280, "height": 720},
  "theme": {
    "background": "#101418",
    "color": "#F2F0EA",
    "accent": "#FF9E8A",
    "fontFamily": "system-ui, sans-serif"
  },
  "slides": [{"id": "s1", "background": "#101418", "elements": []}]
}
```

## Element types (all share `id, x, y, w, h, rotation, opacity`)

- `text` — `html` (inline `<b>/<i>/<br>`), `fontSize`, `fontFamily`,
  `fontWeight`, `color`, `align`, `valign`, `lineHeight`,
  `letterSpacing`. `role: title | subtitle | body | kicker` for layouts.
- `shape` — `shape: rect|ellipse|triangle|arrow|line|path`,
  `fill`, `stroke`, `strokeWidth`, `radius` (rect corners).
  `fillGradient: {angle, stops:[{at:0..1, color}]}`.
  Lines take colour from `fill` (stroke is what morphs tween); draw
  horizontally across the box, rotate for vertical. Path uses `d` +
  `pathBox: [x,y,w,h]`. Connector is line/path with `from/to: {el, side}`.
  `strokeStyle: solid|dashed|dotted`; tips `lineStart/lineEnd:
  arrow|dot|bar`.
- `image` — `src: data:URI | "asset:<key>"` (assets in `doc.assets`),
  `fit: cover|contain|fill`, `radius`. Self-contained files embed
  as data URIs.
- `chart` — `preset: bar|line|pie|scatter`, `option` is ECharts-shaped
  pure JSON. **Bar/line data must be plain numbers** (`{value}` objects
  coerce to 0 — only pie accepts `{name, value}`). `label:` on bar/line
  does NOTHING (pie-only). Dual axis: `yAxis: [axis1, axis2]` +
  `yAxisIndex: 1` per series. Engine is charts-lite, NOT ECharts — keys
  not listed in the parent skill's chart inventory are silently dropped.
- `table` — `columns: [{w}]` fractional widths, `rows:
  [{cells:[{html, align?, color?, bg?, bold?}]}]`, `header: bool`,
  `style: {headerBg, headerColor, zebra, borderColor, borderWidth,
  cellPadX, cellPadY, fontSize, color, radius}`. Renders as a real HTML
  table — best for spec/pricing grids, NOT for numeric trends.
- `svg` — `asset` or `markup`; prefer composing shapes from rects/texts/
  paths so elements stay editable and morph-able.
- `media` — `kind: video|audio`, `src: data:URI|url|"asset:..."`,
  `poster` (video), `controls`, `autoplay`, `loop`, `muted`. **Autoplay
  only fires in present mode**, and browsers REQUIRE `muted:true` for
  autoplay. Embed short clips; host long ones and link via URL.

## Motion: morph (the signature feature)

Slide A: `{ "id":"s1", "transition":"none", "elements": [...]}`
Slide B: `{ "id":"s2", "transition":"morph", "elements": [...] }`

Any element with the same `id` (or `morphId`) on both slides tweens
between them: position, size, color, gradients, opacity. **Replay**
just works — press ← then → and the motion reverses.

Use `morphId` (`"morphId": "running-head"`) to pair independently-named
elements across slides without mutating `id`. `id` stays the stable
identity for selection, anchor references, CRDT node keys.

**Entrance skip on morph:** elements with a morph partner on the previous
slide skip `fx.enter` and `fx.countUp` — they're already mid-motion.
Without `fx.enter`, an element with no partner gets an automatic fade-rise.

## Motion: ambient + loops

- `fx: { ambient: "kenburns", ken: {dir:"drift|out|in", scale: 1.08,
  duration: 22}}` — slow photo drift for hero slides. Pair with a
  full-bleed image + scrim rect + headline.
- `fx: { loop: { type: "dash-march", distance: 18, duration: 1.4 }}` —
  marching dashes on a stroke. **Requires `strokeStyle: dashed` or
  `dotted`**; on solid stroke, the tween runs invisibly.
- `fx: { loop: { type: "motion-path", path: "M0,0 C60,-40 140,40 200,0",
  duration: 6, ease:"none", speeds:[1,1] }}` — drift along path.
  `speeds` is per-anchor dwell multipliers; omit for constant pace.
  Never combine with entrance tweens — they fight over the same transform.
- `fx: { countUp: true }` — numbers tick up to final value.

## Interactivity (drill-down)

```json
// parent slide — clickable element:
{"id":"node","type":"shape","shape":"ellipse",...,"link":"state-ingest"}

// hidden state slide (arrow keys skip, ← returns):
{"id":"state-ingest","stateOf":"parent-slide-id","transition":"morph",
 "name":"INGEST","elements":[
   ...
   {"id":"dismiss","type":"shape","shape":"rect","x":0,"y":0,
    "w":1280,"h":720,"fill":"rgba(0,0,0,0)",..."link":"parent-id"}
 ]}
```

The dismiss rect fills the slide to catch clicks outside content.
`stateOf` makes the arrow-keys navigation skip the slide; only the
explicit `link` reaches it. Differentiate from `hidden: true` which
hides from PDF export and page numbering.

## Layout guardrails (1280×720 canvas)

- 96 px side margins (right-most x ≤ 1184)
- 2 cols at 528 px wide each, gutter 32 (x positions 96, 656)
- 3 cols at 340 px wide, gutter 34 (x positions 96, 470, 844)
- 4 cols at 254 px wide, gutter 24 (x positions 96, 374, 652, 930)
- 60/40 split: 624/432 at x 96, 752, gutter 32
- Title band `y:72 h:84`, content starts `y:208`
- One accent colour, max 2 typefaces
- Use full font stacks: `"'Fraunces', Georgia, serif"`, never a bare family
  name. A missing font falls back silently — verify with
  `window.bento.validate()` which reports `font-not-embedded`.

## Procedure: authoring or editing a deck

1. **Confirm the format and the file location.** If the user has an existing
   `.bento.html`, open it and check `format` in `<bento-doc>` matches
   `"bento/slides"`. If they have nothing, download the starter file:
   ```bash
   curl -fsSL https://bento.page/releases/slides/Bento_Slides.bento.html \
        -o "Topic.bento.html"
   ```
2. **Read the existing `<bento-doc>` block if editing.** Use regex extraction
   (the script tags span multiline); parse as JSON to verify validity before
   changing anything.
3. **Plan the slides first.** List every slide in plain words, then write
   each element. Pick the 1-2 morph transitions that earn their place (a
   stat that evolves, a logo that travels).
4. **Write the JSON document as a Python dict, dump it, then escape.**
   Build in Python or another structured way — hand-typing the JSON for
   multi-slide decks is where mistakes cluster.
5. **Place the escaped JSON into `<bento-doc>`.** Replace via regex:
   ```python
   new_doc = doc.replace('<', '\\u003c')
   content, n = re.subn(
       r'(<script[^>]*id="bento-doc"[^>]*>)\s*(</script>)',
       lambda m: m.group(1) + new_doc + m.group(2),
       template, count=1
   )
   assert n == 1, "must insert into exactly one bento-doc block"
   ```
6. **Sanity check before delivery:**
   ```bash
   python -c "import json; json.loads(open('Topic.bento.html').read()[
       content.find('</script>'.join([\">\", '', '<'])) : content.find('</' + 'script>')-1])"
   ```
   Or programmatically verify the bento-doc block parses and runtime blocks
   are still present.
7. **Open it.** The deck opens directly in a modern browser
   (`file://` works). Press `Esc` for the editor; click any node to see
   the editor surface; `Save ▾ → Copy document JSON` to extract for
   round-trip edits.

## Charts that won't bite you

When writing `chart.option`, remember that the engine ignores unknown keys
silently. Default to:

```json
{
  "preset": "bar",
  "option": {
    "xAxis": {"type": "category", "data": ["2024","2025","2026"]},
    "yAxis": {"type": "value"},
    "series": [{"type": "bar", "data": [12, 39, 87],
                "itemStyle": {"color": "#141310", "borderRadius": [6,6,0,0]},
                "barWidth": 90}],
    "tooltip": {"trigger": "item", "formatter": "{b}: {c}"}
  }
}
```

If user wants percentages with another series, dual axis:
`yAxis: [{type:"value"}, {type:"value", axisLabel:{formatter:"{value}%"}}]`
and `"yAxisIndex":1` on the odd series. Render as `line` over bars.

## Runtime console APIs (use during development)

- `window.bento.doc` — read current document
- `window.bento.loadDoc(json)` — replace (undoable)
- `window.bento.validate()` — returns `{ok, counts, findings: [{code,
  severity, message, slide?, element?, path?}]}`. Filter
  `severity !== 'info'` for actionable issues. Catches unknown property
  names, text overflow, off-canvas elements, broken `link`/`asset:`
  references, duplicate ids, morph-key collisions.
- `window.bento.measure({html, w, fontSize, lineHeight})` → `{height,
  width, lines, fits, overflow}` — pre-size text before placing it.

## Pitfalls

- **Touching the runtime blocks breaks the file.** `bento-rt-css` and
  `bento-rt` are deflate-base64 encoded versions of typed source. Do not
  re-encode or "tidy" them. Even whitespace changes invalidate the
  integrity check on next open.
- **`<` in JSON without `\u003c` escaping makes a future `</script>`
  close the block mid-document.** Always escape. The shared showstopper
  is a user pasting in a `<title>` tag they wrote themselves.
- **Inventing property names cost you silently.** Charts ignore unknown
  options, the renderer ignores unknown style keys. Validate with
  `window.bento.validate()` after generation.
- **`fx.loop` with `dash-march` requires dashed/dotted stroke**, not
  solid. The tween runs either way but only shows on dashed. Validate
  this by reading the slide, not by reasoning about JSON.
- **Empty `<bento-doc>` opened in browser auto-mints a showcase deck.**
  That's the onboarding affordance, not your document. To set up an
  empty canvas you want to write into, download the starter file and
  replace the block before opening.
- **Decks with live collaboration carry room credentials inside the
  JSON.** If reading a deck into context and you see `"collab"` with
  `ownerPriv/writerPriv/invite`, **stop and tell the user** before
  reading further — you've already taken the credentials. The remedy is
  `Share → Rotate keys`, not deletion.
- **Animation requires shared ids across slides AND matching
  `transition: "morph"` on the destination.** Both must be present, and
  the layout-id-on-slide-N must equal layout-id-on-slide-N+1. Don't
  forget the transition side.
- **`docId` is the document identity.** Never regenerate it when
  editing. `template: true` makes every open mint a fresh document —
  remove for personal decks.
- **Custom font names without embedding fall back silently.** The
  check is `validate()` reporting `font-not-embedded` — your local
  font makes it look fine while recipients get the fallback.
- **`window.bento.loadDoc` is undoable**, but pasting via filesystem
  edit isn't. Prefer round-trip via `Save ▾ → Copy document JSON` for
  edit operations so users can undo.
- **Telegram caption has a 1024-char limit when sending the deck file.**
  Long captions (`-F caption=...` on the bot API) return HTTP 400 with
  "Bad Request: message caption is too long". If the deck is big
  enough to deserve a multi-paragraph caption, trim it — the deck file
  itself is the artifact; the caption is a delivery hint only. Don't
  try to stuff the table-of-contents of a long playbook into a caption.
  See `references/bento-vs-pptx.md` and the related Telegram-delivery
  note in MEMORY.md for the curl pattern this user relies on.

## File operations

For the common operations on a deck file, use `scripts/bento_io.py` —
verified helpers for load/save/check:

```python
from bento_io import load_doc, save_doc, new_doc, runtime_blocks_intact

doc = load_doc('MyDeck.bento.html')          # dict or None if empty
assert runtime_blocks_intact('MyDeck.bento.html')  # before and after edits
doc['slides'].append(...)
save_doc('MyDeck.bento.html', doc)
```

Or from the shell:
```bash
python bento_io.py check MyDeck.bento.html   # exits 0 if all 3 blocks present
python bento_io.py load  MyDeck.bento.html   # prints the JSON block
echo '<json>' | python bento_io.py save MyDeck.bento.html
```

The script loads and saves JSON-escapes `<` to `\u003c`, parses and re-emits
data without reformatting, and validates that exactly one `bento-doc`
block is replaced. It never touches the runtime blocks.

For an inline approach (no external file), the equivalent helper is:

```python
import re, json

def load_bento_doc(path):
    text = open(path).read()
    m = re.search(
        r'<script[^>]*id="bento-doc"[^>]*>(.*?)</script>',
        text, re.DOTALL
    )
    if not m: return None, text
    raw = m.group(1).strip()
    return json.loads(raw) if raw else None, text

def save_bento_doc(path, doc):
    text = open(path).read()
    escaped = json.dumps(doc, ensure_ascii=False).replace('<', '\\u003c')
    new, n = re.subn(
        r'(<script[^>]*id="bento-doc"[^>]*>)(.*?)(</script>)',
        lambda m: m.group(1) + '\n' + escaped + '\n' + m.group(3),
        text, count=1, flags=re.DOTALL
    )
    assert n == 1, f"bento-doc block not found exactly once (n={n})"
    open(path, 'w').write(new)
```

Use the loader to read before edit. Use the saver with `json.dumps`
(don't hand-format) so escaping is automatic.

## Related skills

- `claude-design` — when iterating the visual quality of a deck, the
  same anti-slop rules apply; the constraint set is just smaller.
- `powerpoint` — when the deliverable must be a `.pptx` file rather than
  a self-contained HTML deck.
- `excalidraw` — for diagrams that should appear in a slide as a
  composition of shapes (use `shape` with ellipses, rects, paths).
- `persistent-knowledge-base` + its `references/knowledge-garden-export.md`
  — when the deck needs to teach or share the contents of an Obsidian
  vault. Knowledge Garden export produces a different file format aimed
  at non-Obsidian readers, but the design language shares principles.
