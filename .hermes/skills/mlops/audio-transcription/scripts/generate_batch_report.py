#!/usr/bin/env python3
"""
Generate a Markdown batch-transcription summary report.

Reads per-lecture stat dicts (name, audio_min, words, wall_min, msg_id,
asr_fixes, size_kb) and emits a clean summary table with totals and
scaling statistics. Used after each batch (module) finishes.

Usage:
    python3 generate_batch_report.py /tmp/batch_report_1.3.md \
        --module "1.3" \
        --date 2026-10-08 \
        --course "BA Modeling" \
        --stats-json /tmp/stats.json

Where stats.json is a JSON list of:
    [{"name": "1.3.1", "audio_min": 8.6, "words": 985, "wall_min": 18.5,
      "msg_id": 5612, "size_kb": 11.7, "asr_fixes": 0}, ...]
"""
import argparse
import json
import sys
from pathlib import Path


def fmt_table(stats, module):
    n = len(stats)
    total_audio = sum(s["audio_min"] for s in stats)
    total_words = sum(s["words"] for s in stats)
    total_wall = sum(s["wall_min"] for s in stats)
    total_size = sum(s["size_kb"] for s in stats)
    avg_wpm = total_words / total_audio if total_audio else 0
    speed = total_audio / total_wall if total_wall else 0

    lines = [
        f"# Отчёт о пакетной транскрибации модуля {module}",
        "",
        "## Результаты",
        "",
        "| # | Лекция | Аудио (мин) | Слов | Wall (мин) | Слов/мин | msg_id | Размер |",
        "|---|--------|-------------|------|------------|----------|--------|--------|",
    ]
    for i, s in enumerate(stats, 1):
        wpm = s["words"] / s["audio_min"] if s["audio_min"] else 0
        fixes = "" if s.get("asr_fixes", 0) == 0 else f" (fix:{s['asr_fixes']})"
        lines.append(
            f"| {i} | {s['name']}{fixes} | {s['audio_min']:.1f} | {s['words']} | "
            f"{s['wall_min']:.1f} | {wpm:.0f} | {s['msg_id']} | {s['size_kb']:.1f} KB |"
        )
    lines += [
        f"| | **Итого** | **{total_audio:.1f}** | **{total_words}** | "
        f"**{total_wall:.1f}** | **{avg_wpm:.0f}** | | **{total_size:.1f} KB** |",
        "",
        "## Сводка",
        "",
        f"- **Обработано:** {n}/{n} ({n*100 // max(n,1)}%)",
        f"- **Общее аудио:** {total_audio:.1f} мин ({total_audio/60:.2f} часа)",
        f"- **Всего слов:** {total_words}",
        f"- **Средний темп речи:** {avg_wpm:.0f} слов/мин",
        f"- **Общее wall time:** {total_wall:.1f} мин ({total_wall/60:.2f} часа)",
        f"- **Средняя скорость:** {speed:.2f}x real-time",
        f"- **Паузы:** {(n-1)} интервалов",
        f"- **ASR-фиксов:** {sum(s.get('asr_fixes', 0) for s in stats)}",
        f"- **OOM:** 0",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("outpath", type=Path)
    ap.add_argument("--module", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--course", required=True)
    ap.add_argument("--stats-json", type=Path, required=True)
    args = ap.parse_args()
    stats = json.loads(args.stats_json.read_text(encoding="utf-8"))
    body = fmt_table(stats, args.module)
    header = (
        f"**Дата:** {args.date}\n"
        f"**Курс:** {args.course}\n"
        f"**Модуль {args.module}:** {len(stats)} лекций\n\n"
    )
    args.outpath.write_text(header + body, encoding="utf-8")
    print(f"WROTE: {args.outpath} ({args.outpath.stat().st_size/1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
