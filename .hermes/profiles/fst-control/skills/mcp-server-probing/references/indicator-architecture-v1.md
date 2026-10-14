# Indicator architecture (v1.0.0 «Показатели проекта»)

**Date:** 2026-09-02
**Source:** session building секции «Показатели проекта» в `fst-project-health`.

---

## Pattern: 16-indicator section with shared scaffold

When a report section has many similar indicators (e.g. 16 health-checks), structure as:

```
scripts/
├── project_indicators.py        # the orchestrator + each `check_XXX(project, sid)`
├── <thing>_registry.py          # reference data (mandatory КТ per stage, etc.)
├── <thing>_thresholds.py        # numeric thresholds + interpret_indicator()
└── point_states.py              # state enum (Pitfall #23)
```

**Each `check_XXX()` returns `IndicatorResult`:**

```python
@dataclass
class IndicatorResult:
    number: int                    # 6.1, 6.2, ..., 6.16
    name: str                      # human-readable
    result: str                    # "Да Инициирование" / "Нет" / "Вопросы, 80 ч"
    detail: str                    # optional human note
    verdict: str                   # "Норма" / "Информационное" / "Существенное" / "Критическое"
    table: Optional[list]          # nested table rows (each row is dict)
    table_title: Optional[str]     # caption for the nested table
```

**Section verdict = max severity across rows** (critical > substantial > informational > normal).

---

## Pattern: pair-of-indicators differs in one parameter

(See Pitfall #26 in main SKILL.md.)

Pairs in v1.0.0:
- **6.3 vs 6.4** — `forecast_hours` vs `plan_hours`
- **6.5 vs 6.7** — this-project vs all-activities

Extract the varying parameter (`hours_field`, `users_filter`) into a helper that both indicators call.

---

## Pattern: thresholds in separate script

For each indicator family, create `<family>_thresholds.py`:

```python
INDICATOR_THRESHOLDS = {
    "6.X_thing": {
        "critical_when": lambda r: r.get("has_critical", False),
        "substantial_when": lambda r: r.get("has_substantial", False),
        "informational_when": lambda r: r.get("has_informational", False),
        "default_verdict": "Норма",
        # ... numeric constants (hours_per_day, threshold levels, etc.)
    },
}

def interpret_indicator(indicator_key: str, result_value: str, detail: str = "") -> str:
    """Pure function — easy to unit-test."""
    ...

# Also a per-classifier helper when severity is a function of a metric:
def classify_overload_percent(percent: float, cfg: dict) -> str:
    """Returns "informational" / "substantial" / "critical" / "normal"."""
    ...
```

**Why separate file:**
- Numeric thresholds get tweaked by user — keep them in one editable place
- Pure functions are easy to unit-test (no MCP dependency)
- Verdict logic stays consistent across indicators in the family

---

## Pattern: step-by-step modeling (user teaches model how to think)

When implementing complex indicators (e.g. 6.2 lifecycle check), don't guess — model step by step with the user:

1. Present the **simplest scenario** (Шаг 1: пустой проект = Норма)
2. Add the next level (Шаг 2: есть КТ, но нет обязательных)
3. Add severity gradient (Шаг 3: просрочка = Критическое, Шаг 4: не подтверждена = Информационное)
4. Handle superposition (Шаг 5: всё вместе)
5. Final case (Шаг 6: всё сделано, но не переведено)

For each step:
- Lock down a precise Russian-language rule
- Translate to code with EXACT match against the enum (Pitfall #23)
- Live-test on real projects
- Move to next

**Anti-pattern:** ask "what should happen?" for all 16 indicators at once → user gives a vague answer → code is ambiguous → 3 correction rounds. Better: one indicator per session, walk through edge cases.

---

## Pattern: severity scheme from раздел 5 (financial КТ deadlines)

Used in 6.8 (соблюдение сроков финансовых КТ):

```python
def classify_financial_overdue(diff_days: int) -> str:
    """Same scheme as раздел 5 «Замечания по срокам»."""
    if diff_days >= 10:
        return "critical"
    elif diff_days >= 2:
        return "substantial"
    elif diff_days >= 1:
        return "informational"
    # diff_days <= 0 = не превышена (forecast в будущем или = today)
    return "normal"
```

User specified 2026-09-02: «Статус замечаний формируется в точности так, как для пункта 1 "Замечания по срокам"».

---

## Pattern: detect project-type guard (6.8)

Some indicators only apply to specific project types. Check first, return early:

```python
def check_financial_deadlines(project, sid):
    project_type = project.get("ProjectTypeName", "").strip()
    if project_type != "Коммерческий":
        # Прочерк, подкраска нейтральная — дальнейшая проверка не производится
        return IndicatorResult(
            number=8,
            name="...",
            result="—",
            detail="неприменимо для типа проекта «{project_type}»",
            verdict="Норма",
        )
    # ... actual check ...
```

User specified 2026-09-02: «Данная проверка выполняется только для проектов, у которых в поле "Тип проекта" стоит значение "Коммерческий". Для иных — прочерк и дальнейшая проверка не производится.»

**Trap:** the field value comes with a TRAILING SPACE ("Коммерческий ") — must `.strip()` before comparing.

---

## Pattern: union-overlap of forecasts vs plans (for 6.7)

When computing «перегрузка по всем активностям»:
1. First fetch the **user list** from the current project (filtered by ProjectId)
2. Then fetch ALL rows WITHOUT filter (all activities)
3. Filter the all-rows to those whose `username` is in the user list
4. Aggregate per (user, month)

This way the user's plan is the denominator (heavier work), but only users from the current project are reported (else the report would be flooded with every employee in the org).

User specified 2026-09-02: «Использовать ProjectResourcePlan без фильтра по проекту. При этом нужно учитывать, что данные по некоторым проектам могут быть недоступны — ВАЖНО зафиксировать в описании.»

---

## Pattern: skip roles (username == specialization) in overload checks

When checking per-employee overload (6.5, 6.7), skip rows where `username == specialization`:

```python
if username == specialization:
    continue  # ролевой ресурс, не ФИО — учитываем в 6.6
```

`username == specialization` is the only signal we have that this row is a "role" not a person (Pitfall #23 source).

---

## Pattern: format note "Да, NNN ч" / "Вопросы, NNN ч"

User specified 2026-09-02:
- `"Да, 168 ч"` (full coverage)
- `"Вопросы, 80 ч"` (partial)
- `"Нет"` (none)

**Comma AFTER the keyword** (not space). Russian-language formats like `"Да 168 ч"` (no comma) are WRONG.

**No comma** when there's no number ("Нет", "Да Пресейл", "—").

---

## Pattern: row formatting with severity-color hint

Each row in the nested table should carry `severity` (informational/substantial/critical) so the renderer can color the row:

```python
table.append({
    "n": n,
    "period": "Октябрь-2026",
    "remark": "Трудозатраты не заданы",
    "severity": "critical",  # renderer applies .row-critical background
})
```

CSS class scheme (target `tr[data-status="critical|substantial|informational|normal"]`):
- `critical` → `#fee2e2` (red)
- `substantial` → `#fef3c7` (yellow)
- `informational` → `#dbeafe` (blue)
- `normal` → `#ffffff`

---

## Pattern: row merging for combined issues (6.3 / 6.4)

When the same month has both:
- "Трудозатраты не заданы" (no plan/forecast)
- "Не учтены трудозатраты РП" (no PM entry)

Merge into ONE row with comma-joined note:
```
"Трудозатраты не заданы, Не учтены трудозатраты РП"
```

**Severity = max** of the two — red (no plan) wins over yellow (only PM missing).

User specified 2026-09-02: «В том случае, если по другим критериям для строки был назначен статус "Красная", этот статус не меняется. Если строка только про РП — "Жёлтая".»

---

## Summary: checklist for new indicator

1. ☐ Get number + name + (optional) table structure from user
2. ☐ Get criteria as Russian prose (one scenario per "if")
3. ☐ Live-probe MCP for needed fields, verify the data exists
4. ☐ Add `interpret_indicator()` + numeric thresholds to `<family>_thresholds.py`
5. ☐ Implement `check_XXX()` returning `IndicatorResult`
6. ☐ Register in `INDICATORS` list (positional — preserves 6.N numbering)
7. ☐ Run unit tests
8. ☐ Live-test on 4 real projects — print verdict, table rows, severity counts
9. ☐ Update `references/project-indicators-spec.md` with status ✅