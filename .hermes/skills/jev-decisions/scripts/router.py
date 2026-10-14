#!/usr/bin/env python3
"""3-layer routing for JEV vs LLM.

Layer 1: Hard binding (jev_mandatory / llm_only) — instant
Layer 2: Rule-based (keywords, task types) — instant
Layer 3: LLM-routing (fallback) — 1-2 sec, used only if ambiguous
"""
from typing import Literal

# === Hard binding (Layer 1) ===

JEV_MANDATORY = {
    "quality_gate", "self_audit", "tool_injection_check",
    "duplicate_check", "preflight_check", "verification",
}

LLM_ONLY = {
    "playbook_generation", "text_generation", "code_generation",
    "complex_reasoning", "explanation", "summarization",
}

# === Rule-based keywords (Layer 2) ===

JEV_TASK_TYPES = {
    "classify", "categorize", "route", "score", "rank",
    "gate", "verify", "validate", "deduplicate", "tag",
    "label", "detect", "filter", "select",
}

JEV_KEYWORDS = [
    # Russian
    "классифицируй", "определи тип", "это спам", "какая категория",
    "оцени качество", "совпадение", "есть ли", "вероятность",
    "приоритет", "совпадают ли", "релевантно ли", "нужно ли",
    "похоже ли", "дубликат", "совместимо", "соответствует",
    # English
    "classify", "is this", "what type", "category", "score",
    "probability", "duplicate", "match", "relevant",
]

# === Router ===

Tool = Literal["jev", "llm", "terminal", "web_search"]


def should_use_jev(task: dict) -> bool:
    """Rule-based fast routing. Returns True if JEV is appropriate.

    Args:
        task: {
            "type": "classify",
            "description": "определи тип требования",
            "requires_jev": True  # explicit override
        }
    """
    # Explicit override
    if task.get("requires_jev"):
        return True

    # By type
    if task.get("type") in JEV_MANDATORY:
        return True
    if task.get("type") in JEV_TASK_TYPES:
        return True

    # By keywords
    desc = task.get("description", "").lower()
    if any(kw in desc for kw in JEV_KEYWORDS):
        return True

    return False


def should_use_llm_only(task: dict) -> bool:
    """Check if task MUST go to LLM (not JEV)."""
    return task.get("type") in LLM_ONLY


def route(task: dict, llm_router=None) -> Tool:
    """Decide which tool to use for a task.

    Args:
        task: Task description dict
        llm_router: Optional callable for LLM-based routing
                    (called only if Layers 1-2 don't decide)

    Returns:
        "jev" | "llm" | "terminal" | "web_search"
    """
    # Layer 1: Hard binding
    if task.get("type") in JEV_MANDATORY:
        return "jev"
    if should_use_llm_only(task):
        return "llm"

    # Layer 2: Rule-based
    if should_use_jev(task):
        return "jev"

    # Layer 3: LLM-routing fallback
    if llm_router:
        return llm_router(task)

    # Default
    return "llm"


# === Test ===

if __name__ == "__main__":
    test_tasks = [
        {"type": "quality_gate", "description": "Check LLM output"},
        {"type": "playbook_generation", "description": "Create a playbook"},
        {"type": "classification", "description": "Classify this requirement"},
        {"type": "unknown", "description": "Is this email spam?"},
        {"type": "unknown", "description": "Classify the document"},
        {"type": "research", "description": "Find recent papers on X"},
    ]

    print("Routing decisions:")
    for t in test_tasks:
        decision = route(t)
        print(f"  {t['type']:30s} | {t['description']:50s} → {decision}")
