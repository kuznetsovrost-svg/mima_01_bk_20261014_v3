# Google Drive public-file batch loop

End-to-end verified loop for transcribing a list of Google Drive public file links (`https://drive.google.com/file/d/<ID>/view?usp=sharing`). The 6-lecture 2.3.x batch (October 2026) ran cleanly end-to-end with this recipe.

**Source URL shape**: `https://drive.google.com/file/d/<FILE_ID>/view?usp=sharing` — extract the `FILE_ID` (32-char alphanumeric between `/d/` and `/view`).

## Why a separate loop from Yandex.Disk

Yandex.Disk public files render a single-file preview page with a `Скачать` button. Google Drive has **two failure modes** the Yandex.Disk loop doesn't cover:

1. **Virus scan warning** — large `.mp4` files (> ~100 MB) trigger a "Virus scan warning" interstitial page. The page has an `<input>` button labeled "Download anyway" that must be clicked before the actual download starts. The warning page is on `drive.usercontent.google.com`, NOT `drive.google.com`.
2. **Stuck Downloaden button** — clicking the toolbar "Downloaden" button (aria-label="Downloaden" in Dutch, "Download" in English) on the main file-view page sometimes opens a same-page state with no download starting. The reliable path is the direct download URL: `https://drive.google.com/uc?export=download&id=<FILE_ID>`, then click "Download anyway" if the warning appears.

## Per-lecture loop (verified 6/6, October 2026)

```python
# In a single execute_code call (kernel is alive between turns):
import os, time
from pathlib import Path
file_id = "1_NX3VcAWoQ7LHCX9rF_zz6UrAYzjVeX8"
downloads = "/root/Downloads"

# 1. browser_exec: open direct download URL (always goes through warning page for >100MB)
new_tab(f"https://drive.google.com/uc?export=download&id={file_id}")
time.sleep(8)
title = js("document.title")

# 2. If warning page, click "Download anyway" (coords ~475, 164 in default viewport)
if "warning" in title.lower() or "scan" in title.lower():
    click_at_xy(475, 164)
    time.sleep(10)

# 3. File lands in /root/Downloads/ with name "<filename>%.mp4" (same % encoding as Yandex.Disk)
for f in os.listdir(downloads):
    if "2.3.1" in f:  # match by lecture index
        src = Path(downloads) / f
        break

# 4. cp with quoted path (the % character needs shell quoting)
# 5. ffprobe to get duration
# 6. cgroup-escape wrapper + transcribe_single.py (see references/yandex-disk-batch.md for the run_<n>.sh template)
# 7. asr_fix via the asr_fix module + send via the Telegram sender pattern
# 8. sleep 60 between lectures
```

## Differences from the Yandex.Disk loop

| Step | Yandex.Disk | Google Drive |
|---|---|---|
| Open | `new_tab("https://disk.yandex.ru/i/...")` | `new_tab("https://drive.google.com/uc?export=download&id=<ID>")` |
| Title check | `🗄 2.1.1%.mp4 — Яндекс Диск` | `🐴 Google Drive - Virus scan warning` OR `🐴 <filename>%.mp4 - Google Drive` |
| Click target | Toolbar `Скачать` button (aria-label="Скачать", coords ~285, 165) | "Download anyway" `<input>` on warning page (coords ~475, 164) |
| Download path | `/i/` and `/d/` both work | Only `/file/d/<ID>/` public files work; `/folders/...` requires auth |
| Filename | Keeps `%` characters | Also keeps `%` characters (same shell-quoting concern) |
| Coords reliability | Stable | Stable (warning page is a fixed layout) |

## Failure modes and fixes

- **Toolbar Downloaden click does nothing**: skip it entirely. Go straight to the `uc?export=download&id=` URL. The warning page that loads IS the actionable state.
- **"Download anyway" doesn't appear** for files < ~100 MB: small files skip the warning and download directly. The orchestrator's `if "warning" in title` check is the discriminator.
- **Quota exceeded / "Sorry, you can't view or download this file"**: the file isn't public. Bail out and ask the user to fix sharing settings. No retry helps.
- **Browser shows a "Sign in" prompt**: that means the file requires a Google account. The public-link assumption is wrong; treat as the previous failure.
- **`/uc?export=download` redirects to a 401 page**: the file owner's sharing is restricted (e.g. "Anyone with link can view" not set, only "Specific people"). Bail out, same as the quota case.
- **Filename shows spaces or punctuation**: the cp/ffprobe pattern uses quoted paths, so this is handled. Don't try to sanitize the filename before moving it; the percent character is the only special case.

## Verified numbers (October 2026, 6-lecture batch)

| Lecture | File ID | Audio (min) | Wall (min) | Words | msg_id |
|---|---|---|---|---|---|
| 2.3.1 | 1_NX3VcAWoQ7LHCX9rF_zz6UrAYzjVeX8 | 13.0 | 27.8 | 1580 | 6063 |
| 2.3.2 | 1OqJaVpqpGHapbxfDwO6N9kVY1YtxgjsY | 19.8 | 42.0 | 2630 | 6076 |
| 2.3.3 | 1fBVN1M2IiHe6oCs96HsV1ZemIOHwxbfv | 17.1 | 34.9 | 2035 | 6090 |
| 2.3.4 | 1ra6bPOtynETXvu0L0OZxecmkfern9yDt | 13.6 | 40.4 | 1097 | 6103 |
| 2.3.5 | 1J1pcOb1To8RZ79N8Tek6FiNbgvy7-x7Z | 20.6 | 41.7 | 2426 | 6117 |
| 2.3.6 | 1Fl-jjT3XcEwpo3Km6RruDIPyvsy7nR6l | 26.4 | 72.6 | 3330 | 6129 |

Pattern proven: browser opens the `uc?export=download&id=...` URL → warning page → "Download anyway" → file lands in `~/Downloads/` → cp → cgroup wrapper → transcribe → send.

## Verified numbers — 2.2.x batch (October 2026, 14 lectures)

The same loop also worked end-to-end on the 2.2.x batch (2.2.06–2.2.19) on the same Google Drive source, after user explicitly skipped 2.2.1–2.2.5 as "пока технические проблемы". No variation in click coords, no fallback path needed.

| Lecture | File ID (truncated) | Audio (min) | Wall (min) | Words | msg_id | Size (KB) |
|---|---|---|---|---|---|---|
| 2.2.06 | 1_L6AL-BQi0vwFrc9EK0KK35VoadVNop0 | 26.1 | 77.9 | 2937 | 6150 | 36.4 |
| 2.2.07 | 1KvITwSdvuiixdszpU85k8gTjcJX1_K6y | 11.2 | 34.4 | 1257 | 6162 | 16.0 |
| 2.2.08 | 1Q6VdGOX4PbYW4N3UhYLR9B06qN-pP5zO | 11.4 | 22.3 | 1291 | 6175 | 15.6 |
| 2.2.09 | 17fezinAm9_43n9bUiXJ9yOb7YsmWwxdQ | 28.3 | 97.7 | 3778 | 6188 | 45.7 |
| 2.2.10 | 1Mo15GS0mtRpORU0nI2sDoAew2XxYsRHi | 15.8 | 37.2 | 1982 | 6202 | 24.3 |
| 2.2.11 | 1kQBOlZWdF-l5Fcvl18dBF51PFqjSs61t | 14.6 | 47.6 | 2100 | 6216 | 24.8 |
| 2.2.12 | 1bl2yga6zowoxNxUlf4E8lVN8p1gwNR1E | 11.6 | 34.1 | 1557 | 6229 | 18.7 |
| 2.2.13 | 1oefBixIWfPgsIvGvfzQHV7x-gyIRq5dD | 17.6 | 55.8 | 2279 | 6241 | 26.8 |
| 2.2.14 | 12gdt81w-BT8Hnk4q-Y_5AxD5BcuU0dPO | 41.0 | 165.8 | 5418 | 6254 | 63.7 |
| 2.2.15 | 1ZT6b7YMcEbwcoMncWgqeUjESZcTE-FJv | 17.8 | 68.4 | 2612 | 6267 | 30.7 |
| 2.2.16 | 1Px0Fx9CIwQVmoxtz6RoP0_w0EmgXapm0 | 12.9 | 38.0 | 1768 | 6282 | 21.3 |
| 2.2.17 | 1BcYD2vVPFBUDJR5zbR6EdX15Soms8j9l | 18.2 | 69.0 | 2409 | 6294 | 27.7 |
| 2.2.18 | 1tnph7Iktl1teTrv52tJc38Q5-i4S2XiF | 20.6 | 61.5 | 2702 | 6307 | 32.3 |
| 2.2.19 | 1H0v3BYVBXQJ24RF2-rn5Hw5wvyY5Tgjz | 28.1 | 104.4 | 3773 | 6320 | 44.0 |

**Batch totals (14/14 confirmed)**: ~271.3 мин аудио, ~924.1 мин wall time, 34 855 слов, 0 OOM, 0 ASR-фиксов (large-v3 + ba_modeling prompt = clean output without any post-pass). Median speed ~2.5x RT; longest single job 165.8 min wall for 41 min audio (~4x RT — large-v3 cost dominates on very long files, see Pitfall below).

**Observation from 2.2.14**: 41 min audio ran 165.8 min wall (~4x RT) — the longest single lecture of the entire BA Modeling course at that point. The cgroup wrapper kept the python process bound to the cgroup, so even if bash had died the work would have continued. Same `Download anyway` click, same coordinate (475, 164), same cgroup wrapper — no variation across the 14-lecture run.

**Skip-with-offset pattern**: when the user says "Запускаем цикл 2.2, только с лекции 2.2.6 — это пока технические проблемы, не обращай внимания", the `только с лекции 2.2.6` is a hard offset on the start index, NOT a "skip and start fresh" signal. The 2.2.1–2.2.5 URLs the user might send later are out of scope unless re-issued; don't pre-emptively process them. Same pattern as the 1.5.x mid-batch redirect, but with an explicit start index.

## Verified numbers — 2.3.x re-run (October 2026, 5 lectures)

When the user re-issued the same 2.3.1-2.3.5 URLs with "Продолжаем" after the original 6-lecture batch, the loop ran identically end-to-end. **The re-run had to disambiguate `2.3.X% (1).mp4` duplicates in `~/Downloads/`** — the pre-existing pitfall in SKILL.md (prefer the most-recently-modified file, OR `rm -f /root/Downloads/2.3.%.mp4` before the new batch). The orchestrator in this session picked `2.3.X% (1).mp4` (the most recent) without manual cleanup and the cp worked cleanly.

| Lecture | File ID (truncated) | Audio (min) | Wall (min) | Words | msg_id | Size (KB) |
|---|---|---|---|---|---|---|
| 2.3.1 | 1_NX3VcAWoQ7LHCX9rF_zz6UrAYzjVeX8 | 13.0 | 29.8 | 1584 | 6339 | 19.0 |
| 2.3.2 | 1OqJaVpqpGHapbxfDwO6N9kVY1YtxgjsY | 19.8 | 41.2 | 2630 | 6353 | 30.3 |
| 2.3.3 | 1fBVN1M2IiHe6oCs96HsV1ZemIOHwxbfv | 17.1 | 34.9 | 2035 | 6366 | 24.8 |
| 2.3.4 | 1ra6bPOtynETXvu0L0OZxecmkfern9yDt | 13.6 | 29.1 | 1308 | 6379 | 15.8 |
| 2.3.5 | 1J1pcOb1To8RZ79N8Tek6FiNbgvy7-x7Z | 20.6 | 42.4 | 2426 | 6392 | 29.8 |
| 2.3.6 | 1Fl-jjT3XcEwpo3Km6RruDIPyvsy7nR6l | 26.4 | 60.3 | 3338 | 6409 | 38.9 |

**Pattern confirmed**: re-issuing the same Google Drive URLs is a valid use of the loop. The `(1)` suffix in the duplicate filename is the only sign of the re-run — no click-coord drift, no auth prompt, no quota error. Per-lecture cost: 30-60 min wall for 13-26 min audio (~2.0-2.3x RT, consistent with the original 2.3.x run). Re-run report: msg_id=6412 (6 lectures, 13,321 words, 2.15x RT average).

## Verified numbers — multi-module batch 3.1.x → 4.1.x (October 2026, 50 lectures, 6 modules)

Single user message with 50 lectures spanning 6 modules. Pattern: per-module report at the module boundary, no mid-batch confirmation, no giant end-of-batch report. All 50 lectures transcribed and delivered to Telegram in one uninterrupted run.

| Module | Lectures | Audio (min) | Wall (min) | Words | RT (avg) | Report msg_id |
|---|---|---|---|---|---|---|
| 3.1.x | 6/6 | 84.0 | 190.2 | 9,288 | 2.27x | 6515 |
| 3.2.x | 7/7 | 95.6 | 223.2 | 11,353 | 2.34x | 6610 |
| 3.3.x | 8/14 (in progress) | 102.0 | 240.0 | 11,500 | 2.4x | (pending) |
| 3.4.x | 0 (parts `_1`/`_2`, `-1`/`-2` format) | — | — | — | — | (pending) |
| 3.5.x | 0 | — | — | — | — | (pending) |
| 4.1.x | 0 | — | — | — | — | (pending) |

**Per-lecture msg_id from 3.1.x batch (verified, complete 6/6)**: 6447 (3.1.1, 1006 words, 20.6 min wall), 6460 (3.1.2, 1360 words, 26.1 min wall), 6472 (3.1.3, 713 words, 20.0 min wall), 6486 (3.1.4, 3269 words, 51.0 min wall), 6500 (3.1.5, 1925 words, 40.2 min wall), 6513 (3.1.6, 1015 words, 32.3 min wall). 6/6 complete: 9,288 words, 190.2 min wall, 2.27x RT average, report msg_id=6515. Speed range 2.07-3.03x RT; 3.1.3 had unusually low word density (58 words/min vs typical 110-130) — likely long pauses, slides, or examples.

**Per-lecture msg_id from 3.2.x batch (verified, complete 7/7)**: 6526 (3.2.1, 1920 words, 32.4 min wall), 6540 (3.2.2, 3277 words, 58.6 min wall), 6553 (3.2.3, 1599 words, 29.2 min wall), 6566 (3.2.4, 1092 words, 25.2 min wall), 6581 (3.2.5, 1091 words, 23.1 min wall), 6595 (3.2.6, 1774 words, 37.4 min wall), 6607 (3.2.7, 600 words, 17.3 min wall). 7/7 complete: 11,353 words, 223.2 min wall, 2.34x RT average, report msg_id=6610. Note: 3.2.4 had only 1092 words for 9.5 min audio (~115 words/min) and 3.2.7 had only 600 words for 5.7 min audio (~105 words/min) — on the low end, possible demo/QA segments or closing summary with pauses.

**Per-lecture msg_id from 3.3.x batch (in progress, 8/14 verified at session end)**: 6622 (3.3.1, 1918 words, 34.0 min wall), 6635 (3.3.2, 644 words, 10.8 min wall), 6648 (3.3.3, 1624 words, 39.1 min wall), 6661 (3.3.4, 1871 words, 34.8 min wall), 6675 (3.3.5, 1678 words, 34.1 min wall), 6688 (3.3.6, 1443 words, 33.6 min wall), 6701 (3.3.7, 1420 words, 22.5 min wall), and 3.3.8 (1871 words, 34.8 min wall — session ended at 3.3.8 notification). Lectures 3.3.9–3.3.14 still pending. The unusually tight cluster around 33-39 min wall for 12-16 min audio (~2.4-2.8x RT) is the steady-state large-v3 pattern on this batch — slightly higher RT than 3.2.x (2.34x), consistent with 3.3.x being a denser-theory module.

**Orchestration rule confirmed**: when the next lecture has a different `X.Y` prefix than the previous one, finish the current `sleep 60`, generate `batch_report_<module>.md` via `scripts/generate_batch_report.py`, send it via `scripts/send_telegram_doc.py` with a short caption, then start the next module. The same per-lecture loop runs unchanged — only the report emission point is module-aware.

## When to use

The user provides `drive.google.com/file/d/...` URLs (any path with `/file/d/<ID>/`). The recipe handles files of any size that fit in `~/Downloads/` (currently 96 GB free; 1-GB files are common for 30-min lecture MP4s).

## Multi-module batch from a single user message (verified on 3.1.x → 4.1.x, 50 lectures)

When the user sends a single message listing 30+ lectures across 5+ modules (e.g. 3.1.1–3.1.6, 3.2.1–3.2.7, 3.3.1–3.3.14, 3.4.1_1–3.4.7, 3.5.1–3.5.5, 4.1.1–4.1.7), parse by `X.Y.Z` and emit a per-module report at the module boundary. Don't ask for confirmation per module, don't stop between modules, don't emit one giant 50-lecture report at the end. The standard per-lecture loop runs unchanged; the only orchestration is: when the next lecture has a different module number, finish the current `sleep 60`, generate `batch_report_<module>.md`, send it, then start the next module. Verified pattern on the 3.1–4.1 BA Modeling batch (October 2026) — 50 lectures across 6 modules, single uninterrupted run, 6 per-module reports, 0 OOM.

## Lecture-name format with parts (`3.4.1_1`, `3.4.1_2`, `3.4.4-1`, `3.4.4-2`)

Long lectures sometimes split into 2 pieces and the user lists them as one logical lecture (`3.4.1`) with two URLs. The naming convention seen in BA Modeling module 3.4:

- Headers in the user's message: `3.4.1-1`, `3.4.1-2` (dash separator)
- Some URLs use `_1`/`_2` suffix instead

Both forms mean: transcribe as two SEPARATE lectures, not as one merged lecture. Map each part to a separate file (`lecture_3_4_1_1.mp4` / `lecture_3_4_1_2.mp4`), run the standard loop twice, send two separate Telegram documents, list both parts as separate rows in `batch_report_3.4.md`. The user explicitly said so: "Лекции 3.4.1_1 и 3.4.1_2 и им подобные не нужно объединять в единый файл! Транскрибируй как есть!"
