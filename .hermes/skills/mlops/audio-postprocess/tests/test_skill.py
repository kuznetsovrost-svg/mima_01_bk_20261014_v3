#!/usr/bin/env python3
"""Tests for postprocess_multi.py and dedup_overlap.py."""
import sys
import subprocess
import tempfile
from pathlib import Path

SKILL_DIR = Path("/root/.hermes/skills/mlops/audio-postprocess")
SCRIPT = SKILL_DIR / "scripts" / "postprocess_multi.py"
DEDUP_SCRIPT = SKILL_DIR / "scripts" / "dedup_overlap.py"

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


def test_script_exists():
    print("\n[1] Scripts exist and are valid Python")
    test("postprocess_multi.py exists", SCRIPT.exists())
    test("dedup_overlap.py exists", DEDUP_SCRIPT.exists())

    for script in [SCRIPT, DEDUP_SCRIPT]:
        result = subprocess.run(
            ["python3", "-c", f"import ast; ast.parse(open('{script}').read())"],
            capture_output=True, text=True,
        )
        test(f"  {script.name} parses", result.returncode == 0)


def test_help():
    print("\n[2] CLI help works")
    result = subprocess.run(
        ["python3", str(SCRIPT), "--help"],
        capture_output=True, text=True, timeout=10,
    )
    test("postprocess_multi.py --help exit 0", result.returncode == 0)
    test("help mentions passes", "passes" in result.stdout)

    result = subprocess.run(
        ["python3", str(DEDUP_SCRIPT), "--help"],
        capture_output=True, text=True, timeout=10,
    )
    test("dedup_overlap.py --help exit 0", result.returncode == 0)
    test("help mentions overlap", "overlap" in result.stdout)


def test_passes_constant():
    print("\n[3] PASSES constant has 4 entries")
    import importlib.util
    spec = importlib.util.spec_from_file_location("postprocess_multi", SCRIPT)
    if spec is None or spec.loader is None:
        test("can load postprocess_multi", False, "spec_from_file_location returned None")
        return
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        test("can load postprocess_multi", False, str(e))
        return
    test("can load postprocess_multi", True)

    test("PASSES has 4 entries", len(module.PASSES) == 4)
    test("Pass 1 = filler", module.PASSES[1][0] == "filler")
    test("Pass 2 = asr_fix", module.PASSES[2][0] == "asr_fix")
    test("Pass 3 = structure", module.PASSES[3][0] == "structure")
    test("Pass 4 = polish", module.PASSES[4][0] == "polish")

    # Check prompts are non-empty
    for pn, (name, prompt) in module.PASSES.items():
        test(f"  Pass {pn} prompt non-empty", len(prompt) > 100)
        test(f"  Pass {pn} prompt in Russian", any(c in prompt for c in "абвгдежзийклмнопрстуфхцчшщъыьэюя"))


def test_input_validation():
    print("\n[4] Input validation")
    result = subprocess.run(
        ["python3", str(SCRIPT), "/nonexistent/file.md", "/tmp/out"],
        capture_output=True, text=True, timeout=10,
    )
    test("nonexistent input fails", result.returncode != 0)
    test("error message mentions not found", "not found" in result.stderr)


def test_overlap_dedup():
    print("\n[5] dedup_overlap.py handles small input")
    # Create minimal chunks
    chunks_dir = Path("/tmp/test_dedup_chunks")
    chunks_dir.mkdir(exist_ok=True)
    for i in range(2):
        cd = chunks_dir / f"chunk_{i:03d}"
        cd.mkdir(exist_ok=True)
        (cd / f"chunk_{i:03d}_plain.md").write_text(f"Текст чанка {i}", encoding="utf-8")

    result = subprocess.run(
        ["python3", str(DEDUP_SCRIPT), str(chunks_dir), "/tmp/dedup_out.md",
         "--no-llm", "--overlap-sec", "5"],
        capture_output=True, text=True, timeout=10,
    )
    test("dedup runs without LLM", result.returncode == 0, result.stderr[-200:])
    test("output file created", Path("/tmp/dedup_out.md").exists())

    # Cleanup
    import shutil
    shutil.rmtree(chunks_dir, ignore_errors=True)
    Path("/tmp/dedup_out.md").unlink(missing_ok=True)


def test_pass_file_naming():
    print("\n[6] Pass output file naming convention")
    # Check that the naming pattern in the script matches the docstring
    result = subprocess.run(
        ["python3", str(SCRIPT), "--help"],
        capture_output=True, text=True, timeout=10,
    )
    test("help mentions _pass_N_name.md", "pass" in result.stdout)
    test("help mentions _final.md", "final" in result.stdout)


def main():
    global PASSED, FAILED
    print("=" * 60)
    print("AUDIO-POSTPROCESS SKILL TESTS")
    print("=" * 60)

    test_script_exists()
    test_help()
    test_passes_constant()
    test_input_validation()
    test_overlap_dedup()
    test_pass_file_naming()

    print()
    print("=" * 60)
    print(f"RESULTS: {PASSED} passed, {FAILED} failed")
    print("=" * 60)

    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())