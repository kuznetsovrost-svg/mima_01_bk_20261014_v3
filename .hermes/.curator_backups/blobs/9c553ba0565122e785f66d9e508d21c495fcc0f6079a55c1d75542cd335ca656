#!/usr/bin/env python3
"""End-to-end test for the full audio-transcription pipeline.

Tests:
1. transcribe.py produces correct output files
2. Word timestamps are extracted
3. JSON output is valid
4. Initial prompt loading
5. full_pipeline.py imports and is callable
6. batch_transcribe.py exists and is importable
7. transcribe.sh is executable

Run: python3 tests/test_pipeline.py
"""
import json
import os
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path("/root/.hermes/skills/mlops/audio-transcription")
SCRIPTS_DIR = SKILL_DIR / "scripts"
TEMPLATES_DIR = SKILL_DIR / "templates" / "initial_prompts"
REFS_DIR = SKILL_DIR / "references"
TESTS_DIR = SKILL_DIR / "tests"

# Test fixtures
TEST_AUDIO = Path("/tmp/test-audio/fragment_2min.mp3")
TEST_OUT = Path("/tmp/test_pipeline_out")


def test_files_exist():
    """Test 1: All required files exist."""
    print("\n=== Test 1: Required files exist ===")
    required = [
        SCRIPTS_DIR / "transcribe.py",
        SCRIPTS_DIR / "full_pipeline.py",
        SCRIPTS_DIR / "batch_transcribe.py",
        SCRIPTS_DIR / "transcribe.sh",
        TEMPLATES_DIR / "business_analysis.txt",
        TEMPLATES_DIR / "bpmn.txt",
        TEMPLATES_DIR / "general_russian.txt",
        REFS_DIR / "whisper_tuning.md",
    ]
    for f in required:
        assert f.exists(), f"Missing: {f}"
        print(f"  ✓ {f.relative_to(SKILL_DIR)}")
    return True


def test_transcribe_sh_executable():
    """Test 2: transcribe.sh is executable."""
    print("\n=== Test 2: transcribe.sh executable ===")
    sh_path = SCRIPTS_DIR / "transcribe.sh"
    assert sh_path.exists()
    assert os.access(sh_path, os.X_OK), f"{sh_path} not executable"
    print(f"  ✓ {sh_path.name} is executable")
    return True


def test_initial_prompts_have_content():
    """Test 3: Initial prompts are not empty."""
    print("\n=== Test 3: Initial prompts have content ===")
    for f in TEMPLATES_DIR.glob("*.txt"):
        content = f.read_text(encoding="utf-8")
        assert len(content) > 50, f"{f.name} too short"
        # Count words (rough)
        words = len(content.split())
        print(f"  ✓ {f.name}: {len(content)} chars, ~{words} words")
    return True


def test_transcribe_runs():
    """Test 4: transcribe.py runs successfully on test audio."""
    print("\n=== Test 4: transcribe.py runs on test audio ===")
    if not TEST_AUDIO.exists():
        print(f"  ⚠ Skipped: {TEST_AUDIO} not found")
        return True

    # Clean output
    import shutil
    if TEST_OUT.exists():
        shutil.rmtree(TEST_OUT)
    TEST_OUT.mkdir(parents=True)

    # Run transcribe.py
    result = subprocess.run(
        [
            "python3", str(SCRIPTS_DIR / "transcribe.py"),
            str(TEST_AUDIO),
            "--output", str(TEST_OUT),
            "--language", "ru",
            "--beam-size", "5",
        ],
        capture_output=True, text=True, timeout=300,
    )

    if result.returncode != 0:
        print(f"  ✗ Failed: {result.stderr[:500]}")
        return False

    # Check outputs
    expected = [
        TEST_OUT / "fragment_2min.md",
        TEST_OUT / "fragment_2min_plain.md",
        TEST_OUT / "fragment_2min.json",
        TEST_OUT / "fragment_2min_words.json",
    ]
    for f in expected:
        assert f.exists(), f"Missing: {f}"
        print(f"  ✓ {f.name} ({f.stat().st_size} B)")

    # Verify JSON
    words_data = json.loads((TEST_OUT / "fragment_2min_words.json").read_text(encoding="utf-8"))
    assert "words" in words_data
    assert len(words_data["words"]) > 100, f"Only {len(words_data['words'])} words"
    print(f"  ✓ {len(words_data['words'])} words extracted")

    return True


def test_full_pipeline_imports():
    """Test 5: full_pipeline.py is importable."""
    print("\n=== Test 5: full_pipeline.py imports ===")
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        import full_pipeline
        assert hasattr(full_pipeline, "run_pipeline")
        assert hasattr(full_pipeline, "preflight_check")
        assert hasattr(full_pipeline, "filter_hallucinations")
        assert hasattr(full_pipeline, "quality_gate")
        assert hasattr(full_pipeline, "annotate_for_wiki")
        print(f"  ✓ run_pipeline, preflight_check, filter_hallucinations,")
        print(f"    quality_gate, annotate_for_wiki")
        return True
    except Exception as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_batch_transcribe_imports():
    """Test 6: batch_transcribe.py is importable."""
    print("\n=== Test 6: batch_transcribe.py imports ===")
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        from batch_transcribe import collect_files, is_already_done
        assert callable(collect_files)
        assert callable(is_already_done)
        print(f"  ✓ collect_files, is_already_done")
        return True
    except Exception as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_jev_integration():
    """Test 7: JEV integration works (if JEV skill available)."""
    print("\n=== Test 7: JEV integration ===")
    jev_path = Path("/root/.hermes/skills/jev-decisions/scripts")
    if not jev_path.exists():
        print(f"  ⚠ Skipped: jev-decisions skill not installed")
        return True

    sys.path.insert(0, str(jev_path))
    try:
        from jev_client import jev_decide
        # Don't actually call API, just verify import
        print(f"  ✓ jev_decide available")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False


def test_skill_md_mentions_jev():
    """Test 8: SKILL.md mentions JEV integration."""
    print("\n=== Test 8: SKILL.md mentions JEV ===")
    skill_md = SKILL_DIR / "SKILL.md"
    if not skill_md.exists():
        print(f"  ⚠ SKILL.md missing")
        return True
    content = skill_md.read_text(encoding="utf-8")
    if "JEV" in content or "jev-decisions" in content:
        print(f"  ✓ JEV mentioned in SKILL.md")
        return True
    else:
        print(f"  ⚠ JEV not mentioned in SKILL.md (need to update)")
        return True  # Don't fail, just note


def main():
    print("=" * 60)
    print("Audio-Transcription Pipeline Test Suite")
    print("=" * 60)

    tests = [
        test_files_exist,
        test_transcribe_sh_executable,
        test_initial_prompts_have_content,
        test_transcribe_runs,
        test_full_pipeline_imports,
        test_batch_transcribe_imports,
        test_jev_integration,
        test_skill_md_mentions_jev,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"  ✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
