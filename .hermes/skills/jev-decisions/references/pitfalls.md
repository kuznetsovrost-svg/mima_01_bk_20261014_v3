# JEV Pitfalls and How to Avoid Them

Common mistakes when using TypeSafe JEV. From official docs + our practice.

## 1. Treating Noul=0.5 as "medium confidence"

**Wrong**:
```python
noul = jev_noul(state, "Is this important?")
if noul > 0.5:
    # "medium importance" — wrong!
    ...
```

**Right**:
```python
noul = jev_noul(state, "Is this important?")
# 0.5 means "similar probability for yes and no" — REAL UNCERTAINTY
if noul > 0.7:
    handle_as_important()
elif noul < 0.3:
    handle_as_unimportant()
else:
    escalate_to_llm_or_human()  # 0.3-0.7 is uncertain zone
```

**Why**: From official docs — "A Noul near 0.5 means similar probability for yes and no, not medium intensity."

## 2. Vague criteria in Choice/Score

**Wrong**:
```python
criteria = {
    "good": "good",
    "bad": "bad",
}
```

**Right**:
```python
criteria = {
    "excellent": "полностью покрывает, качественно, с примерами",
    "good": "в целом покрывает, понятно, без грубых ошибок",
    "partial": "покрывает частично, есть пробелы",
    "missing": "не покрывает тему",
    "incorrect": "ошибки или неверная информация",
}
```

**Why**: JEV needs to distinguish between options. If criteria are similar, probabilities spread and confidence drops.

## 3. Score levels don't stand alone

**Wrong**:
```python
scale = ["low", "medium", "high", "critical"]
# What does "medium" mean? Depends on context.
```

**Right**:
```python
scale = [
    "0: routine — can wait, no impact",
    "1: today — needs attention today",
    "2: urgent — needs immediate action",
    "3: critical — system down, escalate now",
]
```

**Why**: From official docs — "Score levels must describe concrete situations and stand on their own."

## 4. Asking multiple JEV calls when one would do

**Wrong** (4x latency, 4x cost):
```python
topic = jev_choice(text, options=TOPICS)
type_ = jev_choice(text, options=TYPES)
depth = jev_score(text, scale=DEPTH)
quality = jev_score(text, scale=QUALITY)
```

**Right** (parallel within one call):
```python
result = jev_decide(text, questions={
    "topic": {"type": "choice", "criteria": TOPICS},
    "type": {"type": "choice", "criteria": TYPES},
    "depth": {"type": "score", "criteria": DEPTH},
    "quality": {"type": "score", "criteria": QUALITY},
})
```

**Why**: JEV runs questions in parallel within one request. They cannot see each other's answers, but it's faster and cheaper.

## 5. Forgetting "no-match" option

**Wrong**:
```python
# What if it's none of these?
criteria = {
    "spa": "spa center",
    "restaurant": "restaurant",
    "hotel": "hotel",
}
```

**Right**:
```python
criteria = {
    "spa": "spa center",
    "restaurant": "restaurant",
    "hotel": "hotel",
    "other": "другое, не относится к этим категориям",
}
```

**Why**: From official docs — "Include a no-match outcome when nothing may fit."

## 6. Using JEV where LLM is needed

**Wrong** (JEV can't generate text):
```python
result = jev_decide(
    state=text,
    questions={"rewrite": {"type": "choice", "criteria": {"better": "..."}}}
)
```

**Right**:
```python
classification = jev_decide(text, questions={"quality": {...}})  # what is it
rewrite = llm_generate(f"Перепиши: {text}")  # generate new text
```

**Why**: JEV only chooses from your options. For text generation, use LLM.

## 7. Using JEV where rule-based works

**Wrong** (JEV is overkill for regex):
```python
if jev_noul(email, "Is this a valid email?") > 0.5:
    accept()
```

**Right** (rule-based, instant, free):
```python
import re
if re.match(r"^[\w.-]+@[\w.-]+\.\w+$", email):
    accept()
```

**Why**: JEV costs $0.00001 and takes 200ms. Regex is free and instant. Use JEV when semantic understanding is required.

## 8. Ignoring confidence

**Wrong**:
```python
result = jev_decide(state, questions)
answer = result["answers"]["topic"]["choice"]  # ignore confidence
```

**Right**:
```python
result = jev_decide(state, questions)
ans = result["answers"]["topic"]
if ans["confidence"] < 0.6:
    # Fallback: LLM
    answer = llm_generate(f"Определи тему: {state}")
else:
    answer = ans["choice"]
```

## 9. Calling JEV without caching

**Wrong** (re-calls same thing):
```python
for item in items:
    result = jev_decide(item, questions)  # cache miss every time
```

**Right** (cache by hash):
```python
# jev_client.py uses internal cache by default
for item in items:
    result = jev_decide(item, questions, use_cache=True)
```

## 10. State too long

**Wrong** (sending 50K char text):
```python
state = full_textbook_chapter  # 50K chars
```

**Right** (use structured state + chunking):
```python
state = {
    "chapter": "BPMN Gateways",
    "key_points": extract_key_points(text),  # short summary
    "examples": text[:1000],  # first 1K
}
```

**Why**: Each JEV call has a token cost and latency. Keep state focused.

## 11. Dependent questions in one call

**Wrong** (questions need each other's answers):
```python
# ❌ second question depends on first
result = jev_decide(state, questions={
    "is_food": {"type": "noul", ...},  # first
    "is_vegetarian": {"type": "noul", ...},  # depends on is_food
})
```

**Right** (sequential calls when truly dependent):
```python
is_food = jev_decide(state, {"is_food": {"type": "noul", ...}})
if is_food["answers"]["is_food"]["noul"] > 0.5:
    result = jev_decide(state, {"is_vegetarian": {"type": "noul", ...}})
```

**Why**: From official docs — "A second request is warranted when an earlier answer is needed to fetch evidence, construct new state, or determine the next options."

## 12. Not validating in target domain

**Wrong** (assume JEV works out of the box):
```python
# Deploy JEV-based classifier without testing
classifier = JEVClassifier()
classifier.run_on_production_data()
```

**Right** (validate accuracy first):
```python
# Calibrate on 20-30 examples with ground truth
calibration_set = load_ground_truth()  # 20-30 items
accuracy = measure_accuracy(calibration_set)
if accuracy < 0.85:
    adjust_criteria_or_prompts()
# Then deploy
```

**Why**: From official docs — "validate their performance in the target domain."

## 13. API key in client-side code

**Wrong**:
```python
api_key = "jv_live_abc123..."  # exposed in code
```

**Right**:
```python
api_key = os.environ.get("TYPESAFE_API_KEY")  # from .env
```

**Why**: From official docs — "Keep API credentials server-side in web apps."
