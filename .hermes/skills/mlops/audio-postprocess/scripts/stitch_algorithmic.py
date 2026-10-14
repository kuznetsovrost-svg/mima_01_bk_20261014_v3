#!/usr/bin/env python3
"""
stitch_algorithmic.py - Algorithmic stitching of overlap chunks (no LLM).

Each chunk was cut with ffmpeg -ss OFFSET, so its word timestamps are RELATIVE
(start at 0). To stitch, we need to:
1. Add absolute offset = chunk_index * step to each word's start/end
2. Each chunk N "owns" [N*step, (N+1)*step] in absolute time
3. We extend by stitch_zone (e.g., 2 sec) into adjacent zones
4. Then we deduplicate the result by timestamp overlap

Output: a list of words with absolute timestamps, then deduplicated.
"""
import argparse
import json
import re
import sys
from pathlib import Path


def get_chunk_data(chunk_dir: Path) -> tuple[list[dict], float]:
    """Read chunk's word-level timestamps."""
    words_file = chunk_dir / f"{chunk_dir.name}_words.json"
    if not words_file.exists():
        return [], 0.0

    data = json.loads(words_file.read_text(encoding="utf-8"))
    words = data.get("words", [])
    if not words:
        return [], 0.0
    duration = max(w["end"] for w in words)
    return words, duration


def stitch(chunks: list[dict], step_sec: float, overlap_sec: float) -> tuple[str, dict]:
    """
    Stitch chunks together using absolute timestamps.

    Each chunk N covers [N*step, N*step + duration] in original audio.
    Words from chunk N are tagged with their absolute timestamps.
    We then deduplicate words whose absolute timestamps overlap (with the higher
    probability word winning).
    """
    if not chunks:
        return "", {}

    stitch_zone = min(2.0, overlap_sec / 4)

    all_words = []
    total_words = 0
    kept_words = 0

    for i, c in enumerate(chunks):
        words = c["words"]
        if not words:
            continue

        chunk_offset = i * step_sec
        chunk_duration = c["duration"]

        # Convert to absolute timestamps
        abs_words = []
        for w in words:
            abs_words.append({
                "word": w["word"],
                "start": w["start"] + chunk_offset,
                "end": w["end"] + chunk_offset,
                "probability": w.get("probability", 0.5),
            })

        is_last = (i == len(chunks) - 1)

        # Each chunk N covers [N*step, (N+1)*step] uniquely.
        # We extend by `stitch_zone` seconds into adjacent zones so we have
        # overlapping words at boundaries. The deduplication will be done
        # by the dedup pass at the end.
        keep_start = chunk_offset - stitch_zone
        keep_end = chunk_offset + step_sec + stitch_zone
        if is_last:
            keep_end = chunk_offset + chunk_duration

        keep = [w for w in abs_words if w["start"] >= keep_start and w["end"] <= keep_end]
        total_words += len(abs_words)
        kept_words += len(keep)
        all_words.extend(keep)

    # Deduplicate: sort by start, then for overlapping words keep the one with higher probability
    all_words.sort(key=lambda w: (w["start"], -w["probability"]))

    deduped = []
    for w in all_words:
        # Check if this word overlaps with the last kept word
        if deduped:
            last = deduped[-1]
            # Overlap: starts within last word's range
            if w["start"] < last["end"]:
                # Skip if lower probability
                if w["probability"] <= last["probability"]:
                    continue
                # Else replace last word
                else:
                    deduped.pop()
        deduped.append(w)

    final = " ".join(w["word"] for w in deduped)
    final = re.sub(r"\s+", " ", final).strip()

    stats = {
        "total_words": total_words,
        "kept_words": kept_words,
        "deduped_words": len(deduped),
        "duplicates_removed": kept_words - len(deduped),
        "output_words": len(final.split()),
    }
    return final, stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("chunks_dir", help="Directory with chunk_NNN subdirs")
    parser.add_argument("output", help="Output file path")
    parser.add_argument("--overlap-sec", type=float, default=30.0)
    parser.add_argument("--step-sec", type=float, default=None,
                        help="Seconds between chunk starts (default: chunk_len - overlap)")
    args = parser.parse_args()

    chunks_dir = Path(args.chunks_dir)
    chunk_dirs = sorted(chunks_dir.glob("chunk_*"))

    if len(chunk_dirs) < 2:
        print(f"ERROR: need at least 2 chunks, found {len(chunk_dirs)}", file=sys.stderr)
        return 1

    if args.step_sec is None:
        args.step_sec = 60.0 - args.overlap_sec

    print(f"Processing {len(chunk_dirs)} chunks")
    print(f"  overlap={args.overlap_sec}s, step={args.step_sec}s")

    chunks = []
    for cd in chunk_dirs:
        words, duration = get_chunk_data(cd)
        chunks.append({"name": cd.name, "words": words, "duration": duration})
        print(f"  {cd.name}: {len(words)} words, {duration:.1f}s audio")

    result, stats = stitch(chunks, args.step_sec, args.overlap_sec)

    Path(args.output).write_text(result, encoding="utf-8")
    print(f"\n=== Stats ===")
    print(f"  Total words in chunks: {stats['total_words']}")
    print(f"  Kept (with overlap zone): {stats['kept_words']}")
    print(f"  Duplicates removed: {stats['duplicates_removed']}")
    print(f"  Output words: {stats['output_words']}")
    print(f"\n=== Output: {args.output} ===")

    return 0


if __name__ == "__main__":
    sys.exit(main())