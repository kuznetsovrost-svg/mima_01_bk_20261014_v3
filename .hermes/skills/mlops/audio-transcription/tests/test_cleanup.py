#!/usr/bin/env python3
"""Tests for cleanup.py - проверка очистки постпроцессинговых транскриптов."""
import sys
import re
import subprocess
import tempfile
from pathlib import Path

SKILL_DIR = Path("/root/.hermes/skills/mlops/audio-transcription")
SCRIPT = SKILL_DIR / "scripts" / "cleanup.py"

PASSED = 0
FAILED = 0


def test(name, condition, detail=""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  PASS: {name}")
    else:
        FAILED += 1
        print(f"  FAIL: {name}")
        if detail:
            print(f"        {detail}")


def run_cleanup(content: str) -> str:
    """Запускает cleanup.py на строке, возвращает очищенный результат."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(content)
        src = f.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        out = f.name
    try:
        result = subprocess.run(
            ["python3", str(SCRIPT), src, out],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return f"ERROR: {result.stderr}"
        return Path(out).read_text(encoding="utf-8")
    finally:
        Path(src).unlink(missing_ok=True)
        Path(out).unlink(missing_ok=True)


def test_removes_pause_markers():
    print("\n[1] PAUSE markers are removed")
    sample = "text [PAUSE 0.46] more text [PAUSE 1.22] end"
    result = run_cleanup(sample)
    test("PAUSE markers absent", "[PAUSE" not in result)
    test("Original text remains", "text" in result and "more text" in result and "end" in result)


def test_removes_chunk_comments():
    print("\n[2] Chunk comments are removed")
    sample = "<!-- chunk_000_postprocess.md -->\n\nreal content\n"
    result = run_cleanup(sample)
    test("chunk comment removed", "<!-- chunk_" not in result)
    test("real content preserved", "real content" in result)


def test_removes_metadata():
    print("\n[3] LLM metadata is removed")
    sample = """# Transcription: chunk_000 (LLM postprocessed)

**Word count:** 187
**LLM model:** MiniMax-M3
**LLM response time:** 11.4s

---

actual transcript text
"""
    result = run_cleanup(sample)
    test("Transcription header removed", "# Transcription:" not in result)
    test("Word count removed", "**Word count:**" not in result)
    test("LLM model removed", "**LLM model:**" not in result)
    test("LLM response time removed", "**LLM response time:**" not in result)
    test("--- separator removed", "---" not in result)
    test("transcript text preserved", "actual transcript text" in result)


def test_preserves_normal_text():
    print("\n[4] Normal text is preserved")
    sample = """Денис, у тебя больше вопросов?

С Лёшей? Совсем вместе мы не договорили.

Я рассказал вам половину правды.

— Так, хорошо.
"""
    result = run_cleanup(sample)
    test("Денис preserved", "Денис" in result)
    test("Лёшей preserved", "Лёшей" in result)
    test("question mark preserved", "?" in result)
    test("em-dash preserved", "—" in result)


def test_real_file():
    print("\n[5] Real file processing (full_postprocessed.md)")
    src = Path("/tmp/hermes_audio_transcription/final/full_postprocessed.md")
    if not src.exists():
        print("  SKIP: file not found (run pipeline first)")
        return
    out_dir = Path("/tmp/test_cleanup_output")
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "cleaned.md"

    result = subprocess.run(
        ["python3", str(SCRIPT), str(src), str(out_file)],
        capture_output=True, text=True, timeout=30,
    )
    test("cleanup exit 0", result.returncode == 0, result.stderr[:200])
    test("output file created", out_file.exists())

    if out_file.exists():
        text = out_file.read_text(encoding="utf-8")
        test("no PAUSE markers", "[PAUSE" not in text)
        test("no chunk comments", "<!-- chunk_" not in text)
        test("no section headers", "# Transcription: chunk_" not in text)
        test("no Word count", "**Word count:**" not in text)
        test("no LLM model", "**LLM model:**" not in text)
        test("no LLM time", "**LLM response time:**" not in text)
        test("text not empty", len(text) > 1000)
        test("Russian content preserved", any(c in text for c in "абвгдежзийклмнопрстуфхцчшщъыьэюя"))
        test("size reduced", len(text) < src.stat().st_size,
             f"original={src.stat().st_size} cleaned={len(text)}")


def test_in_place():
    print("\n[6] --in-place option")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("text [PAUSE 0.5] more")
        tmp = Path(f.name)
    try:
        result = subprocess.run(
            ["python3", str(SCRIPT), str(tmp), "--in-place"],
            capture_output=True, text=True,
        )
        test("exit 0", result.returncode == 0)
        content = tmp.read_text(encoding="utf-8")
        test("PAUSE removed in-place", "[PAUSE" not in content)
        test("text preserved in-place", "text" in content and "more" in content)
    finally:
        tmp.unlink(missing_ok=True)


def test_stats():
    print("\n[7] Statistics output")
    sample = "<!-- chunk_000_postprocess.md -->\n# Transcription: chunk_000 (LLM postprocessed)\n\n**Word count:** 100\n\n---\n\n[PAUSE 0.5] real content"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(sample)
        src = f.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        out = f.name
    try:
        result = subprocess.run(
            ["python3", str(SCRIPT), src, out],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout + result.stderr
        test("reports pause_markers", "pause_markers: 1" in output)
        test("reports chunk_comments", "chunk_comments: 1" in output)
        test("reports section_headers", "section_headers: 1" in output)
        test("reports metadata_lines", "metadata_lines: 1" in output)
        test("reports separators", "separators: 1" in output)
    finally:
        Path(src).unlink(missing_ok=True)
        Path(out).unlink(missing_ok=True)


def test_removes_raw_format():
    print("\n[8] Raw transcribe.py format is removed")
    sample = """# chunk_000

# Transcription: chunk_000.wav (plain text, no timestamps)

**Duration:** 00:02:00
**Language:** ru (probability 1.00)
**Model:** medium (int8)
**Segments:** 20
**Transcription time:** 83.0s

---

Здравствуйте. Сегодня у нас первая лекция.
"""
    result = run_cleanup(sample)
    test("raw chunk header removed", "# chunk_000" not in result)
    test("raw section header removed", "# Transcription: chunk_000.wav" not in result)
    test("raw Duration removed", "**Duration:**" not in result)
    test("raw Language removed", "**Language:**" not in result)
    test("raw Model removed", "**Model:**" not in result)
    test("raw Segments removed", "**Segments:**" not in result)
    test("raw Transcription time removed", "**Transcription time:**" not in result)
    test("raw --- separator removed", "---" not in result)
    test("actual text preserved", "Здравствуйте. Сегодня у нас первая лекция." in result)


def test_raw_concatenated_chunks():
    print("\n[9] Multiple concatenated chunks cleaned")
    sample = """# chunk_000

# Transcription: chunk_000.wav (...)

**Duration:** 00:02:00

First chunk text.

# chunk_001

# Transcription: chunk_001.wav (...)

**Duration:** 00:02:00

Second chunk text.
"""
    result = run_cleanup(sample)
    test("chunk_000 header removed", "# chunk_000" not in result)
    test("chunk_001 header removed", "# chunk_001" not in result)
    test("section headers removed", "# Transcription: chunk_" not in result)
    test("Duration metadata removed", "**Duration:**" not in result)
    test("First chunk text preserved", "First chunk text." in result)
    test("Second chunk text preserved", "Second chunk text." in result)


def main():
    global PASSED, FAILED

    print("=" * 60)
    print("CLEANUP.PY TESTS")
    print("=" * 60)

    test_removes_pause_markers()
    test_removes_chunk_comments()
    test_removes_metadata()
    test_preserves_normal_text()
    test_real_file()
    test_in_place()
    test_stats()
    test_removes_raw_format()
    test_raw_concatenated_chunks()

    print()
    print("=" * 60)
    print(f"RESULTS: {PASSED} passed, {FAILED} failed")
    print("=" * 60)

    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())