#!/usr/bin/env python3
"""
Validate a candidate SKILL.md against the same BLOCKER / WARN checks the
bundled `hermes-agent-skill-authoring` skill encodes.

Usage:
    python3 validate_skill.py path/to/SKILL.md [--report report.txt]

Exit codes:
    0  no BLOCKER issues (file is loadable)
    1  BLOCKER issue found (file would fail skill_loader validation)
    2  internal error (bad path, unreadable file)

This script does NOT modify the input file. It prints a structured report
to stdout and (optionally) writes the same report to --report. Use this
when a user asks for a skill review and you want a deterministic baseline
before adding substance / typo observations from the SKILL body.

Lives at:
    skills/software-development/skill-candidate-review/scripts/validate_skill.py
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

import yaml


# Cyrillic homoglyphs that look identical to Latin letters. Used to scan
# slug-like fields for invisible encoding bugs.
CYR_HOMOGLYPHS = {
    "а", "е", "о", "р", "с", "у", "х",  # Russian letters
    "А", "В", "Е", "К", "М", "Н", "О", "Р", "С", "Т", "У", "Х",  # uppercase
}

# Peer-convention: lowercase + hyphens, max 64 chars (validator-enforced).
NAME_PATTERN = re.compile(r"^[a-z0-9-]+$")

# Advisory typo hints. See references/typo-hints.md in this skill for
# context and rationale. These are intentionally short substrings so the
# scan is fast on large bodies.
TYPO_HINTS = [
    # Cyrillic / Latin homoglyphs in otherwise-Latin contexts
    "аcademic", "аnalysis", "сourse", "рrogram", "рython", "хello",
    # Path / filename slips
    "Otputs", "Outpusts", "trainig", "schemа",
    # Russian-language doubled-consonant slips
    "утвержденние", "прохожденния", "обоснованнно",
    # Russian-language dropped-letter slips
    "проаграммы", "преметы", "аритектор",
]


def validate(path: Path) -> tuple[str, int]:
    """Return (report_text, exit_code). 2 on internal error, 1 on BLOCKER, 0 otherwise."""
    if not path.exists():
        return f"ERROR: file not found: {path}\n", 2
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as exc:
        return f"ERROR: cannot read {path}: {exc}\n", 2

    lines = ["=" * 60, f"VALIDATION REPORT: {path}", "=" * 60, ""]
    issues: list[tuple[str, str]] = []

    # --- BLOCKER 1: starts with ---
    if not content.startswith("---"):
        issues.append(("BLOCKER", "file does not start with '---' at byte 0"))
        lines.append("[BLOCKER] file does not start with '---' at byte 0")
        return _finish(lines, issues)
    lines.append("[OK] starts with --- at byte 0")

    # --- BLOCKER 2: closing ---
    m = re.search(r"\n---\s*\n", content[3:])
    if not m:
        issues.append(("BLOCKER", "no closing '\\n---\\n' found"))
        lines.append("[BLOCKER] no closing '\\n---\\n' found")
        return _finish(lines, issues)
    fm_end = m.start() + 3
    lines.append(f"[OK] closing --- at byte offset {fm_end}")

    # --- BLOCKER 3: YAML parses ---
    try:
        fm = yaml.safe_load(content[3:fm_end])
        lines.append(f"[OK] YAML parses; keys: {list(fm.keys()) if isinstance(fm, dict) else fm}")
    except yaml.YAMLError as exc:
        issues.append(("BLOCKER", f"YAML parse failed: {exc}"))
        lines.append(f"[BLOCKER] YAML parse failed: {exc}")
        return _finish(lines, issues)

    if not isinstance(fm, dict):
        issues.append(("BLOCKER", "frontmatter is not a YAML mapping"))
        lines.append("[BLOCKER] frontmatter is not a YAML mapping")
        return _finish(lines, issues)

    # --- BLOCKER 4: required fields ---
    for field in ("name", "description"):
        if field not in fm:
            issues.append(("BLOCKER", f"missing required field: {field}"))
            lines.append(f"[BLOCKER] missing required field: {field}")

    # --- name checks ---
    if "name" in fm:
        name = fm["name"]
        lines.append(f"  name = {name!r} (len {len(name) if isinstance(name, str) else '?'})")
        if not isinstance(name, str):
            issues.append(("BLOCKER", "name is not a string"))
            lines.append("[BLOCKER] name is not a string")
        else:
            if len(name) > 64:
                issues.append(("BLOCKER", f"name length {len(name)} > 64"))
                lines.append(f"[BLOCKER] name length {len(name)} > 64")
            if not NAME_PATTERN.match(name):
                bad = [ch for ch in name if not (ch.isascii() and (ch.isalnum() or ch == "-"))]
                issues.append(("WARN", f"name {name!r} violates peer-convention (lowercase + hyphens): non-conforming chars {bad}"))
                lines.append("[WARN] name violates peer-convention (lowercase + hyphens)")

    # --- description checks ---
    if "description" in fm:
        desc = fm["description"]
        lines.append(f"  description length = {len(desc) if isinstance(desc, str) else '?'}")
        if not isinstance(desc, str):
            issues.append(("BLOCKER", "description is not a string"))
            lines.append("[BLOCKER] description is not a string")
        else:
            if len(desc) > 1024:
                issues.append(("BLOCKER", f"description length {len(desc)} > 1024"))
                lines.append(f"[BLOCKER] description length {len(desc)} > 1024")
            if not desc.lower().startswith("use when"):
                issues.append(("WARN", "description does not start with 'Use when ...' (peer convention)"))
                lines.append("[WARN] description does not start with 'Use when ...'")

    # --- WARN: peer-convention optional fields ---
    for field in ("version", "author", "license", "metadata"):
        if field not in fm:
            issues.append(("WARN", f"missing peer-convention field: {field}"))
            lines.append(f"[WARN] missing peer-convention field: {field}")
        else:
            lines.append(f"  {field} = {fm[field]}")

    # --- metadata.hermes ---
    if "metadata" in fm and isinstance(fm["metadata"], dict):
        hermes = fm["metadata"].get("hermes", {})
        if not isinstance(hermes, dict):
            issues.append(("WARN", "metadata.hermes is not a mapping"))
        else:
            for k in ("tags", "related_skills"):
                if k not in hermes:
                    issues.append(("WARN", f"metadata.hermes.{k} missing"))
                    lines.append(f"[WARN] metadata.hermes.{k} missing")
            tags = hermes.get("tags", [])
            if isinstance(tags, list):
                for t in tags:
                    if isinstance(t, str) and not re.match(r"^[a-z0-9-]+$", t):
                        issues.append(("WARN", f"tag {t!r} violates peer-convention (lowercase + hyphens)"))
                        lines.append(f"[WARN] tag {t!r} violates peer-convention")

    # --- body non-empty ---
    body = content[m.end():].strip()
    lines.append(f"\n  body size = {len(body)} chars")
    if not body:
        issues.append(("BLOCKER", "empty body after closing ---"))
        lines.append("[BLOCKER] empty body after closing ---")

    # --- total size ---
    total = len(content)
    lines.append(f"  total size = {total} chars (limit 100,000)")
    if total > 100_000:
        issues.append(("BLOCKER", f"file size {total} > 100,000 chars"))
        lines.append(f"[BLOCKER] file size {total} > 100,000")

    # --- advisory typo scan ---
    typo_hits: list[tuple[str, int, str]] = []
    for i, line in enumerate(body.splitlines(), 1):
        for hint in TYPO_HINTS:
            if hint in line:
                typo_hits.append((hint, i, line.strip()[:120]))
    if typo_hits:
        issues.append(("WARN", f"potential typos detected: {len(typo_hits)}"))
        lines.append(f"\n  [WARN] Potential typos in body ({len(typo_hits)} hits):")
        for hint, ln, ctx in typo_hits[:20]:
            lines.append(f"     L{ln}: {hint!r} in: {ctx}")

    # --- cyrillic homoglyph scan on slug-like fields ---
    if "name" in fm and isinstance(fm["name"], str):
        for i, ch in enumerate(fm["name"]):
            try:
                name_unicode = unicodedata.name(ch, "")
            except ValueError:
                continue
            if "CYRILLIC" in name_unicode:
                issues.append(("WARN", f"name contains cyrillic homoglyph at position {i}: {ch!r}"))
                lines.append(f"[WARN] name contains cyrillic homoglyph: {ch!r}")

    return _finish(lines, issues)


def _finish(lines: list[str], issues: list[tuple[str, str]]) -> tuple[str, int]:
    lines.append("")
    blockers = sum(1 for s, _ in issues if s == "BLOCKER")
    warns = sum(1 for s, _ in issues if s == "WARN")
    lines.append(f"TOTAL: {blockers} BLOCKER, {warns} WARN")
    exit_code = 1 if blockers else 0
    return "\n".join(lines), exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", type=Path, help="path to SKILL.md")
    parser.add_argument("--report", type=Path, default=None, help="also write report to this file")
    args = parser.parse_args()

    report, exit_code = validate(args.path)
    print(report)

    if args.report:
        args.report.write_text(report, encoding="utf-8")
        print(f"\n[report written to {args.report}]", file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())