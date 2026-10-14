#!/usr/bin/env python3
"""
render_report.py — Build the final dogfood report.md from evidence.jsonl.

Reads evidence.jsonl written by collect_evidence.py (or by hand) and emits
report.md using templates/dogfood-report-template.md as the layout. Sorts
issues by severity (Critical → Low). Writes summary counts and a coverage
table automatically.

Usage:
    python scripts/render_report.py \\
        --evidence ./dogfood-output/evidence.jsonl \\
        --template ./templates/dogfood-report-template.md \\
        --target-url https://app.example.com \\
        --scope "Auth + Checkout + Search" \\
        --output ./dogfood-output/report.md

Optional:
    --pages-tested "List of pages visited"
    --features-tested "List of features exercised"
    --not-tested "Areas out of scope"
    --blockers "Things that prevented testing"
    --notes "Free-form closing notes"
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Iterable

SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
SEVERITY_EMOJI = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🔵"}


def load_issues(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"evidence file not found: {path}")
    out: list[dict] = []
    for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"line {i}: invalid JSON — {exc}") from exc
    return sorted(out, key=lambda r: (SEVERITY_ORDER.get(r["severity"], 9), r["issue_number"]))


def render_issue(rec: dict) -> str:
    steps_md = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(rec["steps"]))
    screenshot_block = f"MEDIA:{rec['screenshot']}" if rec.get("screenshot") else "_No screenshot captured._"
    console_block = (
        f"```\n{rec['console']}\n```" if rec.get("console") else "_None observed._"
    )
    return (
        f"### Issue #{rec['issue_number']}: {rec['title']}\n\n"
        f"| Field | Value |\n"
        f"|-------|-------|\n"
        f"| **Severity** | {rec['severity']} {SEVERITY_EMOJI.get(rec['severity'], '')} |\n"
        f"| **Category** | {rec['category']} |\n"
        f"| **URL** | {rec['url']} |\n\n"
        f"**Description:**\n{rec['title']}\n\n"
        f"**Steps to Reproduce:**\n{steps_md}\n\n"
        f"**Expected Behavior:**\n{rec['expected']}\n\n"
        f"**Actual Behavior:**\n{rec['actual']}\n\n"
        f"**Screenshot:**\n{screenshot_block}\n\n"
        f"**Console Errors** (if applicable):\n{console_block}\n\n"
        f"---\n"
    )


def render_summary_table(issues: Iterable[dict]) -> str:
    rows = ["", "| # | Title | Severity | Category | URL |", "|---|-------|----------|----------|-----|"]
    for r in issues:
        rows.append(f"| {r['issue_number']} | {r['title']} | {r['severity']} | {r['category']} | {r['url']} |")
    return "\n".join(rows) + "\n"


def executive_summary(issues: list[dict]) -> str:
    counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for r in issues:
        counts[r["severity"]] = counts.get(r["severity"], 0) + 1
    total = sum(counts.values())
    if total == 0:
        assessment = "No issues observed during this run. Smoke test passed."
    elif counts["Critical"] or counts["High"] > 2:
        assessment = "Multiple high-severity issues found; fix recommended before release."
    elif counts["High"]:
        assessment = "At least one high-severity issue found; review before release."
    elif counts["Medium"]:
        assessment = "Only medium / low issues found; safe to ship with known issues logged."
    else:
        assessment = "Minor cosmetic issues only."
    return (
        "| Severity | Count |\n|----------|-------|\n"
        f"| 🔴 Critical | {counts['Critical']} |\n"
        f"| 🟠 High | {counts['High']} |\n"
        f"| 🟡 Medium | {counts['Medium']} |\n"
        f"| 🔵 Low | {counts['Low']} |\n"
        f"| **Total** | **{total}** |\n\n"
        f"**Overall Assessment:** {assessment}\n"
    )


def render_coverage(args: argparse.Namespace) -> str:
    def block(title: str, raw: str) -> str:
        if not raw:
            items = "_None._"
        else:
            items = "\n".join(f"- {x.strip()}" for x in raw.split(",") if x.strip())
        return f"### {title}\n{items}\n"

    return (
        "## Testing Coverage\n\n"
        + block("Pages Tested", args.pages_tested)
        + block("Features Tested", args.features_tested)
        + block("Not Tested / Out of Scope", args.not_tested)
        + block("Blockers", args.blockers)
    )


def render(template: str, args: argparse.Namespace, issues: list[dict]) -> str:
    body = template
    body = body.replace("{target_url}", args.target_url)
    body = body.replace("{date}", args.date or date.today().isoformat())
    body = body.replace("{scope_description}", args.scope)
    body = body.replace("{one_sentence_assessment}", "")  # filled below

    issues_md = "".join(render_issue(r) for r in issues) if issues else "_No issues captured._\n"
    body = body.replace("<!-- Repeat this section for each issue found, sorted by severity (Critical first) -->", "")
    body = body.replace(
        "<!-- End of per-issue section -->", issues_md
    )

    exec_summary = executive_summary(issues)
    summary_table = render_summary_table(issues)
    coverage = render_coverage(args)
    notes = args.notes or "_None._"

    body = body.replace(
        "| Severity | Count |\n|----------|-------|\n| 🔴 Critical | {critical_count} |\n| 🟠 High | {high_count} |\n| 🟡 Medium | {medium_count} |\n| � Low | {low_count} |\n| **Total** | **{total_count}** |",
        exec_summary,
    )
    body = body.replace("**Overall Assessment:** {one_sentence_assessment}", "")
    body = body.replace("| {n} | {title} | {severity} | {category} | {url} |", "").replace(
        "| # | Title | Severity | Category | URL |", summary_table.split("\n")[1] if summary_table else ""
    )
    # Simpler replacement: drop the placeholder rows and inject the real table after the heading
    head, _, tail = body.partition("## Issues Summary Table\n")
    if tail:
        body = head + "## Issues Summary Table\n" + summary_table + tail.split("\n", 1)[1]

    body = body.replace(
        "## Testing Coverage\n\n### Pages Tested\n- {list_of_pages_visited}\n\n### Features Tested\n- {list_of_features_exercised}\n\n### Not Tested / Out of Scope\n- {areas_not_covered_and_why}\n\n### Blockers\n- {any_issues_that_prevented_testing_certain_areas}\n",
        coverage,
    )
    body = body.replace("{any_additional_observations_or_recommendations}", notes)
    return body


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--evidence", required=True)
    p.add_argument("--template", required=True)
    p.add_argument("--target-url", required=True)
    p.add_argument("--scope", required=True)
    p.add_argument("--date", default="")
    p.add_argument("--pages-tested", default="")
    p.add_argument("--features-tested", default="")
    p.add_argument("--not-tested", default="")
    p.add_argument("--blockers", default="")
    p.add_argument("--notes", default="")
    p.add_argument("--output", required=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    issues = load_issues(Path(args.evidence).expanduser())
    template = Path(args.template).expanduser().read_text(encoding="utf-8")
    body = render(template, args, issues)
    out = Path(args.output).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print(f"Wrote {out} with {len(issues)} issue(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
