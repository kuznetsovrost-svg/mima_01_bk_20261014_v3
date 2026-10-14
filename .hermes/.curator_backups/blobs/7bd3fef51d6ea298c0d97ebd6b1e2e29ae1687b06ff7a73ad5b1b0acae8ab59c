#!/usr/bin/env python3
"""Batch transcription with progress tracking and resume support.

Usage:
  python3 batch_transcribe.py /path/to/lectures/ --output /path/to/out
  python3 batch_transcribe.py file1.mp3 file2.mp3 --output /path/to/out
  python3 batch_transcribe.py /path/to/lectures/ --output ./out --resume
  python3 batch_transcribe.py /path/to/lectures/ --output ./out --continue-on-error
"""
import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime

# Import the full pipeline
sys.path.insert(0, str(Path(__file__).parent))
from full_pipeline import run_pipeline


SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}


def collect_files(inputs: list[Path]) -> list[Path]:
    """Collect audio files from inputs (files or directories)."""
    files = []
    for inp in inputs:
        if inp.is_file():
            if inp.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(inp)
        elif inp.is_dir():
            for ext in SUPPORTED_EXTENSIONS:
                files.extend(inp.rglob(f"*{ext}"))
    return sorted(set(files))


def is_already_done(file: Path, output_dir: Path) -> bool:
    """Check if file has been successfully processed."""
    base = file.stem
    postprocess = output_dir / f"{base}_postprocess.md"
    quality = output_dir / f"{base}_quality.json"
    annotation = output_dir / f"{base}_annotation.json"
    return postprocess.exists() and quality.exists() and annotation.exists()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--language", default="ru")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--initial-prompt", help="Path to prompt file or text")
    parser.add_argument("--skip-jev", action="store_true")
    parser.add_argument("--resume", action="store_true",
                        help="Skip files that already have output")
    parser.add_argument("--continue-on-error", action="store_true",
                        help="Continue processing on errors")
    parser.add_argument("--report", type=Path, help="Path to save batch report")
    args = parser.parse_args()

    files = collect_files(args.inputs)
    if not files:
        print("ERROR: no audio files found")
        sys.exit(1)

    print(f"=== Batch Transcription ===")
    print(f"Input: {len(files)} files")
    print(f"Output: {args.output}")
    print(f"Resume: {args.resume}")
    print(f"Continue on error: {args.continue_on_error}")
    print()

    # Load prompt
    prompt = None
    if args.initial_prompt:
        p = Path(args.initial_prompt)
        if p.exists():
            prompt = p.read_text(encoding="utf-8")
        else:
            prompt = args.initial_prompt

    # Process
    args.output.mkdir(parents=True, exist_ok=True)
    results = {
        "started": datetime.now().isoformat(),
        "total": len(files),
        "succeeded": [],
        "failed": [],
        "skipped": [],
    }

    for i, file in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] {file.name}")

        if args.resume and is_already_done(file, args.output):
            print(f"  ⏭ Skipped (already done)")
            results["skipped"].append(str(file))
            continue

        t0 = time.time()
        try:
            result = run_pipeline(
                file, args.output,
                language=args.language,
                beam_size=args.beam_size,
                initial_prompt=prompt,
                skip_jev=args.skip_jev,
            )
            elapsed = time.time() - t0
            status = result.get("status", "unknown")

            if status == "success":
                print(f"  ✓ Done in {elapsed:.1f}s")
                results["succeeded"].append({
                    "file": str(file),
                    "elapsed_sec": elapsed,
                })
            else:
                print(f"  ⚠ Status: {status}")
                results["failed"].append({
                    "file": str(file),
                    "status": status,
                })
                if not args.continue_on_error:
                    break
        except Exception as e:
            elapsed = time.time() - t0
            print(f"  ✗ Failed: {e}")
            results["failed"].append({
                "file": str(file),
                "error": str(e),
                "elapsed_sec": elapsed,
            })
            if not args.continue_on_error:
                break

    # Summary
    results["finished"] = datetime.now().isoformat()
    print()
    print("=" * 50)
    print(f"Succeeded: {len(results['succeeded'])}/{len(files)}")
    print(f"Failed: {len(results['failed'])}")
    print(f"Skipped: {len(results['skipped'])}")

    if args.report:
        args.report.write_text(
            json.dumps(results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Report: {args.report}")

    sys.exit(0 if not results["failed"] else 1)


if __name__ == "__main__":
    main()
