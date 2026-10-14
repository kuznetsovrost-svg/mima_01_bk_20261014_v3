# 6.13 Бюджет проекта/пресейла — справочные заметки

## Эскиз

Показывать установленный бюджет проекта и лимит пресейла.

**Результат (конкатенированная строка):**
```
{Сумма проекта:N руб./Пресейл:M руб./Лимит %:Y}
```

**Статус строки:** всегда нейтральный.

**Без вложенной таблицы.**

## Поля (live-probe 2026-09-03 в `ProjectParameter`)

| Поле | Что | Пример для 504-595 |
|------|-----|---------------------|
| `ProjectBudgetGrade` | Бюджет проекта (оценка), руб. | 54 000 000 |
| `DirectProjectCostsGrade` | (?) оценка прямых затрат, возможно = "Лимит на пресейл" | 32 000 000 |
| `PresaleLimit` | Лимит на пресейл, руб. (если есть) | None для всех 4 проектов |
| `PresaleBudgetPercentage` | % пресейла от бюджета | None для всех 4 проектов |

## Открытые вопросы

- **Q1 (задан 2026-09-03):** Какое поле использовать как «Лимит на пресейл»? `DirectProjectCostsGrade` или `PresaleLimit`?
- **Q2 (задан 2026-09-03):** `% пресейла от бюджета` = `PresaleBudgetPercentage` (готовое поле) или вычислять как `(лимит_пресейл / бюджет) × 100`?

Ждём ответ пользователя.

## Текущий статус

⏳ Эскиз получен, реализация отложена до уточнения Q1 и Q2.

## Заготовка кода

```python
def check_budget_limits(project: dict, sid) -> IndicatorResult:
    project_id = project["project_id"]

    rows = fetch_with_cache(
        sid, "Project", "ProjectParameter",
        filters={}, project_id=project_id, limit=200,
    )
    param = next(
        (r for r in rows if str(r.get("code", "")).strip() == project["code"]),
        None,
    )

    if not param:
        return IndicatorResult(...)

    project_budget = param.get("ProjectBudgetGrade") or 0
    presale_limit = param.get("PresaleLimit") or param.get("DirectProjectCostsGrade") or 0
    presale_pct = param.get("PresaleBudgetPercentage")

    if presale_pct is None and project_budget and presale_limit:
        presale_pct = (presale_limit / project_budget) * 100

    result = f"Сумма проекта:{int(project_budget)} руб./Пресейл:{int(presale_limit)} руб./Лимит %:{presale_pct:.1f}"

    return IndicatorResult(
        number=13,
        name="Бюджет проекта/пресейла",
        result=result,
        detail="",
        verdict="Норма",
        table=None,
    )
```

Ждёт подтверждения по полям.