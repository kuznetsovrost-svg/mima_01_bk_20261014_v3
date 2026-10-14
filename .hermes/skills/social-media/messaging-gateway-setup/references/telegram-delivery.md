# Telegram / Matrix delivery preferences & format limits

User-level preferences for how long artifacts and inline answers should
look on this host. Read this when:

- User asks you to "пришли сюда в телеграм в виде файла"
- User asks for a long artifact (guide, report, plan, audit, spec)
- User complains a previous answer looked wrong (table rendering,
  message truncation, "rich message" confusion)
- You need to decide between inline text vs file attachment
- A previous `MEDIA:` delivery apparently failed (user says "не пришли")

## TL;DR

1. **Long artifacts go to a file** and get attached via the
   `MEDIA:/absolute/path` syntax. The chat body carries a one-line
   summary plus `MEDIA:...` on its own line.
2. **Markdown tables** (`| col1 | col2 |`) **do not render in
   Telegram chat body**. Put tabular data in the file; put a
   bullet-list or monospace code-block in the body.
3. **Telegram message body** is capped at 4096 chars — anything
   longer WILL get truncated or auto-split. Anything over ~60
   lines is a file.
4. **HTML / XHTML / Mermaid / SVG** are NOT rendered as inline
   rich media. Files only.
5. **`MEDIA:` is a hint, not a delivery guarantee.** If the user
   says "не пришли", do NOT re-print the `MEDIA:` line. Switch to
   direct `curl sendDocument` against `api.telegram.org` using the
   bot token from `~/.hermes/.env` and the `chat_id` recovered
   from `~/.hermes/logs/gateway.log` — see Pitfall 6 below.
6. **`hermes send` CLI: `MEDIA:` sends IMAGES; `[[as_document]] MEDIA:` sends FILES.** For documents (`.md`, `.txt`, `.pdf`, any non-image), use the `[[as_document]]` modifier or the file arrives as literal text — see Pitfall 7 below.

## Why: the rendering constraints (verified 2026-07-02 on this host)

### Telegram chat body (the `MEDIA:` shortcut excepted)

| Feature                              | Renders? | Notes                        |
|--------------------------------------|----------|------------------------------|
| Bold / italic / strikethrough        | yes      | `**bold**`, `*italic*`, etc. |
| Inline code (`backticks`)            | yes      | monospace font               |
| Code blocks (triple backticks, ≤20 lines) | yes | monospace, no scroll bars   |
| Code blocks > 20 lines               | partial  | client scrolls, but loses alignment |
| Markdown pipe-table                  | **NO**   | server strips, arrives as row-blocks |
| Headers (`#`, `##`, etc.)            | NO       | Telegram flattens them       |
| Links                                | partial  | bare URLs visible; `[text](url)` rendered in some clients |
| HTML inline tags                     | NO       | shown as raw text            |
| Mermaid / SVG inline                 | NO       | shown as raw text            |
| Inline-keyboard reply-markup         | yes      | only via the chat-platform adapter, not stdlib markdown |
| Voice / video bubble                 | yes      | only via TTS / native send   |

### Telegram file attachment (`MEDIA:/path`)

| Extension            | Renders inline (preview)? | Notes                |
|----------------------|---------------------------|----------------------|
| `.md`                | yes, with markdown        | client shows preview |
| `.txt`               | yes, plain                | client shows preview |
| `.csv`               | as table                  | Excel-friendly       |
| `.json` / `.yaml`    | yes, syntax-highlighted    |                      |
| `.png` / `.jpg`      | yes, photo                |                      |
| `.pdf`               | yes, document             |                      |
| `.zip`               | NO (just download icon)   |                      |

## Rule 1: long artifact → file + short summary

When the user asks for any of:

- a guide or howto
- a report or analysis
- a config spec, audit, or plan
- a chunked dump or extraction
- a long-form answer that you know exceeds ~60 lines

Default to:

```bash
# 1) Write the full answer to a file
write_file /root/<Topic>.md "<full content, ≥ ~30 lines>"

# 2) Send a one-line summary in chat, ending with MEDIA:
#    Use bold for filename/size, then a one-line description,
#    then MEDIA: on its own line.
send_message text "
✍ **Topic_01.txt** — ~24 КБ

Полный гайд: ...

MEDIA:/root/Topic_01.txt
"
```

The Telegram gateway's `MEDIA:` prefix is recognized by the platform
adapter on this host (`MMRV_Hermes_bot`). When the gateway is healthy
AND the file exists AND the prefix is on its own line, it triggers a
native file attachment. **But this is NOT a guarantee** — see Pitfall 6.

If the user says "paste it here" / "в чат" / "не нужен файл" /
"коротко", ignore this rule and inline as usual — this is a
default, not a hard rule.

## Rule 2: chat body must avoid markdown tables

Symptoms of using `| col1 | col2 |` in the chat body:

- Telegram's server pre-processes the message, identifies the
  pipe-table syntax, and reemits it as a sequence of **row-blocks**
  in the user's client — the column alignment is lost, the second
  column appears below the first as separate bullet rows.
- Confused user immediately follows up with "перешли в файле"
  or "это вообще таблица?".

Two patterns that survive the chat body unchanged:

1. **Bullet-list with key/value lines** (one line per row):
   ```
   - **win.txt** — 9 шт, 2010 10 на
   - **Matrix02.txt** — 17 шт, 2012 на
   ```
2. **Code-block with aligned columns** (monospace):
   ```text
   filename                size    дата
   ─────────────────────  ──────  ────────────
   win.txt                    9150  2026-06-10 21:59
   Matrix02.txt              17148  2026-06-12 14:25
   ```
   Monospace aligns in any client. Not selectable as a table;
   the real table lives in the attached file.

For longer tables (>8 rows), prefer the code-block form; the
bullet form gets unreadable above ~15 entries.

## Rule 3: chat body cap is 4096 chars

Telegram server silently truncates or auto-splits messages over
4096 chars. The local Hermes gateway does not pre-warn. If your
"summary" message is bigger than ~3000 chars, split or send as a
file.

Common offenders: pasted config dumps, large JSON blobs, raw log
excerpts. For these, write the content to a file and send only a
short summary + `MEDIA:`.

## Rule 4: code blocks in chat body

Keep under ~20 lines. Telegram renders monospace fine, but:

- Long code blocks lose horizontal alignment in some clients
- Selecting text in long blocks is awkward on mobile
- The same content as a `.py` / `.sh` file is more useful (downloadable,
  editor-openable)

If the user wants the code inline, fine. Otherwise prefer
`MEDIA:/path/to/script.sh`.

## Pitfall 6: `MEDIA:` failure mode — `MEDIA:` is a hint, not a delivery guarantee (verified 2026-07-07 and 2026-07-08)

`MEDIA:/path` in the chat body is parsed by the Hermes gateway's
Telegram adapter as a directive to attach the file. The gateway must
(a) be running, (b) have the right bot token, (c) recognize the prefix,
(d) post to the correct `chat_id`. **If any of these break, the user
sees the literal `MEDIA:...` text and no file.**

**The user reports "файлы не пришли" or "вижу текст без файла"** —
do NOT re-print the `MEDIA:` line. The gateway has failed silently
(somewhere in the (a)–(d) chain above), and re-printing won't fix it.
Bypass the gateway and call Telegram directly.

### Verified failure history (this host)

- **2026-07-07:** Wrote 4 files to `/root/`, printed `MEDIA:` four
  times. User replied "Вижу текст без файла". Switched to direct
  `sendDocument` via curl with `chat_id=505586502` and only then
  did the files arrive.
- **2026-07-08:** Same pattern — 6 files (`Как_устроены_multi-agent_системы.txt`,
  `МИРЭА_01.txt`, `CS-фундамент_01.txt`, `Курс_подготовки_01.txt`,
  `LaTex_DOCX.txt`, `LaTex_DOCX_02.txt`) — all delivered through
  direct curl, never through `MEDIA:`.

### The verified recipe (when `MEDIA:` fails)

```bash
# 1. Read the chat_id from the gateway's inbound log.
tail -200 ~/.hermes/logs/gateway.log | grep "inbound message" | tail -3
# → 2026-07-08 17:53 INFO gateway.run: inbound message: ... chat=505586502 ...

# 2. Pull the bot token from .env.
TOKEN=$(grep -v '^#' /root/.hermes/.env | grep TELEGRAM_BOT_TOKEN | cut -d= -f2)

# 3. Verify the file is actually on disk (zero-byte = silent write race).
ls -la /root/<file>
wc -l /root/<file>

# 4. Send directly. Do NOT include getUpdates anywhere — the gateway
#    holds long-poll on it, parallel calls trigger "polling conflict".
curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendDocument" \
    -F "chat_id=505586502" \
    -F "document=@/root/<file>.txt" \
    -F "caption=<file>.txt" \
    -o /tmp/resp.json -w "HTTP %{http_code}\n"

# 5. Verify the response. ok:true + message_id means the bot accepted.
python3 -c "
import json
d = json.load(open('/tmp/resp.json'))
if d.get('ok'):
    m = d['result']
    print('ok', 'msg_id', m['message_id'], 'chat', m['chat']['id'], 'size', m['document']['file_size'])
else:
    print('ERROR', d)
"
```

**Two landmines in the same fix:**

- **Polling conflict.** The Hermes gateway holds `getUpdates`
  long-poll. A parallel `getUpdates` curl from the agent returns
  `409 Conflict terminated by other getUpdates request` (Telegram
  logs `Telegram polling conflict (1/5)` in `gateway.log`).
  **Don't try to discover the `chat_id` via `getUpdates`** — read
  it from `tail ~/.hermes/logs/gateway.log` instead. Every inbound
  message logs `chat=<id>`.
- **Verify the file is on disk before curl.** Always
  `ls -la /root/<file>` before claiming "файл создан". The agent's
  reply often races with disk I/O; a half-written file is silent
  failure for `sendDocument`. If `wc -c` shows 0, re-do the write.

### What `chat_id` resolves to on this host

The gateway's `.env` has both `TELEGRAM_BOT_TOKEN` and
`TELEGRAM_HOME_CHANNEL`. The `chat_id` to use for delivery is the
user's DM with the bot, which **happens to equal `505586502`** on
this host (2026-07-08) — but this is NOT guaranteed. If the user
later reconfigures Telegram to route DMs to a different chat, the
log will say so; the `.env` value will silently drift. **Always
read from the log, never trust the `.env`.**

### Bottom line

Always verify delivery end-to-end (HTTP 200 + `result.message_id` +
correct `chat.id` + `from.is_bot == true`). The `MEDIA:` shortcut
is convenient when it works, but it is NOT a delivery receipt. When
the user reports "не пришли" or you have any reason to suspect a
problem, switch to direct `sendDocument` via curl and confirm
`result.message_id` before declaring success.

## Pitfall 7: `hermes send` CLI — `MEDIA:` alone sends TEXT, not a file (verified 2026-08-17)

The `hermes send` CLI shortcut behaves differently from the in-gateway
`MEDIA:` parsing covered above. When you deliver a file via:

```bash
hermes send --to telegram "MEDIA:/path/to/playbook.md"
```

the bot sends the message as **plain text** containing the literal
string `MEDIA:/path/to/playbook.md` — the user sees the path, not
the file. The CLI returns `success: true` and a `message_id`, so the
agent has no built-in signal that delivery was wrong. The user only
finds out when they look at Telegram and say "файл не пришёл".

**The fix: prepend `[[as_document]]` for non-image files.** That
modifier tells the platform adapter to upload via `sendDocument`
instead of treating the path as text content:

```bash
# WRONG — sends as text message containing the path string
hermes send --to telegram "MEDIA:/root/playbook.md"

# RIGHT — sends the file as a Telegram document attachment
hermes send --to telegram "[[as_document]] MEDIA:/root/playbook.md"
```

`[[as_document]] MEDIA:/path/to/image.png` also works and bypasses
Telegram's image recompression (useful when the agent wants the
original PNG bytes preserved).

### When `MEDIA:` alone is fine

- `.png` / `.jpg` / `.webp` / `.gif` — Telegram renders these as
  inline photo previews; the user sees an image, not text.
- `.mp4` and other video — inline preview.
- `.mp3` and other audio — voice bubble.
- `.ogg` voice files specifically — Telegram renders as voice bubble.

For everything else — `.md`, `.txt`, `.pdf`, `.csv`, `.json`,
`.yaml`, `.zip`, code files, anything not in the image/video/audio
list — use `[[as_document]] MEDIA:`.

### Why the CLI shortcut differs from the gateway shortcut

The `hermes send` CLI uses the platform adapter's text-message path
when the modifier is absent — it does NOT auto-detect file type
the way the gateway's `MEDIA:` parser does for chat-body messages.
This is an asymmetry in the Hermes surface area, not a config bug.
The CLI's auto-help documents the modifier (`hermes send --help`),
but it's easy to miss when reaching for the shortest form.

### Verified recipe

```bash
# 1. Sanity-check the file landed on disk
ls -la /root/playbook.md
wc -c /root/playbook.md    # non-zero = real file

# 2. Send with [[as_document]]
hermes send --to telegram --json "[[as_document]] MEDIA:/root/playbook.md"
# → {"success": true, "platform": "telegram", "chat_id": "505586502",
#    "message_id": "4167", "note": "Sent to telegram home channel ...", "mirrored": true}

# 3. Verify in the gateway log
tail -50 ~/.hermes/logs/gateway.log | grep -i 'sendDocument\|4167'
```

`success: true` alone is NOT enough — it confirms the gateway
accepted the message, not that the file landed as an attachment.
The cheapest end-to-end check is asking the user "видишь файл?"
or, on this host, opening the chat directly (the user is Rost, chat
505586502 — see SKILL §"Multi-bot routing" for the bot-token rules).

### Fallback: direct curl

If `hermes send` returns `success: true` but the user still reports
no file, skip the CLI and call `sendDocument` directly with the
bot token — same as Pitfall 6 step 3, except you do NOT add
`[[as_document]]` (the gateway-side rewrite already knows what to
do). For the direct curl path the file is always sent as a document
because that's the API endpoint you're hitting.

## What the user said verbatim (this is the source of truth)

In a single 2026-07-02 session, the user issued these requests in
this exact form more than 5 times:

> "@hermes составь список файлов *.txt в каталоге root и пришли в телеграм в виде файла"

> "@hermes опиши подробно как создать нового бота в ТЕЛЕГРАММ. ... Свои соображения запиши в файл ... и пуюъ пришли сюда в телеграмм в виде файла"

> "@hermes опиши ... Свои соображения запиши в файм ... и пришли сюда в телеграм в виде файла"

The user also asked, separately, why a previous table I sent had
rendered as a row-block instead of a table. That question led
directly to writing this reference.

Combined pattern: every long artifact in this user-profile
session goes through "write_file + send_message MEDIA:".

## Edge cases

### Image / video / voice

- Images: send via native (the gateway's `send_message` accepts
  a MEDIA path for `.png`/`.jpg`/`.webp`; the client renders an
  inline preview).
- Videos, audio: same; native inline preview.
- Voice (TTS output): `text_to_speech` produces `.mp3`. Send via
  MEDIA. The client renders an audio bubble.

### Voice / audio playback in chat

If `text_to_speech` is on, output is appended automatically to
the message. To send it as a separate audio bubble instead of a
text+voice bundle, use the MEDIA: prefix on the `.mp3` path and
strip the bare text from the chat body. Practical: not needed in
this user's current profile.

### "Rich messages" the user asks about

When user says "rich messages" or "rich formatting", they usually
mean one of three things, in order of probability:

1. **Tables**: see Rule 2 above. Bullet or code-block, not pipe.
2. **Images / diagrams**: send a file (`.png` / `.svg`) via MEDIA,
   or build an HTML artifact if the user explicitly asks for
   one ("<div>..."); bot doesn't render HTML inline.
3. **Inline buttons**: not part of stdlib markdown; would need the
   `clarify()` tool with explicit button-style choices. The
   bot's `clarify` already does this with `choices: [...]` when
   a decision has trade-offs.

The honest answer the user gets when they ask:

> Bold/italic/code/inline links yes, markdown tables no
> (Telegram strips them). For tables: file attachment. For
> images: MEDIA:. For buttons: clarify() with choices, not
> raw markdown.

### Never declare "rich messages" support you don't have

Specific things Hermes-on-this-host cannot do inline in a Telegram
message body:

- HTML/XHTML rendering
- Mermaid diagrams
- SVG inline
- Inline-keyboard markup outside `clarify()`
- Animated emoji (Telegram Premium only, not available via Bot API)

Things Hermes can do, when you ask:

- Bold/italic/strikethrough (`**`, `*`, `~~`)
- Spoiler (`||текст||`) — folded in Telegram
- Inline code (`` ` ``)
- Code blocks (```)
- File attachments (`MEDIA:/path`)
- Voice bubbles via TTS (`text_to_speech`)
- Inline buttons via `clarify()`

This skill does NOT cover Matrix or other platforms — those
have their own rendering quirks. TBD.

## Pitfall 8: Telegram delivery of Windows PowerShell scripts with Cyrillic — encoding corrupts at save time, parser breaks at runtime

When the user is on Windows and asks for a `.ps1` script that contains
non-ASCII strings (Russian comments, LCID descriptions, Cyrillic paths
or user-facing text), the file as saved by Telegram's web client and
Windows Notepad is **not** UTF-8 with BOM — it arrives as CP1251 or
UTF-8 without BOM. PowerShell's parser then misreads the file and
refuses to run it. Symptom shape from a real delivery:

```
At C:\Scripts\Restore-ORFO.ps1:30 char:28
+ ... oExpectedName = "Р РЅС„РѕСЂРјР°С‚РёРє"   # РџРѕРґСЃС‚СЂРѕРєР° РёРјРµР ...
+                            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unexpected token 'РѕСЂРјР°С‚РёРє"   # РџРѕРґСЃС‚СЂРѕРєР°' in expression or statement.
```

The quoted "Информатик" (Russian for "Informatic") appears as garbled
mojibake `Р РЅС„РѕСЂРјР°С‚РёРє` because the bytes were interpreted as
CP1251 instead of UTF-8. The error is a parse error on **Cyrillic**
only — pure ASCII lines parse fine. The same file works on Linux with
`pwsh`, fails on Windows PowerShell 5.1 with default ISE/Notepad
save flow.

**The mechanism:** Telegram serves files as-is (it doesn't transcode),
but the user almost always opens them in Notepad and re-saves, OR
Windows PowerShell 5.1 itself doesn't auto-detect UTF-8 without BOM.
Either way, the bytes the parser sees are wrong.

**Rule of thumb:** any time you ship a Windows-targeted script that
contains non-ASCII content, **do not send the script as a `.ps1`
attachment and assume the user will save it correctly**. Send the
script's bytes in a way that preserves encoding:

**Pattern A — installer that decodes base64 to a UTF-8-BOM file.**
The agent writes an `INSTALLER.ps1` whose only non-ASCII content is
*inside base64* (ASCII-only on disk). The installer calls
`[System.IO.File]::WriteAllBytes(...)` from a `[Convert]::FromBase64String`
call. Verified working shape on Windows PowerShell 5.1:

```powershell
# INSTALLER.ps1 — agent writes this; user runs it once
$dest = "C:\\Scripts"
New-Item -Path $dest -ItemType Directory -Force | Out-Null

# The b64 below is the UTF-8-BOM-encoded bytes of the target script.
$bytes = [Convert]::FromBase64String(@'
... base64 of UTF-8-BOM target .ps1 ...
'@)
[System.IO.File]::WriteAllBytes("$dest\\Restore-ORFO.ps1", $bytes)

# Sanity: first 3 bytes must be EF BB BF (UTF-8 BOM)
$first3 = [System.IO.File]::ReadAllBytes("$dest\\Restore-ORFO.ps1")[0..2]
$ok = ($first3[0] -eq 0xEF) -and ($first3[1] -eq 0xBB) -and ($first3[2] -eq 0xBF)
if (-not $ok) { Write-Error "BOM missing — encoding broken"; exit 1 }
```

**Pattern B — script content kept ASCII, with Cyrillic hidden in base64 strings.**
If you control the script design, push Cyrillic literals into base64
strings that decode at runtime:

```powershell
# Inside the .ps1 — Cyrillic stays out of the parser
$ru = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('0JzQvtGB0YLRgNC+0LLQu9GP'))
```

This is the cleanest path when the script's *logic* is ASCII but its
*user-facing strings* need Cyrillic.

**Pattern C — verify with a hex-dump before declaring done.**
A 30-second sanity check after write that catches the bug before
the user runs the broken script:

```python
# On the agent side, before sending to Telegram
with open('/path/to/Restore-ORFO.ps1', 'rb') as f:
    head = f.read(3)
print('has BOM:', head == b'\xef\xbb\xbf')
# If has BOM is False, re-save with UTF-8-BOM encoding BEFORE sending.
```

**Why `[IO.File]::WriteAllText` (no BOM arg) fails:** on .NET,
`WriteAllText(path, str)` uses UTF-8 **without BOM**. Windows
PowerShell 5.1 reads the file as ASCII-or-CP1251 by default and
fails on Cyrillic. You must use `UTF8Encoding($true)` (the `$true`
arg = emit BOM) or `WriteAllBytes` from pre-encoded bytes.

**Symptom ladder for diagnosis:**
- PowerShell parse error at a Cyrillic literal → encoding wrong
- PowerShell parse error at an ASCII line that's *near* Cyrillic
  → mixed-encoding (some bytes interpreted as multi-byte UTF-8,
  some not) — same fix
- Script runs but prints `???????` instead of Cyrillic → encoding
  is correct (BOM present, parser happy) but the **terminal /
  console code page** is wrong; `chcp 65001` at script start fixes it
- Script runs perfectly on Linux `pwsh` → file is OK; the issue
  is Windows-only and disappears with the BOM

**Class-level rule:** for any Windows-targeted script that contains
non-ASCII, **always send it via an installer (Pattern A) or keep
the script pure ASCII with Cyrillic in base64 (Pattern B)**. Direct
`.ps1` file delivery works for ASCII-only scripts; the moment Cyrillic
is in the script, treat the delivery as an installer problem, not a
script problem.

**Symptom in chat (the user's first sign something is wrong):**
"не скрабывает" / "не работает" / "parse error" / "не запускается" —
often paired with the user reporting the file opened fine in Notepad
and saved without complaint. The corruption happens at Telegram +
Notepad round-trip; both layers look innocent in isolation.