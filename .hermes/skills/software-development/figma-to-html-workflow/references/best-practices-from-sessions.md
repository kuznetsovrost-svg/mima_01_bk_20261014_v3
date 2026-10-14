# Best practices distilled from the FIGMA playbook sessions

Lessons learned across 8+ playbooks created in `/root/*-в-FIGMA.md`. Apply these to **every** new playbook in this series.

## 1. Skeleton every playbook follows (don't invent a new one)

```
1. Главное правило (1-3 sentences, the "one-liner" takeaway)
2. Why this matters (concrete example of the bug it prevents)
3. Convention overview (naming template, taxonomy)
4. Concrete Figma tree (ASCII or code block, every node named)
5. What Figma export produces (the HTML/CSS that comes out of the plugin)
6. What the template does (Jinja2/JS snippet, lines 10-30 max)
7. CSS example with tokens (var(--name), show light + dark)
8. Data structure (JSON snippet for the runtime)
9. Chеск-лист for Figma (5-10 items)
10. Связь с другими playbook'ами (links to other 8 files)
11. Шпаргалка (1-3 lines, copy-pasteable)
```

## 2. User's iteration rhythm (from session 2026-08)

The user iterates 4-5 times per topic. Plan for **at least 3 versions** of any new playbook:

| Iteration | What the user does |
|---|---|
| v1 (initial draft) | User reviews, requests 1-2 corrections |
| v2 (after corrections) | User accepts or requests structural changes |
| v3 (if needed) | Final polish with one more fix |

**Implication:** don't over-invest in v1. Get the structure right; polish later. The user will tell you what's missing.

## 3. The 5 conventions are sacrosanct — don't propose alternatives

When the user asks "how should I do X in Figma", **always** answer through these 5 lenses:

1. `{category.field}` placeholder — never `{{var}}`, never `$VAR`, never `#ID`
2. Semantic Color Styles — never `Red 600`, never literal hex in plugin
3. Figma Variants for state — never draw N copies, never conditionals
4. One-row template in `tbody` — never N pre-drawn rows
5. JSON tokens file — never hard-code hex in HTML

If a request seems to require breaking one of these, **escalate** — write a paragraph explaining the trade-off, propose the 5-convention solution, let the user decide.

## 4. The 7 most common Figma mistakes (warn proactively)

| Mistake | Why it's bad | Where to catch it |
|---|---|---|
| Drawing the table with N pre-baked rows | HTML plugin exports N rows verbatim | Чек-лист: "tbody содержит одну строку-шаблон" |
| Using `Red 600` for critical status | Hex hardcoded in 20 layers | Чек-лист: "Color Styles с осмысленными именами" |
| Separate Components for collapsed/expanded | No Toggle prototype, no Variants Property | Чек-лист: "Один Component, Variants state=..." |
| Dynamic colors baked into Figma rows | Forces Hermes to redraw design per row | Чек-лист: "tr.template нейтральный, severity→CSS" |
| Using `{{var}}` instead of `{var}` | Figma export renders literal `{{var}}` | Чек-лист: "Placeholders в фигурных скобках без префикса $ или {{ }}" |
| Drawing text with placeholder inside Text layer directly | The plugin strips curly braces sometimes | Чек-лист: "Каждый placeholder — отдельный Text layer с осмысленным именем" |
| Forgetting Auto Layout | Plugin exports absolute coordinates, not flexbox | Чек-лист: "Auto Layout: HORIZONTAL/VERTICAL включён везде" |

## 5. Telegram delivery quirks (carry forward from session)

- File names with Cyrillic and dashes get auto-rewritten by Telegram to underscores. Reference by `msg_id`, not filename.
- `caption` field has a 1024-character limit; for longer captions, split.
- Telegram doesn't render Markdown tables; use code blocks (` ` text ` `) or send a separate `.md` file.
- 50 MB upload limit; for larger, split or compress.

## 6. Delivery format depends on artifact type

| Artifact | Format | Why |
|---|---|---|
| Playbook/guide | `.md` via `sendDocument` | Telegram preserves formatting |
| Color swatch map | Self-contained `.html` with inline CSS | Open in browser to see actual colors |
| Tokens | `.json` for Tokens Studio import | One-click import |
| Visual example (e.g. component breakdown) | `.html` with inline CSS | Same as color map |
| Reference tables | ASCII in chat body | Telegram rewrites Markdown tables |

## 7. When the user says "перепиши X" or "поправь X"

- They mean **patch the file in place**, not create a new version. The `cp /tmp/<file>.md /root/<file>.md` recipe handles this.
- After patching, re-send the updated file. Don't ask "should I resend?" — they want the new version.
- Reference the patch in chat body: "Section 'Цветовая схема' переписан; новые шкалы `Spacing.XL` для status badges".

## 8. The user's preferred playbook length

| Length | Use case |
|---|---|
| 13-17 KB | Single-topic concise (e.g. `Компонент-с-вариантами.md` = 13 KB) |
| 25-35 KB | Standard playbook (e.g. `Таблица-в-FIGMA.md` = 35 KB) |
| 37-53 KB | Heavy playbook with full tables and examples (e.g. `Палитра-в-FIGMA.md` = 52 KB) |

**Default to 25-35 KB.** Go below 17 only for very narrow topics; go above 40 only when there's a big color/token table that needs to be exhaustive.

## 9. Recurring user's typos (he accepts his own, but I should help)

The user makes typos in long names. He's OK with his own typos in his filenames (he keeps `FIMA` instead of `FIGMA`). But he expects **me** to spell correctly:

- `Figma`, not `FIMA`
- `HOWPROJET`, not `HOWPROFET`
- `SKILL`, not `IDIND`, `SKIND`, `INDIND`

If I see the user typed a typo, I write the correct version in the file but **don't correct him in chat** unless he asks. He's aware.

## 10. Skill trigger phrases that mean "this playbook"

When the user says any of these, load this umbrella:

- "как сделать в figma..."
- "figma компонент..."
- "макет в figma..."
- "figma + html"
- "адаптивная верстка"
- "figma → html"
- "figma → шаблон"
- "палитра для figma"
- "tokens studio"

When the user says these, look at the playbook index first; **don't** write a new file if existing one covers it. Show the relevant sections via `read_file` + chat snippet, or `sendDocument` the existing file.

## 11. Sanity-check before delivery

Every playbook should answer these 5 questions in §"Шпаргалка":

1. **Что** — one-sentence rule
2. **Почему** — concrete consequence of breaking it
3. **Где** — Figma layer/frame to apply
4. **Как** — minimum 3-line code/placeholder snippet
5. **Проверка** — one item to verify after export

If any of the 5 are missing, **fix the playbook before delivery**.

## 12. Naming convention for new playbook files

Always `Тема-в-FIGMA.md` or `Тема-FIGMA.md`. Russian primary, FIGMA is the brand so kept Latin.

**Bad examples:**
- `playbook_figma.md` (no Russian, slug)
- `FIGMA-design.md` (Latin primary)
- `README.md` (no topic)

**Good examples:**
- `Компонент-с-вариантами.md`
- `Палитра-в-FIGMA.md`
- `Подсветка-строк-в таблице.md`

Note: the user kept `Плейсхолдеры-FIMA-01.md` with the typo. Don't fix it — that's the user's naming.
