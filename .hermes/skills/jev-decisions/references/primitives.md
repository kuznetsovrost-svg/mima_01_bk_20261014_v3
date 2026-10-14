# TypeSafe JEV: 3 Primitives (Choice / Score / Noul)

Reference based on official TypeSafe docs: https://docs.typesafe.ai/primitives/

## Choice — One of a defined set

**When**: "Which category?", "What type?", "Which option?"

```python
result = jev_decide(
    state="Запрос пользователя: найди мне информацию о BPMN",
    questions={
        "type": {
            "type": "choice",
            "instructions": "What type of request is this?",
            "criteria": {
                "code": "кодинг, скрипты, отладка",
                "research": "research, поиск информации",
                "chat": "болтовня, приветствие",
                "command": "прямая команда системе",
            }
        }
    }
)
# Response:
# {
#   "answers": {
#     "type": {
#       "choice": "research",
#       "probabilities": {"code": 0.05, "research": 0.85, "chat": 0.05, "command": 0.05},
#       "confidence": 0.85
#     }
#   }
# }
```

### Important notes

- **Picks one option** from your defined set
- **`probabilities`** compare competing options
- **`confidence`** summarizes distribution concentration
- **Always include "none"** if nothing may fit:
  ```python
  criteria = {"a": "...", "b": "...", "none": "ничего не подходит"}
  ```
- **Check candidate coverage**: model cannot choose an omitted value

## Score — Degree on described scale

**When**: "How urgent?", "Quality 1-5", "Similarity 0-4"

```python
result = jev_decide(
    state="Текст после LLM-обработки: ...",
    questions={
        "readability": {
            "type": "score",
            "instructions": "How readable is this text?",
            "criteria": [
                "0: useless — нечитаемо",
                "1: poor — много мусора",
                "2: ok — есть проблемы",
                "3: good — читается",
                "4: excellent — отлично",
            ]
        }
    }
)
# Response:
# {
#   "answers": {
#     "readability": {
#       "score": 3.5,  # can be fractional (probability-weighted)
#       "confidence": 0.7,
#       "probabilities": {"0": 0.0, "1": 0.05, "2": 0.15, "3": 0.6, "4": 0.2}
#     }
#   }
# }
```

### Important notes

- **Ordered levels** (lowest to highest)
- **Probability-weighted position** — score can be fractional (e.g. 2.7)
- **Each level must stand alone** — describe concrete situation
- **Use comparable per-item Scores** for graded ranking
- Levels should describe **observable reality**, not abstract values

### Bad vs Good example

```python
# BAD: vague
scale = ["bad", "ok", "good"]

# GOOD: descriptive
scale = [
    "0: useless — no useful information",
    "1: poor — confusing structure",
    "2: ok — readable",
    "3: good — clear and complete",
    "4: excellent — actionable and rich",
]
```

## Noul — Whether condition holds

**When**: "Is this spam?", "Duplicate?", "Need escalation?"

```python
result = jev_decide(
    state="Email: 'Купите наш продукт со скидкой 90%! Только сегодня!'",
    questions={
        "is_spam": {
            "type": "noul",
            "instructions": "Is this spam or unsolicited commercial email?",
        }
    }
)
# Response:
# {
#   "answers": {
#     "is_spam": {
#       "noul": 0.92  # probability that statement is true
#     }
#   }
# }
```

### Critical: Noul ≠ Confidence

> A Noul near 0.5 means similar probability for yes and no, **NOT medium intensity**.

- `noul=0.92` → very likely yes
- `noul=0.5` → uncertain, similar probability for yes and no
- `noul=0.1` → very likely no

**Don't interpret 0.5 as "medium confidence"** — it means real uncertainty.

### Use Noul carefully

- **One per label** when several may apply
- **For multi-label classification** (e.g. "is this article about A AND B?"), use multiple Nouls:
  ```python
  questions={
      "is_about_A": {"type": "noul", "instructions": "About topic A?"},
      "is_about_B": {"type": "noul", "instructions": "About topic B?"},
  }
  ```
- **For "any serious violation"** — use separate Nouls, not combined

## Composition: Multiple questions in parallel

**Always prefer multiple questions in one JEV call** vs separate calls:

```python
# GOOD: one call, 4 questions, parallel
result = jev_decide(
    state={"file": "lecture.mp3", "duration_sec": 3600},
    questions={
        "has_speech": {"type": "noul", "instructions": "Contains speech?"},
        "language": {"type": "choice", "criteria": {"ru": "Russian", "en": "English"}},
        "quality": {"type": "score", "criteria": ["bad", "ok", "good"]},
        "action": {"type": "choice", "criteria": {
            "transcribe": "transcribe now",
            "skip": "skip this file",
        }},
    }
)

# BAD: 4 separate calls (4x latency, 4x cost)
has_speech = jev_noul(state, "Contains speech?")
language = jev_choice(state, {"ru": "...", "en": "..."})
quality = jev_score(state, ["bad", "ok", "good"])
action = jev_choice(state, {"transcribe": "...", "skip": "..."})
```

**Why**: JEV runs all questions in parallel within one request. They cannot see each other's answers (independent judgments).

## When questions ARE dependent (rare)

```python
# Step 1: Detect language first
lang_result = jev_decide(state, {
    "language": {"type": "choice", "criteria": {"ru": "...", "en": "..."}}
})
language = lang_result["answers"]["language"]["choice"]

# Step 2: Now make language-specific judgment
if language == "ru":
    result = jev_decide(state, {
        "category": {"type": "choice", "criteria": {...russian...}}
    })
```

This is **2 JEV calls**, not 1. Only do this when second judgment truly needs first.

## Confidence: When to trust

| Confidence | Meaning | Action |
|---|---|---|
| > 0.8 | High concentration | Trust the answer |
| 0.5-0.8 | Moderate | Use as hint, consider fallback |
| < 0.5 | Spread | Fallback to LLM or human |

**But**: low confidence need not invalidate a harmless preference. Several acceptable alternatives can also spread probability. Ignore uncertainty on unused branches.

## Structured state (best practice)

Prefer JSON over text for multi-part context:

```python
# GOOD
state = {
    "file": {"name": filename, "size_kb": 1200},
    "audio": {"duration_sec": duration, "bitrate": 128000},
    "content": text[:2000],
}

# Reference nested fields in instructions:
# "Use `audio.duration_sec` to assess quality"
```

**Why**:
- Easier to maintain
- Referenceable in instructions
- Type-safe
- Reduces ambiguity
