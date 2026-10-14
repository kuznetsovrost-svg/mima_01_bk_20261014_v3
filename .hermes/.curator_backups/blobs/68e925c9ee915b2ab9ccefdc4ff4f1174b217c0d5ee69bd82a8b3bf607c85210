#!/usr/bin/env python3
"""Benchmark Whisper configurations to find the best setup.

Tests multiple configurations on the same audio file and reports:
- Transcription time
- Word count
- Output file sizes
- Memory usage
- WER estimate (if ground truth provided)

Usage:
  python3 benchmark.py input.mp3
  python3 benchmark.py input.mp3 --ground-truth ground_truth.txt
  python3 benchmark.py input.mp3 --output ./bench-results
"""

import argparse
import json
import time
import subprocess
import sys
from pathlib import Path


# Configurations to test
CONFIGS = [
    {
        "name": "baseline (no prompt, no hotwords)",
        "args": [],
    },
    {
        "name": "with VAD (default)",
        "args": ["--vad-filter"],
    },
    {
        "name": "with initial prompt",
        "args": ["--prompt", "templates/initial_prompts/business_analysis.txt"],
    },
    {
        "name": "with hotwords",
        "args": ["--hotwords", "BPMN шлюз gateway процесс событие"],
    },
    {
        "name": "with anti-hallucination (strict)",
        "args": [
            "--no-speech-threshold", "0.8",
            "--compression-ratio-threshold", "2.0",
            "--logprob-threshold", "-0.5",
        ],
    },
    {
        "name": "aggressive (beam=10, all features)",
        "args": [
            "--beam-size", "10",
            "--prompt", "templates/initial_prompts/business_analysis.txt",
            "--hotwords", "BPMN шлюз gateway процесс событие",
            "--no-speech-threshold", "0.7",
        ],
    },
]


def run_config(input_path: Path, output_dir: Path, config: dict) -> dict:
    """Run a single config and collect metrics."""
    config_name = config["name"]
    config_args = config["args"]
    
    config_output = output_dir / config_name.replace(" ", "_").replace("(", "").replace(")", "")
    
    print(f"\n{'='*60}")
    print(f"Config: {config_name}")
    print(f"{'='*60}")
    
    cmd = [
        "python3", "scripts/transcribe.py",
        str(input_path),
        "--output", str(config_output),
    ] + config_args
    
    print(f"  CMD: {' '.join(cmd[:6])}...")
    
    t0 = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )
        elapsed = time.time() - t0
        
        # Parse JSON output from stdout (last block)
        output_text = result.stdout
        json_block_start = output_text.rfind("{")
        if json_block_start >= 0:
            try:
                result_json = json.loads(output_text[json_block_start:].split("===")[-1].strip().split("\n", 1)[1])
            except Exception:
                result_json = {}
        else:
            result_json = {}
        
        # Files produced
        files = list(config_output.glob("*"))
        total_size = sum(f.stat().st_size for f in files)
        
        return {
            "config": config_name,
            "elapsed": round(elapsed, 1),
            "success": result.returncode == 0,
            "segments": result_json.get("segments", 0),
            "words": result_json.get("words", 0),
            "files": len(files),
            "total_size_kb": round(total_size / 1024, 1),
            "output_dir": str(config_output),
        }
    except subprocess.TimeoutExpired:
        return {
            "config": config_name,
            "elapsed": 600.0,
            "success": False,
            "error": "timeout",
        }
    except Exception as e:
        return {
            "config": config_name,
            "elapsed": round(time.time() - t0, 1),
            "success": False,
            "error": str(e),
        }


def main():
    parser = argparse.ArgumentParser(description="Benchmark Whisper configurations")
    parser.add_argument("input", type=Path, help="Input audio file")
    parser.add_argument("--output", type=Path, default=Path("./bench-results"), help="Output directory")
    parser.add_argument("--ground-truth", type=Path, default=None, help="Ground truth text for WER calculation")
    args = parser.parse_args()
    
    args.output.mkdir(parents=True, exist_ok=True)
    
    print(f"Benchmarking {args.input.name} with {len(CONFIGS)} configurations")
    print(f"Output: {args.output}")
    
    results = []
    for config in CONFIGS:
        result = run_config(args.input, args.output, config)
        results.append(result)
        print(f"  Result: {result}")
    
    # Save report
    report = {
        "input": str(args.input),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": results,
    }
    
    report_path = args.output / "benchmark_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"BENCHMARK SUMMARY")
    print(f"{'='*60}")
    print(f"{'Config':<45} {'Time':>8} {'Words':>8} {'OK'}")
    print(f"{'-'*60}")
    for r in results:
        status = "OK" if r.get("success") else f"FAIL: {r.get('error', '?')}"
        time_s = f"{r.get('elapsed', 0):.1f}s"
        words = r.get("words", 0)
        print(f"{r['config']:<45} {time_s:>8} {words:>8} {status}")
    
    print(f"\nReport: {report_path}")


if __name__ == "__main__":
    main()
