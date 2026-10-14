#!/usr/bin/env python3
"""
cleanup.py - очистка постпроцессинговых транскриптов от служебных элементов.

Удаляет из текста:
  1) Метки пауз: [PAUSE 0.46], [PAUSE 1.22], ...
  2) HTML-комментарии заголовков чанков: <!-- chunk_NNN_postprocess.md -->
  3) Markdown-заголовки секций: # Transcription: chunk_NNN (LLM postprocessed)
  4) Служебные метаданные: **Word count:**, **LLM model:**, **LLM response time:**
  5) Разделители: --- (сразу после метаданных)
  5b) Raw-формат метаданных из transcribe.py: **Duration:**, **Language:**, **Model:**, **Segments:**, **Transcription time:**
  5c) Raw-формат заголовков секций: # Transcription: chunk_NNN.wav (...)
  5d) Заголовки склеенных чанков: # chunk_NNN

Использование:
    python3 cleanup.py <input.md> <output.md>
    python3 cleanup.py <input.md>            # печатает в stdout

Опции:
    --in-place  записать в тот же файл
    --preview   показать первые 500 символов до/после
"""
import argparse
import re
import sys
from pathlib import Path


def clean_transcript(text: str) -> tuple[str, dict]:
    """Применяет все правила очистки. Возвращает (очищенный_текст, статистика)."""

    stats = {
        "pause_markers": 0,
        "chunk_comments": 0,
        "section_headers": 0,
        "metadata_lines": 0,
        "separators": 0,
        "extra_blank_lines": 0,
    }

    # 1) [PAUSE X.XX] — любые варианты: [PAUSE 0.46], [PAUSE 1.22]
    pause_pattern = re.compile(r"\[PAUSE\s+[\d.]+\]")
    stats["pause_markers"] = len(pause_pattern.findall(text))
    text = pause_pattern.sub("", text)

    # 2) HTML-комментарии заголовков чанков: <!-- chunk_NNN_postprocess.md -->
    comment_pattern = re.compile(r"^<!-- chunk_\d+_postprocess\.md -->\s*\n", re.MULTILINE)
    stats["chunk_comments"] = len(comment_pattern.findall(text))
    text = comment_pattern.sub("", text)

    # 3) Заголовки секций: # Transcription: chunk_NNN (LLM postprocessed)
    section_pattern = re.compile(r"^# Transcription: chunk_\d+ \(LLM postprocessed\)\s*\n", re.MULTILINE)
    stats["section_headers"] = len(section_pattern.findall(text))
    text = section_pattern.sub("", text)

    # 4) Служебные метаданные
    meta_pattern = re.compile(
        r"^\*\*(Word count|LLM model|LLM response time):\*\*[^\n]*\n",
        re.MULTILINE,
    )
    stats["metadata_lines"] = len(meta_pattern.findall(text))
    text = meta_pattern.sub("", text)

    # 5) Разделители --- в начале секции метаданных
    # Они идут сразу после заголовка секции (который уже удалён).
    # Ищем --- окружённые пустыми строками — обычно первая после удаления метаданных
    sep_pattern = re.compile(r"^\s*---\s*\n", re.MULTILINE)
    stats["separators"] = len(sep_pattern.findall(text))
    text = sep_pattern.sub("", text)

    # 5b) Raw-формат из transcribe.py: блок метаданных **Duration/Language/Model/...**
    raw_meta_pattern = re.compile(
        r"\*\*[A-Z][a-zA-Z ]+:\*\*\s*[^\n]*\n",
        re.MULTILINE,
    )
    raw_meta_count = len(raw_meta_pattern.findall(text))
    text = raw_meta_pattern.sub("", text)
    stats["raw_metadata"] = raw_meta_count

    # 5c) Raw-формат заголовков секций: # Transcription: chunk_NNN.wav (...)
    raw_section_pattern = re.compile(
        r"^# Transcription: chunk_\d+\.wav[^\n]*\n",
        re.MULTILINE,
    )
    raw_section_count = len(raw_section_pattern.findall(text))
    text = raw_section_pattern.sub("", text)
    stats["raw_section_headers"] = raw_section_count

    # 5d) Raw-формат заголовков чанков: # chunk_NNN (после склейки через конкатенацию)
    raw_chunk_header_pattern = re.compile(
        r"^# chunk_\d+\s*\n", re.MULTILINE,
    )
    raw_chunk_header_count = len(raw_chunk_header_pattern.findall(text))
    text = raw_chunk_header_pattern.sub("", text)
    stats["raw_chunk_headers"] = raw_chunk_header_count

    # 6) Подчистка лишних пустых строк (>2 подряд → 1)
    blank_pattern = re.compile(r"\n{3,}")
    before = len(blank_pattern.findall(text))
    text = blank_pattern.sub("\n\n", text)
    stats["extra_blank_lines"] = before

    # Trim trailing whitespace
    text = text.strip() + "\n"

    return text, stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Очистка постпроцессинговых транскриптов",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input", help="Путь к входному MD-файлу")
    parser.add_argument("output", nargs="?", help="Путь к выходному файлу (по умолчанию: stdout)")
    parser.add_argument("--in-place", action="store_true", help="Записать в тот же файл")
    parser.add_argument("--preview", action="store_true", help="Показать первые 500 символов до/после")

    args = parser.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"ERROR: {src} не найден", file=sys.stderr)
        return 1

    text = src.read_text(encoding="utf-8")
    cleaned, stats = clean_transcript(text)

    if args.preview:
        print("=" * 60)
        print("BEFORE (first 500 chars):")
        print("=" * 60)
        print(text[:500])
        print()
        print("=" * 60)
        print("AFTER (first 500 chars):")
        print("=" * 60)
        print(cleaned[:500])
        print()

    print("Cleanup statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print(f"  total size: {len(text)} → {len(cleaned)} chars ({len(text) - len(cleaned)} removed)")

    if args.in_place:
        src.write_text(cleaned, encoding="utf-8")
        print(f"\nWrote (in-place): {src}")
    elif args.output:
        out = Path(args.output)
        out.write_text(cleaned, encoding="utf-8")
        print(f"\nWrote: {out}")
    else:
        sys.stdout.write(cleaned)

    return 0


if __name__ == "__main__":
    sys.exit(main())