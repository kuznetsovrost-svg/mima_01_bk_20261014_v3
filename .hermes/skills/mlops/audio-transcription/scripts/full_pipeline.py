#!/usr/bin/env python3
"""Complete transcription pipeline with JEV validation stages.

Pipeline (5 stages, 3 of which use JEV):
  0. Pre-flight (JEV): check if file is worth transcribing
  1. Whisper: faster-whisper large-v3 with word_timestamps
  2. Hallucination filter (JEV): remove Whisper artifacts
  3. LLM postprocess: punctuation + paragraphs via hermes -z
  4. Quality gate (JEV): accept / redo / manual / discard
  5. Wiki annotation (JEV): topic, type, quality, related lectures

Usage:
  python3 full_pipeline.py input.mp3 --output ./out
  python3 full_pipeline.py input.mp3 --output ./out --skip-jev
  python3 full_pipeline.py input.mp3 --output ./out --only-stage 1
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Add jev-decisions to path
JEV_PATH = Path("/root/.hermes/skills/jev-decisions/scripts")
sys.path.insert(0, str(JEV_PATH))

try:
    from jev_client import jev_decide, jev_choice, jev_score, jev_noul
    JEV_AVAILABLE = True
except Exception:
    JEV_AVAILABLE = False


# === Stage 0: Pre-flight (JEV) ===

def preflight_check(audio_path: Path) -> dict:
    """JEV decides if file is worth transcribing."""
    import subprocess
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_format", "-of", "json", str(audio_path)],
            capture_output=True, text=True, timeout=10,
        )
        info = json.loads(result.stdout).get("format", {})
        meta = {
            "duration_sec": float(info.get("duration", 0)),
            "bitrate_bps": int(info.get("bit_rate", 0)),
            "size_bytes": int(info.get("size", 0)),
        }
    except Exception:
        meta = {"duration_sec": 0, "bitrate_bps": 0, "size_bytes": audio_path.stat().st_size}

    return jev_decide(
        state={
            "file": {"name": audio_path.name, "size_mb": round(meta["size_bytes"] / 1e6, 1)},
            "audio": meta,
        },
        questions={
            "has_speech": {
                "type": "noul",
                "instructions": "Is there human speech in this audio? (not just music/silence/noise)",
            },
            "language": {
                "type": "choice",
                "criteria": {
                    "ru": "Russian",
                    "en": "English",
                    "mixed": "Mixed (ru+en)",
                    "other": "Other language",
                    "none": "No speech",
                },
            },
            "audio_quality": {
                "type": "score",
                "criteria": [
                    "0: garbage (unintelligible)",
                    "1: poor (heavy noise)",
                    "2: medium (audible with effort)",
                    "3: good (clear)",
                    "4: studio quality",
                ],
            },
            "action": {
                "type": "choice",
                "criteria": {
                    "transcribe": "Run Whisper transcription",
                    "skip_silence": "Skip (no speech detected)",
                    "skip_wrong_lang": "Skip (not Russian)",
                    "manual": "Send for manual review",
                },
            },
        },
    )


# === Stage 1: Whisper ===

def transcribe_whisper(
    audio_path: Path,
    output_dir: Path,
    language: str = "ru",
    beam_size: int = 5,
    model_size: str = "large-v3",
    compute_type: str = "int8",
    initial_prompt: str | None = None,
    hotwords: str | None = None,
    vad_filter: bool = True,
    compression_ratio_threshold: float = 2.4,
    log_prob_threshold: float = -1.0,
    no_speech_threshold: float = 0.6,
    temperature_fallback: bool = True,
) -> dict:
    """Run faster-whisper transcription with word_timestamps."""
    from faster_whisper import WhisperModel

    print(f"  Loading model {model_size} ({compute_type})...")
    model = WhisperModel(model_size, device="cpu", compute_type=compute_type)

    print(f"  Transcribing {audio_path.name}...")
    t0 = time.time()
    transcribe_kwargs = {
        "language": language,
        "beam_size": beam_size,
        "word_timestamps": True,
        "vad_filter": vad_filter,
        "vad_parameters": {"min_silence_duration_ms": 500},
    }
    if initial_prompt:
        transcribe_kwargs["initial_prompt"] = initial_prompt
    if hotwords:
        transcribe_kwargs["hotwords"] = hotwords
    if compression_ratio_threshold is not None:
        transcribe_kwargs["compression_ratio_threshold"] = compression_ratio_threshold
    if log_prob_threshold is not None:
        transcribe_kwargs["log_prob_threshold"] = log_prob_threshold
    if no_speech_threshold is not None:
        transcribe_kwargs["no_speech_threshold"] = no_speech_threshold
    if temperature_fallback:
        transcribe_kwargs["temperature"] = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

    segments_iter, info = model.transcribe(str(audio_path), **transcribe_kwargs)
    elapsed = time.time() - t0

    # Collect segments + words
    all_segments = []
    all_words = []
    for seg in segments_iter:
        all_segments.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text,
        })
        if seg.words:
            for w in seg.words:
                all_words.append({
                    "word": w.word,
                    "start": w.start,
                    "end": w.end,
                    "probability": w.probability,
                })

    return {
        "info": {
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
        },
        "segments": all_segments,
        "words": all_words,
        "elapsed": elapsed,
    }


# === Stage 2: Hallucination filter (JEV) ===

def filter_hallucinations(words: list[dict], segment_sec: int = 30) -> list[dict]:
    """JEV identifies and removes Whisper hallucination segments."""
    if not JEV_AVAILABLE:
        return words

    # Group words into chunks by time
    chunks = []
    current_chunk = []
    chunk_start = 0
    if words:
        chunk_start = words[0]["start"]
    for w in words:
        if w["start"] - chunk_start > segment_sec and current_chunk:
            chunks.append(current_chunk)
            current_chunk = [w]
            chunk_start = w["start"]
        else:
            current_chunk.append(w)
    if current_chunk:
        chunks.append(current_chunk)

    # Check each chunk
    clean = []
    for chunk in chunks:
        text = " ".join(w["word"] for w in chunk).strip()
        if len(text) < 10:
            clean.extend(chunk)
            continue

        result = jev_decide(
            state=f"Time: {chunk[0]['start']:.1f}-{chunk[-1]['end']:.1f}s\n{text}",
            questions={
                "is_repetition": {
                    "type": "noul",
                    "instructions": "Contains 3+ repeated words/phrases in a row (Whisper hallucination)?",
                },
                "is_filler_only": {
                    "type": "noul",
                    "instructions": "Only filler words (э-э, ммм, ну) without meaning?",
                },
                "is_coherent": {
                    "type": "noul",
                    "instructions": "Is the text coherent and meaningful?",
                },
            },
        )
        ans = result["answers"]

        # Skip if any indicator of garbage
        if (ans["is_repetition"]["noul"] > 0.7
            or ans["is_filler_only"]["noul"] > 0.7
            or not ans["is_coherent"]["noul"]):
            continue

        clean.extend(chunk)

    return clean


# === Stage 3: LLM postprocess ===

def postprocess_with_llm(words: list[dict]) -> str:
    """Call hermes -z to add punctuation and paragraphs."""
    if not words:
        return ""

    # Build marked text with [PAUSE X.XX] markers
    parts = []
    for i, w in enumerate(words):
        word = w["word"].strip()
        if not word:
            continue
        parts.append(word)
        if i < len(words) - 1:
            pause = words[i + 1]["start"] - w["end"]
            if pause >= 0.1:
                parts.append(f" [PAUSE {pause:.2f}] ")
            else:
                parts.append(" ")
        else:
            parts.append(".")

    marked_text = "".join(parts)

    # Build prompt
    prompt = f"""You are a Russian text post-processor for a Whisper transcription.
Add punctuation and paragraph breaks to the raw run-on text below.

INPUT FORMAT:
- Plain text without punctuation
- Pauses between words marked as [PAUSE X.XX] seconds

RULES:
- pause >= 0.7s → end of sentence (. or ?)
- pause >= 2.0s → paragraph break (blank line)
- Capitalize proper names (Денис, Ростислав, Лёша)
- Don't insert random commas
- Preserve all words exactly

OUTPUT: Only the punctuated text with paragraph breaks.

TEXT:
<<<
{marked_text}
>>>

Output ONLY the punctuated text, nothing else.
"""

    # Call hermes -z
    result = subprocess.run(
        ["hermes", "-z", prompt, "--model", "MiniMax-M3", "--reasoning", "low"],
        capture_output=True, text=True, timeout=300,
        env={**os.environ, "HERMES_PROFILE": "default"},
    )
    output = result.stdout.strip()

    # Strip "Saved to..." and trailing ---
    lines = output.split("\n")
    if lines and lines[0].startswith("Saved to"):
        lines = lines[1:]
    while lines and lines[0].strip() == "---":
        lines = lines[1:]
    while lines and lines[-1].strip() == "---":
        lines.pop()

    return "\n".join(lines).strip()


# === Stage 4: Quality gate (JEV) ===

def quality_gate(postprocessed: str, original_words: list[dict]) -> dict:
    """JEV evaluates quality and decides next action."""
    if not original_words:
        duration = 0
    else:
        duration = original_words[-1]["end"] - original_words[0]["start"]

    return jev_decide(
        state={
            "audio": {"duration_sec": round(duration, 1), "word_count": len(original_words)},
            "text_preview": postprocessed[:2000],
        },
        questions={
            "readability": {
                "type": "score",
                "criteria": [
                    "0: unreadable",
                    "1: poor (lots of garbage)",
                    "2: medium (issues present)",
                    "3: good (readable)",
                    "4: excellent",
                ],
            },
            "punctuation_quality": {
                "type": "score",
                "criteria": [
                    "0: no punctuation",
                    "1: partial",
                    "2: acceptable",
                    "3: good",
                    "4: excellent",
                ],
            },
            "paragraph_quality": {
                "type": "noul",
                "instructions": "Are paragraphs logically split?",
            },
            "action": {
                "type": "choice",
                "criteria": {
                    "accept": "Accept as is",
                    "polish": "Polish (one more LLM call)",
                    "redo": "Redo postprocess",
                    "manual": "Send for manual review",
                    "discard": "Discard (too poor)",
                },
            },
        },
    )


# === Stage 5: Wiki annotation (JEV) ===

def annotate_for_wiki(postprocessed: str, meta: dict) -> dict:
    """JEV annotates lecture for wiki integration."""
    return jev_decide(
        state={
            "title": meta.get("title", "Untitled"),
            "duration_min": round(meta.get("duration", 0) / 60, 1),
            "text_preview": postprocessed[:3000],
        },
        questions={
            "primary_topic": {
                "type": "choice",
                "criteria": {
                    "bpmn_2": "BPMN 2.0",
                    "bpmn_vs_uml": "BPMN vs UML",
                    "process_mining": "Process Mining",
                    "ba_basics": "BA basics",
                    "requirements": "Requirements management",
                    "tools": "Tools (jBPM, Camunda)",
                    "case_study": "Practical case study",
                    "theory": "Theoretical lecture",
                },
            },
            "content_type": {
                "type": "choice",
                "criteria": {
                    "intro": "Introduction to topic",
                    "standard": "Standard material",
                    "deep_dive": "Deep dive",
                    "case_study": "Case study",
                    "comparison": "Comparison",
                },
            },
            "quality_score": {
                "type": "score",
                "criteria": [str(i) for i in range(1, 11)],
                "instructions": "Quality for wiki (1-10)",
            },
            "needs_enrichment": {
                "type": "noul",
                "instructions": "Does this need enrichment for wiki (definitions, links)?",
            },
        },
    )


# === Output writing ===

def write_outputs(
    output_dir: Path,
    base: str,
    info: dict,
    segments: list[dict],
    words: list[dict],
    postprocessed: str,
    quality: dict | None = None,
    annotation: dict | None = None,
    elapsed: float = 0.0,
):
    """Write all output files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. MD with timestamps
    md_path = output_dir / f"{base}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Transcription: {base}\n\n")
        f.write(f"**Duration:** {info.get('duration', 0):.1f}s\n")
        f.write(f"**Language:** {info.get('language', '?')} "
                f"(probability {info.get('language_probability', 0):.2f})\n")
        f.write(f"**Model:** large-v3 (int8)\n")
        f.write(f"**Time:** {elapsed:.1f}s\n\n---\n\n")
        for seg in segments:
            ts = f"[{int(seg['start']//3600):02d}:{int(seg['start']%3600//60):02d}:{int(seg['start']%60):02d}]"
            f.write(f"{ts} {seg['text'].strip()}\n\n")

    # 2. Plain MD (no timestamps)
    plain_path = output_dir / f"{base}_plain.md"
    with open(plain_path, "w", encoding="utf-8") as f:
        f.write(f"# Transcription: {base} (plain)\n\n---\n\n")
        for seg in segments:
            f.write(f"{seg['text'].strip()}\n")

    # 3. JSON with segments
    json_path = output_dir / f"{base}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "language": info.get("language", "?"),
            "language_probability": info.get("language_probability", 0),
            "duration": info.get("duration", 0),
            "model": "large-v3 (int8)",
            "transcription_time": elapsed,
            "segments": segments,
        }, f, ensure_ascii=False, indent=2)

    # 4. Words JSON
    words_path = output_dir / f"{base}_words.json"
    with open(words_path, "w", encoding="utf-8") as f:
        json.dump({
            "duration": info.get("duration", 0),
            "language": info.get("language", "?"),
            "words": words,
        }, f, ensure_ascii=False, indent=2)

    # 5. Postprocess MD
    if postprocessed:
        pp_path = output_dir / f"{base}_postprocess.md"
        with open(pp_path, "w", encoding="utf-8") as f:
            f.write(f"# Transcription: {base} (postprocessed)\n\n")
            f.write(f"**Word count:** {len(words)}\n")
            f.write(f"**LLM model:** MiniMax-M3\n\n---\n\n")
            f.write(postprocessed)

    # 6. Quality report
    if quality:
        q_path = output_dir / f"{base}_quality.json"
        with open(q_path, "w", encoding="utf-8") as f:
            json.dump(quality, f, ensure_ascii=False, indent=2)

    # 7. Annotation
    if annotation:
        a_path = output_dir / f"{base}_annotation.json"
        with open(a_path, "w", encoding="utf-8") as f:
            json.dump(annotation, f, ensure_ascii=False, indent=2)

    return {
        "md": str(md_path),
        "plain_md": str(plain_path),
        "json": str(json_path),
        "words_json": str(words_path),
        "postprocess_md": str(pp_path) if postprocessed else None,
        "quality_json": str(q_path) if quality else None,
        "annotation_json": str(a_path) if annotation else None,
    }


# === Main pipeline ===

def run_pipeline(
    audio_path: Path,
    output_dir: Path,
    language: str = "ru",
    beam_size: int = 5,
    initial_prompt: str | None = None,
    hotwords: str | None = None,
    vad_filter: bool = True,
    compression_ratio_threshold: float = 2.4,
    log_prob_threshold: float = -1.0,
    no_speech_threshold: float = 0.6,
    temperature_fallback: bool = True,
    skip_jev: bool = False,
    only_stage: int | None = None,
) -> dict:
    """Run the full pipeline."""
    output_dir.mkdir(parents=True, exist_ok=True)
    base = audio_path.stem
    result = {
        "input": str(audio_path),
        "output_dir": str(output_dir),
        "stages_run": [],
    }

    # Stage 0: Pre-flight
    if only_stage is None or only_stage == 0:
        print("\n[0/5] Pre-flight (JEV)...")
        if JEV_AVAILABLE and not skip_jev:
            try:
                pf = preflight_check(audio_path)
                action = pf["answers"]["action"]["choice"]
                pf_lang = pf["answers"]["language"]["choice"]
                result["preflight"] = pf["answers"]
                result["stages_run"].append("preflight")

                print(f"  Language: {pf_lang}, Action: {action}")
                if action in ("skip_silence", "skip_wrong_lang"):
                    result["status"] = f"skipped ({action})"
                    return result
                if action == "manual":
                    result["status"] = "manual_review"
                    # Continue anyway
            except Exception as e:
                print(f"  Pre-flight failed: {e}, continuing...")
        else:
            print("  Skipped (JEV unavailable)")

    # Stage 1: Whisper
    if only_stage is None or only_stage == 1:
        print("\n[1/5] Whisper transcription...")
        try:
            whisper_result = transcribe_whisper(
                audio_path, output_dir,
                language=language, beam_size=beam_size,
                initial_prompt=initial_prompt,
                hotwords=hotwords,
                vad_filter=vad_filter,
                compression_ratio_threshold=compression_ratio_threshold,
                logprob_threshold=logprob_threshold,
                no_speech_threshold=no_speech_threshold,
                temperature_fallback=temperature_fallback,
            )
            result["stages_run"].append("whisper")
            result["info"] = whisper_result["info"]
            result["segments"] = whisper_result["segments"]
            result["words"] = whisper_result["words"]
            result["elapsed"] = whisper_result["elapsed"]
            print(f"  Done in {whisper_result['elapsed']:.1f}s, "
                  f"{len(whisper_result['segments'])} segments, "
                  f"{len(whisper_result['words'])} words")
        except Exception as e:
            result["status"] = f"whisper_failed: {e}"
            return result

    # Stage 2: Hallucination filter
    words = result.get("words", [])
    if (only_stage is None or only_stage == 2) and words:
        print("\n[2/5] Hallucination filter (JEV)...")
        if JEV_AVAILABLE and not skip_jev:
            try:
                clean = filter_hallucinations(words)
                removed = len(words) - len(clean)
                result["words"] = clean
                result["stages_run"].append("hallucination_filter")
                print(f"  Removed {removed} hallucinated words")
            except Exception as e:
                print(f"  Filter failed: {e}, continuing...")

    # Stage 3: LLM postprocess
    words = result.get("words", [])
    postprocessed = ""
    if (only_stage is None or only_stage == 3) and words:
        print("\n[3/5] LLM postprocess (hermes -z)...")
        try:
            postprocessed = postprocess_with_llm(words)
            result["postprocessed"] = postprocessed
            result["stages_run"].append("llm_postprocess")
            print(f"  Got {len(postprocessed)} chars")
        except Exception as e:
            print(f"  LLM postprocess failed: {e}, continuing...")

    # Stage 4: Quality gate
    quality = None
    if (only_stage is None or only_stage == 4) and postprocessed:
        print("\n[4/5] Quality gate (JEV)...")
        if JEV_AVAILABLE and not skip_jev:
            try:
                qg = quality_gate(postprocessed, words)
                quality = qg["answers"]
                action = quality["action"]["choice"]
                result["quality"] = quality
                result["stages_run"].append("quality_gate")
                print(f"  Readability: {quality['readability']['score']}/4, Action: {action}")

                if action == "discard":
                    result["status"] = "discarded"
                    write_outputs(
                        output_dir, base,
                        result.get("info", {}),
                        result.get("segments", []),
                        words, postprocessed,
                        quality=quality, elapsed=result.get("elapsed", 0),
                    )
                    return result
            except Exception as e:
                print(f"  Quality gate failed: {e}, continuing...")

    # Stage 5: Wiki annotation
    annotation = None
    if (only_stage is None or only_stage == 5) and postprocessed:
        print("\n[5/5] Wiki annotation (JEV)...")
        if JEV_AVAILABLE and not skip_jev:
            try:
                ann = annotate_for_wiki(postprocessed, {
                    "title": base,
                    "duration": result.get("info", {}).get("duration", 0),
                })
                annotation = ann["answers"]
                result["annotation"] = annotation
                result["stages_run"].append("annotation")
                print(f"  Topic: {annotation['primary_topic']['choice']}, "
                      f"Quality: {annotation['quality_score']['score']}/10")
            except Exception as e:
                print(f"  Annotation failed: {e}, continuing...")

    # Write outputs
    print("\n[output] Writing files...")
    files = write_outputs(
        output_dir, base,
        result.get("info", {}),
        result.get("segments", []),
        words, postprocessed,
        quality=quality, annotation=annotation,
        elapsed=result.get("elapsed", 0),
    )
    result["files"] = files
    result["status"] = "success"
    print(f"  Output: {output_dir}")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Full transcription pipeline with JEV validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic: just Whisper (no JEV)
  python3 full_pipeline.py input.mp3 --output ./out --skip-jev

  # Full pipeline (Whisper + 5 JEV stages)
  python3 full_pipeline.py input.mp3 --output ./out

  # With initial prompt + hotwords
  python3 full_pipeline.py input.mp3 --output ./out \\
      --initial-prompt templates/initial_prompts/bpmn.txt \\
      --hotwords "BPMN шлюз gateway процесс"

  # Strict anti-hallucination
  python3 full_pipeline.py input.mp3 --output ./out \\
      --no-speech-threshold 0.8 \\
      --compression-ratio-threshold 2.0 \\
      --logprob-threshold -0.5
        """,
    )
    parser.add_argument("input", type=Path, help="Audio file")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--language", default="ru")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--initial-prompt", help="Path to prompt file or text")
    parser.add_argument("--hotwords", type=str, default=None,
                        help="Hotwords to boost (space-separated)")
    parser.add_argument("--no-vad", action="store_true", help="Disable Voice Activity Detection")
    parser.add_argument("--no-temperature-fallback", action="store_true",
                        help="Disable temperature fallback")
    parser.add_argument("--compression-ratio-threshold", type=float, default=2.4,
                        help="Skip segments above this compression ratio (default: 2.4)")
    parser.add_argument("--log-prob-threshold", type=float, default=-1.0,
                        help="Skip segments below this avg log_prob (default: -1.0)")
    parser.add_argument("--no-speech-threshold", type=float, default=0.6,
                        help="Skip segments above this no-speech probability (default: 0.6)")
    parser.add_argument("--skip-jev", action="store_true", help="Skip all JEV stages")
    parser.add_argument("--only-stage", type=int, choices=[0, 1, 2, 3, 4, 5],
                        help="Run only one stage (0-5)")
    parser.add_argument("--report", type=Path, help="Path to save JSON report")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: {args.input} not found")
        sys.exit(1)

    prompt = None
    if args.initial_prompt:
        prompt_path = Path(args.initial_prompt)
        if prompt_path.exists():
            prompt = prompt_path.read_text(encoding="utf-8")
        else:
            prompt = args.initial_prompt

    print(f"=== Full Pipeline: {args.input.name} ===")
    print(f"Output: {args.output}")
    print(f"JEV: {'enabled' if JEV_AVAILABLE and not args.skip_jev else 'DISABLED'}")

    result = run_pipeline(
        args.input, args.output,
        language=args.language,
        beam_size=args.beam_size,
        initial_prompt=prompt,
        hotwords=args.hotwords,
        vad_filter=not args.no_vad,
        compression_ratio_threshold=args.compression_ratio_threshold,
        log_prob_threshold=args.log_prob_threshold,
        no_speech_threshold=args.no_speech_threshold,
        temperature_fallback=not args.no_temperature_fallback,
        skip_jev=args.skip_jev,
        only_stage=args.only_stage,
    )

    if args.report:
        args.report.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nReport: {args.report}")

    print(f"\n=== Status: {result.get('status', 'unknown')} ===")
    sys.exit(0 if result.get("status") == "success" else 1)


if __name__ == "__main__":
    main()
