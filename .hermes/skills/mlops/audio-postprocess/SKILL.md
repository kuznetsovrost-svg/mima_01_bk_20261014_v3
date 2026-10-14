---
name: audio-postprocess
description: Multi-pass LLM postprocess for Russian transcripts. NOT recommended for lectures (deletes lecturer meaning). Use for prose rewrites only. Includes conservative punctuation-only mode.
version: 1.1.0
author: Hermes Agent (developed by R. Kuznetsov)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [audio, postprocess, llm, russian, lecture, cleanup, structure, asr-fix]
    related_skills: [audio-transcription, transcription-postprocess, jev-decisions]
---

# Audio Postprocess Skill (Multi-Pass LLM)

**⚠️ DO NOT USE for lectures.** This skill was tested on Russian BA lectures and produced materially wrong output — it deletes 20-60% of the lecturer's words under the guise of "filler removal" and "polish". The user confirmed: the lecturer's exact phrasing is sacrosanct and must not be edited by an LLM.

## When (Not) to Use

**Only use** when the transcript is being prepared as **publishable prose**, NOT as a faithful lecture record. Specifically:
- Speaker is being edited into a written article or blog post
- Errors are clearly wrong (not just stylistic)
- User has explicitly approved text rewriting

**Do NOT use** when:
- This is a transcript of a lecture, talk, course, or interview
- The lecturer's exact words have semantic, legal, or training value
- Output will be cited as "what the lecturer said"

**Safer alternatives** for faithful lecture transcripts:
- `transcribe_single.py` (single-chunk mode in `audio-transcription`) — no LLM editing at all
- `punctuate_v3.py` (in this skill) — punctuation-only LLM prompt with explicit "do not change words" rules
- `sed -i 's/фактальной/фрактальной/g'` for 1-3 known ASR errors

## What This Skill Does (when you do use it)

## The 4 Passes

Each pass uses `hermes -z` with a focused prompt. They run sequentially; each pass improves on the previous output.

### Pass 1: Filler Word Removal
**Removes**: "Вот", "Значит", "Ну", "Так", "Это самое", "Как бы" (only when they don't carry meaning)
**Adds**: Basic punctuation (`.`, `,`), paragraph breaks
**Time**: ~30 sec per 2000 words

### Pass 2: ASR Error Fix
**Fixes known errors** (Whisper patterns):
- `имперический` → `эмпирический`
- `сниженка Коха` → `снежинка Коха`
- `фактальной` → `фрактальной`
- `свепроводящих` → `сверхпроводящих`
- Артефакты на стыках чанков ("Использование токовых")

**Special rule for proper names**: First occurrence gets full form (e.g., "Георг Симон Ом"), subsequent occurrences use declined form ("закон Ома", "Омом", "Ому") — distinguishes names from acronyms.

**Time**: ~30 sec per 2000 words

### Pass 3: Structure
**Splits** flat transcript into thematic blocks with `##` headings.
**Headings** are 3-7 word summaries of each block.
**Preserves** all words, names, numbers, paragraphs.
**Time**: ~40 sec per 2000 words

### Pass 4: Polish
**Final** style polish: removes roughness, smooths transitions, ensures consistent punctuation.
**Preserves** lecture's spoken style (this is not a written article).
**Time**: ~30 sec per 2000 words

## Quick Reference

```bash
# Full pipeline (all 4 passes)
python3 scripts/postprocess_multi.py input.md output_base

# Custom base name (creates _pass_1_filler.md, _pass_2_asr_fix.md, ..., _final.md)
python3 scripts/postprocess_multi.py raw.md ./output/ba_lecture

# Specific passes only
python3 scripts/postprocess_multi.py raw.md ./output/ba_lecture --passes 1,2,3

# Resume from a specific pass (skip earlier ones)
python3 scripts/postprocess_multi.py raw.md ./output/ba_lecture \
  --passes 2,3,4 --start-from 2
```

## Overlap-Aware Deduplication

When source was transcribed with **15-sec overlap** (e.g. via `transcribe_overlap.sh`), use `dedup_overlap.py` to remove duplicate text in overlap zones:

```bash
# After overlap transcription
python3 scripts/dedup_overlap.py chunks_overlap_out/ deduped.md --overlap-sec 15
```

The script:
- Identifies overlap zones using word timestamps
- For first chunk: keeps all except last 15 sec
- For middle chunks: keeps middle (drops first and last 15 sec)
- For last chunk: keeps all except first 15 sec
- Concatenates with single-space separation

**Note**: in practice this heuristic misaligns when chunk duration ≈ 2× overlap (every chunk's middle is empty), and even when alignment works, LLM stitching downstream deletes content. The `audio-transcription` skill now defaults to single-chunk mode and avoids this problem entirely. Use `dedup_overlap.py` only for legacy multi-chunk transcriptions.

## Algorithmic Stitching (for long audio that exceeds single-chunk memory)

For audio longer than ~30 min where single-chunk mode would overflow KV-cache, chunk WITHOUT overlap and stitch the chunks by absolute timestamp:

```bash
# 1) Transcribe each chunk separately with transcribe.py (no overlap, word_timestamps=True)
# 2) Stitch
python3 scripts/stitch_algorithmic.py chunks_out/ final.md --step-sec 60 --overlap-sec 0
```

The script converts each chunk's RELATIVE word timestamps to ABSOLUTE (offset by chunk index × step), then concatenates. No LLM, no hallucination risk. See `references/whisper_tuning.md` in `audio-transcription` for chunk-size selection.

## Conservative Punctuation-Only Mode

When the lecturer's words are sacrosanct but the raw output lacks punctuation, use `punctuate_v3.py` — a single punctuation pass with an explicit "do not change words, do not delete, do not rephrase" prompt. This is the ONLY safe LLM pass for lecture material.

## Output Files

For `output_base = ./output/ba_lecture`, the pipeline produces:

| File | Content |
|---|---|
| `ba_lecture_pass_1_filler.md` | After filler removal |
| `ba_lecture_pass_2_asr_fix.md` | After ASR corrections |
| `ba_lecture_pass_3_structure.md` | With ## thematic headings |
| `ba_lecture_pass_4_polish.md` | Final polished text |
| `ba_lecture_final.md` | Copy of last pass output |

## Cost & Time Estimate

**Per 2000 words (MiniMax-M3 model)**:

| Stage | Time | Cost |
|---|---|---|
| Pass 1 (filler) | ~30 sec | ~$0.005 |
| Pass 2 (ASR fix) | ~30 sec | ~$0.005 |
| Pass 3 (structure) | ~40 sec | ~$0.007 |
| Pass 4 (polish) | ~30 sec | ~$0.005 |
| **Total** | **~2-3 min** | **~$0.022** |

For 20-min lecture (~2000 words), full pipeline takes **~5 min** (including model loading).

## Customization

To add or modify passes, edit `scripts/postprocess_multi.py`:

```python
PASSES = {
    1: ("filler", "..."),      # Edit prompt here
    2: ("asr_fix", "..."),     # Add your known errors
    3: ("structure", "..."),   # Change heading style
    4: ("polish", "..."),      # Tighten style
}
```

Each prompt should:
1. State the role ("Ты редактор...")
2. List the rules (1, 2, 3...)
3. Specify output format ("Только текст, без комментариев")

## When to Skip Passes

**Skip Pass 1** if you don't have many filler words (e.g., technical lecture, not lecture-hall recording).

**Skip Pass 2** if you've manually verified ASR accuracy.

**Skip Pass 3** if the topic has no clear structure or you prefer one continuous flow.

**Pass 4 is always useful** for final readability.

## Integration with audio-transcription

This skill is **downstream** of `audio-transcription`:

```
audio-transcription (raw _plain.md)
        ↓
audio-postprocess (4-pass LLM cleanup)
        ↓
Optional: cleanup.py (remove metadata)
        ↓
Final polished transcript
```

## Pitfalls

- **Each pass needs the previous output** — don't skip the chain unless intentional
- **Cost adds up**: 4 passes = 4x LLM cost. For drafts, run only passes 1-2
- **Pass 3 may produce many small blocks** — if too granular, lower the block count by giving more topic context
- **Proper name handling**: First-mention rule requires context awareness; works best for prominent names
- **LLM "polish" deletes lecturer meaning** — Pass 4 ("polish") and Pass 1 ("filler removal") were observed deleting the key phrase "A является моделью B, если A отвечает на вопрос относительно B" from a Russian lecture transcript. Even with "preserve all words" instructions, the LLM interprets them as guidance rather than absolute rules. If you must use this skill on lecture material, run only Pass 2 (specific ASR fixes) and verify word count delta is < 5%.

## See Also

- `audio-transcription` — upstream (produces raw transcripts)
- `transcription-postprocess` — alternative single-pass LLM cleanup
- `jev-decisions` — could be used for quality scoring of pass outputs
- `cleanup.py` (in audio-transcription) — removes metadata from final output

## Files in This Skill

```
audio-postprocess/
├── SKILL.md                           # this file
└── scripts/
    ├── postprocess_multi.py           # 4-pass LLM postprocess pipeline
    └── dedup_overlap.py               # Overlap-aware deduplication
```