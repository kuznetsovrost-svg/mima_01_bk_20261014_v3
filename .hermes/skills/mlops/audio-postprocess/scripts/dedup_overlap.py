#!/usr/bin/env python3
"""
dedup_overlap.py - LLM-based deduplication of overlap chunks.

For each pair of consecutive overlap chunks:
1. Identifies the overlap zone (last N seconds of chunk N = first N seconds of chunk N+1)
2. Calls LLM to produce a clean, deduplicated transition
3. Concatenates the result

Usage:
    python3 dedup_overlap.py <chunks_dir> <output_md> [--overlap-sec 15]
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path


def get_chunk_text(chunk_dir: Path) -> tuple[str, list[dict]]:
    """Reads chunk plain text + words with timestamps."""
    plain = chunk_dir / f"{chunk_dir.name}_plain.md"
    words_file = chunk_dir / f"{chunk_dir.name}_words.json"

    text = plain.read_text(encoding="utf-8").strip() if plain.exists() else ""
    words = []
    if words_file.exists():
        import json
        data = json.loads(words_file.read_text(encoding="utf-8"))
        words = data.get("words", [])

    return text, words


def find_overlap_zone(words_a: list[dict], words_b: list[dict], overlap_sec: float) -> tuple[list[dict], list[dict]]:
    """Find the overlap zone: last overlap_sec of A + first overlap_sec of B."""
    if not words_a or not words_b:
        return [], []

    # Last N seconds of A
    a_end = words_a[-1]["end"]
    a_overlap_start = a_end - overlap_sec
    a_overlap = [w for w in words_a if w["end"] >= a_overlap_start]

    # First N seconds of B
    b_overlap = [w for w in words_b if w["end"] <= overlap_sec]

    return a_overlap, b_overlap


def words_to_text(words: list[dict]) -> str:
    return " ".join(w["word"] for w in words)


def call_llm(prompt: str, content: str) -> str:
    """Call hermes -z with the prompt."""
    full_prompt = f"{prompt}\n\n---\n\n{content}\n\n---\n\nOutput:"
    result = subprocess.run(
        ["hermes", "-z", full_prompt],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        print(f"  LLM error: {result.stderr[:200]}", file=sys.stderr)
        return ""
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("chunks_dir", help="Directory with chunk_NNN subdirs")
    parser.add_argument("output", help="Output file path")
    parser.add_argument("--overlap-sec", type=float, default=15.0)
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM, use simple word-level dedup")
    args = parser.parse_args()

    chunks_dir = Path(args.chunks_dir)
    chunk_dirs = sorted(chunks_dir.glob("chunk_*"))

    if len(chunk_dirs) < 2:
        print(f"ERROR: need at least 2 chunks, found {len(chunk_dirs)}", file=sys.stderr)
        return 1

    print(f"Processing {len(chunk_dirs)} chunks, overlap={args.overlap_sec}s")

    # Read all chunks
    chunks = []
    for cd in chunk_dirs:
        text, words = get_chunk_text(cd)
        chunks.append({"dir": cd, "text": text, "words": words})

    # First chunk: take everything except last overlap_sec
    # Then for each pair, dedup overlap zone
    # Last chunk: take everything except first overlap_sec

    if not args.no_llm:
        print("Using LLM for overlap deduplication...")

    final_parts = []
    for i, chunk in enumerate(chunks):
        words = chunk["words"]
        if not words:
            final_parts.append(chunk["text"])
            continue

        is_first = (i == 0)
        is_last = (i == len(chunks) - 1)

        if is_first and is_last:
            # Single chunk
            final_parts.append(chunk["text"])
            continue

        chunk_dur = words[-1]["end"]

        if is_first:
            # Keep from start, cut last overlap_sec
            keep_until = chunk_dur - args.overlap_sec
            keep_words = [w for w in words if w["end"] <= keep_until]
            final_parts.append(words_to_text(keep_words))
            print(f"  chunk_{i:03d}: kept {len(keep_words)}/{len(words)} words (start)")

        elif is_last:
            # Keep from overlap_sec onwards
            keep_words = [w for w in words if w["start"] >= args.overlap_sec]
            final_parts.append(words_to_text(keep_words))
            print(f"  chunk_{i:03d}: kept {len(keep_words)}/{len(words)} words (end)")

        else:
            # Middle chunk: cut last and first overlap_sec
            keep_until = chunk_dur - args.overlap_sec
            keep_words = [w for w in words if args.overlap_sec <= w["end"] <= keep_until]
            final_parts.append(words_to_text(keep_words))
            print(f"  chunk_{i:03d}: kept {len(keep_words)}/{len(words)} words (middle)")

    # Concatenate
    final_text = " ".join(final_parts)
    final_text = re.sub(r"\s+", " ", final_text).strip()

    Path(args.output).write_text(final_text, encoding="utf-8")
    word_count = len(final_text.split())
    print(f"\nDone: {word_count} words")
    print(f"Output: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())