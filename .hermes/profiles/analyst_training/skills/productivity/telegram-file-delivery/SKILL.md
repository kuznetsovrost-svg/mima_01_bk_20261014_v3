---
name: telegram-file-delivery
description: "Use when shipping one or more files to the user via Telegram and reliability matters. Send a single file with MEDIA:<abs path>. When the user asks for multiple files one-by-one, bundle into a zip first — sequential MEDIA: lines silently drop most attachments."
version: 1.0.0
author: Hermes Agent + Rostislav Kuznetsov
license: MIT
metadata:
  hermes:
    tags: [telegram, messaging, file-delivery, attachments, hermes-gateway]
    category: productivity
    related_skills: []
---

# Telegram File Delivery

## Overview

The Hermes Telegram gateway extracts `MEDIA:/abs/path` markers from replies and ships the referenced file as a native attachment. For **one file**, this is reliable. For **multiple files in one reply**, it is not — most attachments drop silently and the user sees only the last 1-2. This skill codifies the workaround.

## When to Use

- The user asks to receive files via Telegram ("пришли файл", "send to telegram", "сюда в телеграм").
- You need to ship N files where N ≥ 2 and the user wants them as separate files.
- You're tempted to paste multiple `MEDIA:` lines one after another in a single reply.

## Decision Rule

| Count of files | Method |
|---|---|
| 1 | Single `MEDIA:<path>` — works reliably |
| 2 | Borderline; default to bundling into a zip |
| 3+ | **Always** bundle into a zip, send the zip |

## Why

In a real session (Rost, 2026-07-16, analyst_training profile), 7 sequential `MEDIA:` lines in one reply resulted in only 2 files arriving — the last one and one earlier. Cause: gateway-side rate-limit or send-buffer cap. Adding sleep() between sends did **not** fix it; bundling into a 41 KB zip **did**. The user's preference is explicit: he wants separate files, but reliability beats format when reliability is at stake.

## Procedure

1. **Plan the delivery.** Count files. If N ≥ 2, switch to zip.
2. **If zipping:** use Python's `zipfile` (always available) — `zip`/`unzip` shell binaries may not be installed.
   - Preserve a sensible layout inside the zip (e.g. mirror the source path structure, or flatten to one folder).
   - Use `zipfile.ZIP_DEFLATED` for compression.
3. **Send the zip** with one `MEDIA:<zip-path>` marker.
4. **In the message body**, list what the zip contains so the user can see what's inside before unpacking.
5. **Never** send more than 1 `MEDIA:` line per assistant turn as a safety rule. If the user reports a dropped file, send only that file again.

## Bundling Snippet

```python
import zipfile
from pathlib import Path

zip_path = Path("/tmp/<task>-bundle.zip")
files = [
    Path("/path/to/file1.md"),
    Path("/path/to/file2.md"),
    # ...
]
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for f in files:
        zf.write(f, arcname=f.name)  # or arcname=<relative path>
```

## Pitfalls

- **Assuming `zip` is installed.** It often isn't on minimal containers. Always use Python's `zipfile` module.
- **Sleeping between sends.** Does not fix the multi-`MEDIA:`-line drop. Bundling is the only known fix.
- **Pasting file contents inline "as a fallback".** The user explicitly prefers attachments. Inline paste breaks the workflow (no download, can't open in external viewer, breaks UTF-8 in some clients).
- **Mixing `MEDIA:` with markdown image syntax `![alt](url)` in the same reply.** Image URLs send natively but the gateway may pick up the wrong marker. Send files and images in separate turns if both are needed.

## Verification

Before considering delivery complete, confirm:
- [ ] Exactly one `MEDIA:` line in the assistant reply.
- [ ] For N≥2 files: zip exists, contains all expected entries, total size is sane.
- [ ] Message body lists what's in the bundle so the user can verify without unpacking.
- [ ] If user reports a missing file: re-send **only that file** as a fresh single `MEDIA:`, do not re-bundle.

## Reference

- Observed failure pattern: 7/7 sequential `MEDIA:` lines → 1/7 or 2/7 arrived (Rost, 2026-07-16).
- Hermes docs: `MEDIA:` extraction and extension allowlist documented at `hermes-agent/website/docs/user-guide/messaging/telegram.md`.
- Supported extensions include `.txt`, `.md`, `.pdf`, `.csv`, `.json`, `.xml`, `.yaml`, `.yml`, `.log`, `.docx`, `.xlsx`, `.pptx`, `.zip`, archives, images, audio, video.