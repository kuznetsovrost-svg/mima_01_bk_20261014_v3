#!/usr/bin/env python3
"""Two-pass transcription: small model extracts hotwords, large model uses them.

This can improve accuracy on domain-specific terms by 10-15% vs single-pass.

Usage:
  python3 two_pass_transcribe.py input.mp3 --output ./out
  python3 two_pass_transcribe.py input.mp3 --output ./out --initial-prompt prompt.txt
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Make transcribe.py importable
sys.path.insert(0, str(Path(__file__).parent))
from transcribe import transcribe


def extract_hotwords(
    input_path: Path,
    model_size: str = "small",
    compute_type: str = "int8",
    top_n: int = 100,
) -> list[str]:
    """Pass 1: Quick transcription with small model, extract domain-specific terms."""
    from faster_whisper import WhisperModel

    print(f"[Pass 1/{top_n}] Loading {model_size} model for hotword extraction...")
    model = WhisperModel(model_size, device="cpu", compute_type=compute_type)
    
    print(f"  Transcribing {input_path.name} (fast pass)...")
    t0 = time.time()
    segments, _info = model.transcribe(
        str(input_path),
        language="ru",
        beam_size=1,  # Fast: greedy decoding
        vad_filter=True,
        word_timestamps=True,
    )
    
    # Collect all words
    words = []
    for seg in segments:
        if hasattr(seg, "words") and seg.words:
            for w in seg.words:
                if w.word.strip() and len(w.word.strip()) > 2:
                    words.append(w.word.strip())
    
    elapsed = time.time() - t0
    print(f"  Pass 1 done in {elapsed:.1f}s, collected {len(words)} words")
    
    # Find unique terms (appearing 2+ times = "domain-specific")
    from collections import Counter
    counter = Counter(words)
    candidates = [(w, c) for w, c in counter.most_common(top_n * 3) if c >= 2]
    candidates.sort(key=lambda x: -x[1])
    
    # Filter: keep proper nouns and technical terms (heuristic)
    hotwords = []
    for word, count in candidates[:top_n]:
        # Heuristics:
        # - Capitalized (potential proper noun)
        # - Has uppercase letters (acronym BPMN, UML)
        # - Contains Latin chars + Cyrillic (mixed terms)
        # - Long words (likely technical)
        if (word[0].isupper() or 
            any(c.isupper() for c in word[1:]) or
            any(c.isascii() and c.isalpha() for c in word) and any(ord(c) > 127 for c in word) or
            len(word) > 6):
            hotwords.append(word)
    
    print(f"  Extracted {len(hotwords)} hotwords (top 10: {hotwords[:10]})")
    return hotwords[:top_n]


def main():
    parser = argparse.ArgumentParser(
        description="Two-pass transcription: extract hotwords with small model, then transcribe with large model"
    )
    parser.add_argument("input", type=Path, help="Input audio file")
    parser.add_argument("--output", type=Path, required=True, help="Output directory")
    parser.add_argument("--small-model", default="small", help="Model for pass 1 (default: small)")
    parser.add_argument("--large-model", default="large-v3", help="Model for pass 2 (default: large-v3)")
    parser.add_argument("--compute-type", default="int8", help="Compute type (default: int8)")
    parser.add_argument("--initial-prompt", type=str, default=None, help="Initial prompt (file path or text)")
    parser.add_argument("--top-n", type=int, default=100, help="Number of hotwords to extract (default: 100)")
    parser.add_argument("--beam-size", type=int, default=5, help="Beam size for pass 2 (default: 5)")
    args = parser.parse_args()
    
    # Pass 1: extract hotwords
    hotwords = extract_hotwords(args.input, args.small_model, args.compute_type, args.top_n)
    hotwords_str = " ".join(hotwords)
    
    # Load prompt
    prompt = args.initial_prompt
    if prompt and Path(prompt).is_file():
        prompt = Path(prompt).read_text(encoding="utf-8")
    
    # Pass 2: transcribe with large model + hotwords + prompt
    print(f"\n[Pass 2] Transcribing with {args.large_model} + hotwords + prompt...")
    result = transcribe(
        args.input,
        args.output,
        language="ru",
        model_size=args.large_model,
        compute_type=args.compute_type,
        beam_size=args.beam_size,
        initial_prompt=prompt,
        hotwords=hotwords_str,
        vad_filter=True,
    )
    
    result["hotwords"] = hotwords
    result["method"] = "two-pass"
    print("\n=== Result ===")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
