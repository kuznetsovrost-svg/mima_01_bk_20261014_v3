#!/usr/bin/env python3
"""
collect_evidence.py — Dogfood helper for collecting issue evidence.

Appends structured issue records to evidence.jsonl in the dogfood output
directory. Each line is a JSON object that render_report.py later consumes
to build the final report.md.

Usage (from within a dogfood session):

    python scripts/collect_evidence.py \\
        --output-dir ./dogfood-output \\
        --severity High \\
        --category Functional \\
        --title "Submit button does nothing" \\
        --url https://app.example.com/checkout \\
        --steps "1. Click Submit" "2. Observe no request fires" \\
        --expected "POST /api/order" \\
        --actual "Nothing happens, no console error" \\
        --screenshot ./dogfood-output/screenshots/issue-3.png \\
        --console "Uncaught TypeError: ..."

Or pipe stdin for batch collection.

Why a helper instead of inline Markdown:
- keeps the agent loop free of repetitive boilerplate
- ensures every issue gets the same fields
- lets render_report.py generate a uniform report.md
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SEVERITIES = {"Critical", "High", "Medium", "Low"}
CATEGORIES = {"Functional", "Visual", "Accessibility", "Console", "UX", "Content"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--output-dir", required=True, help="Dogfood output directory (will create evidence.jsonl)")
    p.add_argument("--severity", required=True, choices=sorted(SEVERITIES))
    p.add_argument("--category", required=True, choices=sorted(CATEGORIES))
    p.add_argument("--title", required=True)
    p.add_argument("--url", required=True)
    p.add_argument("--steps", nargs="+", required=True, help="Numbered reproduction steps")
    p.add_argument("--expected", required=True)
    p.add_argument("--actual", required=True)
    p.add_argument("--screenshot", default="", help="Relative or absolute path to evidence image")
    p.add_argument("--console", default="", help="Console error block (multi-line string)")
    p.add_argument("--notes", default="", help="Free-form notes")
    return p.parse_args()


def next_issue_number(out_dir: Path) -> int:
    path = out_dir / "evidence.jsonl"
    if not path.exists():
        return 1
    n = 0
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                n = max(n, int(rec.get("issue_number", 0)))
            except json.JSONDecodeError:
                continue
    return n + 1


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "screenshots").mkdir(exist_ok=True)

    record = {
        "issue_number": next_issue_number(out_dir),
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "severity": args.severity,
        "category": args.category,
        "title": args.title,
        "url": args.url,
        "steps": args.steps,
        "expected": args.expected,
        "actual": args.actual,
        "screenshot": args.screenshot,
        "console": args.console,
        "notes": args.notes,
    }

    path = out_dir / "evidence.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Recorded issue #{record['issue_number']}: [{args.severity}] {args.title}")
    print(f"  → {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
