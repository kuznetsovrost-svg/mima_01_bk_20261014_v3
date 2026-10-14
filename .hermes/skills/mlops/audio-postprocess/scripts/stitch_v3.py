#!/usr/bin/env python3
"""
stitch_v3.py - LLM-based conservative stitching of overlap chunks.

For each pair of consecutive overlap chunks, the script:
1. Identifies the overlap zone using word timestamps
2. Asks LLM to PRODUCE a clean transition that:
   - Keeps ALL semantic content from both chunks
   - Does NOT delete words
   - Does NOT paraphrase
   - Does NOT add new content
   - Resolves repetitions in the overlap zone
3. Concatenates the result

This is "conservative" stitching: the LLM is a SMART JOINER, not an EDITOR.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


STITCH_PROMPT = """\
Ты — стенографист, который соединяет два перекрывающихся фрагмента транскрипции лекции.

У тебя есть два фрагмента (A и B), которые частично перекрываются. Твоя задача:
1. Выдать ОДИН непрерывный текст, который включает ВСЁ содержание из A и B.
2. В зоне перекрытия — выбрать наиболее полную и точную формулировку.
3. НЕ удалять слова, фразы, предложения.
4. НЕ перефразировать, НЕ сокращать, НЕ добавлять.
5. Сохранить стиль лекции, разговорные обороты, ВСЕ слова лектора.
6. Если какое-то слово испорчено распознаванием — оставь как есть (исправим отдельно).
7. Поставь минимальную пунктуацию (точки между предложениями, запятые в сложных).
8. НЕ дели текст на абзацы сам — это будет сделано позже.
9. ВЫВОД: только непрерывный текст, без пояснений, без заголовков.

---

ФРАГМЕНТ A (конец):
{text_a}

---

ФРАГМЕНТ B (начало):
{text_b}

---

Непрерывный текст:"""


def get_chunk_text(chunk_dir: Path) -> tuple[str, list[dict], float]:
    plain = chunk_dir / f"{chunk_dir.name}_plain.md"
    words_file = chunk_dir / f"{chunk_dir.name}_words.json"

    if not plain.exists():
        return "", [], 0.0

    text = plain.read_text(encoding="utf-8").strip()
    words = []
    if words_file.exists():
        data = json.loads(words_file.read_text(encoding="utf-8"))
        words = data.get("words", [])

    duration = 0.0
    if words:
        duration = max(w["end"] for w in words)

    return text, words, duration


def find_overlap(words_a: list[dict], words_b: list[dict], overlap_sec: float) -> tuple[list[dict], list[dict]]:
    """Find overlap zone: last overlap_sec of A + first overlap_sec of B."""
    if not words_a or not words_b:
        return [], []

    a_end = words_a[-1]["end"]
    a_start = a_end - overlap_sec
    a_overlap = [w for w in words_a if w["end"] >= a_start]

    b_overlap = [w for w in words_b if w["end"] <= overlap_sec]

    return a_overlap, b_overlap


def words_to_text(words: list[dict]) -> str:
    return " ".join(w["word"] for w in words)


def call_llm(prompt: str, text_a: str, text_b: str) -> str:
    full_prompt = STITCH_PROMPT.format(text_a=text_a, text_b=text_b)
    result = subprocess.run(
        ["hermes", "-z", full_prompt],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        print(f"  LLM error: {result.stderr[:200]}", file=sys.stderr)
        return ""
    out = result.stdout.strip()
    if out.startswith("```"):
        out = re.sub(r"^```\w*\n?", "", out)
        out = re.sub(r"\n?```$", "", out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("chunks_dir", help="Directory with chunk_NNN subdirs")
    parser.add_argument("output", help="Output file path")
    parser.add_argument("--overlap-sec", type=float, default=30.0)
    parser.add_argument("--context-sec", type=float, default=20.0,
                        help="Context seconds around overlap zone (for context window)")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM, use simple trim")
    args = parser.parse_args()

    chunks_dir = Path(args.chunks_dir)
    chunk_dirs = sorted(chunks_dir.glob("chunk_*"))

    if len(chunk_dirs) < 2:
        print(f"ERROR: need at least 2 chunks, found {len(chunk_dirs)}", file=sys.stderr)
        return 1

    print(f"Processing {len(chunk_dirs)} chunks, overlap={args.overlap_sec}s, context={args.context_sec}s")

    # Read all chunks
    chunks = []
    for cd in chunk_dirs:
        text, words, duration = get_chunk_text(cd)
        chunks.append({"dir": cd, "text": text, "words": words, "duration": duration})
        print(f"  {cd.name}: {len(text.split())} words, {duration:.1f}s audio")

    # Strategy:
    # - First chunk: take everything
    # - For each transition (chunk N -> chunk N+1):
    #   - Show LLM: end of chunk N (last context_sec+overlap_sec) + start of chunk N+1 (overlap_sec+context_sec)
    #   - LLM returns clean stitched text for the transition zone
    # - Replace overlap zone in the result with LLM's stitching

    if args.no_llm:
        # Simple trim: first chunk full, subsequent chunks only keep beyond overlap
        parts = []
        for i, c in enumerate(chunks):
            if c["words"]:
                if i == 0:
                    parts.append(c["text"])
                else:
                    keep_words = [w for w in c["words"] if w["start"] >= args.overlap_sec]
                    parts.append(words_to_text(keep_words))
            else:
                parts.append(c["text"])
        final_text = " ".join(parts)
        final_text = re.sub(r"\s+", " ", final_text).strip()
        Path(args.output).write_text(final_text, encoding="utf-8")
        print(f"Done (no LLM): {len(final_text.split())} words")
        return 0

    # With LLM: process in pairs
    print("\n=== Stitching in pairs ===")
    stitched_parts = []

    for i in range(len(chunks)):
        c = chunks[i]
        if not c["words"] or not c["text"]:
            stitched_parts.append(c["text"])
            continue

        is_first = (i == 0)
        is_last = (i == len(chunks) - 1)

        if is_first and is_last:
            stitched_parts.append(c["text"])
            continue

        if is_first:
            # Take beginning of first chunk (everything except last overlap_sec+context_sec)
            keep_until = c["duration"] - args.overlap_sec - args.context_sec
            keep_words = [w for w in c["words"] if w["end"] <= keep_until]
            part = words_to_text(keep_words)
            stitched_parts.append(part)
            print(f"  chunk_{i:03d}: kept {len(keep_words)}/{len(c['words'])} words (head)")

        elif is_last:
            # Take end of last chunk (everything from overlap_sec onwards)
            keep_words = [w for w in c["words"] if w["start"] >= args.overlap_sec]
            part = words_to_text(keep_words)
            stitched_parts.append(part)
            print(f"  chunk_{i:03d}: kept {len(keep_words)}/{len(c['words'])} words (tail)")

        else:
            # Transition: need LLM stitching of overlap zone
            prev = chunks[i - 1]
            curr = c

            # Get text for LLM: end of prev + start of curr
            prev_end = prev["duration"]
            prev_keep_until = prev_end - args.overlap_sec - args.context_sec
            prev_tail_words = [w for w in prev["words"] if w["end"] > prev_keep_until]
            text_a = words_to_text(prev_tail_words)

            curr_keep_from = args.overlap_sec - args.context_sec
            curr_head_words = [w for w in curr["words"] if w["start"] < args.overlap_sec + args.context_sec]
            text_b = words_to_text(curr_head_words)

            print(f"  Stitching {prev['dir'].name} -> {curr['dir'].name}...")
            print(f"    Text A ({len(text_a.split())} words): ...{text_a[-100:]}")
            print(f"    Text B ({len(text_b.split())} words): {text_b[:100]}...")

            stitched = call_llm(STITCH_PROMPT, text_a, text_b)
            if not stitched:
                # Fallback: simple concatenation
                print(f"    LLM failed, falling back to simple concatenation")
                stitched = text_a + " " + text_b

            stitched_parts.append(stitched)
            print(f"    Stitched: {len(stitched.split())} words")

    # Concatenate all parts
    final_text = " ".join(stitched_parts)
    final_text = re.sub(r"\s+", " ", final_text).strip()

    Path(args.output).write_text(final_text, encoding="utf-8")
    word_count = len(final_text.split())
    print(f"\n=== Done: {word_count} words ===")
    print(f"Output: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())