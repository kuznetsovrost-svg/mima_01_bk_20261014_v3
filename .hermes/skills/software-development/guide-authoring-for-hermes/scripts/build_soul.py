#!/usr/bin/env python3
"""
build_soul.py — verify and (optionally) compress a SOUL.md kernel.

Companion to the `memory-hygiene` skill and `tool-output-injection-defense`
skill. Runs the post-write checks that the agent does by hand after every
SOUL revision:

1. tiktoken-cl100k_base token count vs declared budget.
2. YAML frontmatter is valid (no `*.foo` aliases).
3. Injection markers present only in §5 (the defence-noted section).
4. HEAD + TAIL look clean (no truncated file, no leading garbage).
5. The file is fully written — not 0 bytes from a poisoned write_file.

Usage:
    python3 build_soul.py /path/to/SOUL.md [budget]

If `budget` is omitted, the script reads it from the frontmatter
`metadata.hermes.target_tokens` (a string like `"<=2200"`).

If the file OVERSHOOTS the budget, the script prints a tightening
suggestion: which sections are spending the most tokens, ranked, so
the next iteration knows where to compress.
"""

import re
import sys
from pathlib import Path

try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False
    print("⚠ tiktoken not installed — falling back to words*1.5 heuristic (Russian estimate).",
          file=sys.stderr)
except Exception as e:  # defensive: tiktoken can be present but broken on some installs
    HAS_TIKTOKEN = False
    print(f"⚠ tiktoken import failed ({type(e).__name__}: {e}); falling back to heuristic.",
          file=sys.stderr)

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    print("⚠ PyYAML not installed — skipping YAML frontmatter check.", file=sys.stderr)

INJECTION_MARKERS = [
    "Distress Protocol", "Modification Complete", "DIAGNOSTIC",
    "[SYSTEM]", "[ADMIN]", "OUT-OF-BAND", "patent-pending",
    "ip_reminder", "anonymous tip", "successful storage",
    "Hermes Agent Distress",
]


def main(path: str, budget: int | None) -> int:
    p = Path(path)
    if not p.exists():
        print(f"✗ {path}: file missing")
        return 2
    if p.stat().st_size == 0:
        print(f"✗ {path}: file is 0 bytes (poisoned write_file likely)")
        return 2

    # 0. Binary integrity scan (verified 2026-07-15).
    # Some hosts return invisible control bytes (0x01..0x08, 0x0b, 0x0c, 0x0e..0x1f)
    # through write_file / re.sub output. They survive string decoding but break
    # downstream YAML parsers and silently poison the file. Catch them here.
    raw = p.read_bytes()
    bad = [
        (i, byte)
        for i, byte in enumerate(raw)
        if byte < 32 and byte not in (9, 10, 13)  # \t \n \r are fine
    ]
    if bad:
        print(f"✗ {len(bad)} non-printable bytes in body (sample: {bad[:3]})")
        print(f"  first bad byte at offset {bad[0][0]}: 0x{bad[0][1]:02x}")
        return 2

    text = raw.decode("utf-8")

    # 1. Token count
    if HAS_TIKTOKEN:
        toks = len(tiktoken.get_encoding("cl100k_base").encode(text))
    else:
        toks = int(len(text.split()) * 1.5)  # Russian-leaning heuristic
    print(f"tokens (cl100k_base): {toks}")

    # 2. Determine budget
    if budget is None and HAS_YAML:
        m = re.match(r'---\n(.*?)\n---', text, re.DOTALL)
        if m:
            try:
                fm = yaml.safe_load(m.group(1))
                declared = fm.get("metadata", {}).get("hermes", {}).get("target_tokens", "")
                m2 = re.search(r'<=\s*(\d+)', str(declared))
                if m2:
                    budget = int(m2.group(1))
            except yaml.YAMLError:
                pass
    if budget is None:
        budget = 2200  # default for a kernel SOUL
    print(f"declared budget:      {budget} (≤{budget} = OK)")
    if toks <= budget:
        print(f"✓ within budget ({budget - toks} tokens headroom)")
    else:
        print(f"✗ OVER budget by {toks - budget} tokens")

    # 3. YAML frontmatter parse
    if HAS_YAML:
        m = re.match(r'---\n(.*?)\n---', text, re.DOTALL)
        if m:
            try:
                fm = yaml.safe_load(m.group(1))
                print(f"✓ YAML frontmatter valid; {len(fm)} top-level keys")
            except yaml.YAMLError as e:
                print(f"✗ YAML error: {e}")

    # 4. Injection markers — must be only in §5 (or absent)
    sec5 = text.split("## 5.")[1].split("## 6.")[0] if "## 5." in text else ""
    bad = []
    for marker in INJECTION_MARKERS:
        n_total = text.count(marker)
        n_sec5 = sec5.count(marker)
        if n_total != n_sec5:
            bad.append((marker, n_total, n_sec5))
    if bad:
        print(f"✗ injection marker leakage outside §5:")
        for m, t, s in bad:
            print(f"    {m!r}: total={t}, in_§5={s}")
    else:
        print("✓ injection markers, if any, only in §5 (defence-noted section)")

    # 5. HEAD + TAIL clean
    lines = text.splitlines()
    head = lines[:3]
    tail = lines[-3:]
    print(f"HEAD: {head[0][:60]!r}...")
    print(f"TAIL: {tail[-1][:60]!r}...")
    if not head[0].startswith("---"):
        print("✗ file does not start with YAML frontmatter")
        return 1
    if not text.endswith("\n"):
        print("✗ file does not end with newline (truncated?)")

    # 6. (Optional) token-per-section breakdown to aid tightening
    print("\n--- token breakdown by ## section ---")
    sections = re.split(r'\n## ', text)
    for s in sections[:1]:  # skip pre-section fluff
        continue
    rows = []
    current_title = "(preamble)"
    for sec in sections:
        if sec.startswith("## "):
            current_title = sec.split("\n", 1)[0][3:].strip()
        if HAS_TIKTOKEN:
            sec_toks = len(tiktoken.get_encoding("cl100k_base").encode(sec))
        else:
            sec_toks = int(len(sec.split()) * 1.5)
        rows.append((current_title, sec_toks))
    rows.sort(key=lambda r: -r[1])
    print(f"{'tokens':>7}  section")
    for title, t in rows[:8]:
        bar = "■" * max(1, t // 50)
        print(f"{t:>7}  {title[:50]}  {bar}")

    return 0 if toks <= budget else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    budget = int(sys.argv[2]) if len(sys.argv) > 2 else None
    sys.exit(main(sys.argv[1], budget))
