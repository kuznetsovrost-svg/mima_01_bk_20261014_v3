---
name: figma-to-html-workflow
description: Use when the user asks for a Figma → HTML/Adaptive template workflow — placeholder conventions, headers, tables, dynamic colors, palettes, status badges, or JSON tokens for Figma Tokens Studio. Triggers include "как в FIGMA задать плейсхолдер", "сделай компонент с вариантами", "карту цветов", "готовая палитра для Figma", "тёмная тема в Figma", "таблица с подсветкой строк", and "пришли JSON для Tokens Studio". Covers naming conventions, Auto Layout rules, the Figma Variants → CSS classes bridge, the 1:1 mapping between Figma Tokens Studio JSON and CSS custom properties, and the "/root/*-в-FIGMA.md" playbook corpus that grows each session.
version: 0.1.1
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [figma, design-system, html, css, json-tokens, placeholders, telegram-delivery]
    related_skills: [guide-authoring-for-hermes, design-md, popular-web-designs, claude-design, figma-api-import]
    changelog: 'v0.1.0 (2026-08-01): initial creation. Captures the eight playbook files in /root/ (Плейсхолдеры-FIMA-01, Шапка-в-FIGMA, Таблица-в-FIGMA, Динамические-цвета-в-FIGMA, Палитра-в-FIGMA, Компонент-с-вариантами, Подсветка-строк-в таблице, figma-tokens-full.json) as a single class-level umbrella. Codifies the 5 conventions: {category.field} placeholders, semantic Color Styles, Figma Variants for status, one-row templates for tables, JSON tokens for theme switching. v0.1.1 (2026-08-08): added references/best-practices-from-sessions.md (distilled lessons: iteration rhythm, skeleton, 7 most common Figma mistakes, user typo policy, playbook length guide) and references/api-integration.md (how figma-api-import JSON feeds this workflow). Future playbook in this series should be added as a `references/<topic>.md` rather than a new file at /root/.'
---

# Figma → HTML Workflow

Class: the user designs in Figma with conventions that make the export → HTML template workflow cheap. The conventions are: `{category.field}` placeholders, semantic Color Styles (not "Red 600"), Figma Variants for dynamic states, one-row templates for tables, and a JSON tokens file that produces 144 CSS custom properties (72 light + 72 dark) on import.

Eight files in `/root/` already implement this corpus. New requests in this series are usually "the N+1th playbook" — locate the existing files, identify the gap, and extend the recipe.

## Corpus index (always check these before writing a new playbook)

| File | Topic | Size |
|---|---|---|
| `/root/Плейсхолдеры-FIMA-01.md` | `{category.field}` placeholder convention, layer prefixes (`sec.` `grp.` `cmp.` `btn.` `ico.` `img.` `txt.static.<role>`), Auto Layout | 23 502 B |
| `/root/Шапка-в-FIGMA.md` | Headers: 2 text layers (static + dynamic), separator styles, responsive | 37 927 B |
| `/root/Таблица-в-FIGMA.md` | Tables: one row template + `{rows[N].<field>}` for loop, collapsible accordion variant | 35 242 B |
| `/root/Динамические-цвета-в-FIGMA.md` | Status badges: Figma Variants `state=red|yellow|green|neutral`, exports to `badge--<state>` CSS class | 38 725 B |
| `/root/Палитра-в-FIGMA.md` | Color map: 60+ semantic colors × light + dark, 6 groups | 52 357 B |
| `/root/Компонент-с-вариантами.md` | Collapsible row: `cmp.collapsible-row` with `state=collapsed|expanded` Variants, maps to `<details>`/`<summary>` | 13 026 B |
| `/root/Подсветка-строк-в таблице.md` | Row coloring: Figma stays neutral, CSS adds `row--critical` / `row--attention` via Jinja2 from `severity` field | 16 112 B |
| `/root/figma-tokens-full.json` | Tokens Studio import: 144 colors + 21 typography + 16 spacing + 10 radius + 5 shadow, light + dark themes | 31 964 B |

Auxiliary artifacts (HTML deliverables, JSON for individual projects):

| File | Purpose |
|---|---|
| `/root/color-map.html` | Self-contained visual swatch map of the palette (inline CSS, opens in browser) |
| `/root/colormap-showcase.html` | Design preview of token variants |

## The 5 conventions (memorize these — every playbook references them)

### 1. Placeholders: `{category.field}` in curly braces

| Source example | Figma export | HTML template |
|---|---|---|
| `{report.title}` | `<text>{{ report.title }}</text>` | `<h1>{{ report.title }}</h1>` |
| `{rows[N].code}` | rendered N times in loop | `{% for row in rows %}<td>{{ row.code }}</td>{% endfor %}` |
| `{rows.length}` | static text in collapsed state | `{{ rows.length }} замечаний` |

Layer prefix taxonomy:
- `sec.<role>` — Frame sections (cards, header rows)
- `grp.<role>` — Frame groups (icon + text clusters)
- `cmp.<name>` — Component (Variant source)
- `btn.<role>` — Button (preferred over `cmp.button`)
- `ico.<name>` — Layer-embedded icon (chevron, status)
- `img.<name>` — Image/Photo slot
- `txt.static.<role>` — Static text (not a placeholder) so the static/dynamic split is visible in the layer panel

### 2. Color Styles: semantic, not literal

| ❌ Don't | ✅ Do |
|---|---|
| `Red 600` | `Status / Critical / Bg` |
| `Blue 500` | `Action / Primary / Bg` |
| `Gray 200` | `Border / Default` |

Naming template: `<Группа>/<Вариант>/<Роль>` where
- `Группа` = `Status`, `Text`, `Background`, `Border`, `Action`, `Brand`
- `Вариант` = `Critical`, `Attention`, `Healthy`, `Info`, `Primary`, `Secondary`, ...
- `Роль` = `Bg`, `BgHover`, `Text`, `TextMuted`, `Border`, `Dot`, `Icon`, `Accent`

This 3-tuple maps 1:1 to CSS custom properties: `var(--status-critical-bg)`.

### 3. Figma Variants for dynamic states

Don't draw 4 separate components for 4 states. Use one Component with Variants:

| Component | Property | Values |
|---|---|---|
| `cmp.status-badge` | `state` | `critical`, `attention`, `healthy`, `neutral` |
| `cmp.collapsible-row` | `state` | `collapsed`, `expanded` |
| `cmp.btn-primary` | `state` | `default`, `hover`, `active`, `disabled` |

The variant default (typically `state=neutral` or `state=default`) is what the Figma export shows. The HTML template then swaps the class based on data:

```html
<!-- Figma export shows: -->
<span class="badge badge--neutral">...</span>

<!-- After Herald fill-in with row.severity = "critical": -->
<span class="badge badge--critical">...</span>
```

### 4. One-row template for tables

The `tbody` contains **exactly one row instance** — the template. The HTML template generates N rows via `{% for row in rows %}`:

```html
<tbody>
  <tr class="row">
    <td class="td td--status">{{ row.code }}</td>
    ...
  </tr>
</tbody>
```

For dynamic row coloring (Подсветка-строк-в таблице.md), the Figma row stays neutral:

```html
<tr class="row {% if row.severity == 'critical' %}row--critical{% endif %}">
```

The CSS lives in tokensStudio imports, not in the Figma export:

```css
.row--critical { background: var(--status-critical-bg); }
.row--attention { background: var(--status-attention-bg); }
```

### 5. JSON tokens for theme switching

The `figma-tokens-full.json` file exports to Tokens Studio and produces 144 Color Styles + 21 Text Styles + 16 Spacing + 10 Radius + 5 Shadow Styles. Two themes (`light`, `dark`) are preconfigured — flip a switch in the plugin to switch every styled layer.

The HTML template's CSS loads the same tokens as CSS custom properties:

```css
:root {
  --status-critical-bg: #FEE2E2;
  --status-critical-text: #991B1B;
  --spacing-4: 16px;
  --radius-lg: 8px;
}

[data-theme="dark"] {
  --status-critical-bg: #450A0A;
  --status-critical-text: #FECACA;
}
```

## Workflow: when the user asks for the N+1th playbook

1. **Locate the corpus.** `ls /root/*-в-FIGMA.md /root/*-FIMA*.md`. Read the README index of `figma-to-html-workflow` (this file) and skim the most relevant existing playbook.
2. **Identify the gap.** Is it a new placeholder shape (icons? avatars? charts?), a new component (slider? dropdown?), a new color role (warning? brand-2?), a new spacing/radius rule, or a new delivery artifact (PDF? email)?
3. **Use the same skeleton.** Russian-language guide, ~30-50 KB, 14-18 sections: `Главное правило` → `Пример` → `Дерево в Figma` → `HTML после экспорта` → `CSS` → `JSON` → `Чек-лист` → `Связь с другими playbook'ами` → `Шпаргалка`.
4. **Reuse the conventions.** Placeholders via `{category.field}`, semantic Color Styles, Figma Variants, one-row template, JSON tokens. Don't introduce a new naming convention — the whole point is consistency.
5. **Write to `/tmp/<file>.md` first**, then `cp /tmp/<file>.md /root/<file>.md`, then verify with `python3 -c "d=open(...).read(); bad=[...]"`. Don't use `write_file` directly to `/root/` — the `guide-authoring-for-hermes` skill documents why (write_file injection on this host).
6. **Deliver via curl `sendDocument`** through `@MMRV_Hermes_bot` (token from `/root/.hermes/.env`, chat_id 505586502). The mode depends on the artifact:
   - **Markdown playbook** → `.md` file via `sendDocument`
   - **Color map** → standalone HTML with inline CSS (`color-map.html` is the reference)
   - **Tokens** → JSON for Tokens Studio import
   - **Reference tables** → ASCII tables in chat body (Telegram rewrites Markdown tables)

## When a new request is NOT a new playbook

Sometimes the user asks for something that fits one of the existing eight files. Pre-check before writing a new one:

| Request shape | Likely existing playbook |
|---|---|
| "как сделать status badge" | `Динамические-цвета-в-FIGMA.md` |
| "таблица с разной подсветкой строк" | `Подсветка-строк-в таблице.md` |
| "открывашка в Figma" | `Компонент-с-вариантами.md` |
| "палитра для Tokens Studio" | `figma-tokens-full.json` + `Палитра-в-FIGMA.md` |
| "плейсхолдер для названия проекта" | `Плейсхолдеры-FIMA-01.md` + `Шапка-в-FIGMA.md` |
| "заголовок отчёта" | `Шапка-в-FIGMA.md` |
| "таблица с разными строками" | `Таблица-в-FIGMA.md` |

If the existing playbook covers it, point the user to it (read_file + show key sections in chat, or `sendDocument` the existing file). **Don't write a duplicate.**

## Pitfalls

### Same-host injection: `write_file` to `/root/` is sketchy

`write_file` injects "Modification Complete / DIAGNOSTIC / Distress Protocol" markers into the tool echo on this host. The verified recipe (also in `guide-authoring-for-hermes` Pitfall "write_file itself is being used as an injection channel") is: write to `/tmp/<file>.md` first, `cp` to `/root/<file>.md`, then verify with an independent tool (e.g. `python3 -c "d=open(...).read(); bad=[...]"`). Skip `read_file` for verification — the same channel can serve fake content back.

### Telegram auto-rewrites Cyrillic filenames to underscores

`Инструкция-отправка-файлов-в-Telegram.md` arrives in the chat as `Инструкция_отправка_файлов_в_Telegram.md`. This is a Telegram-side quirk, not a bug. Reference the file by its `<msg_id>` (returned from the curl response) instead of relying on the visual filename.

### Tokens Studio plugin requires Color Styles, not just Variables

The plugin's "Create Styles" button creates the Figma Color Styles from imported tokens. If you only use Variables (no Styles), the styles won't appear in the Styles panel for layer-level application. Keep the "create both Variables AND Styles" workflow — the 144 Color Styles get applied per layer, the Variables sit in the design system.

### Empty `tbody` looks like a bug to Figma plugins

The HTML+CSS plugin treats an empty `tbody` as an error. The `tr.template` row must contain real dummy text ("124-XXX", "—", "Q1") so the plugin produces a valid HTML scaffold. The dummy text is replaced by Jinja2 at template-time.

### Connecting Variants to status data: design-time vs runtime

The Figma design shows ONE variant per Component instance (default). The HTML template then applies the runtime class based on row data. The mapping (default → runtime) is **documented** in the playbook, not enforced anywhere. If the user asks "can Figma show the dynamic version", the answer is "no — that's the template's job, Figma shows the design-time neutral state."

### Don't use `@fst_control_bot` for these deliveries

These playbooks are discussed in a session running through `@MMRV_Hermes_bot` (default profile). If the user mentions `fst_control`, that's a separate bot with its own session — don't try to deliver through it from here. The `messaging-gateway-setup` skill §"Multi-bot routing" has the rule.

## Reference files

### Corpus (in `/root/`)

The 8 playbook files listed in the corpus index above.

### Skill-internal references

- **`references/best-practices-from-sessions.md`** — distilled lessons from 8+ playbook creation sessions. **Read this before writing any new playbook.** Covers: iteration rhythm (3 versions per playbook), standard skeleton (11 sections), the 5 sacrosanct conventions, 7 most common Figma mistakes with catch locations, delivery format by artifact type, user's typo policy (he accepts his own, expects mine correct), preferred playbook length (25-35 KB default), 5-question sanity check before delivery, naming convention `Тема-в-FIGMA.md`.
- **`references/api-integration.md`** — how `figma-api-import` JSON feeds this workflow. The bridge diagram, JSON→HTML mapping table (FRAME/RECTANGLE/TEXT/INSTANCE/GROUP/ELLIPSE → HTML), Variants to runtime classes, Variables → Tokens Studio conversion, when to use API vs manual.

### Conversation artifacts (recent files for reference)

Files in `/root/` from prior sessions, archived here for the next session to find:
- `Проект агента для ЦОРПУ.md` — 7-этапный план для будущего ИИ-продавца курсов ПМ СТАНДАРТ (АНО ЦОРПУ, ГК Проектная ПРАКТИКА)
- `Проект_агента_для_ЦОРПУ.docx` — DOCX-конвертация через python-docx
- `figma-api-import/` — новый скилл, класс-уровень (использует Figma REST API, импортирует frame + все components со всеми Variants, авто-токен из `.env`)
- `Инструкция-отправка-файлов-в-Telegram.md` — канонический синтаксис `curl -F document=@...` для @MMRV_Hermes_bot

## Related skills

- **`guide-authoring-for-hermes`** owns the Russian-language delivery workflow (sending these playbooks to the user via Telegram). Load it for delivery mechanics.
- **`design-md`** is the Google DESIGN.md format — *different* from Tokens Studio JSON. Don't conflate the two.
- **`popular-web-designs`** for inspiration on real design systems (Stripe, Linear, Vercel); useful for benchmarking the palette typography.
- **`claude-design`** for one-off HTML mockups that don't fit the Figma→HTML pipeline (when the user wants a quick prototype, not a templated report).
- **`figma-api-import`** — when the user provides a Figma file URL with components, run this to get JSON before consulting this skill. The JSON→HTML mapping table lives in `references/api-integration.md`.