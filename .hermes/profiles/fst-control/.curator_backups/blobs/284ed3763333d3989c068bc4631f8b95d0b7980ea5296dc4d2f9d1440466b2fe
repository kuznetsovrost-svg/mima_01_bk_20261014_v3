# Working example: project-health report data model (v0.1.0)

**Date:** 2026-08-21
**Context:** First real application of `versioned-json-data-model` skill, born from `fst-project-health` v0.9.0.

## Why this example exists

The user wanted to **store project-health reports in a database via MCP** for future trend analysis ("строить новый вид отчета по нескольким таким JSON за разные даты"). The current MD/HTML/WORD outputs are **presentation formats**, not **storage formats** — they embed styling, lose structured data, and break on any pipeline change. We needed a stable, versioned JSON that:

1. Captures everything the report uses (sections 3-7, summary, indicator)
2. Survives schema evolution without breaking old data
3. Validates against an explicit schema
4. Carries enough metadata to be self-describing

## Where it lives

All artifacts are at `/tmp/project-json-design/` (kept isolated from `fst-project-health` until the user explicitly asks for integration):

```
project-json-design/
├── README.md
├── MODEL.md                       # human-readable description
├── specs/v0.1.0.json              # JSON Schema (draft 2020-12)
├── examples/                      # 4 real-data examples
├── migrations/
│   ├── __init__.py                # MIGRATIONS registry
│   └── _template.py               # boilerplate for v0.1.0_to_v0.2.0
├── scripts/
│   ├── generate_json.py           # MD → versioned JSON
│   ├── read_json.py               # version-aware summary
│   ├── migrate_json.py            # chain migrations
│   └── diff_specs.py              # schema diff
└── docs/
    ├── DESIGN.md                  # 9 ADRs
    └── CHANGELOG.md               # version history
```

## The model at a glance (v0.1.0)

```json
{
  "_meta": {
    "schema_version": "0.1.0",
    "generated_at": "2026-08-21T22:30:00Z",
    "generator": "fst-project-health",
    "generator_version": "0.9.0",
    "project_code": "504-314",
    "project_id": 4314,
    "source_md_hash": "a7ba0d0c4aeb908b"
  },
  "summary": {
    "verdict": "Болен",
    "verdict_status": "sick",
    "indicator_text": "Проект болен",
    "section_verdicts": {
      "s3": {"verdict": "Болен", "critical": 7, "warning": 4, "info": 2},
      "s4": {"verdict": "Здоров"},
      "s5": {"verdict": "Болен", "critical": 7, "warning": 4, "info": 2},
      "s6": {"verdict": "Болен"}
    },
    "total_counts": {"critical": 14, "warning": 10, "info": 2}
  },
  "sections": {
    "s3": {"verdict": "Болен", "counts": {...}, "remarks": [...]},
    "s4": {"verdict": "Здоров", "indicators": [...], "effort": {...}, "budget": {...}},
    "s5": {"verdict": "Болен", "counts": {...}, "overdue": [...]},
    "s6": {"verdict": "Болен", "indicators": [...], "raw": {...}},
    "s7": {"rows": [...]},
    "s8": {"status": "Болен", "table": [...]}
  },
  "metadata": {
    "user": "...",
    "metamodel_title": "Копия прода для MCP",
    "metamodel_core_version": "2026.8.21.1040",
    "mcp_url": "https://ppreplica.hera.pmpractice.ru/mcp",
    "mcp_version": "v3.2.4"
  }
}
```

## What each section captures

| Section | Source (in `fst-project-health`) | Captures |
|---------|----------------------------------|----------|
| `_meta` | generated at runtime | version, timestamp, generator, project IDs |
| `summary` | aggregate of all sections | overall verdict + per-section + counts |
| `sections.s3` | `/tmp/section_3_result.md` | KТ with `forecast != plan`, color, status |
| `sections.s4` | `run_all.build_section_4()` | 5 indicators (Owner, Leader, Passport, Effort, Budget) + Effort + Budget summaries |
| `sections.s5` | `/tmp/section_5_result.md` | КТ where `forecast < today` and `fact IS NULL` |
| `sections.s6` | `run_all.build_section_6()` | 3 financial indicators + raw ProjectHealthCostMy numbers |
| `sections.s7` | `run_all.build_section_7()` | technical metadata (5 rows) |
| `sections.s8` | `/tmp/section_8_result.md` | summary indicator table |
| `metadata` | `mcp_config.MCP_URL` + MetaModel | URL MCP, metamodel fields |
| `_raw` (optional) | raw MCP responses | for audit / future reproducibility |
| `_legacy` (optional) | removed fields from older versions | preserved on rename/delete |

## Lessons baked into v0.1.0 (already documented in SKILL.md as P1-P10)

These are the specific quirks that bit us during v0.1.0 implementation:

- **P1:** verdict enum case mismatch — source MD used `БОЛЕН` (uppercase); schema enum was `Болен` (titlecase). Fixed by `normalize_verdict()` helper.
- **P2:** `overdue_days` was sometimes `"—"` (em-dash) in source MD; schema required `integer`. Fixed by `type: ["integer", "null"]`.
- **P3:** `total_counts` was wrong because generator summed `s3` + `s5` but not `s6` (where criticality is `result == "Да"`). Fixed by per-section aggregation.
- **P4:** Generator copied raw cells verbatim — including trailing whitespace in names, em-dashes in dates, etc. Fixed by normalize-on-write.
- **P5 (anticipatory):** Migration must update `_meta.schema_version` to target.
- **P8 (anticipatory):** Generator must run `jsonschema.validate()` before commit.

## Validation: all 4 examples pass

```bash
$ python3 -c "
import jsonschema, json
schema = json.load(open('specs/v0.1.0.json'))
for code in ['504-314', '503-434', '504-595', '503-152']:
    data = json.load(open(f'examples/v0.1.0_{code}.json'))
    jsonschema.validate(data, schema)
    print(f'  ✅ {code}: валиден ({data[\"summary\"][\"verdict\"]})')
"

✅ 504-314 (12,509 bytes) — verdict: Болен
✅ 503-434 (15,419 bytes) — verdict: Болен
✅ 504-595 (6,267 bytes) — verdict: Болен
✅ 503-152 (58,975 bytes) — verdict: Болен
```

## Future evolution path (when user gives the green light)

Once the user accepts v0.1.0:

1. **v0.2.0:** add `_raw` content for projects where live-MCP snapshot is meaningful (504-595, 504-314 — projects with `?ProjectId` server-side filter applied).
2. **v0.3.0:** add `metadata.session_id` to correlate reports run in the same session.
3. **v0.4.0:** when `Word Форма 1`/`MD Форма 2` content is stabilized, add `sections.s7.word_output_available: bool` so trend queries know which rows have printable versions.
4. **v1.0.0:** freeze schema, start requiring explicit migration paths for any new field.

Each migration:

- `migrations/v0.X.Y_to_v0.A.B.py` with `def migrate(old: dict) -> dict`
- Register in `migrations/__init__.py:MIGRATIONS`
- Update `examples/` with migrated examples
- Update `MODEL.md`
- Add CHANGELOG entry

## Anti-patterns observed (for future reference)

When designing v0.2.0, watch for:

- **Adding fields to `required`** — this breaks old data. Add as optional instead.
- **Renaming fields without `_legacy`** — old data becomes unreadable. Move to `_legacy.<old_name>` first.
- **Removing `_raw` to "simplify"** — it may be the only way to reproduce a decision. Move old `_raw` to `_raw.v0_X_Y_snapshot` instead.
- **Skipping jsonschema validation** — invalid JSON propagates to all readers. Always validate at generation time.

## Files referenced

- `references/json-schema-cheatsheet.md` (to be written)
- `references/migration-strategies.md` (to be written)
- `references/normalize-on-write-recipes.md` (to be written)
- All artifacts at `/tmp/project-json-design/`