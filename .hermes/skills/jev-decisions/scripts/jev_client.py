#!/usr/bin/env python3
"""TypeSafe JEV (System One) API client.

Provides low-level access and convenient wrappers for Choice / Score / Noul.
https://docs.typesafe.ai

Usage:
    from jev_client import jev_decide, jev_choice, jev_score, jev_noul

    result = jev_decide(state="...", questions={...})
    chosen, prob = jev_choice(state="...", options={...})
    score, conf = jev_score(state="...", scale=[...])
    prob = jev_noul(state="...", statement="...")
"""
import os
import json
import hashlib
import requests
from typing import Any
from pathlib import Path

# Auto-load TYPESAFE_API_KEY from /root/.hermes/.env if not in environment
def _load_env():
    """Load TYPESAFE_API_KEY from Hermes .env if not already set."""
    if os.environ.get("TYPESAFE_API_KEY"):
        return
    env_path = Path("/root/.hermes/.env")
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text(encoding="utf-8", errors="ignore").split("\n"):
            line = line.strip()
            if line.startswith("TYPESAFE_API_KEY=") and not line.startswith("#"):
                value = line.split("=", 1)[1].strip()
                if value and "your_" not in value.lower():
                    os.environ["TYPESAFE_API_KEY"] = value
                    return
    except Exception:
        pass

_load_env()

API_URL = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"
TIMEOUT = 30
CACHE_FILE = Path("~/.cache/hermes/jev_cache.json").expanduser()


# === Low-level API call ===

def _cache_key(state: Any, questions: dict) -> str:
    """Generate cache key from state + questions."""
    content = json.dumps(
        {"state": str(state), "questions": questions},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.md5(content.encode()).hexdigest()


def _load_cache() -> dict:
    """Load JEV cache from disk."""
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    """Save JEV cache to disk."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def jev_decide(
    state: str | dict,
    questions: dict,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
    timeout: int = TIMEOUT,
    use_cache: bool = True,
) -> dict:
    """Call JEV API with one or more questions.

    Args:
        state: Text or structured dict to evaluate.
               Prefer JSON for multi-part context.
        questions: Dict of {name: question_spec}.
                   Each spec: {"type": "choice"|"score"|"noul",
                               "instructions": "...",
                               "criteria": {...} or [...]}
        api_key: Bearer key. Defaults to $TYPESAFE_API_KEY env var.
        model: JEV model (default: jev-latest).
        timeout: Request timeout in seconds.
        use_cache: Whether to use local file cache.

    Returns:
        {
          "model": "jev-1.13.0",
          "answers": {
            "q_name": {
              "type": "choice",
              "choice": "selected_key",
              "probabilities": {...},
              "confidence": 0.85
            }
          },
          "usage": {...}  // if returned
        }

    Raises:
        ValueError: If api_key is not set.
        requests.HTTPError: On API error.
    """
    # Cache check
    if use_cache:
        cache = _load_cache()
        key = _cache_key(state, questions)
        if key in cache:
            return cache[key]

    # Resolve API key
    api_key = api_key or os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        raise ValueError(
            "TYPESAFE_API_KEY not set. "
            "Get one at https://console.typesafe.ai and add to ~/.hermes/.env"
        )

    # API call
    payload = {
        "model": model,
        "state": state,
        "questions": questions,
    }
    resp = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    result = resp.json()

    # Cache save
    if use_cache:
        cache[key] = result
        _save_cache(cache)

    return result


# === Convenience wrappers ===

def jev_choice(
    state: str | dict,
    options: dict[str, str],
    instructions: str = "Pick the best option",
    **kwargs,
) -> tuple[str, float]:
    """Single Choice question. Returns (chosen_key, probability)."""
    result = jev_decide(
        state,
        {
            "choice": {
                "type": "choice",
                "instructions": instructions,
                "criteria": options,
            }
        },
        **kwargs,
    )
    ans = result["answers"]["choice"]
    return ans["choice"], ans["probabilities"][ans["choice"]]


def jev_score(
    state: str | dict,
    scale: list[str],
    instructions: str = "Score this",
    **kwargs,
) -> tuple[int, float]:
    """Single Score question. Returns (score_index, confidence).

    scale is ordered list of descriptions, lowest to highest.
    """
    result = jev_decide(
        state,
        {
            "score": {
                "type": "score",
                "instructions": instructions,
                "criteria": scale,
            }
        },
        **kwargs,
    )
    ans = result["answers"]["score"]
    return int(ans["score"]), ans["confidence"]


def jev_noul(
    state: str | dict,
    statement: str,
    **kwargs,
) -> float:
    """Single Noul question. Returns probability (0-1) that statement is true.

    Note: Noul near 0.5 means similar probability for yes and no,
    NOT medium intensity. Use as guidance, not as confidence.
    """
    result = jev_decide(
        state,
        {
            "noul": {
                "type": "noul",
                "instructions": statement,
            }
        },
        **kwargs,
    )
    return result["answers"]["noul"]["noul"]


# === CLI ===

def _cli():
    import argparse
    parser = argparse.ArgumentParser(description="JEV CLI")
    parser.add_argument("state", help="State to evaluate")
    parser.add_argument("questions", help="JSON string of questions")
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()

    questions = json.loads(args.questions)
    result = jev_decide(args.state, questions, use_cache=not args.no_cache)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _cli()
