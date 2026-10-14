# MCP write pitfalls: AttributeValue for project-tagged data

**Date:** 2026-08-22
**Live-probed against:** Foresight PMForesight MCP `https://ppreplica.hera.pmpractice.ru/mcp`
**Skill origin:** `fst-project-health` v0.9.0 JSON reports

This file documents the **real** write-cycle pitfalls encountered when persisting
versioned JSON model output to MCP via the `AttributeValue` entity. Every pitfall
below was reproduced on a live server. Use as a checklist before persisting any
JSON to MCP-backed storage.

## The setup that works (verified 2026-08-22)

```python
from mcp_config import mcp_init, mcp_call

sid, _ = mcp_init(client_name="upload-<project_id>")

# 12 fields total in AttributeValue. Required: DataId, EntityId, AttributeId.
# Optional but useful: AttrValue, AttrValueSource, date_start, date_stop.
resp = mcp_call(sid, "save_entity", {
    "id": "new",                    # "new" for create, existing UUID for update
    "entityName": "AttributeValue",
    "data": {
        "DataId": "<subject_id_string>",  # e.g. "4314" for project 504-314
        "EntityId": "<entity_uuid>",      # see table below
        "AttributeId": "<attribute_uuid>", # see table below
        "AttrValue": "<json_string>",      # the actual payload
        "AttrValueSource": "<part_name>", # optional: distinguish parts of split JSON
    }
})
# Returns: {AttributeValueId, DataId, EntityId, AttributeId, AttrValue, ...}
```

| Subject | EntityId UUID |
|---------|---------------|
| Project | `46caa4ad-02b8-4d70-a1db-196bab860742` |
| (other entity types require their own EntityId) |

For project-tagged health reports:
`AttributeId = d78f0b2d-5ec1-4094-9dcb-3bba9f77fc73` (AI: "Данные отчета Здоровье проекта").

## P-MCP-1. `create_entity` does not exist — use `save_entity` with `id="new"`

`tools/list` shows 12 tools for Foresight MCP. There is no `create_entity`. The
write tool is `save_entity` with the convention `id="new"` for create, or
`id=<existing_uuid>` for update.

```python
# ❌ UNKNOWN TOOL
mcp_call(sid, "create_entity", {"entityName": "AttributeValue", "data": {...}})

# ✅ CORRECT
mcp_call(sid, "save_entity", {"id": "new", "entityName": "AttributeValue", "data": {...}})
```

**Check:** `python3 scripts/mcp_probe.py --tools | grep -E 'create|save'` — if
`create_entity` is missing, use `save_entity` + `id="new"`.

## P-MCP-2. PostgreSQL b-tree limit (2704 bytes) on composite indexes

**Live error** (504-314, 12.5 KB JSON, 2026-08-22):

```
HTTP 500 — Ошибка запроса к /entity/AttributeValue/new
PostgreSQL: размер строки индекса (2992) больше предельного
для btree версии 4 размера (2704)
(индекс "ix_attributevalue_data_entity_attribute")
```

| Project | ProjectId | JSON size (bytes) | Error? | Why |
|---------|-----------|-------------------:|--------|-----|
| 504-595 | 4595 | 6 267 | ✅ OK | within limit |
| 504-314 | 4314 | 12 509 | ❌ row=2992 | too big |
| 503-434 | 3434 | 15 419 | ❌ row=3360 | too big |
| 503-152 | 3152 | 58 975 | ❌ row=7792 | way too big |

**Root cause:** The unique composite index `ix_attributevalue_data_entity_attribute`
includes the indexed `AttrValue` (or its prefix) as part of the b-tree key.
PostgreSQL b-tree v4 hard limit is **2704 bytes per row**. Exceed it → 500 error.

**Cyrillic multiplier:** UTF-8 Cyrillic = **2 bytes/char**. So a "1200-char" Russian
JSON is actually **2400+ bytes** on the wire. The safe upper bound is around
**1200–1300 Cyrillic characters** per `AttrValue` payload.

**Three workarounds** (in order of preference):

1. **Request a partial index** from the dev team — `WHERE length(AttrValue) < 1000`
   instead of a full unique index. (Documented in the v2 letter to devs.)
2. **Split the JSON into parts** and write each as a separate `AttributeValue` with
   different `AttrValueSource` and `date_start`/`date_stop` markers. Reassemble at
   read time. See `parse_attr_values()` and `reassemble_json()` in
   `scripts/build_html_from_mcp.py` for the pattern.
3. **Move large sections** to other entities (separate JSON storage, file
   system, or a dedicated `ProjectHealthReport` entity). For now, split is the
   only option that works without server changes.

**Check:** after writing, look for `500 - размер строки индекса` in the response.
If the limit is `>2704`, split.

## P-MCP-3. Three `AttrValue` payload formats coexist

When you split a JSON across multiple `AttributeValue` records, you have **three
on-the-wire shapes** and your reader must accept all of them.

### Format 1: full JSON (single record, payload < ~6 KB)

```json
{
  "_meta": {"schema_version": "0.1.0", "project_code": "504-595", ...},
  "summary": {"verdict": "Болен", ...},
  "sections": {"s3": {...}, "s4": {...}, ...}
}
```

**When used:** small JSON fits in one record.

### Format 2: split with `_part_data` envelope (current best practice)

```json
{
  "_part_name": "summary",
  "_part_data": {
    "verdict": "Болен",
    "section_verdicts": {...},
    "total_counts": {...}
  }
}
```

**When used:** split into parts, each ≤1200 chars. Reader extracts `_part_data`
and uses `_part_name` as the key in the reassembled dict.

### Format 3: split with `_part_name` only (legacy / no envelope)

```json
{
  "_part_name": "summary",
  "verdict": "Болен",
  "section_verdicts": {...}
}
```

**When used:** older data without the `_part_data` envelope. Reader must strip
`_part_name` and treat the rest as the data.

**Reader pattern (handle all 3):**

```python
def parse_attr_values(records):
    parts = {}
    for row in records:
        raw = row.get("AttrValue", "")
        if not raw or not isinstance(raw, str):
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(data, dict):
            continue

        # Format 1: full JSON
        if "_meta" in data and "summary" in data and "sections" in data:
            parts["_full"] = data
        # Format 2: split with envelope
        elif "_part_data" in data and isinstance(data["_part_data"], dict):
            source = data.get("_part_name") or row.get("AttrValueSource") or "_unknown"
            parts[source] = data["_part_data"]
        # Format 3: split without envelope
        elif "_part_name" in data:
            source = data["_part_name"]
            parts[source] = {k: v for k, v in data.items() if k != "_part_name"}
        # Unknown — keep as-is
        else:
            source = row.get("AttrValueSource") or "_unknown"
            parts[source] = data
    return parts
```

**Check:** before committing a generator, write all 3 formats to test data,
round-trip them through the reader, verify the output equals the input.

## P-MCP-4. Date format: ISO date string vs timestamp-with-tz

**Live error** (504-595, 2026-08-22):

```
HTTP 500 — Ошибка приведения значения '2026-08-21' к типу 'Date'
поля 'date_start' сущности 'public.AttributeValue'
```

**Working format:** `2026-08-21T00:00:00+03:00` (full ISO-8601 with timezone) or
`2026-08-21T00:00:00Z` (UTC). The server accepts these and stores them in
`date_start`/`date_stop` `timestamp without time zone` columns.

**Failing format:** `2026-08-21` (date-only). The server tries to coerce to
`Date` type and fails.

**Workaround:** either omit `date_start`/`date_stop` (they're optional), or use
the full ISO-8601 timestamp. For this experiment, both fields were omitted and
work proceeded without date filtering.

**Check:** after writing, look for `500 - Ошибка приведения значения.*Date` in
the response. If the format you sent is `YYYY-MM-DD`, switch to
`YYYY-MM-DDTHH:MM:SS+ZZ:ZZ`.

## P-MCP-5. `find_entity` argument is `name`, not `entityName`

Live error:

```
3 validation errors for call[find_entity]
name      Missing required argument
entityName Unexpected keyword argument
```

`find_entity` only accepts `name` (the entity name as a string) plus `limit` and
`offset`. There's no way to filter by criteria from `find_entity` itself — for
filtered lookups, use `get_view` with a view that has the right filter, or
`get_entity_data` if you already know the ID.

```python
# ❌ validation error
mcp_call(sid, "find_entity", {
    "entityName": "AttributeValue",
    "criteria": {"DataId": "4595"},
    "limit": 50,
})

# ✅ use get_view with appropriate viewName
resp = mcp_call(sid, "get_view", {
    "entityName": "AttributeValue",
    "viewName": "AttributeValue",  # or a view with ?ProjectId= filter
    "limit": 500,
})
rows = resp.get("data", [])
target = [r for r in rows if str(r.get("DataId")) == "4595"]
```

## P-MCP-6. `get_view` returns `data` array with `id` field — not the entity's primary key

The first column in every `get_view` row is `id` — an internal sequence
**unrelated to the entity's own UUID**. For `AttributeValue`, the actual primary
key is `AttributeValueId`.

```python
rows = mcp_call(sid, "get_view", {
    "entityName": "AttributeValue",
    "viewName": "AttributeValue",
    "limit": 500,
})["data"]

# ❌ row["id"] might be 1, 2, 3... (internal sequence, NOT a UUID)
attr_value_id = row["id"]

# ✅ use AttributeValueId for the actual key
attr_value_id = row.get("AttributeValueId")
```

**Pitfall:** the internal `id` is **stable but meaningless** for cross-MCP
references. Always use the entity-named field (e.g. `AttributeValueId`,
`ProjectId`).

## P-MCP-7. `delete_entity` accepts `remove` array — but format is undocumented

Live-probed 4 formats. All but one returned 500. The schema says:

```json
{
  "remove": {"type": "array", "items": {}},
  "cascade_delete": {"type": "boolean", "default": false}
}
```

**Items shape is `{}` (empty schema)** — server doesn't document what goes inside.
Live results:

| Body | Response |
|------|----------|
| `{"entityName": "AttributeValue", "id": "00ab000f-..."}` | 400 — `entityName`/`id` are not valid named args |
| `{"remove": [{"entityName": "AttributeValue", "id": "00ab000f-..."}]}` | 500 — `Cannot perform runtime binding on a null reference` |
| `{"remove": ["AttributeValue\|00ab000f-..."]}` | 500 — `'string' does not contain a definition for 'entityName'` |
| `{"remove": [{"classid": "cb750276-...", "id": "00ab000f-..."}]}` | 500 — `Cannot perform runtime binding on a null reference` |

**Workaround:** ask the dev team to document the format, or use the Форсайт UI to
delete records manually. As of 2026-08-22, no programmatic delete path is known.

**Implication for the model:** the model assumes **append-only** semantics. If
you need to update a record, **rewrite** it (use `save_entity` with the existing
`AttributeValueId` as `id`). Never assume a record can be deleted via API.

## P-MCP-8. Every record needs `EntityId` even if `DataId` identifies the project

The MCP data model is **denormalized**: `DataId` is a string that points to
the project's ID, but `EntityId` (UUID) tells the server **which type of
entity** `DataId` refers to. The two together disambiguate.

```python
# ❌ incomplete
data = {
    "DataId": "4314",
    "AttributeId": "d78f0b2d-...",
    "AttrValue": "...",
}

# ✅ correct
data = {
    "DataId": "4314",
    "EntityId": "46caa4ad-02b8-4d70-a1db-196bab860742",  # Project entity
    "AttributeId": "d78f0b2d-...",
    "AttrValue": "...",
}
```

**Check:** if writing returns `400 - Foreign key violation` or `500 - cannot
insert NULL into "EntityId"`, you forgot `EntityId`. The UUIDs are
entity-specific — query `describe_entity(Project)` to get Project's
`classid`.

## P-MCP-9. Network round-trip dominates write time — batch if possible

Live-probed latencies (504-595, 2026-08-22, single-part writes):

| Step | Time |
|------|-----:|
| `mcp_init` (or reuse) | ~0.5 sec |
| `save_entity` HTTP round-trip | ~0.7–1.0 sec |
| **`get_view` (read 12 records)** | **~1.7 sec** |
| **`build_html_from_mcp` end-to-end (fetch + parse + MD + HTML)** | **~1.8 sec** |
| `rebuild_md` (local) | <0.01 sec |
| `build_html_report.main` (local, in-process) | <0.01 sec |

**Bottleneck is always the network**, not the parsing or rendering. If you're
writing multiple parts, you can parallelize via `concurrent.futures.ThreadPoolExecutor`
since MCP-сессия is thread-safe. If you're reading, you can cache `get_view`
results in `/tmp/.cache_<entity>.json` with TTL=5 minutes.

**Check:** measure with `time.time()` around each phase. If the network
phase is >50% of total time, optimize the network (parallelize, cache, or
batch) — not the local code.

## P-MCP-10. `_meta.generator` + `generator_version` enable future migration

When you persist JSON via MCP, always include in the payload (or its envelope):

```json
{
  "_meta": {
    "schema_version": "0.1.0",
    "generated_at": "2026-08-22T11:25:46+03:00",
    "generator": "fst-project-health",
    "generator_version": "0.9.0",
    "project_code": "504-314",
    "project_id": 4314
  }
}
```

`generator` + `generator_version` are the **provenance** — when the data model
changes (e.g. v0.1.0 → v0.2.0), a future agent reading old records knows which
producer version to look for in the migration code. Without these, you have
data with no way to know which migration path to apply.

**Live example (504-595, 2026-08-22):** an `AttrValue` was written with
`"generator": "fst-project-health"` and `"generator_version": "0.9.0"`. When
`fst-project-health` is bumped to v1.0.0, the migration script can
introspect the `generator_version` and apply appropriate defaults for v0.9.0
data.

## Diagnostic recipe

```bash
# 1. Check which tools are available
python3 scripts/mcp_probe.py --tools

# 2. Check if AttributeValue view exists
python3 scripts/mcp_probe.py --tool get_view \
    --args '{"entityName":"AttributeValue","viewName":"AttributeValue","limit":5}'

# 3. Get UUIDs
python3 scripts/mcp_probe.py --tool list_entities | python3 -c "
import json, sys
data = json.load(sys.stdin)
for e in data:
    print(e['Name'], '->', e.get('EntityId'))
"

# 4. Describe AttributeValue schema
python3 scripts/mcp_probe.py --tool describe_entity \
    --args '{"entityName":"AttributeValue","data_id":"new"}' | python3 -c "
import json, sys
content = json.load(sys.stdin)
for name, p in content['properties'].items():
    print(f'  {name}: {p[\"type\"]} required={p.get(\"IsRequired\")}')
"

# 5. Test write of minimal payload
python3 -c "
import sys
sys.path.insert(0, 'scripts')
import mcp_config
sid, _ = mcp_config.mcp_init()
resp = mcp_config.mcp_call(sid, 'save_entity', {
    'id': 'new',
    'entityName': 'AttributeValue',
    'data': {'DataId': '4314', 'EntityId': '46caa4ad-02b8-4d70-a1db-196bab860742',
             'AttributeId': 'd78f0b2d-5ec1-4094-9dcb-3bba9f77fc73',
             'AttrValue': '{\"test\": \"probe\"}'}
})
print(resp)
"
```

## End-to-end test: JSON → MCP → report HTML

This is the **proven path** for storing structured reports and rebuilding them:

```bash
# 1. Generate JSON from source data
python3 project-json-design/scripts/generate_json.py --code 504-595
# → /tmp/project-json-design/examples/v0.1.0_504-595.json

# 2. Upload to MCP (split if necessary)
python3 project-json-design/scripts/upload_split.py --code 504-595
# → creates multiple AttributeValue records with AttrValueSource = part name

# 3. Read back from MCP, reassemble, generate HTML
python3 project-json-design/scripts/build_html_from_mcp.py --project-id 4595
# → /tmp/project_from_mcp_report.html (15.5 KB)
```

**Total time:** ~10 sec for a 6-KB JSON, ~60 sec for a 50-KB JSON with 9 parts.

**Live benchmark (504-595, 2026-08-22):**

| Stage | Time |
|-------|-----:|
| `get_view` (12 records) | 1.68 sec |
| Parse + reassemble | <0.01 sec |
| Validate schema | 0.10 sec |
| JSON → MD | <0.01 sec |
| MD → HTML | <0.01 sec |
| **TOTAL** | **1.79 sec** |

## Letter to MCP developers (v2, 2026-08-22)

If you need to write back to the dev team, the **second letter**
(`Письмо_разработчикам_MCP_2026_08_22_v2.md`) covers:

- 4 projects tested (Code + ProjectId)
- Exact error text per project (with row sizes)
- 4 deletion format attempts with responses
- List of 33 test records for cleanup
- 3 suggested workarounds for the b-tree limit

The first letter (`Письмо_разработчикам_MCP_2026_08_22.md`) is shorter and covers
just the delete issue.
