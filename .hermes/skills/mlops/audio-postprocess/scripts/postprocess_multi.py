#!/usr/bin/env python3
"""
postprocess_multi.py - Multi-pass LLM postprocess for Russian lecture transcripts.

Passes (each calls hermes -z separately):
  1) Cleanup filler words (Вот, Значит, Ну, Так, How...) + minor punctuation
  2) Fix ASR errors (use context + known terms list)
  3) Structure: split into thematic blocks (headings)
  4) Final polish: style, paragraph flow

Each pass produces intermediate file: <name>_pass_N.md
Final output: <name>_final.md

Usage:
    python3 postprocess_multi.py <input.md> <output_base> [--passes 1,2,3,4]
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path


# ============ PROMPTS ============

PASS_1_FILLER = """\
Ты редактор русского текста. Твоя задача: убрать слова-паразиты и поставить базовую пунктуацию.

ПРАВИЛА:
1) Удали слова-паразиты: "Вот", "Значит", "Ну", "Так", "Это самое", "Как бы", "Собственно", "Кстати" (если не несёт смысла).
2) НЕ удаляй их, если они несут эмфазу или нужны для ритма.
3) Поставь точки в конце предложений, запятые в сложных предложениях.
4) Раздели абзацы по логическим паузам (каждые 2-4 предложения).
5) Сохрани все смысловые слова, имена, числа.
6) НЕ исправляй технические термины (оставляй ошибки распознавания для следующего прохода).

ФОРМАТ ВЫВОДА:
Только обработанный текст, без комментариев. Сохрани все абзацы.
"""

PASS_2_ASR_FIX = """\
Ты корректор русского текста. Твоя задача: исправить ошибки распознавания речи (ASR).

ИЗВЕСТНЫЕ ОШИБКИ В ТАКИХ ТЕКСТАХ:
- "имперический" → "эмпирический"
- "фактальной" → "фрактальной"
- "сниженка Коха" → "снежинка Коха"
- "использование токовых" (артефакт) → удалить или переписать предложение
- "свепроводящих" → "сверхпроводящих"
- "ТЗ, ЧТЗ" → оставить как есть
- технические термины: проверь орфографию (IDEF, BPMN, ARIS, ArchiMate и т.п.)

ПРАВИЛА ДЛЯ ИМЕНИ "ОМ" (учёный Георг Симон Ом, физик, автор закона):
- В ПЕРВОМ упоминании в тексте: "Георг Симон Ом" (полное имя).
- Во всех последующих упоминаниях: только фамилия "Ом" с правильным склонением по падежам русского языка:
  - И.п. "Ом" (Ом сформулировал закон)
  - Р.п. "Ома" (закон Ома)
  - Д.п. "Ому" (по Ому)
  - В.п. "Ома" (упомянуть Ома)
  - Т.п. "Омом" (законом Ома)
  - П.п. "об Оме" (об Оме речь)
- НЕ писать "Ом" с большой буквы каждый раз — только в первом упоминании "Георг Симон Ом".
- НЕ сокращать до "Ома" как аббревиатуру (ОМА = что-то другое).
- Контекст для первого упоминания: речь про физика и его закон.

ПРАВИЛА В ЦЕЛОМ:
1) Исправляй ТОЛЬКО очевидные ошибки распознавания.
2) Если не уверен — оставь как есть.
3) Сохрани все слова, имена, числа.
4) Сохрани структуру абзацев.
5) НЕ добавляй новый смысл.

ФОРМАТ ВЫВОДА:
Только исправленный текст, без комментариев.
"""

PASS_3_STRUCTURE = """\
Ты редактор-структуратор. Твоя задача: разбить длинный текст лекции на логические блоки.

ПРАВИЛА:
1) Определи тематические блоки лекции (вступление, тезис 1, пример, тезис 2, ...).
2) Перед каждым блоком добавь заголовок второго уровня (##).
3) Заголовки должны быть ёмкими (3-7 слов), отражать суть блока.
4) Между блоками — пустая строка.
5) Сохрани все слова, имена, числа, абзацы внутри блоков.
6) НЕ добавляй новый смысл, только структуру.

ФОРМАТ ВЫВОДА:
Только структурированный текст с заголовками ##, без комментариев.
"""

PASS_4_POLISH = """\
Ты литературный редактор. Твоя задача: финальная полировка текста лекции.

ПРАВИЛА:
1) Проверь стилистическую целостность и плавность переходов.
2) Убери шероховатости, повторы слов в соседних предложениях.
3) Сохрани разговорный стиль лекции (это не статья, это живая речь).
4) Сохрани все заголовки, абзацы, имена, числа.
5) Пунктуация должна быть корректной для русского языка.
6) НЕ переписывай текст, только полируй.

ФОРМАТ ВЫВОДА:
Только отполированный текст, без комментариев.
"""


PASSES = {
    1: ("filler", PASS_1_FILLER),
    2: ("asr_fix", PASS_2_ASR_FIX),
    3: ("structure", PASS_3_STRUCTURE),
    4: ("polish", PASS_4_POLISH),
}


def call_llm(prompt: str, text: str, model: str = "MiniMax-M3") -> str:
    """Call hermes -z with the prompt and text."""
    full_prompt = f"{prompt}\n\n---\n\n{text}\n\n---\n\nВыходной текст:"
    result = subprocess.run(
        ["hermes", "-z", full_prompt],
        capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        print(f"  LLM error: {result.stderr[:300]}", file=sys.stderr)
        return ""
    out = result.stdout.strip()
    # Strip potential markdown code blocks
    if out.startswith("```"):
        out = re.sub(r"^```\w*\n?", "", out)
        out = re.sub(r"\n?```$", "", out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input MD file (cleaned, no metadata)")
    parser.add_argument("output_base", help="Output base path (will create _pass_N.md and _final.md)")
    parser.add_argument("--passes", default="1,2,3,4", help="Comma-separated pass numbers (default: 1,2,3,4)")
    parser.add_argument("--start-from", type=int, default=1, help="Skip passes before this (use if resuming)")
    args = parser.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"ERROR: {src} not found", file=sys.stderr)
        return 1

    out_base = Path(args.output_base)
    out_base.parent.mkdir(parents=True, exist_ok=True)

    text = src.read_text(encoding="utf-8")
    word_count = len(text.split())
    print(f"Input: {src} ({word_count} words)")

    pass_nums = [int(p) for p in args.passes.split(",")]
    pass_nums = [p for p in pass_nums if p in PASSES]
    pass_nums.sort()

    current_text = text
    if args.start_from > 1:
        prev = out_base.with_name(out_base.name + f"_pass_{args.start_from - 1}.md")
        if prev.exists():
            current_text = prev.read_text(encoding="utf-8")
            print(f"Resuming from pass {args.start_from}, loaded {len(current_text.split())} words from {prev.name}")

    for pn in pass_nums:
        if pn < args.start_from:
            continue

        name, prompt = PASSES[pn]
        out_file = out_base.with_name(out_base.name + f"_pass_{pn}_{name}.md")

        print(f"\n=== Pass {pn}: {name} ===")
        print(f"Input: {len(current_text.split())} words")

        result = call_llm(prompt, current_text)
        if not result:
            print(f"  FAIL: empty response, skipping pass {pn}")
            continue

        out_file.write_text(result, encoding="utf-8")
        out_words = len(result.split())
        print(f"  Output: {out_words} words -> {out_file.name}")

        current_text = result

    # Final output
    final_file = out_base.with_name(out_base.name + "_final.md")
    final_file.write_text(current_text, encoding="utf-8")
    print(f"\n=== Final: {final_file} ({len(current_text.split())} words) ===")

    return 0


if __name__ == "__main__":
    sys.exit(main())