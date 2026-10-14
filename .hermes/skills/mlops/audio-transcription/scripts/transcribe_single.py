#!/usr/bin/env python3
"""
transcribe_single.py - Transcribe entire audio as ONE chunk (no overlap).

- Uses medium model with int8 quantization
- Limits memory consumption by setting CTranslate2 threads
- Processes the whole file in a single Whisper call
- beam_size=5 for better accuracy
"""
import argparse
import gc
import json
import os
import re
import resource
import subprocess
import sys
import time
from pathlib import Path

# Limit threads to control memory
os.environ["CT2_NUM_THREADS"] = "2"
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"

from faster_whisper import WhisperModel


def set_memory_limit(max_gb: float):
    """Try to set process memory limit. Best-effort, OS-dependent."""
    try:
        max_bytes = int(max_gb * 1024 * 1024 * 1024)
        resource.setrlimit(resource.RLIMIT_AS, (max_bytes, max_bytes))
    except (ValueError, OSError):
        pass


def format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Audio file (mp3, wav, m4a, ...)")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--model", default="medium", help="Model name (default: medium)")
    parser.add_argument("--beam-size", type=int, default=5, help="Beam size (default: 5)")
    parser.add_argument("--prompt", help="Path to initial_prompt file")
    parser.add_argument("--hotwords", help="Hotwords string")
    parser.add_argument("--no-speech-threshold", type=float, default=0.6)
    parser.add_argument("--compression-ratio-threshold", type=float, default=2.4)
    parser.add_argument("--log-prob-threshold", type=float, default=-1.0)
    parser.add_argument("--no-vad", action="store_true", help="Disable VAD")
    parser.add_argument("--no-temperature-fallback", action="store_true")
    parser.add_argument("--max-memory-gb", type=float, default=4.0,
                        help="Max memory in GB (default: 4.0)")
    args = parser.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"ERROR: {src} not found")
        return 1

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = src.stem

    print(f"Source: {src}")
    print(f"Output: {out_dir}")
    print(f"Model: {args.model}, Beam: {args.beam_size}")
    print(f"Memory limit: {args.max_memory_gb} GB")

    # Set memory limit
    set_memory_limit(args.max_memory_gb)

    # Load model
    print("Loading model...")
    t0 = time.time()
    model = WhisperModel(
        args.model,
        device="cpu",
        compute_type="int8",
    )
    print(f"Model loaded in {time.time() - t0:.1f}s")

    # Read prompt if file
    initial_prompt = None
    if args.prompt:
        prompt_path = Path(args.prompt)
        if prompt_path.exists():
            initial_prompt = prompt_path.read_text(encoding="utf-8")[:1000]
            print(f"Prompt: {len(initial_prompt)} chars from {prompt_path}")

    # Transcribe
    print("Starting transcription (single chunk, no overlap)...")
    t0 = time.time()

    transcribe_kwargs = {
        "language": "ru",
        "beam_size": args.beam_size,
        "word_timestamps": True,
        "vad_filter": not args.no_vad,
        "compression_ratio_threshold": args.compression_ratio_threshold,
        "log_prob_threshold": args.log_prob_threshold,
        "no_speech_threshold": args.no_speech_threshold,
    }
    if not args.no_temperature_fallback:
        transcribe_kwargs["temperature"] = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    if initial_prompt:
        transcribe_kwargs["initial_prompt"] = initial_prompt
    if args.hotwords:
        transcribe_kwargs["hotwords"] = args.hotwords

    segments_iter, info = model.transcribe(str(src), **transcribe_kwargs)
    print(f"Detected language: {info.language} (prob={info.language_probability:.2f})")
    print(f"Duration: {info.duration:.1f}s")

    # Collect all segments
    all_segments = []
    all_words = []
    for segment in segments_iter:
        seg_data = {
            "id": segment.id,
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "avg_logprob": segment.avg_logprob,
            "no_speech_prob": segment.no_speech_prob,
            "compression_ratio": segment.compression_ratio,
        }
        all_segments.append(seg_data)

        if segment.words:
            for w in segment.words:
                all_words.append({
                    "word": w.word,
                    "start": w.start,
                    "end": w.end,
                    "probability": w.probability,
                })

    elapsed = time.time() - t0
    print(f"Transcribed in {elapsed:.1f}s ({elapsed/60:.1f} min)")

    # Write outputs
    segments_text = "\n\n".join(
        f"**[{format_timestamp(s['start'])} - {format_timestamp(s['end'])}]** {s['text'].strip()}"
        for s in all_segments
    )
    plain_text = " ".join(s["text"].strip() for s in all_segments)

    # .md with timestamps
    (out_dir / f"{base}.md").write_text(
        f"# Transcription: {src.name} (single chunk, beam={args.beam_size})\n\n"
        f"**Duration:** {format_timestamp(info.duration)}\n"
        f"**Language:** {info.language} (probability {info.language_probability:.2f})\n"
        f"**Model:** {args.model} (int8)\n"
        f"**Segments:** {len(all_segments)}\n"
        f"**Transcription time:** {elapsed:.1f}s\n\n---\n\n"
        f"{segments_text}\n",
        encoding="utf-8",
    )

    # _plain.md
    (out_dir / f"{base}_plain.md").write_text(plain_text + "\n", encoding="utf-8")

    # .json
    (out_dir / f"{base}.json").write_text(json.dumps({
        "duration": info.duration,
        "language": info.language,
        "language_probability": info.language_probability,
        "model": args.model,
        "beam_size": args.beam_size,
        "segments": all_segments,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # _words.json
    (out_dir / f"{base}_words.json").write_text(json.dumps({
        "duration": info.duration,
        "words": all_words,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    word_count = sum(len(s["text"].split()) for s in all_segments)
    print(f"Words: {word_count}")
    print(f"Files written: {out_dir}/{base}.md, _plain.md, .json, _words.json")

    return 0


if __name__ == "__main__":
    sys.exit(main())