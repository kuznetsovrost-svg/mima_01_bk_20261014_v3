#!/usr/bin/env python3
"""
build_diff.py - Build a sentence-level diff between two transcriptions.

Output: Markdown table with columns:
| # | Medium (beam=5) | Large-v3 (beam=5) | Verdict |

Diffs are based on sentence boundaries. Both texts are split into
sentences using ru-specific punctuation, then aligned.
"""
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path


def split_sentences(text: str) -> list[str]:
    """Split Russian text into sentences on . ! ? (keeping them with sentence)."""
    # Заменяем многоточие на точку для упрощения
    text = text.replace("...", ".").replace("..", ".")
    # Нормализуем пробелы
    text = re.sub(r"\s+", " ", text).strip()
    # Разделяем по . ! ? и оставляем их с предложением
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def normalize(s: str) -> str:
    """Normalize for comparison: lowercase, strip, collapse spaces."""
    s = s.lower()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def build_diff(medium_text: str, large_text: str) -> list[dict]:
    """
    Build diff rows by aligning sentences.

    Each row:
    {
      "medium": str,
      "large": str,
      "verdict": "same" | "different" | "medium_only" | "large_only",
      "score": float (similarity 0-1)
    }
    """
    medium_sents = split_sentences(medium_text)
    large_sents = split_sentences(large_text)

    # Используем SequenceMatcher для выравнивания
    sm = SequenceMatcher(None, medium_sents, large_sents, autojunk=False)
    rows = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                rows.append({
                    "medium": medium_sents[i1 + k],
                    "large": large_sents[j1 + k],
                    "verdict": "same",
                    "score": 1.0,
                })
        elif tag == "replace":
            # Сопоставляем попарно
            for k in range(max(i2 - i1, j2 - j1)):
                m = medium_sents[i1 + k] if i1 + k < i2 else ""
                l = large_sents[j1 + k] if j1 + k < j2 else ""
                score = 0.0
                if m and l:
                    score = SequenceMatcher(None, normalize(m), normalize(l)).ratio()
                verdict = "different"
                if not m:
                    verdict = "large_only"
                elif not l:
                    verdict = "medium_only"
                rows.append({
                    "medium": m,
                    "large": l,
                    "verdict": verdict,
                    "score": score,
                })
        elif tag == "delete":
            for k in range(i2 - i1):
                rows.append({
                    "medium": medium_sents[i1 + k],
                    "large": "",
                    "verdict": "medium_only",
                    "score": 0.0,
                })
        elif tag == "insert":
            for k in range(j2 - j1):
                rows.append({
                    "medium": "",
                    "large": large_sents[j1 + k],
                    "verdict": "large_only",
                    "score": 0.0,
                })
    return rows


def render_table(rows: list[dict]) -> str:
    """Render as Markdown table with limited columns."""
    # Markdown-таблица с text по 100 chars max
    lines = [
        "# Diff: Medium (beam=5) vs Large-v3 (beam=5)",
        "",
        f"**Same:** {sum(1 for r in rows if r['verdict']=='same')} | "
        f"**Different:** {sum(1 for r in rows if r['verdict']=='different')} | "
        f"**Medium only:** {sum(1 for r in rows if r['verdict']=='medium_only')} | "
        f"**Large only:** {sum(1 for r in rows if r['verdict']=='large_only')}",
        "",
        "| # | Verdict | Medium | Large |",
        "|---|---|---|---|",
    ]
    for i, r in enumerate(rows, 1):
        verdict_marker = {
            "same": "✅",
            "different": "⚠️",
            "medium_only": "➖M",
            "large_only": "➖L",
        }.get(r["verdict"], "?")
        m = (r["medium"][:200] + "...") if len(r["medium"]) > 200 else r["medium"]
        l = (r["large"][:200] + "...") if len(r["large"]) > 200 else r["large"]
        m = m.replace("|", "\\|").replace("\n", " ")
        l = l.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {i} | {verdict_marker} | {m} | {l} |")
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: build_diff.py MEDIUM.md LARGE.md OUTPUT.md")
        return 1

    medium_path = Path(sys.argv[1])
    large_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])

    if not medium_path.exists() or not large_path.exists():
        print(f"Files not found: {medium_path} {large_path}")
        return 1

    medium_text = medium_path.read_text(encoding="utf-8")
    large_text = large_path.read_text(encoding="utf-8")

    rows = build_diff(medium_text, large_text)
    table = render_table(rows)

    output_path.write_text(table, encoding="utf-8")
    print(f"Wrote {output_path} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())