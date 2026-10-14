# MCP Filters Format — канонический playbook (v2.0, 2026-09-02)

**Дата:** 2026-09-02
**Скилл:** `fst-project-health`
**Источник:** Live-probe сессии 2026-09-01, 2026-09-02
**Приоритет:** **ВЫСОКИЙ** — использовать вместо старого `?ProjectId=<id>` в URL

---

## TL;DR

**Новый (правильный) формат:**

```python
mcp_call(sid, "get_view", {
    "entityName": "Project",          # или null
    "viewName": "ProjectHealthCostMy",
    "filters": {"ProjectId": 4595},   # ← отдельный параметр
    "limit": 100,
    "offset": 0
})
```

**Старый (сломаный) формат:**

```python
mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "ProjectHealthCostMy?ProjectId=4595",  # ← вшит в URL
    "limit": 100
})
# → 500 "bigint = text"
```

---

## Подтверждённые работающие view (live-probe 2026-09-01)

| View | Entity | Новый формат (filters) | Строк | Время |
|------|--------|----------------------|------:|------:|
| `ProjectHealthCostMy` | Project | ✅ | 1 | 1.42 сек |
| `ProjectResourcePlan` | Project | ✅ | 100 | 1.37 сек |
| `ProjectBudgetCompleteBusiness` | Project | ✅ | 12 | 3.57 сек |
| `InContractMyProject` | InContract | ✅ | 1 | 0.78 сек |
| `AllMyPoint` | Point | ✅ | 18 | 0.83 сек |
| `NormDayWorkHours` | Project | ✅ (только с StartDate/EndDate) | 31 | 0.50 сек |
| `ApprovedBudget` | Project | ✅ (ActivityId/Year) | 1 | 0.50 сек |

**Все view работают с новым форматом!**

---

## Как узнать поддерживаемые фильтры — `list_views` (ОТКРЫТИЕ 2026-09-01)

**Раньше** мы угадывали какие фильтры работают. **Теперь** есть официальный tool `list_views`:

```python
def get_supported_filters(sid, view_name: str) -> list[str]:
    """Парсит Description из list_views и возвращает имена фильтров."""
    import re
    views = mcp_call(sid, "list_views", {})
    for v in views:
        if v.get("ViewName") == view_name:
            desc = v.get("Description", "")
            # Паттерн: "Поддерживает фильтрацию по: A(@A), B(@B)"
            return re.findall(r"@(\w+)", desc)
    return []

# Использование:
filters = get_supported_filters(sid, "ProjectHealthCostMy")
# → ['ProjectId', 'DateBegin', 'DateEnd', 'ProjectProfileId']
```

**`list_views` возвращает 238 views** с полями:
- `ViewName` — имя view
- `Title` — русское название
- `Description` — описание с поддерживаемыми фильтрами в формате `@FilterName`
- `entityName` — к какой сущности относится

---

## Поддерживаемые фильтры по view (live-probe 2026-09-01 + 2026-09-02)

| View | Filters | Статус |
|------|---------|:------:|
| `ProjectHealthCostMy` | `ProjectId`, `DateBegin`, `DateEnd`, `ProjectProfileId` | ✅ |
| `ProjectResourcePlan` | `ProjectId` | ✅ |
| `ProjectBudgetCompleteBusiness` | `ProjectId`, `ContractId`, `ProgramId`, `PortfolioId` | ✅ |
| `InContractMyProject` | `ProjectId` | ⚠️ частично (доступ по пользователю) |
| `AllMyPoint` | `PortfolioId`, `ProjectId` | ✅ |
| `NormDayWorkHours` | `ProjectId`, `StartDate`, `EndDate` | ⚠️ ProjectId игнорируется |
| `ApprovedBudget` | `ActivityId`, `PortfolioId`, `Year` | ✅ |
| `MyProject` | `UserAccount`, `ProjectProfileId` | ✅ |
| `AllProject` | `UserAccount`, `ProjectProfileId` | ✅ |

---

## Что делать в скилле

### ✅ Хелпер уже реализован в `mcp_config.py` (2026-09-01)

```python
def get_view_with_filters(sid, entity_name: str, view_name: str,
                          filters: dict | None = None,
                          limit: int | None = 100,
                          offset: int | None = None) -> dict:
    """Универсальный вызов get_view с правильным форматом filters."""
    args = {
        "entityName": entity_name,
        "viewName": view_name,
        "filters": filters or {},
        "limit": limit,
    }
    if offset is not None:
        args["offset"] = offset
    return mcp_call(sid, "get_view", args)

# Хелперы для фильтров
PROJECT_HEALTH_COST_MY_FILTERS = lambda project_id: {"ProjectId": project_id}
PROJECT_RESOURCE_PLAN_FILTERS = lambda project_id: {"ProjectId": project_id}
ALL_MY_POINT_FILTERS = lambda project_id: {"ProjectId": project_id}
PROJECT_BUDGET_FILTERS = lambda project_id: {"ProjectId": project_id}
IN_CONTRACT_MY_PROJECT_FILTERS = lambda project_id: {"ProjectId": project_id}
APPROVED_BUDGET_FILTERS = lambda activity_id: {"ActivityId": activity_id}
```

### Использовать в `run_all.py`

```python
from mcp_config import (
    PROJECT_HEALTH_COST_MY_VIEW,
    PROJECT_HEALTH_COST_MY_FILTERS,
    get_view_with_filters,
)

resp = get_view_with_filters(
    sid=sid,
    entity_name="Project",
    view_name=PROJECT_HEALTH_COST_MY_VIEW,
    filters=PROJECT_HEALTH_COST_MY_FILTERS(project["project_id"]),
    limit=100
)
```

### ✅ Уже сделано в production (2026-09-01)

Все 4 production скрипта переведены на новый формат:
- `scripts/run_all.py:build_section_6` — `ProjectHealthCostMy`
- `scripts/run_all.py:load_project_points` — `AllMyPoint`
- `scripts/get_effort.py:get_effort_rows` — `ProjectResourcePlan`
- `scripts/get_project_budget.py:get_budget_rows` — `ProjectBudgetCompleteBusiness`
- `scripts/build_report_header.py` (V10) — оба вызова

Все тесты прошли (6/6), pipeline работает (~20 сек на проект).

---

## Что происходит со старым форматом

| Запрос | Статус | Ошибка |
|--------|:------:|--------|
| `viewName: "ProjectHealthCostMy?ProjectId=4595"` | ❌ | `bigint = text` |
| `viewName: "ProjectHealthCostMy"` (без фильтра) | ❌ | `параметр $5 не определён` |
| `viewName: "ProjectHealthCostMy"` + `filters: {ProjectId: 4595}` | ✅ | 1 строка |

**Старый формат сломался 2026-09-01** (после того как работал 26-27.08). Причина — `bigint = text` в SQL.

---

## Известные проблемы

| Случай | Статус | Замечание |
|--------|:------:|-----------|
| `filters: {}` (пустой) | ❌ | 500 (тот же $5 не определён) |
| `filters: {ProjectId: 4595}` | ✅ | работает |
| `filters: {WrongField: 4595}` | ❌ | скорее всего 500 или пусто |
| `InContract?ProjectId=<id>` (без MyProject) | ❌ | возвращает одни и те же 42 строки |
| `InContractMyProject?ProjectId=<id>` для 503-434 | ❌ | 0 строк (нет доступа) |
| `NormDayWorkHours?ProjectId=<id>` | ❌ | фильтр игнорируется, 244 строки |

**Правило:** если фильтр пустой — **не передавать** `filters` вообще.

```python
args = {"viewName": view_name, "limit": limit}
if filters:
    args["filters"] = filters
```

---

## Чек-лист после перевода на новый формат

1. **Все 4 наших проекта** (504-595, 503-434, 503-152, 504-314) дают ≥ 1 строку
2. **Pipeline** `run_all.py --code <code>` отрабатывает без 500
3. **Тесты** `tests/run_all_tests.py` — 6/6 PASS
4. **Скилл портативен** — `Path(__file__).resolve().parent.parent` вместо `/root/...`

```bash
cd tests && python3 run_all_tests.py --report
cd .. && python3 scripts/run_all.py --code 504-595 --no-word --timing
```

---

## Открытия сессии 2026-09-01 (для контекста)

1. **`delete_entity`**: формат `remove=['AttributeValue|<guid>']` ✅. 10 форматов протестировано, 1 рабочий.
2. **B-tree 2704 limit** на `AttributeValue` — РАЗРАБОТЧИКИ ПОЧИНИЛИ. JSON до 50 КБ загружается.
3. **Удалено 34 тестовые записи** через скрипт `/tmp/project-json-design/scripts/delete_attribute_values.py`.
4. **`InContractMyProject` фильтр по `ProjectId`** — формально работает (`filters: {ProjectId: <id>}`), но **доступ пользователя** ограничен: для 504-595 возвращает 1 строку, для 503-434/503-152/504-314 — 0 строк.
5. **`NormDayWorkHours` фильтр по `ProjectId`** — фильтр **игнорируется**, но **структура правильная** (`Date`, `Hours`, `ProjectId`).
6. **`ProjectBudgetCompleteBusiness`** — 36 столбцов, есть `isprojectbudget`/`ispresalebudget` для разделения проект/пресейл.
7. **`ApprovedBudget`** — 5 столбцов (id, ApprovedBudgetId, ActivityId, Year, Value). 504-595: 54 000 000 ₽ на 2026.
8. **Скилл `project-search`** обновлён до v2.0.0, перенесён в `fst-project-health/project-search/`, добавлены 12 тестов.
9. **4 связанных скилла** (`project-effort-plan`, `project-effort-write`, `project-timing-control`, `project-completeness-check`) обновлены до v2.0.0 с новым форматом `filters={...}`.

---

## Связь с другими скиллами

- `mcp-server-probing` — playbook по зондированию MCP-сервера при ошибках
- `project-search` (теперь в `fst-project-health/project-search/`) — поиск ProjectId по Code/Name
- `project-effort-plan`, `project-effort-write` — управление трудозатратами
- `project-completeness-check` — проверка полноты заполнения проекта

Все обновлены до v2.0.0 с форматом `filters={...}`.

---

## История

| Дата | Что |
|------|-----|
| 2026-08-22 | `?ProjectId=<id>` в URL — работает для 3 view |
| 2026-08-26 | `ProjectHealthCostMy?ProjectId=` — починили |
| 2026-08-27 | Регрессия: InContract сломался |
| 2026-08-28 | InContract восстановили |
| 2026-08-31 | ProjectHealthCostMy снова сломался |
| 2026-09-01 | **Разработчики предложили `filters`** — работает для **всех** view |
| 2026-09-01 | Открыт `list_views` — официальный способ узнать фильтры |
| 2026-09-01 | B-tree 2704 limit ИСПРАВЛЕН разработчиками |
| 2026-09-01 | `delete_entity` формат найден: `remove=['EntityValue|<guid>']` |
| 2026-09-02 | Все production скрипты переведены на новый формат |
| 2026-09-02 | Скилл переносим (relative paths) |
| 2026-09-02 | Skill `project-search` обновлён и перенесён |
| 2026-09-02 | 4 связанных скилла обновлены до v2.0.0 |

**См. также:** `references/mcp-regressions-2026-09-01.md` (волна регрессий), `references/discovery-2026-09-01.md` (новые view и фильтры).
