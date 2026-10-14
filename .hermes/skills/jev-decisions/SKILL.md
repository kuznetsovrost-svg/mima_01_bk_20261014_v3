---
name: typesafe-ai
description: >
  Build AI-powered software with TypeSafe JEV (System One model): structured decisions with calibrated probabilities.
  Use when a feature needs programmable common sense (routing, ranking, classification, extraction, verification),
  or when an LLM prompt-and-parse step could become a structured decision.
  JEV returns typed answers (Choice / Score / Noul) not free-form text, and runs ~200ms at $0.042/1M input tokens.
version: 1.0.0
author: Hermes Agent (adapted from official typesafe-ai/skills)
license: MIT
metadata:
  hermes:
    tags: [ai, decisions, classification, routing, scoring, jev, typesafe]
    related_skills: [audio-transcription, transcription-postprocess]
---

# Build with TypeSafe (JEV)

TypeSafe provides units of AI intelligence usable like programming primitives: small judgments you can compose into larger capabilities. **JEV** is TypeSafe's flagship System One model. It understands natural language and returns **typed answers and probabilities** rather than generating text or reasoning explanations.

**Key properties**:
- 3 primitives: **Choice** (one of set), **Score** (degree along dimension), **Noul** (yes/no probability)
- ~200 ms latency
- $0.042 / 1M input tokens (output free)
- Cannot generate text — only choose from your options

## When to Use This Skill

**Use JEV when**:
- You need a **structured decision** with calibrated probability
- The answer is one of a defined set, a degree, or yes/no
- You have a clear state and well-defined criteria
- An LLM step could be replaced with a typed judgment

**Don't use for**:
- Free-form text generation (use LLM)
- Code generation, debugging (use LLM with reasoning)
- Long explanations (use LLM)
- Open-ended questions without defined options

## Quick Start

```python
from jev_client import jev_decide, jev_choice, jev_score, jev_noul

# Single Choice
chosen, prob = jev_choice(
    state="Запрос пользователя: найди мне информацию о BPMN",
    options={
        "code": "кодинг, скрипты",
        "research": "research, поиск",
        "chat": "болтовня",
    }
)

# Single Score
score, confidence = jev_score(
    state="Текст после LLM-обработки",
    scale=["unreadable", "poor", "ok", "good", "excellent"]
)

# Single Noul
prob = jev_noul(
    state="Запрос: пришли мне отчёт",
    statement="Это спам или реклама?"
)

# Multiple questions in parallel (recommended)
result = jev_decide(
    state={
        "file": {"name": "lecture.mp3", "size_kb": 1200},
        "audio": {"duration_sec": 3600, "bitrate": 128000},
    },
    questions={
        "has_speech": {"type": "noul", "instructions": "Contains speech?"},
        "language": {"type": "choice", "criteria": {"ru": "Russian", "en": "English"}},
        "quality": {"type": "score", "criteria": ["bad", "ok", "good"]},
    },
)
```

## The 3 Primitives

| Need | Primitive | When |
|---|---|---|
| One of defined set | **Choice** | "Which category?", "What type?", "Which option?" |
| Degree on described scale | **Score** | "How urgent?", "Quality 1-5", "Similarity 0-4" |
| Whether condition holds | **Noul** | "Is this spam?", "Duplicate?", "Need escalation?" |

See `references/primitives.md` for detailed usage.

## Design Principles (from official docs)

### 1. Use Structured State (JSON, not text)

**Bad**:
```python
state=f"File: {filename}\nDuration: {duration}\nContent: {text}"
```

**Good**:
```python
state={
    "file": {"name": filename, "size_kb": 1200},
    "audio": {"duration_sec": duration, "bitrate": 128000},
    "content": text[:2000],
}
```

Reference nested fields with backticks: `ticket.messages[0].text`.

### 2. Ask Independent Questions Together

```python
# GOOD: one JEV call with 4 questions
result = jev_decide(state, questions={
    "topic": {...},
    "depth": {...},
    "quality": {...},
    "needs_enrichment": {...},
})

# BAD: 4 separate JEV calls
topic = jev_decide(state, {"topic": ...})
depth = jev_decide(state, {"depth": ...})
# ...
```

### 3. Confidence ≠ Correctness

> A Noul near 0.5 means similar probability for yes and no, **not medium intensity**.
> Several acceptable alternatives can also spread probability; low confidence need not invalidate a harmless preference choice.

Use confidence to **guide behavior**, not as a quality gate:
- `confidence > 0.7` → trust the answer
- `confidence 0.5-0.7` → use as hint, consider fallback
- `confidence < 0.5` → fallback to LLM or human

### 4. Include "no-match" Outcomes

```python
# GOOD: explicit option for "none of the above"
criteria = {
    "category_a": "...",
    "category_b": "...",
    "category_c": "...",
    "none": "ничего не подходит",
}
```

### 5. Score Levels Must Stand Alone

Each level in a Score scale must describe a concrete situation:

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

## 6 Architectural Patterns (from official docs)

1. **Route and fill known arguments** — select handler + its typed parameters
2. **Select instead of generate** — find candidates in code, JEV selects, code normalizes
3. **Find and judge evidence** — retrieve candidates, rerank with JEV
4. **Composite scoring** — score dimensions once, weights change in code
5. **Verify and escalate** — JEV checks, uncertain → LLM, still uncertain → human
6. **Respond to changing state** — code keeps goals, JEV guides next step

See `references/patterns.md` for detailed examples.

## 3-Layer Routing (recommended)

### Layer 1: Rule-based (instant, free)

```python
JEV_TASK_TYPES = {"classify", "route", "score", "gate", "verify", "deduplicate"}
JEV_KEYWORDS = ["классифицируй", "это спам?", "оцени", "совпадение", "вероятность"]

def should_use_jev(task):
    if task.get("type") in JEV_TASK_TYPES:
        return True
    return any(kw in task.get("description", "").lower() for kw in JEV_KEYWORDS)
```

### Layer 2: LLM-routing (fallback)

```python
def llm_routing(task):
    prompt = f"Задача: {task['description']}\nВыбери ОДНО: jev / llm / terminal / web_search"
    return llm_generate(prompt, max_tokens=10).strip().lower()
```

### Layer 3: Hard binding (for critical)

```yaml
jev_mandatory: [quality_gate, self_audit, tool_injection_check, duplicate_check]
jev_preferred: [classification, tagging, scoring, routing, verification]
llm_only: [playbook_generation, text_generation, code_generation, complex_reasoning]
```

## Cookbook References

For deeper patterns, see the official TypeSafe cookbooks:

| Pattern | Cookbook | When to use |
|---|---|---|
| Function calling | [function_calling.md](https://docs.typesafe.ai/cookbooks/function_calling.md) | Routing with typed parameters |
| Speculative fan-out | [fan-out.md](https://docs.typesafe.ai/patterns/fan-out.md) | Multiple parallel judgments |
| Value extraction | [pre_parsed_value_extraction_cookbook.md](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook.md) | Find values in code, JEV selects |
| Structure recovery | [autoformat.md](https://docs.typesafe.ai/cookbooks/autoformat.md) | Parse unstructured to structured |
| Reranking | [rerank_typesafe.md](https://docs.typesafe.ai/cookbooks/rerank_typesafe.md) | Search results ranking |
| Hierarchical classification | [hierarchical_classification.md](https://docs.typesafe.ai/cookbooks/hierarchical_classification.md) | Multi-level categorization |
| Composite scoring | [composite-scoring.md](https://docs.typesafe.ai/patterns/composite-scoring.md) | Weighted multi-dimension scoring |
| Feature discovery | [autoresearch_feature_discovery.md](https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery.md) | JEV judgments → ML features |
| Citation checks | [citation_check.md](https://docs.typesafe.ai/cookbooks/citation_check.md) | Verify claims against sources |
| Extraction cascades | [sde_cascade.md](https://docs.typesafe.ai/cookbooks/sde_cascade.md) | Fallback JEV → LLM → human |

## API Quick Reference

```python
POST https://jevtypesafeai.com/api/v1/decide
Authorization: Bearer $TYPESAFE_API_KEY
Content-Type: application/json

{
  "model": "jev-latest",
  "state": {...} or "string",
  "questions": {
    "q_name": {
      "type": "choice" | "score" | "noul",
      "instructions": "What to judge",
      "criteria": {"key": "description"} or ["desc1", "desc2", ...]  // for choice/score
    }
  }
}
```

Response:
```json
{
  "model": "jev-1.13.0",
  "answers": {
    "q_name": {
      "type": "choice",
      "choice": "selected_key",
      "probabilities": {"key1": 0.7, "key2": 0.3},
      "confidence": 0.7
    }
  }
}
```

## Setup

1. Get API key at https://console.typesafe.ai ($5 free credit)
2. Save to `/root/.hermes/.env`: `TYPESAFE_API_KEY=jv_live_...`
3. Use `scripts/jev_client.py` from this skill
4. Test: `python3 scripts/jev_client.py "hello" "test:is this a test?"`

## Files in This Skill

- `scripts/jev_client.py` — Python client (low-level + convenience wrappers)
- `scripts/cache.py` — caching layer for JEV calls
- `scripts/router.py` — 3-layer routing (rule-based + LLM + hard binding)
- `references/primitives.md` — detailed usage of Choice / Score / Noul
- `references/patterns.md` — 6 architectural patterns with code
- `references/pitfalls.md` — common mistakes and how to avoid them
- `templates/state_examples.json` — structured state examples

## Related Skills

- `audio-transcription` — JEV for quality gate, hallucination filter, annotation
- `transcription-postprocess` — LLM-based punctuation (not JEV — needs generation)
- `wiki-enrichment-worker` — JEV for prioritization, deduplication

## See Also

- Official docs: https://docs.typesafe.ai
- Live cookbook index: https://docs.typesafe.ai/llms.txt
- Internal playbook `JEV-Playbook-01` (6 patterns from our discussion)
