# PMForesight file round-trip: upload → list → verify → download

Recipe for moving a file into a project card and reading it back, useful
for self-contained snapshots (MD, JSON, JSON-derived artifacts). The
PMForesight MCP exposes file storage as a side-channel of any entity
(commonly `Project`); the `documentId` argument selects the category.

Use this whenever you need to prove that an artifact written to a project
card is byte-identical to the original on disk — or whenever you need to
read one back as part of a verification run.

## When to use

- Persisting a self-contained snapshot (MD, JSON) into a project card for
  audit, history, or downstream consumption.
- Verifying that an existing snapshot in MCP is intact (round-trip test).
- Restoring a historical artifact to disk for re-render (paired with
  `fst-project-health/build_html_report.py --md PATH`).

Do NOT use this for read-only inspection (`fst-mcp-tester` covers that) —
the call surface here is write-capable and gates a destructive op.

## Slot map (PMForesight specifics)

| Argument | Value | Meaning |
|---|---|---|
| `entityName` | `"Project"` (или любой класс с прикреплёнными документами) | What owns the file. |
| `dataId` | project ID as STRING (`"4595"`) | `find_entity` returns it as int in `url.rsplit("/",1)[-1]`; pass as string per Pydantic. |
| `documentId` | `70139` для «Документы ИИ», другие категории — свои | Slot within the card. |
| `uploadedFileName` | `<prefix>-<code>-<YYYY-MM-DD_HH-MM-SS>.<ext>` | Use uppercase `.MD` to match convention. |
| `uploadedFileContentBase64` | `base64.b64encode(bytes).decode("ascii")` | File body. |

The `documentId` is per-deployment — discover via `mcp_call(sid,
"describe_entity", {"entityName": "Project"})` and grep the
`allowed_values` for known categories («Документы ИИ», «Документы»,
«Результаты» etc.). For Foresight v3.x the «Документы ИИ» slot is 70139.

## 4-step recipe

### 1. Initialize MCP (with handshake)

```python
sid, info = mcp_init(client_name="roundtrip")
# mcp_init() already sends `notifications/initialized` after `initialize`.
# Skipping the notification causes `tools/call` to silently 200 with
# `isError: true` on some servers — see Pitfall #37.
```

### 2. Upload (`upload_entity_file`)

```python
import base64
content = Path(local_path).read_bytes()
res = mcp_call(sid, "upload_entity_file", {
    "entityName": "Project",
    "dataId": str(project_id),
    "documentId": DOCUMENT_ID_AI,        # e.g. 70139
    "uploadedFileName": file_name,
    "uploadedFileContentBase64": base64.b64encode(content).decode("ascii"),
})
# Success shape: {"success": true, "id": <int>, "name": "...", "url": "..."}
# Failure: result.isError == true (no exception).
assert res.get("success"), res
file_id = res["id"]
```

`upload_entity_file` accepts any payload size that fits in
`AttributeValue` storage (see Pitfall #15 — PMForesight has a
`b-tree 2704` byte composite-index cap on a different table; the file
body slots into a separate path that does not share that limit, but
verify with a 50 KB test before relying on bulk uploads).

### 3. List and discover (`list_files`)

```python
files = mcp_call(sid, "list_files", {
    "documentId": DOCUMENT_ID_AI,
    "dataId": project_id,                # int OK here, only `get_entity_data` requires str
    "className": "Project",
})
# Response is a LIST (not wrapped in {"items": [...]}). Each item:
#   {physicalFileId: "<uuid>", name: "...", fileSize: <int>, url: "...", isLink: bool}
```

The `className` argument is mandatory — without it the server returns
empty regardless of `dataId`. Discover via
`describe_entity(entityName="Project")` for the canonical
`ClassName`.

### 4. Read back (`get_file_info` + `resources/read`)

```python
target = next(f for f in files if f["name"] == file_name)
phys = target["physicalFileId"]

info = mcp_call(sid, "get_file_info", {"physicalFileId": phys})
# {physicalFileId, fileName, fileSize, mimeType, url, contentMode: "bytes" | "url"}

read = mcp_call(sid, "resources/read", {
    "uri": f"file://download-file/{phys}",
})
# shape: result.contents[0].{uri, mimeType, blob: "<base64>"}
import base64
downloaded = base64.b64decode(read["contents"][0]["blob"])
```

The `file://download-file/{physicalFileId}` URI scheme is the only
documented download transport. There is no `download_file` tool — only
this resource URI. (Servers with a heavy `contentMode="url"` return
empty `blob` and force you to GET `info.url` directly.)

### Verification (byte-identity check)

```python
import hashlib
src = Path(local_path).read_bytes()
assert hashlib.sha256(src).hexdigest() == hashlib.sha256(downloaded).hexdigest(), (
    "round-trip mismatch — PMForesight may have rewritten line endings "
    "or inserted a BOM; check info.mimeType and re-decode as utf-8"
)
```

A byte-identical round-trip proves MCP storage is transparent for the
content types stored in «Документы ИИ» slots. Live-probe on
504-595: 14 210 bytes MD up, 14 210 bytes MD down, sha256 identical.

## Timing (PMForesight v3.2.4, 504-595)

| Step | p50 | Notes |
|---|---|---|
| `mcp_init` | 200–300 ms | One-time per session. |
| `upload_entity_file` | ~4 900 ms (14 KB) | Proportional to payload size. |
| `list_files` | ~1 900 ms | Server-side filter on `dataId`. |
| `get_file_info` | ~2 600 ms | Includes URL signing. |
| `resources/read file://download-file/...` | ~12 500 ms | Two-step base64 encode inside the response. |
| SHA-256 + compare | <1 ms | Local. |

Round-trip total for a 14 KB snapshot: ~22 s. Worth caching the
downloaded bytes; the MCP side is cacheable at the resource-URI level
for ~5 minutes using a standard ETag check.

## Pitfalls & gotchas

### Pitfall #37 (NEW): `notifications/initialized` is required, not optional

Calling `mcp_call(sid, ...)` immediately after `mcp_init()` without
the `notifications/initialized` JSON-RPC notification can result in
HTTP 200 with `isError: true` and a useless `Bad Request: No
mcp-session-id` — or, on PMForesight v3.x, silent success on
`initialize` followed by `tools/call` returning `[Tool result
missing due to internal error]`. Always send the notification:

```python
requests.post(URL, json={
    "jsonrpc": "2.0", "method": "notifications/initialized"
}, headers={**headers, "mcp-session-id": sid}, timeout=10)
```

Some MCP clients treat it as no-op; PMForesight treats its absence as
"session not ready." When a sequence of `tools/call` returns
inconsistent errors, this is the first thing to verify.

### Pitfall #38 (NEW): SSE JSON-parsing trap on cyrillic responses (recap of P7a)

`requests.Response.text` + `r.json()` will throw `JSONDecodeError:
Unterminated string` on responses containing cyrillic payloads from
PMForesight (e.g. `instructions` field of the server info). The fix
already lives in `mcp_config.parse_sse_response()` — use it, or
replicate the idiom:

```python
body = r.content.decode("utf-8", errors="replace")   # NOT r.json()
```

Without this, the `upload_entity_file` call appears to work but the
follow-up JSON parse fails — masking the real round-trip behavior.

### Pitfall #39 (NEW): `dataId` vs `data_id` — different tools, different casing

- `upload_entity_file` and `list_files` accept `dataId` (camelCase).
- `get_entity_data` requires `data_id` (snake_case) **as a string**.

Mismatching casing silently returns empty data, not an error. Audit
any helper that copies request payloads between tools.

### Pitfall #40 (NEW): `contentMode="url"` for large files

When `get_file_info` returns `contentMode="url"` (typically payloads
>~10 MB), `resources/read` returns `blob=""` and the actual content
must be fetched via the `info.url` field. The skill does NOT auto-
detect this — callers must branch on `info["contentMode"]`:

```python
if info.get("contentMode") == "bytes":
    body = base64.b64decode(res["contents"][0]["blob"])
else:
    import requests
    body = requests.get(info["url"], headers={"Authorization": f"Bearer {token}"}).content
```

### Pitfall #41 (NEW): bytes-vs-str decoding round-trip

A byte-identical round-trip is the strongest verification, but
suffers one failure mode: PMForesight has been observed to send
non-UTF-8 byte sequences through the resource URI for some
binary types. Always compare `sha256` of raw bytes, not decoded text.

## Verification checklist

- [ ] `mcp_init()` returns `(sid, server_info)` — record server version.
- [ ] `notifications/initialized` is sent before first `tools/call`.
- [ ] `upload_entity_file` returns `success=true` and a numeric `id`.
- [ ] `list_files` for the same `(documentId, dataId, className)` finds the upload.
- [ ] `physicalFileId` from `list_files` matches the round-trip candidate.
- [ ] `get_file_info.fileSize` matches original payload size.
- [ ] `resources/read file://download-file/{physicalFileId}` returns non-empty `blob` (or `contentMode=url`).
- [ ] `sha256(downloaded) == sha256(source)` for full byte-identity proof.

## Reuse

The same recipe works for any MCP server implementing `upload_entity_file`
+ `list_files` + the `file://download-file/{id}` URI scheme — the
argument names may differ (`uploadFile` vs `upload_entity_file`,
`physicalFileId` vs `fileId`) but the four-step shape is portable.
Patch the field-name table above for the target server; everything else
transfers unchanged.
