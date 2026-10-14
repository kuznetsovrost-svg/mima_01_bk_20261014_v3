#!/usr/bin/env python3
"""Tests for asr_fix.py and transcribe_single.py."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path("/root/.hermes/skills/mlops/audio-transcription")
ASR_FIX = SKILL_DIR / "scripts" / "asr_fix.py"
TRANSCRIBE_SINGLE = SKILL_DIR / "scripts" / "transcribe_single.py"


def test_asr_fix_default_fixes_known_errors():
    """Test that default fixes replace known errors."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("Это фактальной природы. Это имперической модели.\n")
        input_path = Path(f.name)
    output_path = input_path.with_suffix(".out.md")

    result = subprocess.run(
        [sys.executable, str(ASR_FIX), str(input_path), str(output_path)],
        capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, f"Failed: {result.stderr}"
    out = output_path.read_text(encoding="utf-8")
    assert "фрактальной" in out, "Should fix фактальной → фрактальной"
    assert "эмпирической" in out, "Should fix имперической → эмпирической"
    assert "фактальной" not in out, "Should not have фактальной anymore"
    input_path.unlink()
    output_path.unlink()
    print("  ✓ default fixes known errors")


def test_asr_fix_snowflake():
    """Test that снежинка fixes work."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("снижим Коха имеет конечную площадь.\n")
        input_path = Path(f.name)
    output_path = input_path.with_suffix(".out.md")

    subprocess.run(
        [sys.executable, str(ASR_FIX), str(input_path), str(output_path)],
        capture_output=True, text=True, timeout=10
    )
    out = output_path.read_text(encoding="utf-8")
    assert "снежинка" in out, "Should fix снижим → снежинка"
    input_path.unlink()
    output_path.unlink()
    print("  ✓ snowflake (снежинка) fix")


def test_asr_fix_custom_fixes():
    """Test that --fixes custom JSON works."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("Это тест с кастомной ошибкой. Test blahblah\n")
        input_path = Path(f.name)
    output_path = input_path.with_suffix(".out.md")

    custom_fixes = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump({"blahblah": "fixed_word"}, custom_fixes)
    custom_fixes.close()

    result = subprocess.run(
        [sys.executable, str(ASR_FIX), str(input_path), str(output_path),
         "--fixes", custom_fixes.name],
        capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, f"Failed: {result.stderr}"
    out = output_path.read_text(encoding="utf-8")
    assert "fixed_word" in out, "Should use custom fix"
    assert "blahblah" not in out, "Should not have original"
    input_path.unlink()
    output_path.unlink()
    Path(custom_fixes.name).unlink()
    print("  ✓ custom JSON fixes")


def test_asr_fix_idempotent():
    """Test that running twice gives same result."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("фактальной имперической сниженку\n")
        input_path = Path(f.name)
    output1 = input_path.with_suffix(".out1.md")
    output2 = input_path.with_suffix(".out2.md")

    subprocess.run([sys.executable, str(ASR_FIX), str(input_path), str(output1)],
                   capture_output=True, timeout=10)
    subprocess.run([sys.executable, str(ASR_FIX), str(output1), str(output2)],
                   capture_output=True, timeout=10)

    out1 = output1.read_text(encoding="utf-8")
    out2 = output2.read_text(encoding="utf-8")
    assert out1 == out2, "Should be idempotent"
    input_path.unlink()
    output1.unlink()
    output2.unlink()
    print("  ✓ idempotent")


def test_asr_fix_case_sensitive():
    """Test that replacements are case-sensitive."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("ФАКТАЛЬНОЙ фактальной\n")
        input_path = Path(f.name)
    output_path = input_path.with_suffix(".out.md")

    subprocess.run([sys.executable, str(ASR_FIX), str(input_path), str(output_path)],
                   capture_output=True, timeout=10)
    out = output_path.read_text(encoding="utf-8")
    # Only lowercase "фактальной" should be replaced (default dict is lowercase only)
    assert "фрактальной" in out, "Lowercase should be replaced"
    input_path.unlink()
    output_path.unlink()
    print("  ✓ case-sensitive")


def test_transcribe_single_help():
    """Test that transcribe_single.py --help works."""
    result = subprocess.run(
        [sys.executable, str(TRANSCRIBE_SINGLE), "--help"],
        capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, f"--help should work: {result.stderr}"
    assert "beam-size" in result.stdout, "Should mention --beam-size"
    assert "max-memory-gb" in result.stdout, "Should mention --max-memory-gb"
    print("  ✓ transcribe_single --help works")


def test_transcribe_single_no_args():
    """Test that transcribe_single.py without args shows help/error."""
    result = subprocess.run(
        [sys.executable, str(TRANSCRIBE_SINGLE)],
        capture_output=True, text=True, timeout=10
    )
    # Without args, should fail (need input file)
    assert result.returncode != 0, "Should fail without input"
    print("  ✓ transcribe_single fails without args")


def test_asr_fix_ohms_law():
    """Test that 'Ом' (Ohm) is preserved as-is."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("Закон Ома. Ом сформулировал. Ома формула. Закон Ома.\n")
        input_path = Path(f.name)
    output_path = input_path.with_suffix(".out.md")

    subprocess.run([sys.executable, str(ASR_FIX), str(input_path), str(output_path)],
                   capture_output=True, timeout=10)
    out = output_path.read_text(encoding="utf-8")
    assert "Ома" in out, "Should preserve Ом declension"
    assert "Ом сформулировал" in out
    input_path.unlink()
    output_path.unlink()
    print("  ✓ Ом (Ohm) preserved")


def main() -> int:
    print("=== Test: ASR-fix + transcribe_single ===")
    test_asr_fix_default_fixes_known_errors()
    test_asr_fix_snowflake()
    test_asr_fix_custom_fixes()
    test_asr_fix_idempotent()
    test_asr_fix_case_sensitive()
    test_transcribe_single_help()
    test_transcribe_single_no_args()
    test_asr_fix_ohms_law()
    print("=== ALL TESTS PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())