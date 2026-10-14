#!/usr/bin/env python3
"""
punctuate_v3.py - Conservative postprocess: punctuation + ASR fix only.

This is the OPPOSITE of multi-pass v1. It does NOT:
- Remove filler words (Вот, Значит, Ну)
- Rephrase sentences
- Restructure into thematic blocks
- Polish style

It DOES:
- Add punctuation (. , ? ! : —)
- Fix specific known ASR errors
- Add paragraph breaks based on detected long pauses

Two passes:
  1) Punctuation: minimal, non-invasive
  2) ASR fix: only specific known errors

Both passes use STRONG instructions to LLM: "НЕ МЕНЯЙ слова лектора!"
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path


PUNCTUATION_PROMPT = """\
Ты — стенографист, который ставит знаки препинания в транскрипции лекции.

ЖЁСТКИЕ ПРАВИЛА:
1) НЕ МЕНЯЙ НИ ОДНОГО СЛОВА. Слова лектора священны.
2) НЕ удаляй слова: "Вот", "Значит", "Ну", "Так", "Это" — все оставь.
3) НЕ перефразируй, НЕ сокращай, НЕ добавляй.
4) Можно ТОЛЬКО расставить знаки препинация: . , ? ! : — ;
5) Раздели текст на абзацы по СМЫСЛОВЫМ ПАУЗАМ (когда лектор меняет тему).
   - Признак смены темы: длинная пауза в аудио (5+ секунд).
   - Признак смены темы: лектор говорит "Теперь", "Дальше", "Следующий момент", "Итак".
   - Признак смены темы: переход к новому примеру или тезису.
6) Сохрани разговорный стиль лекции.
7) Имена собственные и аббревиатуры оставь как в оригинале.
8) ВЫВОД: только размеченный текст, без пояснений, без заголовков ## (это будет сделано позже).

ТЕКСТ:
{text}

РАЗМЕЧЕННЫЙ ТЕКСТ:"""


ASR_FIX_PROMPT = """\
Ты — корректор русского текста, исправляешь ОШИБКИ РАСПОЗНАВАНИЯ РЕЧИ (ASR).

ЖЁСТКИЕ ПРАВИЛА:
1) Исправляй ТОЛЬКО очевидные ошибки распознавания (когда слово фонетически похоже на правильное).
2) НЕ МЕНЯЙ СЛОВА ЛЕКТОРА. Каждое слово лектора имеет значение.
3) НЕ удаляй "Вот", "Значит", "Ну", "Так" — это слова лектора.
4) НЕ перефразируй, НЕ переставляй слова, НЕ сокращай.
5) НЕ добавляй новые слова.
6) Сохрани пунктуацию, абзацы, имена собственные.

ИЗВЕСТНЫЕ ОШИБКИ В ТАКИХ ТЕКСТАХ (физика, моделирование, BA):
- "имперический" → "эмпирический"
- "фактальной" → "фрактальной"  
- "сниженка Коха" → "снежинка Коха"
- "свепроводящих" → "сверхпроводящих"
- "адронных" (если речь о коллайдере) → "адронных" (это правильно)
- "явленные требования" → возможно "заявленные требования" (если контекст подходит)
- имена собственные: проверь правильность написания

ПРАВИЛА ДЛЯ ИМЕНИ "ОМ" (учёный Георг Симон Ом):
- В первом упоминании в тексте: "Георг Симон Ом" (полное имя).
- В остальных: только фамилия "Ом" с правильным склонением по падежам.

ТЕКСТ:
{text}

ИСПРАВЛЕННЫЙ ТЕКСТ:"""


def call_llm(prompt_template: str, text: str) -> str:
    full_prompt = prompt_template.format(text=text)
    result = subprocess.run(
        ["hermes", "-z", full_prompt],
        capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        print(f"  LLM error: {result.stderr[:200]}", file=sys.stderr)
        return ""
    out = result.stdout.strip()
    if out.startswith("```"):
        out = re.sub(r"^```\w*\n?", "", out)
        out = re.sub(r"\n?```$", "", out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input MD file (from stitch_v3.py)")
    parser.add_argument("output_base", help="Output base path (creates _pass_1_punct.md, _pass_2_asr.md, _final.md)")
    parser.add_argument("--passes", default="1,2", help="Which passes to run (default: 1,2)")
    parser.add_argument("--start-from", type=int, default=1, help="Resume from pass N")
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

    current_text = text
    if args.start_from > 1:
        prev = out_base.with_name(out_base.name + f"_pass_{args.start_from - 1}.md")
        if prev.exists():
            current_text = prev.read_text(encoding="utf-8")
            print(f"Resuming from pass {args.start_from}: {len(current_text.split())} words")

    if 1 in pass_nums and args.start_from <= 1:
        print(f"\n=== Pass 1: Punctuation ===")
        print(f"Input: {len(current_text.split())} words")
        result = call_llm(PUNCTUATION_PROMPT, current_text)
        if not result:
            print("  FAIL: empty response, aborting")
            return 1
        out1 = out_base.with_name(out_base.name + "_pass_1_punct.md")
        out1.write_text(result, encoding="utf-8")
        print(f"  Output: {len(result.split())} words -> {out1.name}")
        current_text = result

    if 2 in pass_nums:
        if args.start_from <= 2:
            print(f"\n=== Pass 2: ASR fix ===")
            print(f"Input: {len(current_text.split())} words")
            result = call_llm(ASR_FIX_PROMPT, current_text)
            if not result:
                print("  FAIL: empty response, aborting")
                return 1
            out2 = out_base.with_name(out_base.name + "_pass_2_asr.md")
            out2.write_text(result, encoding="utf-8")
            print(f"  Output: {len(result.split())} words -> {out2.name}")
            current_text = result

    # Final
    final_file = out_base.with_name(out_base.name + "_final.md")
    final_file.write_text(current_text, encoding="utf-8")
    print(f"\n=== Final: {final_file} ({len(current_text.split())} words) ===")

    return 0


if __name__ == "__main__":
    sys.exit(main())