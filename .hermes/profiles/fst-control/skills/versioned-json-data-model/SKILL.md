---
name: versioned-json-data-model
description: "Class-level workflow for designing versioned JSON data models that capture structured information (reports, assessments, snapshots) and persist them to a backend store (MCP, DB, file system) with version-aware reads. Each version has: JSON Schema (draft 2020-12) in specs/vX.Y.Z.json, human-readable MODEL.md, real-data examples in examples/vX.Y.Z_<subject>.json, Python migration script migrations/vA.B.C_to_vD.E.F.py with migrate(old: dict) -> dict, and a MIGRATIONS registry. Every JSON embeds _meta.schema_version + generated_at + generator + subject_id. Lessons baked in: schema-driven dev, defaults for forward compat, _legacy section for removed fields, normalize enum variants, validate with jsonschema before commit, diff_specs.py for schema diffs. ALSO covers MD-as-self-contained-snapshot-artifact: YAML front-matter + HTML-comments-in-last-cell + snapshot == one file (not folder) + byte-for-byte deterministic renders + --generator CLI for caller attribution. Born from fst-project-health v0.9.0 report-JSON work (2026-08-21), generalised with v1.0.19 MD-only rendering (2026-09-23)."
version: 0.3.0
author: ROSTISLAV KUZNETSOV
metadata:
  hermes:
    tags: [json, schema, versioning, mcp, persistence, migration, reporting, ru, design]
    category: productivity
    related_skills: [fst-project-health, mcp-server-probing, fst-project-trends]
changelog:
  - "0.5.0 (2026-09-01): b-tree 2704 limit IS FIXED by MCP developers — JSON up to ~50 KB now persists without split. Live-probe 504-595 (5 KB), 504-314 (10 KB), 503-434 (13 KB), 503-152 (50 KB) — all work. `delete_entity` correct format FOUND: `remove=['AttributeValue|<guid>']` (live-probe 10 formats, only this one works; 34/34 test records successfully deleted). Update P-MCP-2 in references/mcp-attribute-value-write-pitfalls.md: split workaround is now optional (only needed if `AttrValue` > ~50 KB UTF-8 JSON, but no current use case requires that)."
  - "0.6.0 (2026-09-23): Generalized 'Markdown as a self-contained snapshot artifact' from a JSON-specific addendum into first-class support. Source skill: `fst-project-health` v1.0.19 — `rebuild_report.py` writes YAML front-matter, `build_html_report.py` renders HTML only from MD (no MCP at render time). Living examples: 5 project snapshots under `fst-project-health-snap-md/outputs/`. Added: (1) numbered-section-to-md-cells contract — every consumer reads only MD, no parallel JSON sidecar for HTML render; (2) 'extract_section multiline-anchor pattern' (P11) moved here as a hard pitfall — already covered, made authoritative; (3) 'self-contained determinism contract' — render output for the same MD is byte-for-byte identical except for 'Отчёт создан' timestamp; (4) HTML comments inside the LAST cell only — preserve `|` row start so pipe-table parsers don't break; (5) `--generator` CLI as the canonical way for callers to attribute MD provenance (no hardcoded generator in the writer); (6) 'snapshot is either one MD or one .tar.gz' rule codified — never a directory, for lifecycle/permission reasons."
  - "0.4.0 (2026-08-26): Live-probe 2026-08-26 подтвердил — MCP фильтр `ProjectHealthCostMy?ProjectId=<id>` теперь работает (1 строка за 1.5 сек, было 2000 строк / 41 сек). Pipeline `fst-project-health` ускорен с 60 до 19 сек (−68%). Разработчики также починили регрессию (view падал с 500 даже без фильтра). Live status фильтров в `mcp-server-probing/references/view-filter-playbook.md`."
  - "0.3.0 (2026-08-22): Added `references/inline-svg-visualization.md` — playbook for rendering JSON-data trends as Inline SVG. Will be used by the future `fst-project-trends` skill (still in /tmp/trend-report-design/, not yet installed). 5 patterns: multi-line, step, stacked-area, sparkline, donut. Standard color palette for health-reports. Python template generator. 6 SVG pitfalls (S1-S6). Sources: MDN, W3C, D3 Gallery, Tufte, FT Visual Vocabulary."
  - "0.2.0 (2026-08-22): Live-probed persisting JSON to MCP via `AttributeValue` entity. Added `references/mcp-attribute-value-write-pitfalls.md` with 10 documented pitfalls: b-tree 2704 byte limit (forces split for Cyrillic-heavy JSON), `create_entity` doesn't exist (use `save_entity` + `id=new`), 3 payload formats (full / split with `_part_data` / split with `_part_name` only), `find_entity` arg is `name`, `get_view` row `id` is internal sequence, `delete_entity` returns 500 on all known formats (append-only assumption), date format must include time+tz, `EntityId` required even with `DataId`. End-to-end test: 504-595 generate→upload→fetch→rebuild HTML in ~12 sec for 6 KB JSON. Added 'Persisting to MCP' section with the proven write shape and split threshold."
  - "0.1.0 (2026-08-21): Initial design. 4-section structure (_meta, summary, sections, metadata + optional _raw, _legacy). Migration framework with chain support. Generator + reader + diff scripts. 4 real-data examples (504-314, 503-434, 504-595, 503-152). Reference: working-example-project-health.md."
---

# versioned-json-data-model

Class-level workflow for designing **versioned JSON data models** that capture structured information (reports, assessments, snapshots) and persist them to a backend store (MCP-backed database, file system, REST API) with **version-aware reads**.

The core problem this skill solves: when you store structured data that evolves over time (new fields added, old fields renamed, enums extended), **how do you read old data reliably without code breaking?** The answer is a small set of conventions and tooling:

1. **Schema per version** — every version has its own JSON Schema (`specs/vX.Y.Z.json`).
2. **Migration scripts** — Python `migrate(old: dict) -> dict` that upgrade older data. Stored in `migrations/` with `MIGRATIONS` registry.
3. **Versioned `_meta` block** — every produced JSON carries `_meta.schema_version`, `_meta.generated_at`, `_meta.generator`, `_meta.project_code` so a reader can pick the right parser.
4. **Default values + `_legacy` section** — forward compatibility (new fields have defaults) and backward preservation (removed fields land in `_legacy`).

## When to load

Trigger phrases:

- «спроектируй JSON для отчёта», «JSON-модель данных отчёта», «нужна схема для хранения»
- «схема JSON с версионированием», «JSON Schema с миграциями», «versioned JSON»
- «нужно хранить отчёты в базе», «сохранять снепшоты», «snapshot через MCP»
- «будут класть этот JSON в базу данных через MCP», «MCP persistence»
- «как разработать скрипты для автоматического изменения процедуры подготовки JSON»
- «diff между версиями схемы», «как безопасно менять JSON-модель»

Don't load for: generic JSON Schema design (any validator works); in-memory data classes (use Python dataclasses / pydantic); one-off JSON serialization (use `json.dumps`). This skill is for **persisted, versioned, evolving structured data**.

## Canonical directory layout

```
project-json-design/                # or any <domain>-json-design/
├── README.md                        # one-paragraph summary + design intent
├── MODEL.md                         # current model description (human-readable)
├── specs/
│   └── vX.Y.Z.json                  # JSON Schema (draft 2020-12)
├── examples/                        # real-data examples per version
│   └── vX.Y.Z_<subject>.json        # for each (version, subject) pair
├── migrations/
│   ├── __init__.py                  # MIGRATIONS = {("0.1.0", "0.2.0"): "v0.1.0_to_v0.2.0", ...}
│   └── vA.B.C_to_vD.E.F.py          # def migrate(old: dict) -> dict
├── scripts/
│   ├── generate_json.py             # source data → versioned JSON
│   ├── read_json.py                 # version-aware JSON → readable summary
│   ├── migrate_json.py              # apply migrations chain
│   └── diff_specs.py                # diff between two JSON Schema files
└── docs/
    ├── DESIGN.md                    # ADR-style architecture decisions
    └── CHANGELOG.md                 # version history
```

All paths are **relative** — the convention is portable. Drop this structure anywhere; only the scripts' argparse defaults point to the canonical locations.

## Five principles

### 1. Schema-driven development

Every version has:

- **`specs/vX.Y.Z.json`** — JSON Schema (draft 2020-12) with `$id`, `version`, `type: "object"`, `required`, `properties`, `$defs` for nested types.
- **`MODEL.md`** — human-readable description with examples per field.
- **`examples/vX.Y.Z_<subject>.json`** — at least one real-data example that validates against the schema. Example subjects are real entities (project codes, customer IDs), not synthetic placeholders.

Validate every example with `jsonschema.validate(data, schema)` before commit. **If an example doesn't validate, the schema is wrong** (likely overly restrictive enum or required field that should be optional).

### 2. Forward compatibility through defaults

When adding a new field:

- Make it **optional** in the schema (`required` array unchanged, just add to `properties`).
- Code readers see it as `data.get("new_field", default_value)`.
- Older data simply lacks the field — readers tolerate it.

When adding a new enum value:

- Old data with the old enum is still valid (backward compat).
- New readers must accept both old and new enum values — see P1 below.

### 3. Backward preservation via `_legacy`

When **removing** a field from the schema:

- The migration script moves the field to `_legacy.<old_field_name>` instead of dropping it.
- `_legacy` is `additionalProperties: true` in the schema — anything can live there.
- Future readers see `_legacy` and know "this field used to exist; ignore or migrate manually".

When **renaming** a field:

- Old field → `_legacy.<old_name>` with original value.
- New field gets the value if it can be derived; otherwise `_legacy` only.
- Document the rename in CHANGELOG.md and DESIGN.md.

### 4. `_meta` block is mandatory and consistent

Every produced JSON has:

```json
{
  "_meta": {
    "schema_version": "0.1.0",                  // semver of the data model
    "generated_at": "2026-08-21T22:30:00Z",    // ISO-8601 UTC
    "generator": "<skill-name>",                // const, identifies the producer
    "generator_version": "0.9.0",               // semver of the producer skill
    "<subject_id_field>": "<value>",            // e.g. project_code, customer_id
    "<subject_id_field_2>": <value>,           // optional second id
    "source_<input>_hash": "..."                // optional, for traceability
  }
}
```

Reader logic:

```python
version = data["_meta"]["schema_version"]
if version == CURRENT_VERSION:
    parse_v_current(data)
elif version in MIGRATION_CHAIN:
    data = migrate_to_current(data)
    parse_v_current(data)
else:
    raise UnsupportedSchemaVersionError(version)
```

### 5. Migrations are Python code, not data

When the structure changes:

- Write `migrations/v0.1.0_to_v0.2.0.py` with `def migrate(old: dict) -> dict: ...`.
- Register it in `migrations/__init__.py`: `MIGRATIONS = {("0.1.0", "0.2.0"): "v0.1.0_to_v0.2.0", ...}`.
- `migrate_json.py` walks the chain (`A → B → C`) if direct `A → C` is missing.
- **Test** every migration: pass real `v0.1.0` example through, validate the output against `v0.2.0` schema.

Migration scripts use ordinary Python — they can compute new fields, split dictionaries, normalize values. They can also call the existing `scripts/` of the producing skill (e.g. re-run a section, look up an entity).

## Markdown as a self-contained snapshot artifact

When the consumer is human-readable text (reports, audit logs, project digests) and the producer is MCP-driven, MD can replace JSON **if** it carries its own metadata:

### Two-tier metadata channel

- **Top of file (machine-readable):** YAML front-matter between `---\n` and `\n---\n`. Holds `schema_version`, `generator`, `generated_at`, `subject_id`, optional `source_<input>_hash`. A consumer parses it once and dispatches by version, the same way it would for `_meta` in JSON.
- **Inside pipe-table cells (machine-readable, visually invisible):** HTML-comment `<!-- key="value" -->` placed inside the last cell of a row. Holds per-row data the parser needs (severity, verdict, classification) that a human shouldn't see.

The HTML-comment trick works because `parse_md_table`-style consumers read row cells and ignore HTML-comment syntax; the comment is fully transparent to humans (renders as nothing) and survives any markdown-to-HTML conversion unchanged. Restrict it to **inside the last cell** so the row still starts with `|` and the pipe-table parser doesn't break on a bare comment line.

### Determinism contract

A self-contained MD artifact lets the same MD be re-rendered later (in a different session, on another machine, without MCP access) into the same HTML. To hold this contract:

- **Every consumer of the MD must read only the MD.** No fallback paths to live JSON, MCP views, or sibling files. If the parser needs severity, the severity is in the MD.
- **The producer-side generator must write everything the consumer needs.** Single source of truth — never "regenerate JSON because MD didn't have field X".
- **Render output is structurally deterministic.** A live render and a from-snapshot render differ only by render timestamp ("Отчёт создан:"), not by structure.

### Snapshot == single file (no folders)

The user-level rule "либо один .md, либо один .tar.gz" decides shape:

- If the artifact fits in one MD — use MD, no extra files (cleanest, easily copy-pasteable, diff-friendly).
- If multiple artifacts must travel together (MD + JSON + assets) — pack into one `.tar.gz`. Never use a directory of loose files — context-permission and lifecycle rules rarely survive that.

### Worked pattern: md-as-snapshot

The recipe that works:

1. Producer writes `<!-- key="..." -->` HTML-comments inside the **last cell** of pipe-table rows for per-row metadata (verdict, severity), and a YAML front-matter at the top for whole-file metadata (schema_version, generator).
2. Consumer (HTML renderer, reader, etc.) parses front-matter first for version dispatch, then per-row `<!-- ... -->` for cell-level data.
3. Both producer and consumer reference **only the MD**; no parallel JSON sidecar for HTML rendering.
4. Snapshot is the MD byte-for-byte (no extra HTML-comment wrapping by the snapshotter — the YAML metadata is already there).

### Attribute MD provenance via `--generator` (not hardcoded)

When multiple callers can produce the same kind of MD (a live pipeline, a periodic snapshotter, a historical replay tool), the writer must not assume which one ran. Hardcoding `generator: "<writer name>"` in the writer hides provenance and makes the YAML metadata wrong whenever a different caller runs the same writer.

Right shape: the writer exposes `--generator <name>` (or the equivalent parameter when called in-process). Each caller passes its own name:

```python
# rebuild_report.py / run_all.py canonical CLI
python3 scripts/rebuild_report.py <code> <name> <id> "" "" fst-project-health      # live pipeline
python3 scripts/rebuild_report.py <code> <name> <id> "" "" fst-project-health-snap-md  # snapshotter
```

The default `generator` (when no caller passes one) should be the most likely caller — but it MUST be overridable. Snapshot consumers reading MD should be able to trust `generator:` to mean "who ran me", not "who wrote the writer".

### Self-contained byte-for-byte determinism

Two renders of the same MD — one live from the pipeline, one from a snapshot months later — must produce HTML that differs ONLY in render-time fields (timestamp of "Отчёт создан:"). All structural marks (table counts, `<tr>` rows, `<details>` blocks, severity classes, verdict text) must match byte-for-byte. Test this by counting:

- `<table class='tbl` count (e.g. 29 in fst-project-health)
- `<details class='indicator-details` count (e.g. 7 in fst-project-health)
- number of `<tr...>` rows
- preview strings per `tbl-name` block

If a render that should match diverges by more than 2–3 occurrences in any of these counters, you have a regression — not merely a natural time-driven drift.

## Pitfalls

### P1. Enum value case mismatch between data and schema

Live-probe 2026-08-21: MD said `"**Статус: БОЛЕН**"` (uppercase). JSON Schema enum was `["Болен", "Требует внимания", "Здоров"]` (titlecase). Validation failed for all 4 examples. **Fix:** normalize on parse — define a `normalize_verdict(s: str) -> str` helper that lowercases input and maps `"болен" → "Болен"`, `"внимания" → "Требует внимания"`, `"здоров" → "Здоров"`. Apply **before** writing to JSON. Document the canonical forms in MODEL.md.

```python
def normalize_verdict(text: str) -> str:
    t = text.strip().lower()
    if "болен" in t: return "Болен"
    if "внимания" in t: return "Требует внимания"
    if "здоров" in t: return "Здоров"
    return "Здоров"  # safe default
```

### P2. Numeric field can't be null

Live-probe 2026-08-21: `overdue_days` was sometimes the literal string `"—"` in source MD. Schema required `integer` and `minimum: 1`. Validation failed. **Fix:** declare `type: ["integer", "null"]` and `minimum: 1` for positive counts, or remove `minimum` and accept negative (e.g. `forecast < today` → `overdue_days = -2`). When in doubt, allow `null` and document that readers must handle `None`.

### P3. Forgetting `total_counts` aggregation

Live-probe 2026-08-21: `summary.total_counts = {critical: 0, warning: 0, info: 0}` even when sections had rich data. **Cause:** generator summed counts from `s3` + `s5` only (where `counts` is structured that way), but `s6` stores criticality as `indicators[].result == "Да"`. **Fix:** generator must know how each section stores its counts and aggregate accordingly. Document the per-section counts shape in MODEL.md under "Counts aggregation rules".

### P4. Generator uses `shutil.copy` semantics where it should recompute

Naïve generators copy raw MD cells verbatim into JSON. But the raw MD may have:

- Stray whitespace (`Кузнецов Ростислав ` with trailing space)
- Em-dashes `—` vs hyphens `-`
- Date strings in different formats (`2026-08-21` vs `21.08.2026`)

Always **normalize on write** — `.strip()`, `date.fromisoformat()`, `null` for empty. The reader should never have to do post-processing.

### P5. Migration script forgets `_meta.schema_version`

When a migration runs `old → new`, it MUST update `_meta.schema_version` to the target. Common mistake: leave the old version in place, then the reader thinks it's still old data and migrates again. **Fix:** always end migration with:

```python
new["_meta"] = dict(old.get("_meta", {}))
new["_meta"]["schema_version"] = NEW_VERSION
```

### P6. Skipping the chain — direct migration without intermediate steps

If you have `v0.1.0 → v0.2.0` and `v0.2.0 → v0.3.0`, the reader should handle `v0.1.0 → v0.3.0` automatically by chaining. **`migrate_json.py` walks the chain**: look up `(current, target)` first; if missing, find an intermediate `next_v` where `(current, next_v)` is registered, migrate once, repeat. Without this, you accumulate duplicate migration scripts for every N → N+1 combination.

### P7. `MIGRATIONS` registry vs `scripts/migrate_json.py`

Keep the registry in **one place** — `migrations/__init__.py`. `migrate_json.py` reads it. Don't define migrations in two files; the registry is the source of truth. When adding a migration:

```python
# migrations/__init__.py
MIGRATIONS = {
    ("0.1.0", "0.2.0"): "v0.1.0_to_v0.2.0",
    ("0.2.0", "0.3.0"): "v0.2.0_to_v0.3.0",
}
```

```python
# migrations/v0.1.0_to_v0.2.0.py
def migrate(old: dict) -> dict:
    new = dict(old)
    new["_meta"] = dict(old.get("_meta", {}))
    new["_meta"]["schema_version"] = "0.2.0"
    # ... actual data transformation
    return new
```

### P8. Skipping validation of generated JSON

Always run `jsonschema.validate(data, schema)` after generation. Without it, you'll commit an invalid JSON that breaks all readers downstream. **Add a `--validate` flag** to the generator that fails loud if output doesn't validate.

```bash
python3 scripts/generate_json.py --code 504-314 --validate
# Exit code 0 = OK, 1 = validation failed (with details)
```

### P9. Mixing schema versions in one dataset

If you're writing a comparison report ("v0.1.0 vs v0.2.0 JSON"), **don't** load both with the same reader. Each version must be migrated to current before joining. The chain logic must be deterministic — same input version always reaches the same output.

### P11. Regex lookahead without line anchor matches `### N.M` as `## N`

When sectioning MD by chapter heading (e.g. `extract_section(text, 6)` parsing `## 6. …`), the lookahead `(?=## \d|## Сводка)` will **silently match `## 6` inside the line `### 6.3 subsection`**. The regex has no `^` anchor, so it finds `## 6` mid-line and stops the section right there — subsections disappear from the extracted slice. Symptom: extracted section seems valid but is missing all `### N.M` blocks below the first one.

**Fix:** anchor with multiline mode and explicit `^`:

```python
# Wrong: matches mid-line "## 6" inside "### 6.3 ..." sub-section headings.
pattern = rf"## {n}\. .*?(?=## \d|## Сводка)"

# Right: lookahead is anchored to start of line; sub-headings won't match.
pattern = rf"(?m)^## {n}\. .*?(?=^## \d|^## Сводка)"
```

**Same trap applies to any markdown sectioning by `#`/`##`/`###` count. Always add `(?m)` and `^` to both the heading match and the lookahead.

### P12. Per-row metadata placement in pipe-table — last cell only

When MD rows need cell-level metadata that's visually invisible to humans (verdict, severity, classification, etc.), the natural-looking option is to write it as a separate line under the row:

```markdown
| 6.3 | Прогнозы по ресурсам заданы | Вопросы, 703 ч | ▼ |
<!-- 6.3 verdict="Существенное" -->
```

Looks harmless. **It is not.** `parse_md_table`-style consumers typically scan rows by `line.startswith("|")` and stop at the first non-`|`-starting line. A comment line under the row breaks the table boundary, so the row is either dropped, treated as a new "row of None" cell, or — most commonly — the parser keeps reading only-`|`-starting lines and the next "row" is treated as a continuation, garbling the structured output.

**Fix:** put the `<!-- key="..." -->` comment **inside the last cell** of the row:

```markdown
| 6.3 | Прогнозы по ресурсам заданы | Вопросы, 703 ч | ▼<!-- 6.3 verdict="Существенное" --> |
```

The row still starts with `|` and the pipe-table parser reads it as one normal row. The comment is invisible in any HTML render and survives markdown→HTML conversion unchanged. Extract with a regex on the cell value: `re.search(r'<!--\s*([\w.]+)\s*=\s*"([^"]+)"\s*-->', cell_text)`.

Same trap applies to where you put inline images, footnotes, or any "sidecar" content for a row — they're never separate lines, always embedded.

### P13. Severity-count map keys don't match verdict string language

When a section's per-row metadata values come from a domain vocabulary that uses Russian (or any non-English) terms — "Критическое", "Существенное", "Информационное", "Норма" — and the section's aggregation dict uses English keys — `"critical"`, `"substantial"`, `"informational"`, `"normal"` — the line `sev = r.verdict if r.verdict in severity_counts else "normal"` silently forces every count to `normal` because `"Критическое"` is NOT in `{"critical", ...}`.

Symptom: the section's summary "Критических: N / Существенных: N / Информационных: N / Норма: N" reports total ≈ section size for "Норма", zero for everything else. The per-row verdict IS correct in the MD; only the aggregate counts are wrong.

**Fix:** explicit map, applied both ways (write-side when building counts, read-side when reading):

```python
# Write side: aggregate counts
verdict_to_sev = {
    "Критическое": "critical",
    "Существенное": "substantial",
    "Информационное": "informational",
    "Норма": "normal",
}
for r in results:
    sev_key = verdict_to_sev.get(r.verdict, "normal")
    severity_counts[sev_key] += 1
```

**Read side** (preview render): when the consumer-side helper rebuilds counts from per-row metadata, it MUST apply the same map. Two helpers in two places will drift; either centralise the map in one module both import, or define canonical-form constants in MODEL.md and `assert verdict in K`. When the two sides disagree, you get "preview says 16 normal, table says 2 critical" — silent until someone runs the structured smoke-test against an authoritative HTML reference.

## `diff_specs.py` — schema diff for human review

When you change a schema, run `python3 scripts/diff_specs.py 0.1.0 0.2.0` to see:

- Top-level: added/removed required fields, added/removed properties
- Each `$defs`: added/removed required fields, added/removed properties
- (Doesn't yet compare `type`/`format`/`minimum`/`enum` changes — extend as needed)

The output is plain text. Use it for CHANGELOG entries:

```markdown
## v0.2.0 (2026-08-XX)
- ➕ required: ["summary.indicator_text"] (new required field)
- ➕ properties.sections.s5.overdue[].owner (added optional field)
- ➖ properties.sections.s7.os_version (removed, moved to metadata.mcp_version)
- ➕ $defs.section_forecast.overdue[].notes (free text field)
```

## Reference files (suggested)

| File | Purpose |
|------|---------|
| `references/json-schema-cheatsheet.md` | JSON Schema 2020-12 syntax — `type`, `enum`, `format`, `$ref`, `additionalProperties`, `pattern`, `minimum`/`maximum` |
| `references/migration-strategies.md` | When to use rename-in-place vs split vs merge; chain migration patterns |
| `references/normalize-on-write-recipes.md` | Common normalizers (dates, enums, trailing whitespace, em-dash, null-coercion) |
| `references/working-example-project-health.md` | Annotated walkthrough of `/tmp/project-json-design/` (the canonical v0.1.0 report data model) |
| `references/mcp-attribute-value-write-pitfalls.md` | **Live-probed 2026-08-22.** 10 pitfalls of persisting JSON to MCP via `AttributeValue` (b-tree 2704 limit, 3 payload formats, `save_entity` vs `create_entity`, `find_entity` quirks, `delete_entity` 500 errors, network round-trip dominance, `_meta` provenance). |
| `references/inline-svg-visualization.md` | **Added 2026-08-22.** Playbook for rendering JSON data trends as Inline SVG (line, step, stacked-area, donut, sparkline). Used by future `fst-project-trends` skill for trend reports over `fst-project-health` JSONs. |

## Templates

| File | Purpose |
|------|---------|
| `templates/v0.1.0.json.j2` | Starter JSON Schema skeleton — copy, edit, save as `specs/v0.1.0.json` |
| `templates/migration-template.py` | Boilerplate `def migrate(old: dict) -> dict` with `_meta.schema_version` already updated |
| `templates/_meta-block.json` | Canonical `_meta` block to embed in every produced JSON |

## Canonical example: project-health report data (v0.1.0)

The working example at `/tmp/project-json-design/` (or `references/working-example-project-health.md` in this skill) demonstrates the convention end-to-end:

- **Source:** `/tmp/project_<code>_report.md` produced by `fst-project-health` skill.
- **Schema:** `/tmp/project-json-design/specs/v0.1.0.json` — 4 top-level sections, 6 `$defs` for nested types.
- **Generator:** `/tmp/project-json-design/scripts/generate_json.py` — parses MD → JSON, normalizes verdicts, computes `summary.section_verdicts` from per-section data.
- **Examples:** 4 real reports (`504-314`, `503-434`, `504-595`, `503-152`), all validate against the schema.
- **Reader:** `read_json.py` — accepts any version, warns on outdated, prints readable summary.
- **Migration:** template ready in `migrations/_template.py`; first real migration will be `v0.1.0_to_v0.2.0` when the schema changes.

**Lessons baked into v0.1.0:**

- `overdue_days` typed as `["integer", "null"]` — handles "—" cells and missing data.
- Verdict enum values are normalized to `Болен / Требует внимания / Здоров` (titlecase) regardless of source MD case.
- `_meta` is `required` and has `schema_version` with `pattern: "^[0-9]+\\.[0-9]+\\.[0-9]+$"` — every produced JSON is greppable by version.
- `summary.total_counts` aggregates from `s3`, `s5` (structured counts), AND `s6` (counts derived from `result == "Да"` indicators) — see P3.
- `_raw` and `_legacy` are optional — schema doesn't break if missing.

## Diagnostic recipe

When the user says "the JSON schema is wrong":

```bash
# 1. List current versions
ls specs/

# 2. Diff two versions
python3 scripts/diff_specs.py 0.1.0 0.2.0

# 3. Validate an example against a schema
python3 -c "
import json, jsonschema
data = json.load(open('examples/v0.1.0_504-314.json'))
schema = json.load(open('specs/v0.1.0.json'))
jsonschema.validate(data, schema)  # raises ValidationError if mismatch
print('OK')
"

# 4. Find what changed in a generator
git diff scripts/generate_json.py
# Look for: did normalize_*() get called? is _meta updated? is total_counts computed?
```

When the user says "the migration broke old data":

```bash
# 1. Run every example through the migration
for ex in examples/*.json; do
    python3 scripts/migrate_json.py "$ex" --to latest --output /tmp/migrated.json
    python3 -c "
import json, jsonschema
data = json.load(open('/tmp/migrated.json'))
schema = json.load(open('specs/v0.3.0.json'))  # use current
jsonschema.validate(data, schema)
print('$ex → OK')
"
done

# 2. Inspect what _legacy fields accumulated
python3 -c "
import json
data = json.load(open('/tmp/migrated.json'))
print('Legacy fields:', list(data.get('_legacy', {}).keys()))
"
```

## Working example — `/tmp/project-json-design/`

The living example from 2026-08-21. Use as the canonical shape:

```
project-json-design/
├── README.md                      # design intent + scope
├── MODEL.md                       # current model v0.1.0 (human-readable)
├── specs/v0.1.0.json              # JSON Schema
├── examples/                      # 4 real-data examples
│   ├── v0.1.0_504-314.json
│   ├── v0.1.0_503-434.json
│   ├── v0.1.0_504-595.json
│   └── v0.1.0_503-152.json
├── migrations/
│   ├── __init__.py                # MIGRATIONS registry (empty for v0.1.0)
│   └── _template.py               # boilerplate for future migrations
├── scripts/
│   ├── generate_json.py           # MD → JSON
│   ├── read_json.py               # JSON → readable summary
│   ├── migrate_json.py            # chain migrations
│   └── diff_specs.py              # schema diff
└── docs/
    ├── DESIGN.md                  # 9 ADRs (model design, ADR-001..009)
    └── CHANGELOG.md               # version history
```

## What this skill is NOT

- It is **not** a database schema tool. The JSON Schema describes the wire format; how it's stored (SQL, MongoDB, MCP-backed store) is a separate concern.
- It is **not** an ORM. Each producing skill generates JSON independently; this skill provides the conventions and tooling to make those JSONs interoperable.
- It is **not** a validation framework. Use `jsonschema` (Python) for validation; this skill teaches you **when** to validate (P8).
- It is **not** a versioning system for arbitrary data. Specifically targets structured records with stable subjects (project reports, assessment snapshots, similar).

## Known limitations

- Migrations are Python code, not declarative. Hard to write a generic "automatic migration" — every change is bespoke.
- `diff_specs.py` is shallow — it doesn't compare `type`, `format`, `enum` changes. Extend it as needed (regex on property values).
- Generator currently parses MD; alternative sources (API responses, MCP, DB rows) need their own generators. **Pattern** is portable; **code** is source-specific.
- `_legacy` is unbounded — if you accumulate 100 versions, `_legacy` will be huge. Periodically prune old `_legacy` sub-keys via a "housekeeping" migration.

## Persisting to MCP via `AttributeValue` (live-probed 2026-08-22)

The pattern below was verified end-to-end on Foresight MCP
(`https://ppreplica.hera.pmpractice.ru/mcp`). Read `references/mcp-attribute-value-write-pitfalls.md`
for the full 10-pitfall reference. Quick summary:

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| `create_entity` doesn't exist | `Unknown tool` | Use `save_entity` with `id="new"` |
| **b-tree 2704 byte limit** | `500 - размер строки индекса` | Split JSON into parts via `AttrValueSource` + `_part_data` envelope |
| `find_entity` arg is `name` (not `entityName`) | 400 validation error | Use `get_view` for filtered lookups |
| `get_view` row `id` is internal sequence | Cross-refs break | Use `AttributeValueId` (entity-named) |
| `delete_entity` returns 500 on every format | All variants fail | Use UI; assume append-only |
| `date_start` with `YYYY-MM-DD` fails | `500 - Date type error` | Omit dates or use `YYYY-MM-DDTHH:MM:SS+ZZ:ZZ` |
| `EntityId` is required even with `DataId` | `400 - Foreign key violation` | Always set both |

**Proven write shape (for project-tagged health reports):**

```python
mcp_call(sid, "save_entity", {
    "id": "new",                        # or AttributeValueId for update
    "entityName": "AttributeValue",
    "data": {
        "DataId": "<project_id_string>",
        "EntityId": "46caa4ad-02b8-4d70-a1db-196bab860742",  # Project entity
        "AttributeId": "d78f0b2d-5ec1-4094-9dcb-3bba9f77fc73",  # AI: "Данные отчета Здоровье проекта"
        "AttrValue": "<json_string>",    # < 1200 Cyrillic chars OR split
        "AttrValueSource": "<part_name>", # optional, distinguishes parts
    },
})
```

**When to split (Cyrillic-aware):** if `AttrValue` is > ~1200 Cyrillic chars,
split into parts. Each part is a separate `AttributeValue` with different
`AttrValueSource` (e.g. `_meta`, `summary`, `s3_part1`, `metadata`). Reader
reassembles by collecting all `AttrValue` for the same `(DataId, EntityId, AttributeId)`
group, grouping by `AttrValueSource`.

**End-to-end test that worked (504-595, ProjectId=4595, 2026-08-22):**
- Generate JSON: 0.5 sec
- Upload (6 parts for small JSON, 9 parts for 50 KB): ~10 sec
- Fetch from MCP + reassemble + MD + HTML: 1.79 sec
- Result: 15.5 KB HTML, all 6 sections rendered, 9 status-tagged rows

**Network round-trip is the bottleneck** (~1 sec per HTTP call). Local
parsing, MD generation, and HTML rendering together are <0.1 sec. If you need
bulk read, cache `get_view` results in `/tmp/.cache_<entity>.json` with TTL=5 min.

## Persisting to MCP via `DocumentFile` (live-probed 2026-09-15)

An **alternative write path** to the AttributeValue approach above: attach
JSON files to a project card as a document in a named category tab
(e.g. «Документы ИИ»). This is the path used by `fst-project-health-snapshot`
for weekly snapshot persistence. The two paths have different trade-offs.

| | `AttributeValue` (above) | `DocumentFile` (this) |
|---|---|---|
| Storage | Inline JSON string in attribute | Uploaded binary file |
| Where it shows in UI | Project's custom-attribute panel | Project's Documents tab, by category |
| Best for | Structured key-value lookups, dashboard queries | Human-visible attachments, audit trail |
| Size limit | **~2704 bytes per row** (b-tree, see P-MCP-2) | **No hard limit** — multi-MB files work |
| Delete via API | All formats 500 (see P-MCP-7) | "Нет доступа к удалению" (permission denied) |
| Discoverability | `get_view("AttributeValue")` | `list_files(className, dataId, documentId)` |

### Discovery — find the `documentId` for a category tab

Document categories (tabs) live in the `Document` entity, not `DocumentFile`.
`find_entity("Документ")` does NOT filter by entity type — it returns
`Point` items because that's what matches the literal name. Use `get_view`:

```python
resp = mcp_call(sid, "get_view", {
    "entityName": "Document",
    "viewName": "DocumentView",
    "limit": 100,
})
# Each row has DocumentId, Entity="Проект", Name="Документы ИИ",
# ActivityPhase="Архив, Завершение, Инициирование, Отменено,
#                Подготовка, Постпроектный мониторинг [отключен],
#                Пресейл, Реализация"
```

To find the right row by name, filter client-side. «Документы ИИ» is
**DocumentId=70139** for `entityName="Project"`, bound to all 8 lifecycle
phases. Other categories (e.g. «Паспорт проекта», DocumentId=60093) are
bound to a single phase — pass `activityPhaseId` in the upload call to
land in the correct phase.

If the category doesn't exist, create it with
`save_entity(id="new", entityName="Document", ...)` (see P-MCP-1).

### Write — `upload_entity_file`

```python
import base64
content_b64 = base64.b64encode(json_bytes).decode("ascii")

resp = mcp_call(sid, "upload_entity_file", {
    "entityName": "Project",
    "dataId":      "4595",            # numeric project_id as string
    "documentId":  70139,            # from discovery step above
    "uploadedFileName": "Слепок v0.1.0 504-595 2026-09-15.json",
    "uploadedFileContentBase64": content_b64,
    # activityPhaseId — skip for multi-phase categories, set for single-phase.
})
# resp: {"success": true, "id": <FileId>, "url": "/api/file/get/..."}
```

### Read — `list_files`

```python
files = mcp_call(sid, "list_files", {
    "className": "Project",    # NB: not "entityName" — this method uses className
    "dataId":    "4595",
    "documentId": 70139,
})
# Returns: [{physicalFileId, url, name, fileSize, isLink}, ...]
```

`list_files` uses `className`, not `entityName` — easy mismatch with
other MCP methods.

### The two identification mechanisms (defence in depth)

Both should identify "this JSON is from our snapshot skill", so a
consumer can filter reliably even if one mechanism is corrupted:

1. **Filename prefix** (e.g. `Слепок fst-project-health-snapshot-YYYY-MM-DD_HH-MM-SS.JSON`)
   — visible in UI, easy for humans to scan.
2. **`_meta.generator`** inside the JSON
   (`"fst-project-health-snapshot"`) — machine-readable, survives
   filename renames, version-agnostic.

Either alone is sufficient; both together is robust.

### Append-only assumption

**Both write paths are append-only.** `delete_entity` is unreliable or
disallowed:

- `AttributeValue`: `delete_entity` returns 500 for every known format
  (P-MCP-7).
- `DocumentFile`: `delete_entity` returns `"Удаление не выполнено: Нет
  доступа к удалению"` (permission denied on user-token scope).

Design your consumer around this: never assume you can update by
deleting first. For `AttributeValue`, update by
`save_entity(id=<existing_uuid>, ...)` to rewrite. For `DocumentFile`,
accept that old snapshots accumulate and let humans clean up via UI.

### When to choose which path

- Use **`AttributeValue`** when you need structured query/dashboard access
  (`get_view(AttributeValue, ...)`), when the JSON is small (≤ ~6 KB
  Cyrillic, ~12 KB ASCII), and when you want version-aware reads.
- Use **`DocumentFile`** when the JSON is large, when humans need to see
  the file in the project card's Documents tab, or when the consumer is
  another agent that just needs to fetch and parse a JSON.

The `fst-project-health-snapshot` skill chose `DocumentFile` because
humans reviewing the project card should be able to download the
snapshot without switching screens, and because snapshots will grow
over time as the source schema evolves.


## Workflow: producing a new JSON model from scratch

```bash
# 1. Initialize structure
mkdir -p project-json-design/{specs,examples,migrations,scripts,docs,templates,references}

# 2. Write specs/v0.1.0.json (JSON Schema)
# 3. Write MODEL.md (human-readable)
# 4. Write scripts/generate_json.py (source → JSON)
# 5. Generate first example
python3 scripts/generate_json.py --code 504-314
# 6. Validate
python3 -c "import json, jsonschema; jsonschema.validate(json.load(open('examples/v0.1.0_504-314.json')), json.load(open('specs/v0.1.0.json')))"

# 7. Add migration template
cp migrations/_template.py migrations/v0.1.0_to_v0.2.0.py
# Edit migrate() function

# 8. Document in CHANGELOG.md
```

## Workflow: evolving the schema

```bash
# 1. Edit specs/v0.1.0.json → specs/v0.2.0.json (copy, increment, modify)
# 2. Write migration in migrations/v0.1.0_to_v0.2.0.py
# 3. Register in migrations/__init__.py
# 4. Generate new example from existing data
python3 scripts/migrate_json.py examples/v0.1.0_504-314.json --to 0.2.0 --output examples/v0.2.0_504-314.json

# 5. Validate the migrated example
python3 -c "import json, jsonschema; jsonschema.validate(json.load(open('examples/v0.2.0_504-314.json')), json.load(open('specs/v0.2.0.json')))"

# 6. Run diff_specs to see what changed for the CHANGELOG
python3 scripts/diff_specs.py 0.1.0 0.2.0

# 7. Update MODEL.md to describe new fields
# 8. Bump CHANGELOG.md with the diff output + migration notes
```

This workflow keeps the JSON model **a living artifact** — old data stays readable, new data is well-formed, the diff between versions is always explainable.