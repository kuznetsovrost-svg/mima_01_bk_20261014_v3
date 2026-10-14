# 6 Architectural Patterns (TypeSafe Official)

Reference: https://docs.typesafe.ai/cookbooks/

These patterns are **starting points**, not limits. Combine primitives around your goal.

## 1. Route and fill known arguments

A request selects a handler and its typed parameters. Ask useful branch-specific questions up front.

```python
# Routing + filling parameters in one call
result = jev_decide(
    state={"user_message": "пришли мне отчёт по JEV за прошлую неделю"},
    questions={
        # 1. Route
        "route": {
            "type": "choice",
            "instructions": "Which handler?",
            "criteria": {
                "report": "user wants a report",
                "config": "user wants to configure",
                "help": "user wants help",
            }
        },
        # 2. Fill parameters (only relevant if route=report)
        "time_range": {
            "type": "choice",
            "instructions": "Time range?",
            "criteria": {"today": "...", "week": "...", "month": "...", "all": "..."}
        },
        "format": {
            "type": "choice",
            "instructions": "Output format?",
            "criteria": {"pdf": "...", "md": "...", "json": "..."}
        },
    }
)
```

**Cookbook**: [function_calling.md](https://docs.typesafe.ai/cookbooks/function_calling.md), [fan-out.md](https://docs.typesafe.ai/patterns/fan-out.md)

## 2. Select instead of generate

Find candidate values in code, JEV selects the intended one, code normalizes.

```python
# Ingest a TZ with 100 requirements. Code extracts candidates.
requirements_a = [...]  # 100 requirements from reference
requirements_b = [...]  # 100 requirements from new system

# JEV selects which pair to compare deeply (not all 100×100)
# First, code uses embeddings to find top-K candidates
import numpy as np
embeddings_a = [...]  # pre-computed
embeddings_b = [...]

candidates = []
for i, emb_a in enumerate(embeddings_a):
    sims = [cosine_similarity(emb_a, emb_b) for emb_b in embeddings_b]
    top_3 = np.argsort(sims)[-3:]  # top 3 by similarity
    candidates.append({"a": i, "candidates": top_3.tolist()})

# JEV selects best match + score
for cand in candidates:
    result = jev_decide(
        state={
            "req_a": requirements_a[cand["a"]],
            "candidates": [requirements_b[i] for i in cand["candidates"]],
        },
        questions={
            "best_match": {
                "type": "choice",
                "instructions": "Which candidate best matches req_a?",
                "criteria": {str(i): requirements_b[i] for i in cand["candidates"]}
            },
            "match_score": {
                "type": "score",
                "criteria": ["0: no match", "1: weak", "2: medium", "3: strong", "4: identical"]
            },
        }
    )
```

**Cookbook**: [pre_parsed_value_extraction_cookbook.md](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook.md), [autoformat.md](https://docs.typesafe.ai/cookbooks/autoformat.md)

## 3. Find and judge evidence

Retrieve candidates, compare their relevance to a query, select useful context.

```python
# Wiki search: embeddings → top-K → JEV reranking
query = "BPMN parallel gateway"
candidate_pages = vector_search(query, top_k=20)  # fast embedding search

# JEV reranks with semantic understanding
result = jev_decide(
    state={"query": query, "candidates": candidate_pages},
    questions={
        "best_match": {
            "type": "choice",
            "instructions": "Which page best answers the query?",
            "criteria": {f"page_{i}": page["title"] for i, page in enumerate(candidate_pages)}
        },
        "relevance_scores": {
            "type": "score",
            "instructions": "How relevant is each page overall?",
            "criteria": ["0: irrelevant", "1: tangential", "2: related", "3: directly relevant"]
        }
    }
)
```

**Cookbook**: [rerank_typesafe.md](https://docs.typesafe.ai/cookbooks/rerank_typesafe.md), [hierarchical_classification.md](https://docs.typesafe.ai/cookbooks/hierarchical_classification.md)

## 4. Turn judgments into reusable data

Score dimensions once, weights change in code. With labeled outcomes, signals become ML features.

```python
# Score lecture on multiple dimensions
result = jev_decide(
    state=lecture_text,
    questions={
        "depth": {"type": "score", "criteria": ["surface", "shallow", "standard", "deep", "expert"]},
        "clarity": {"type": "score", "criteria": ["confusing", "ok", "clear", "excellent"]},
        "actionability": {"type": "score", "criteria": ["theoretical", "mixed", "practical", "ready-to-use"]},
        "freshness": {"type": "score", "criteria": ["outdated", "old", "current", "cutting-edge"]},
    }
)

# Composite score with adjustable weights
WEIGHTS = {"depth": 0.4, "clarity": 0.3, "actionability": 0.2, "freshness": 0.1}

def composite_score(answers: dict, weights: dict) -> float:
    total = 0
    for dim, weight in weights.items():
        score = answers[dim]["score"]
        max_score = len(answers[dim]["probabilities"]) - 1
        normalized = score / max_score
        total += weight * normalized
    return total

# In future: train local ML on these scores + user feedback
```

**Cookbook**: [composite-scoring.md](https://docs.typesafe.ai/patterns/composite-scoring.md), [autoresearch_feature_discovery.md](https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery.md)

## 5. Verify and escalate

Check specific claims against evidence. Send uncertain or failing cases to LLM or human.

```python
def verify_with_escalation(claim: str, evidence: str) -> dict:
    """JEV verifies, escalates to LLM if uncertain, to human if still uncertain."""
    
    # Layer 1: JEV
    jev_result = jev_decide(
        state={"claim": claim, "evidence": evidence},
        questions={
            "is_supported": {
                "type": "noul",
                "instructions": "Does the evidence support the claim?"
            }
        }
    )
    
    noul = jev_result["answers"]["is_supported"]["noul"]
    
    # Layer 2: If uncertain, escalate to LLM
    if 0.3 < noul < 0.7:
        llm_result = llm_generate(
            f"Claim: {claim}\n\nEvidence: {evidence}\n\n"
            f"Is the claim supported? Answer YES or NO with reasoning."
        )
        return {"layer": "llm", "result": llm_result}
    
    # Layer 3: If JEV is confident
    if noul > 0.8 or noul < 0.2:
        return {"layer": "jev", "noul": noul, "verified": noul > 0.5}
    
    # Layer 4: True uncertainty → human
    return {"layer": "human", "noul": noul, "needs_human": True}
```

**Cookbook**: [citation_check.md](https://docs.typesafe.ai/cookbooks/citation_check.md), [sde_cascade.md](https://docs.typesafe.ai/cookbooks/sde_cascade.md)

## 6. Respond to changing state

Code retains goals and observations while fresh judgments guide next step.

```python
# Long-running lecture processing pipeline
class LecturePipeline:
    def __init__(self, lecture_id: str):
        self.lecture_id = lecture_id
        self.state = "initialized"
        self.observations = {}
    
    def next_step(self) -> str:
        """JEV decides next step based on current state and observations."""
        result = jev_decide(
            state={
                "lecture_id": self.lecture_id,
                "state": self.state,
                "observations": self.observations,
            },
            questions={
                "next_step": {
                    "type": "choice",
                    "instructions": "What should we do next?",
                    "criteria": {
                        "transcribe": "run whisper transcription",
                        "filter": "filter hallucinations",
                        "postprocess": "LLM postprocess",
                        "quality_gate": "JEV quality check",
                        "annotate": "JEV annotation",
                        "save": "save final result",
                        "wait": "wait for human input",
                        "stop": "stop processing",
                    }
                }
            }
        )
        return result["answers"]["next_step"]["choice"]
    
    def run(self):
        while self.state != "done":
            step = self.next_step()
            print(f"Step: {step}")
            
            if step == "transcribe":
                self.observations["text"] = whisper.transcribe(...)
            elif step == "filter":
                self.observations["clean_text"] = filter_hallucinations(...)
            elif step == "postprocess":
                self.observations["final_text"] = llm_postprocess(...)
            elif step == "stop":
                break
            # ... etc
            
            self.state = step
```

**Key idea**: Code owns workflow logic, JEV provides bounded decisions at each step.

## When to combine patterns

| Scenario | Pattern(s) |
|---|---|
| User message → handler | 1 (route and fill) |
| Ingest structured data | 2 (select from candidates) |
| Search/ranking | 3 (rerank) |
| Prioritization queue | 4 (composite scoring) |
| Quality assurance | 5 (verify and escalate) |
| Long-running pipeline | 6 (respond to state) |
| Wiki-building | 2 + 3 + 4 + 5 |
| TZ comparison | 2 + 5 |
| Transcription pipeline | 5 + 6 |
| Memory hygiene | 5 |
| Self-audit | 5 |
