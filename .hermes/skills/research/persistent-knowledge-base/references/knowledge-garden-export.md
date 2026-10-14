# Knowledge Garden Export — Reference

This reference documents the **share-and-view side** of the persistent-knowledge-base pipeline: how a multi-vault wiki (the result of `llm-wiki` / `persistent-knowledge-base` + the Enrichment Pipeline) is exported into a self-contained HTML artifact that non-Obsidian users can open, rotate, and click through.

See parent skill's "Knowledge Garden Export" intent for the cross-vault picture; this file is the technical spec.

## Goal

A single `.kg.html` file (~500 KB for a 700-node vault) that:

- Opens by double-click in a modern browser — works through `file://`, no server
- Shows an interactive force-directed graph of all notes
- Renders each note as Markdown (Obsidian-flavored: `[[wikilinks]]`, embeds, tables, callouts)
- Lets the user click a node to read its note, click `[[wikilinks]]` in the note to navigate, click to focus a neighbourhood
- Is **Russian UI** by default (with offline-embeddable toggle for English)
- Toggles dark/light theme with persistence in `localStorage`
- Warns about broken `[[wikilinks]]` and missing images via `_warnings.md`

## Decided format decisions (do not re-litigate)

These were chosen in the original design session (see `/tmp/wiki-export/decisions-2026-09-06.md`). Use them as gospel; deviations require new discussion.

| Question | Decision | Why |
|---|---|---|
| Size of vault | 500-700 nodes | Confirmed by user |
| Image rule | Embed via `assets/img/<sha256>.<ext>` with dedup by SHA-256 | Self-contained, no external deps |
| Wikilink forms | Full set: `[[Page]]`, `[[filename#anchor]]`, `[[vaultname:Page]]`, `![[image]]`, `![[note/image\|400]]`, `![[note#heading]]` | Matches Karpathy / Obsidian |
| Multi-vault | Single graph with colour-coding per vault, cross-vault edges shown distinctly | One artifact, not N |
| UI language | Russian | User preference |
| Themes | Light + dark, toggle, `localStorage` persistence, `prefers-color-scheme` auto-detect | |
| Offline | Everything inline (cytoscape + marked + config); no CDN; works through `file://` | Distribution over email / USB / read-only mirror |
| ZIP | User archives the directory themselves — exporter outputs a directory only | Simpler build, no signing concerns |
| README | `README.md` inside the directory in Russian, instructions for opening | Self-documenting |
| Broken wikilinks | Warn in `_warnings.md`; still generate | Don't block on tidy issues |
| Versions | Each export is a new directory snapshot — no incremental update | Simpler, no diff UI to build |

## Output directory structure

```
exports/<vaults>-<YYYYMMDD-HHMM>/
├── index.html                  # main artifact — single self-contained file
├── README.md                   # instructions in Russian
├── _warnings.md                # broken wikilinks, missing assets
├── _build-report.txt           # counts, timing, versions
└── assets/
    ├── notes/
    │   ├── index.js            # search index (filename → id → body)
    │   └── <id>.js             # pre-rendered note bodies (lazy-loaded)
    └── img/
        └── <sha256>.<ext>      # deduped images
```

**Naming example**: `exports/research-hermes-platform-20260909-143000/`

## Index.html — what's inline, what's lazy

Total budget for a 700-node vault ≈ 500 KB. Allocation:

| Component | Size | Where |
|---|---|---|
| `cytoscape.min.js` | ~370 KB | Inline `<script>` |
| `marked.min.js` | ~40 KB | Inline `<script>` |
| `app.js` | ~10-15 KB | Inline `<script>` |
| `style.css` | ~7-10 KB | Inline `<style>` |
| `graph-data.js` | 5-50 KB | Inline `<script>` (700 nodes × ~50 bytes) |
| Theme persistence + UI | ~5 KB | Inline |

That leaves ~20-30 KB for first-paint overhead. Note bodies are NEVER inline; always lazy-loaded as `assets/notes/<id>.js` (each note = 1-15 KB).

## JS architecture

The runtime lives in `index.html` and is roughly:

```
graph-data.js → cytoscape initialises with nodes/edges
notes/index.js → exposed as window.__notes_index__
user clicks node → fetch assets/notes/<id>.js → marked.parse() → side panel
user clicks [[wikilink]] → resolved against window.__notes_index__
if not yet loaded → fetch on demand
```

Three globals the runtime expects:

- `window.__GRAPH_DATA__` — `{ nodes: [{id, label, color, vault, tags}], edges: [{source, target, label}] }`
- `window.__NOTES_INDEX__` — `[id → {title, file, path}]` — listing for search & resolution
- `fetch('assets/notes/<id>.js')` — returns a JSON module: `{id, html, frontmatter}`

Single `app.js` coordinator: handles click routing, neighbourhood focus via cytoscape's `cose` re-layout, theme toggle, search via substring (no external index library).

## Cytoscape configuration (validated)

From the prototype work — these settings produced the "rotates, neighbourhood tightens" behaviour the user liked:

```js
{
  layout: {
    name: 'cose',
    animate: true,
    animationDuration: 800,
    idealEdgeLength: 110,
    nodeRepulsion: 8000,
    gravity: 0.4,
    numIter: 1500,
    padding: 40
  },
  minZoom: 0.3,
  maxZoom: 2.5,
  wheelSensitivity: 0.3
}
```

For larger vaults (1000+), swap to `cose-bilkent` or `fcose`:

```js
{ name: 'fcose', animate: 'end', randomize: true, quality: 'default' }
```

## Motion features (Obsidian-like, prototype-validated)

Three motion behaviours the user approved in the test mock:

1. **Hover expand** — node `transition-property: width, height, border-color` with `transition-duration: 300ms ease-in-out`. Hovering enlarges the node 50→60 px and adds a 4 px coloured border.
2. **Click focus** — when a node is tapped, run `cose` re-layout **only on the neighbourhood**. The shared element is the central node's layout target; `idealEdgeLength: 80` brings neighbours closer than global default. Non-neighbours fade to opacity 0.2.
3. **Drag + release re-layout** — when a node is dropped, trigger `cose` re-layout on the whole graph (not just local) so neighbours find their new equilibrium around the moved node.

These three behaviours together create the "Obsidian-like" feel without needing Obsidian-style editor surface.

## Build script responsibilities

The exporter takes `<vault_dir>` (or a comma-separated list for multi-vault) and produces the directory above. Pipeline:

1. Parse each `<vault>/AGENTS.md` for vault-specific config (theme colours, hidden tags, ignored paths)
2. Walk `<vault>/80_Wiki/**/*.md` — collect frontmatter, body, wikilink references
3. Walk `<vault>/raw/assets/**` — collect images, record SHA-256, copy to `assets/img/<sha256>.<ext>` (dedup if referenced from multiple notes)
4. Resolve cross-vault links: `[[vaultname:Page]]` → if `vaultname` is in this export, point at that note's id; otherwise mark as cross-vault (no resolve, but show in graph if the resolved page exists)
5. Validate wikilinks: any `[[target]]` whose resolved note doesn't exist → append to `_warnings.md`
6. Pre-render each note body → `assets/notes/<id>.js` as a JSON module
7. Generate `index.js` search index
8. Generate `assets/img/<sha256>.<ext>` (deduped across all notes)
9. Generate `graph-data.js` with all node/edge data inline as JSON
10. Generate `_build-report.txt` (counts, vault list, image count, generation time)
11. Generate `README.md` (Russian instructions: how to open, what to expect)
12. Generate `index.html` as a string-template + assembly, with cytoscape + marked + app.js inlined
13. If `lint` is requested: ALSO produce `_warnings.md` (still proceed even if there are warnings)

## Frontend inline-everything policy

Two strict rules (because `file://` mode blocks many browser conventions):

- **No remote CDN** — every library is inline. CDN import breaks when the user opens the file without internet.
- **No `fetch` cross-origin** — every JS file must be relative (`assets/notes/...`). Relative fetches work through `file://`.

Violating either → "blank graph" or "script won't load" errors with no useful console message.

## Cryptographic & content considerations

- **Markdown escaping**: every `<` in wikilink target names must be `&lt;` after the marked pass (the markdown renderer handles this naturally).
- **`[[wikilinks]]` resolution**: case-insensitive, hyphenated-slug match. If neither matches, the link renders as plain text.
- **Image embedding**: SHA-256 hash prevents filename collisions when multiple notes reference the same source image. `<img src="assets/img/<sha256>.<ext>">` paths stay stable when notes are renamed.
- **No comments / collaboration markers** in the wiki body should leak into the export — strip during parse.

## What the prototypes proved and what's still open

**Validated through prototypes** (in `/tmp/wiki-export/` and `/tmp/obsidian-graph-physics/`):

- Cytoscape 3.30.2 + marked.js inline = ~410 KB runtime; fits with budget
- `cose` layout renders smoothly with 5 nodes
- Hover/click/drag motion work as designed with CSS transitions
- Single HTML file passes through Telegram, opens in Chrome/Firefox/Safari
- Theme toggle + `localStorage` persistence work in `file://`

**Still not built (deferred to implementation phase)**:

- `assets/notes/<id>.js` lazy-load (prototype inlined all notes because it was 5 nodes)
- Image dedup by SHA-256
- Multi-vault colour coding with cross-vault edge distinction
- 700-node performance under `fcose` (vs `cose`)
- `_warnings.md` validator
- `README.md` generator
- Build-script Python implementation

## Related references and skills

- Parent skill: `persistent-knowledge-base` — overall multi-vault architecture
- `llm-wiki` — the source-of-truth workflow on the server
- `obsidian` — when the source vault needs interaction on a workstation
- `claude-design` — when iterating the index.html's visual design
- `excalidraw-grid-analyzer`, `idef0-excalidraw-methodology` — example skill size budgets and Python-with-tests patterns to mirror
