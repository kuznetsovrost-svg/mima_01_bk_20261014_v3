#!/usr/bin/env python3
"""JEV cache layer.

Hashes (state, questions) and stores responses on disk.
Returns cached response if available, otherwise calls API.
"""
import json
import hashlib
import time
from pathlib import Path

CACHE_DIR = Path("~/.cache/hermes/jev_cache").expanduser()


def _key(state, questions) -> str:
    """Generate SHA-256 key from state + questions."""
    content = json.dumps(
        {"state": str(state), "questions": questions},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(content.encode()).hexdigest()


def _path(key: str) -> Path:
    """Get cache file path for a key."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{key}.json"


def get(state, questions, max_age_days: int = 7) -> dict | None:
    """Get cached response if exists and not expired."""
    key = _key(state, questions)
    path = _path(key)
    if not path.exists():
        return None

    # Check age
    mtime = path.stat().st_mtime
    age_days = (time.time() - mtime) / 86400
    if age_days > max_age_days:
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def put(state, questions, response: dict) -> None:
    """Store response in cache."""
    key = _key(state, questions)
    path = _path(key)
    path.write_text(
        json.dumps(response, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def clear() -> int:
    """Clear all cached responses. Returns count deleted."""
    if not CACHE_DIR.exists():
        return 0
    count = 0
    for f in CACHE_DIR.iterdir():
        if f.is_file() and f.suffix == ".json":
            f.unlink()
            count += 1
    return count


def stats() -> dict:
    """Cache statistics."""
    if not CACHE_DIR.exists():
        return {"count": 0, "size_mb": 0}
    files = list(CACHE_DIR.glob("*.json"))
    total_size = sum(f.stat().st_size for f in files)
    return {
        "count": len(files),
        "size_mb": round(total_size / (1024 * 1024), 2),
    }
