#!/usr/bin/env python3
"""Postprocess a chunk + JEV quality gate."""
import sys
import json
import subprocess
from pathlib import Path

SKILL_DIR = Path("/root/.hermes/skills/note-taking/transcription-postprocess")
sys.path.insert(0, str(SKILL_DIR.parent.parent / "jev-decisions" / "scripts"))

CHUNK_DIR = Path(sys.argv[1])  # e.g. /tmp/hermes_audio_transcription/chunks_out/chunk_000
POST_DIR = Path(sys.argv[2])    # /tmp/hermes_audio_transcription/postprocessed
EVAL_DIR = Path(sys.argv[3])    # /tmp/hermes_audio_transcription/quality_eval

POST_DIR.mkdir(parents=True, exist_ok=True)
EVAL_DIR.mkdir(parents=True, exist_ok=True)

base = CHUNK_DIR.name
words_file = CHUNK_DIR / f"{base}_words.json"
post_file = POST_DIR / f"{base}_postprocess.md"
eval_file = EVAL_DIR / f"{base}_quality.json"

if not words_file.exists():
    print(f"[{base}] SKIP: no words.json")
    sys.exit(0)

if post_file.exists() and post_file.stat().st_size > 100:
    print(f"[{base}] SKIP: already postprocessed ({post_file.stat().st_size} bytes)")
    sys.exit(0)

# Step 1: Run transcription-postprocess
print(f"[{base}] Postprocessing...")
import time
t0 = time.time()

result = subprocess.run(
    ["python3", str(SKILL_DIR / "scripts" / "postprocess.py"), str(words_file),
     "--output", str(POST_DIR)],
    capture_output=True, text=True, timeout=60,
)
post_time = time.time() - t0

if result.returncode != 0 or not post_file.exists():
    print(f"[{base}] POSTPROCESS FAIL: {result.stderr[-500:]}")
    sys.exit(1)

post_size = post_file.stat().st_size
print(f"[{base}] Postprocess OK: {post_size} bytes in {post_time:.1f}s")

# Step 2: JEV quality gate
print(f"[{base}] Running JEV quality gate...")
try:
    from jev_client import jev_score

    post_text = post_file.read_text(encoding="utf-8")
    body_start = post_text.find("---") + 4
    preview = post_text[body_start:body_start + 600]

    state = {
        "transcript_preview": preview,
        "criteria": {
            "punctuation": "Periods, commas, question marks present",
            "paragraphs": "Sentences split into logical paragraphs (blank lines)",
            "names": "Proper nouns capitalized: Денис, Ростислав, Лёша"
        }
    }
    scale = ["1_fails_all", "2_poor", "3_partial", "4_good", "5_excellent"]

    score_value, confidence = jev_score(
        state=state,
        scale=scale,
        instructions="Score the postprocessed Russian lecture transcript preview based on three criteria above."
    )

    eval_data = {
        "chunk": base,
        "score": score_value,
        "confidence": round(confidence, 3),
        "postprocess_size_bytes": post_size,
        "postprocess_time_sec": round(post_time, 2),
        "preview_chars": len(preview),
    }
    eval_file.write_text(json.dumps(eval_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{base}] JEV OK: score={score_value} conf={confidence:.3f}")
except Exception as e:
    eval_data = {
        "chunk": base,
        "score": None,
        "confidence": None,
        "error": str(e)[:200],
    }
    eval_file.write_text(json.dumps(eval_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{base}] JEV FAIL: {e}")

print(f"[{base}] DONE")