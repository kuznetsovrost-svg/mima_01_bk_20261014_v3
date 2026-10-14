---
name: transcription-postprocess
description: Punctuate and paragraphize Whisper transcripts via LLM with pause hints.
version: 1.0.0
author: Hermes Agent (transcribed by R. Kuznetsov)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [audio, transcription, punctuation, postprocessing, russian, llm]
    related_skills: [audio-transcription]
---

# Transcription Postprocess Skill

Add punctuation (`.`, `,`, `?`, `!`, `:`), capitalize proper nouns, and split into paragraphs for a raw Whisper transcript. Uses an LLM via `hermes -z` (one-shot mode) with explicit pause hints from word-level timestamps.

## When to Use

- You have a transcript from `audio-transcription` (or any Whisper JSON with `words[]`).
- Text is currently a single run-on paragraph (no punctuation, no paragraphs).
- You want a readable Markdown output suitable for editing/printing.

Don't use for: short utterances (< 30 sec), transcripts that already have punctuation, anything that must run without network.

## Prerequisites

- `audio-transcription` skill (or any source that generates `<base>_words.json`).
- `hermes` CLI on `PATH` (the script calls `hermes -z` internally).
- An LLM model configured in Hermes (default: `MiniMax-M3`).

No additional Python packages. No model downloads. The LLM is already loaded by Hermes.

## Quick Reference

```bash
# Single file
python3 scripts/postprocess.py /path/to/transcript_words.json --output /tmp/postprocessed/

# Multiple files (batch)
python3 scripts/postprocess.py /path/to/transcripts/ --output /tmp/postprocessed/ --batch

# Different model
python3 scripts/postprocess.py words.json --output ./out --model claude-opus-4.6
```

## How to Run

The script expects `<base>_words.json` produced by `audio-transcription` skill. Each entry:

```json
{"word": "так", "start": 5.48, "end": 5.96, "probability": 0.10}
```

It produces three files:

| File | Content |
|---|---|
| `<base>_postprocess.md` | Readable Markdown: sentences + paragraphs |
| `<base>_diff.md` | Before/after diff for review (if `<base>_plain.md` exists in same dir) |
| `<base>_postprocess.json` | (if needed) Structured paragraphs → text |

## Algorithm

1. **Load word list.** Read `<base>_words.json`.
2. **Build pause-annotated text.** Insert `[PAUSE X.XX]` markers between words where the speaker paused ≥ 100 ms.
3. **Build prompt.** Compose a Russian-language instruction telling the LLM to use the pause markers as sentence/paragraph boundaries.
4. **Call LLM via `hermes -z`.** Single-shot mode prints only the response text.
5. **Strip preamble.** Remove any "Here is the result:" wrapper the LLM adds.
6. **Write Markdown.**

## Quality Notes

The LLM approach was tested against `fullstop-punctuation-multilang-large` neural model on a 2-min Russian lecture fragment. Result:

| Aspect | fullstop | LLM |
|---|---|---|
| Time per 2 min audio | 1.8 sec | ~10 sec |
| Proper nouns capitalized | ❌ (lowercase) | ✅ (Денис, Ростислав, Лёша) |
| Em-dashes for dialogue | ❌ | ✅ (— Ну давай) |
| Compound words | ❌ (split) | ✅ (чуть-чуть, 15–20) |
| Random commas | ⚠️ many | ✅ grammatically correct |

## Verification

After running, check:
- [ ] Sentence boundaries look plausible (no sentence longer than ~30 words)
- [ ] Paragraphs separated by blank lines
- [ ] Names start with capital letter (Денис, not денис)
- [ ] Punctuation reasonable (no random `:` mid-sentence)
- [ ] First sentence starts with capital letter

## JEV quality gate (optional)

For bulk validation of postprocessed output, score each chunk with JEV using a **structured-criteria** state — flat text state underweights the score (returns 1/5 with confidence 0.15 even on good text):

```python
from jev_client import jev_score

state = {
    "transcript_preview": preview_text[:600],
    "criteria": {
        "punctuation": "Periods, commas, question marks present",
        "paragraphs": "Sentences split into logical paragraphs (blank lines)",
        "names": "Proper nouns capitalized (Денис, Ростислав, Лёша)",
    },
}
scale = ["1_fails_all", "2_poor", "3_partial", "4_good", "5_excellent"]

score, confidence = jev_score(
    state=state,
    scale=scale,
    instructions="Score the postprocessed Russian lecture preview based on the three criteria.",
)
```

Throughput: ~0.5 sec per chunk on top of LLM postprocess (~10 sec). Structured state with named criteria returns score 3/5 conf 0.51 on the same input that flat state scores 1/5 conf 0.15.

## Pitfalls

- **Network latency.** Each call to `hermes -z` takes 5-15 sec depending on LLM provider. For 120 lectures × 15 min each, plan ~30 min of LLM time per lecture.
- **LLM may paraphrase.** The prompt says "preserve all words exactly", but models occasionally drop filler words (э-э, ммм). Manual review of `<base>_diff.md` is recommended.
- **Long inputs.** `hermes -z` truncates very long prompts. If a transcript is > 30 min input at start, split it first.
- **Token cost.** Each call uses ~2-3K tokens (prompt + completion). For 120 lectures, that's ~300-400K tokens. Check your provider's pricing.

## Cost / Time Estimate

For 120 lectures × 15 min each = ~30 hours of audio:

| Stage | Wall time | Cost |
|---|---|---|
| Whisper transcription | ~50-70 hours (CPU) | $0 |
| LLM postprocess | ~30 hours (10 sec per 2 min audio) | depends on model |
| **Total** | **~80-100 hours** | |

If LLM cost is a concern, use a local model or batch-process overnight.