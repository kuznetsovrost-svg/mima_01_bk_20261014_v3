# Entity-state lifecycle pattern (for MCP-exposed entities)

**Date:** 2026-09-02
**Source:** session designing `point_states.py` for `fst-project-health` indicators.

---

## Problem

When an MCP entity has a lifecycle (Point states, Project states, Issue states, etc.), the state field is usually a foreign key to a shared lookup. The same lookup is referenced from multiple entities — but the **canonical list of states differs per entity**. Hardcoding a state list from one entity's perspective will silently include states that don't apply to yours.

User correction (2026-09-02): «Ты не отбираешь состояния, свойственные только КТ. Это нас приведёт к ошибкам!»

---

## Right way to get state list (MCP)

```python
# 1. Find the field that holds state on your entity:
desc = mcp_call(sid, "describe_entity", {"entityName": "Point"})
field_with_state = next(
    f for f, p in desc["properties"].items()
    if p.get("RefPropertyName") in ("ActivityPhase", "State", "Status")
)

# 2. Get the SCOPED state list (only for this entity):
scoped = mcp_call(sid, "describe_entity", {
    "entityName": "Point",                     # THE entity
    "show_allowed_values": [field_with_state], # THE field
})
states = scoped["allowed_values"][field_with_state]
# → [{"value": 10012, "title": "В работе"}, {"value": 10018, "title": "Выполнена"}, ...]

# 3. NEVER use a different entity's state list:
#    PointTemplateActivityPhase = 106 states (mixed entities) — DO NOT USE for Point logic.
```

---

## Right way to model it in code

`scripts/point_states.py` — the canonical pattern. Use `str, Enum` + classification helpers. Single source of truth.

```python
from enum import Enum

class PointState(str, Enum):
    """States scoped to ONE entity (Point)."""
    IN_PROGRESS = "В работе"      # level=0, КТ не выполнена
    COMPLETED   = "Выполнена"     # level=1, факт.дата есть, не согласована
    CONFIRMED   = "Подтверждена"  # level=2, финал
    CANCELLED   = "Отменено"     # level=-1, отменена

    @property
    def level(self) -> int:
        return {
            PointState.IN_PROGRESS: 0,
            PointState.COMPLETED: 1,
            PointState.CONFIRMED: 2,
            PointState.CANCELLED: -1,
        }[self]

    def blocks_stage_transition(self) -> bool:
        """Does this state block transition to next ЖЦ stage?"""
        return self in (PointState.IN_PROGRESS, PointState.COMPLETED)

    @classmethod
    def from_name(cls, name: str) -> "PointState | None":
        """EXACT match only — no fuzzy matching to 'similar' words."""
        if not name:
            return None
        name_lower = name.lower().strip()
        for state in cls:
            if state.value.lower() == name_lower:
                return state
        return None

# ID ↔ State mapping (sourced from MCP describe_entity above)
POINT_STATE_IDS: dict[int, PointState] = {
    10012: PointState.IN_PROGRESS,
    10018: PointState.COMPLETED,
    40031: PointState.CANCELLED,
    40041: PointState.CONFIRMED,
}

# Universal classification helpers — no "similar word" matches
def is_confirmed(state: str) -> bool:
    return PointState.from_name(state) == PointState.CONFIRMED

def is_initial(state: str) -> bool:
    return PointState.from_name(state) == PointState.IN_PROGRESS
```

---

## Discipline: how to avoid the "similar word" trap

When implementing classifier functions, **never** write:
```python
# ❌ BAD — fuzzy match invites bugs
return state.lower() in ("выполнено", "выполнена", "выполнен", "согласован", "согласовано")
```

Always write:
```python
# ✅ GOOD — exact match via enum
return PointState.from_name(state) == PointState.COMPLETED
```

Same discipline for constants:
```python
# ❌ BAD
POINT_STATE_FINAL = "Подтверждена"  # could be re-typed wrong elsewhere

# ✅ GOOD
POINT_STATE_FINAL = PointState.CONFIRMED.value  # single source of truth
```

---

## When to use this pattern

Any time you have an entity with a state machine that:
- Is referenced from multiple entities (sharing the same lookup)
- Has subtle distinctions (e.g. "Confirmed" vs "Completed" are different lifecycle steps)
- Affects business logic (block transitions, affect verdicts, etc.)

Examples in PMForesight:
- `Point.ActivityPhaseId` → 4 states (this pattern)
- `Project.ActivityPhaseId` → 6 stages of ЖЦ
- `InContract.StateId` → contract lifecycle
