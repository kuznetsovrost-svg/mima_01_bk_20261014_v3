#!/usr/bin/env python3
"""asr_fix.py - Dictionary-based ASR error fixer (no LLM, no editing risk).

Replaces known Whisper recognition errors in a transcript file using a
word/phrase → correct-form dictionary. Pure string replacement via str.replace().

For 1-10 known wrong forms, this is faster, cheaper, and safer than an LLM pass.
Reserve the LLM for errors that appear during review (not in the transcript yet).

Usage:
    python3 asr_fix.py INPUT.md OUTPUT.md
    python3 asr_fix.py INPUT.md OUTPUT.md --fixes fixes.json

If --fixes is omitted, uses DEFAULT_FIXES (the empirically observed BA-lecture
error set).
"""
import argparse
import json
import sys
from pathlib import Path


# Default fixes: confirmed observed errors in Russian BA lectures
DEFAULT_FIXES = {
    # Phonetically similar
    "фактальной": "фрактальной",
    "фактальную": "фрактальную",
    "фактального": "фрактального",
    "фактальные": "фрактальные",
    "имперической": "эмпирической",
    "имперические": "эмпирические",
    "имперических": "эмпирических",
    "империческая": "эмпирическая",
    "имперический": "эмпирический",
    # Tatar-style substitutions
    "свепроводящих": "сверхпроводящих",
    "свепроводящую": "сверхпроводящую",
    "сверпроводящую": "сверхпроводящую",
    "сверпроводящих": "сверхпроводящих",
    # Other commonly observed
    "сниженку": "снежинку",
    "сниженка": "снежинка",
    "сниженки": "снежинки",
    "снижим": "снежинка",
}


def load_fixes(fixes_path: str | None) -> dict[str, str]:
    """Load fix dictionary from JSON or use defaults."""
    if fixes_path is None:
        return DEFAULT_FIXES

    path = Path(fixes_path)
    if not path.exists():
        print(f"WARNING: {fixes_path} not found, using defaults", file=sys.stderr)
        return DEFAULT_FIXES

    return json.loads(path.read_text(encoding="utf-8"))


def apply_fixes(text: str, fixes: dict[str, str]) -> tuple[str, dict[str, int]]:
    """Apply all fixes, return (new_text, {wrong: count})."""
    counts = {}
    for wrong, right in fixes.items():
        n = text.count(wrong)
        if n > 0:
            text = text.replace(wrong, right)
            counts[wrong] = n
    return text, counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input .md file")
    parser.add_argument("output", help="Output .md file")
    parser.add_argument("--fixes", help="JSON file with {wrong: right} pairs")
    args = parser.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"ERROR: {src} not found", file=sys.stderr)
        return 1

    fixes = load_fixes(args.fixes)
    text = src.read_text(encoding="utf-8")
    new_text, counts = apply_fixes(text, fixes)

    Path(args.output).write_text(new_text, encoding="utf-8")

    total = sum(counts.values())
    print(f"Applied {total} replacements:")
    for wrong, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {wrong} → {fixes[wrong]}: {n}")
    if total == 0:
        print("  (no matches — dictionary may not match this transcript)")
    print(f"Output: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())