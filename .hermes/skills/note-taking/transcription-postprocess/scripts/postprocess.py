#!/usr/bin/env python3
"""Postprocess a Whisper transcript via LLM (Hermes Agent).

Pipeline:
1. Read <base>_words.json
2. Build text with explicit pause markers [PAUSE X.XX]
3. Send to LLM via terminal (hermes CLI call) with detailed prompt
4. Parse LLM output (punctuated Markdown)
5. Write <base>_postprocess.md

Use when neural punctuation (fullstop) is too noisy.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SENTENCE_PAUSE = 0.7
PARAGRAPH_PAUSE = 2.0

PROMPT = """\
You are a Russian text post-processor for a Whisper transcription of a Russian lecture.
Your task: add punctuation and paragraph breaks to a raw run-on text.

INPUT FORMAT:
- Plain text without punctuation
- Pauses between words are marked as [PAUSE X.XX] where X.XX is duration in seconds

PAUSE RULES:
- pause >= 0.7 sec → end of sentence (use . or ?)
- pause >= 2.0 sec → end of paragraph (blank line)
- pause < 0.7 sec → inside sentence (possibly comma if natural)

ADDITIONAL RULES:
- Capitalize proper names (Денис, Ростислав, Лёша, etc.)
- Don't insert random commas — only where they belong grammatically
- Preserve all words exactly as given — do not paraphrase
- Use ? if the sentence is a question (judge by content, not just intonation)
- Split long sentences at natural pauses even if pause < 0.7 sec
- Don't make sentences longer than ~30 words

OUTPUT FORMAT:
- Plain Markdown text
- Paragraphs separated by a blank line
- No headers, no metadata, no bullet points
- Just the readable transcript

TEXT TO PROCESS:
<<<
{text}
>>>

Output ONLY the punctuated text, nothing else.
"""


def words_to_marked_text(words: list[dict]) -> str:
    """Build text with explicit pause markers between words."""
    parts = []
    for i, w in enumerate(words):
        word = w["word"].strip()
        if not word:
            continue
        parts.append(word)
        # Маркер паузы (после слова)
        if i < len(words) - 1:
            pause = words[i + 1]["start"] - w["end"]
            if pause >= 0.1:  # показываем паузы от 100 мс
                parts.append(f" [PAUSE {pause:.2f}] ")
            else:
                parts.append(" ")
        else:
            parts.append(".")
    return "".join(parts)


def call_hermes_llm(prompt: str, model: str = "MiniMax-M3", timeout: int = 300) -> str:
    """Call Hermes CLI as a one-shot LLM query.

    Uses `hermes -z "<prompt>"` (one-shot mode that prints only the final response).
    """
    cmd = [
        "hermes", "-z", prompt,
        "--model", model,
        "--reasoning", "low",
        "--no-restore-cwd",
        "--cli",
    ]

    env = {
        "HERMES_PROFILE": "default",
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    }
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    if result.returncode != 0:
        print(f"  hermes stderr: {result.stderr[:500]}")
    return result.stdout.strip()


def process_file(input_path: Path, output_dir: Path, model: str = "MiniMax-M3") -> dict:
    """Process one <base>_words.json file via LLM."""
    output_dir.mkdir(parents=True, exist_ok=True)
    base = input_path.stem.replace("_words", "")
    print(f"\n=== Processing {input_path.name} via {model} ===")

    # 1. Load
    data = json.loads(input_path.read_text(encoding="utf-8"))
    words = data.get("words", [])
    if not words:
        print(f"  WARNING: no words")
        return None
    print(f"  Loaded {len(words)} words ({data.get('duration', 0):.1f}s)")

    # 2. Build marked text
    marked_text = words_to_marked_text(words)
    print(f"  Marked text: {len(marked_text)} chars")

    # 3. Build prompt
    prompt = PROMPT.format(text=marked_text)
    print(f"  Prompt size: {len(prompt)} chars")

    # 4. Call LLM
    t0 = time.time()
    print(f"  Calling LLM ({model})...")
    raw_output = call_hermes_llm(prompt, model=model, timeout=300)
    elapsed = time.time() - t0
    print(f"  LLM responded in {elapsed:.1f}s ({len(raw_output)} chars)")

    if not raw_output:
        print(f"  ERROR: empty LLM response")
        return None

    # 5. Strip any markdown fences / explanation LLM might add
    text = raw_output
    # Remove leading "Here is..." preamble
    lines = text.split("\n")
    # Find first line that's actual content (not preamble)
    cleaned = []
    skip_preamble = True
    for line in lines:
        if skip_preamble:
            stripped = line.strip()
            # Skip empty
            if not stripped:
                continue
            # Skip common preamble patterns
            if any(stripped.lower().startswith(p) for p in [
                "here is", "here's", "the punctuated", "punctuated text",
                "output:", "result:", "transcript:", "---",
            ]):
                continue
            # Otherwise this is content
            skip_preamble = False
        cleaned.append(line)
    cleaned_text = "\n".join(cleaned).strip()

    # Strip trailing explanations
    for marker in ["\n\n---\n", "\nExplanation:", "\nNote:", "\n```"]:
        if marker in cleaned_text:
            cleaned_text = cleaned_text.split(marker)[0].strip()

    # 6. Write Markdown
    md_lines = [
        f"# Transcription: {base} (LLM postprocessed)",
        "",
        f"**Word count:** {len(words)}",
        f"**LLM model:** {model}",
        f"**LLM response time:** {elapsed:.1f}s",
        "",
        "---",
        "",
        cleaned_text,
    ]
    md_path = output_dir / f"{base}_postprocess.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"  Wrote {md_path}")

    # 7. Diff
    diff_path = output_dir / f"{base}_diff.md"
    plain_path = input_path.parent / f"{base}_plain.md"
    if plain_path.exists():
        plain_text = plain_path.read_text(encoding="utf-8")
        plain_body = re.split(r'\n---\n', plain_text, maxsplit=1)[-1].strip()
        diff_path.write_text(
            f"# Diff: {base}\n\n"
            f"## BEFORE (plain.md, no punctuation)\n\n{plain_body}\n\n"
            f"## AFTER (LLM postprocess)\n\n{cleaned_text}\n",
            encoding="utf-8",
        )
        print(f"  Wrote {diff_path}")

    return {
        "md": str(md_path),
        "diff": str(diff_path) if diff_path.exists() else None,
        "llm_time": elapsed,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="<base>_words.json file or directory")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch", action="store_true")
    parser.add_argument("--model", default="MiniMax-M3")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: {input_path} not found")
        sys.exit(1)

    files = []
    if args.batch or input_path.is_dir():
        files = sorted(input_path.glob("*_words.json"))
        print(f"Found {len(files)} files in {input_path}")
    else:
        files = [input_path]

    results = []
    for f in files:
        r = process_file(f, args.output, model=args.model)
        if r:
            results.append(r)

    print(f"\n=== Done: {len(results)} files ===")
    for r in results:
        print(f"  {r['md']}")


if __name__ == "__main__":
    main()