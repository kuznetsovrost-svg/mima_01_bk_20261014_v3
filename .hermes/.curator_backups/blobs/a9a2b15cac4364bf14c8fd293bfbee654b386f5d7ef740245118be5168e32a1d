#!/usr/bin/env python3
"""Transcribe audio file to Markdown using faster-whisper large-v3 (int8, CPU).

Outputs four files per input:
  <base>.md         — Markdown with timestamps [HH:MM:SS]
  <base>_plain.md   — Markdown without timestamps (continuous text)
  <base>.json       — Full metadata + segments + word timestamps (machine-readable)
  <base>_words.json — Just the word list with timestamps (for post-processing)
"""
import argparse
import json
import re
import time
from pathlib import Path

from faster_whisper import WhisperModel


def format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def join_plain(segments: list[dict]) -> str:
    """Join segments into one paragraph, capitalize after sentence endings."""
    texts = [seg["text"].strip() for seg in segments if seg["text"].strip()]
    joined = " ".join(texts)
    if not joined:
        return ""
    # Capitalize first letter
    out = joined[0].upper() + joined[1:]
    # Capitalize after . ! ?
    out = re.sub(r'([.!?])\s+([а-яёa-z])', lambda m: m.group(1) + " " + m.group(2).upper(), out)
    # Add period at end if missing
    if out[-1] not in ".!?":
        out += "."
    return out


def write_markdown_with_timestamps(
    input_name: str,
    info,
    model_size: str,
    compute_type: str,
    elapsed: float,
    segments: list[dict],
    path: Path,
) -> None:
    md = [
        f"# Transcription: {input_name}",
        "",
        f"**Duration:** {format_timestamp(info.duration)}",
        f"**Language:** {info.language} (probability {info.language_probability:.2f})",
        f"**Model:** {model_size} ({compute_type})",
        f"**Segments:** {len(segments)}",
        f"**Transcription time:** {elapsed:.1f}s",
        "",
        "---",
        "",
    ]
    for seg in segments:
        ts = format_timestamp(seg["start"])
        md.append(f"[{ts}] {seg['text']}")
    path.write_text("\n".join(md), encoding="utf-8")


def write_markdown_plain(
    input_name: str,
    info,
    model_size: str,
    compute_type: str,
    elapsed: float,
    segments: list[dict],
    path: Path,
) -> None:
    plain = join_plain(segments)
    md = [
        f"# Transcription: {input_name} (plain text, no timestamps)",
        "",
        f"**Duration:** {format_timestamp(info.duration)}",
        f"**Language:** {info.language} (probability {info.language_probability:.2f})",
        f"**Model:** {model_size} ({compute_type})",
        f"**Segments:** {len(segments)}",
        f"**Transcription time:** {elapsed:.1f}s",
        "",
        "---",
        "",
        plain,
    ]
    path.write_text("\n".join(md), encoding="utf-8")


def write_json(
    input_path: Path,
    info,
    model_size: str,
    compute_type: str,
    beam_size: int,
    elapsed: float,
    segments: list[dict],
    words: list[dict],
    path: Path,
) -> None:
    path.write_text(
        json.dumps(
            {
                "input": str(input_path),
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
                "model": model_size,
                "compute_type": compute_type,
                "beam_size": beam_size,
                "transcription_time_seconds": round(elapsed, 2),
                "segments": segments,
                "words": words,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def transcribe(
    input_path: Path,
    output_dir: Path,
    language: str = "ru",
    model_size: str = "large-v3",
    compute_type: str = "int8",
    beam_size: int = 5,
    initial_prompt: str | None = None,
    hotwords: str | None = None,
    vad_filter: bool = True,
    # Anti-hallucination parameters (faster-whisper built-in)
    compression_ratio_threshold: float = 2.4,
    log_prob_threshold: float = -1.0,
    no_speech_threshold: float = 0.6,
    # Temperature fallback: retries with higher temperature on failures
    temperature_fallback: bool = True,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    base = input_path.stem

    print(f"[1/5] Loading model {model_size} ({compute_type}) on CPU...")
    t0 = time.time()
    model = WhisperModel(model_size, device="cpu", compute_type=compute_type)
    print(f"  Loaded in {time.time()-t0:.1f}s")

    # Build transcribe kwargs
    transcribe_kwargs = dict(
        language=language,
        beam_size=beam_size,
        initial_prompt=initial_prompt,
        vad_filter=vad_filter,
        word_timestamps=True,
    )
    # Add optional parameters
    if hotwords:
        transcribe_kwargs["hotwords"] = hotwords
        print(f"  Hotwords enabled: {len(hotwords.split())} words")
    if compression_ratio_threshold is not None:
        transcribe_kwargs["compression_ratio_threshold"] = compression_ratio_threshold
    if log_prob_threshold is not None:
        transcribe_kwargs["log_prob_threshold"] = log_prob_threshold
    if no_speech_threshold is not None:
        transcribe_kwargs["no_speech_threshold"] = no_speech_threshold
    # Temperature fallback: try 0.0, 0.2, 0.4, 0.6, 0.8, 1.0
    if temperature_fallback:
        transcribe_kwargs["temperature"] = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        print(f"  Temperature fallback enabled")

    print(f"[2/5] Transcribing {input_path.name}...")
    t0 = time.time()
    segments_iter, info = model.transcribe(
        str(input_path),
        **transcribe_kwargs,
    )

    segments = []
    all_words = []
    for seg in segments_iter:
        seg_dict = {
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
        }
        segments.append(seg_dict)
        print(f"  [{format_timestamp(seg.start)}] {seg.text.strip()[:80]}...")
        # Сбор слов с timestamps (если есть)
        if hasattr(seg, "words") and seg.words:
            for w in seg.words:
                if w.word.strip():
                    all_words.append({
                        "word": w.word.strip(),
                        "start": round(w.start, 3),
                        "end": round(w.end, 3),
                        "probability": round(w.probability, 4),
                    })

    elapsed = time.time() - t0
    print(f"  Transcribed in {elapsed:.1f}s ({len(segments)} segments)")

    print(f"[3/5] Writing Markdown with timestamps...")
    md_path = output_dir / f"{base}.md"
    write_markdown_with_timestamps(
        input_path.name, info, model_size, compute_type, elapsed, segments, md_path
    )
    print(f"  Wrote {md_path} ({md_path.stat().st_size / 1024:.1f} KB)")

    print(f"[4/5] Writing plain Markdown (no timestamps)...")
    plain_path = output_dir / f"{base}_plain.md"
    write_markdown_plain(
        input_path.name, info, model_size, compute_type, elapsed, segments, plain_path
    )
    print(f"  Wrote {plain_path} ({plain_path.stat().st_size / 1024:.1f} KB)")

    print(f"[5/6] Writing JSON metadata...")
    json_path = output_dir / f"{base}.json"
    write_json(
        input_path, info, model_size, compute_type, beam_size, elapsed, segments, all_words, json_path
    )
    print(f"  Wrote {json_path}")

    print(f"[6/6] Writing word timestamps...")
    words_path = output_dir / f"{base}_words.json"
    words_path.write_text(
        json.dumps({
            "input": str(input_path),
            "language": info.language,
            "duration": info.duration,
            "word_count": len(all_words),
            "words": all_words,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"  Wrote {words_path} ({len(all_words)} words)")

    return {
        "md": str(md_path),
        "plain_md": str(plain_path),
        "json": str(json_path),
        "words_json": str(words_path),
        "segments": len(segments),
        "words": len(all_words),
        "duration": info.duration,
        "transcription_time": elapsed,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio with faster-whisper (Whisper large-v3 default)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic transcription
  python3 transcribe.py input.mp3 --output ./out

  # With initial prompt for vocabulary
  python3 transcribe.py input.mp3 --output ./out --prompt templates/initial_prompts/business_analysis.txt

  # With hotwords (boost specific words)
  python3 transcribe.py input.mp3 --output ./out --hotwords "BPMN шлюз gateway процесс"

  # Aggressive anti-hallucination
  python3 transcribe.py input.mp3 --output ./out \\
      --no-speech-threshold 0.8 \\
      --compression-ratio-threshold 2.0 \\
      --logprob-threshold -0.5

  # Fast transcription without VAD
  python3 transcribe.py input.mp3 --output ./out --no-vad --beam-size 1
        """,
    )
    parser.add_argument("input", type=Path, help="Input audio file (mp3, wav, m4a, etc.)")
    parser.add_argument("--output", type=Path, required=True, help="Output directory")
    parser.add_argument("--language", default="ru", help="Language code (default: ru)")
    parser.add_argument("--model", default="large-v3", help="Whisper model size (default: large-v3)")
    parser.add_argument("--compute-type", default="int8", help="Compute type (default: int8)")
    parser.add_argument("--beam-size", type=int, default=5, help="Beam size (default: 5, lower=faster)")
    parser.add_argument("--prompt", type=str, default=None, help="Initial prompt (file path or text)")
    parser.add_argument("--hotwords", type=str, default=None, help="Hotwords to boost (space-separated)")
    parser.add_argument("--no-vad", action="store_true", help="Disable Voice Activity Detection filter")
    parser.add_argument("--no-temperature-fallback", action="store_true",
                        help="Disable temperature fallback (use only temperature=0)")
    parser.add_argument("--compression-ratio-threshold", type=float, default=2.4,
                        help="Skip segments with compression ratio above this (default: 2.4)")
    parser.add_argument("--log-prob-threshold", type=float, default=-1.0,
                        help="Skip segments with avg log_prob below this (default: -1.0)")
    parser.add_argument("--no-speech-threshold", type=float, default=0.6,
                        help="Skip segments with no-speech probability above this (default: 0.6)")
    args = parser.parse_args()

    # Load prompt from file if it's a path
    prompt = args.prompt
    if prompt and Path(prompt).is_file():
        print(f"Loading prompt from {prompt}")
        prompt = Path(prompt).read_text(encoding="utf-8")

    result = transcribe(
        args.input,
        args.output,
        language=args.language,
        model_size=args.model,
        compute_type=args.compute_type,
        beam_size=args.beam_size,
        initial_prompt=prompt,
        hotwords=args.hotwords,
        vad_filter=not args.no_vad,
        compression_ratio_threshold=args.compression_ratio_threshold,
        log_prob_threshold=args.log_prob_threshold,
        no_speech_threshold=args.no_speech_threshold,
        temperature_fallback=not args.no_temperature_fallback,
    )
    print("\n=== Result ===")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()