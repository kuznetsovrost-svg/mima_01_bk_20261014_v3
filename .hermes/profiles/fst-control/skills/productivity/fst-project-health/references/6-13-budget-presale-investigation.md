# 6.13 — Бюджет проекта/пресейла

## ✅ RESOLVED 2026-09-03

Реализовано через `get_entity_data(Project, data_id)`. См. `references/indicator-6-13-budget.md` для деталей реализации.

## История расследования

| Дата | Статус |
|------|--------|
| 2026-09-02 | ⏸️ BLOCKED: `PresaleLimit`/`PresaleBudgetPercentage` есть в `describe_entity(Project)`, но **не возвращаются ни одним view пресейлов** (`MyPresale`, `AllPresales`, `ActivePresales`, `FreezePresales`, `ProjectParameter`). User: «Пока фиксируй все наши подготовительные рассуждения». |
| 2026-09-03 | ✅ **RESOLVED** через `get_entity_data` (Pitfall #140, #141). Helper `mcp_config.get_project_property()` добавлен. `check_budget_limits()` работает на 4 проектах. |

## Итоговое решение (Pitfall #140)

```python
mcp_call(sid, "get_entity_data", {
    "entityName": "Project",
    "data_id": str(project_id),  # snake_case, string
})
# Возвращает properties.<prop>.value
```

Все нужные поля доступны:
- `ProjectBudgetGrade` (Бюджет проекта)
- `PresaleLimit` (Лимит на пресейл)
- `PresaleBudgetPercentage` (% пресейла)
- `DirectProjectCostsGrade`
- `ProjectLimit`

## Pitfall #141: `data_id` (snake_case, string)

```python
# ✅ Правильно
mcp_call(sid, "get_entity_data", {"entityName": "Project", "data_id": "4595"})

# ❌ Неправильно — "data_id Missing required argument"
mcp_call(sid, "get_entity_data", {"entityName": "Project", "dataId": 4595})
```

## Pitfall #130 (опровергнут)

**Неверная гипотеза:** `DirectProjectCostsGrade` ≈ лимит пресейла.
**Факт:** для 504-595 `DirectProjectCostsGrade = 32М`, а `PresaleLimit = 2.7М` (5% от бюджета) — это **разные** суммы.

`DirectProjectCostsGrade` — это **прямые затраты проекта** (оценочные), а НЕ лимит пресейла.