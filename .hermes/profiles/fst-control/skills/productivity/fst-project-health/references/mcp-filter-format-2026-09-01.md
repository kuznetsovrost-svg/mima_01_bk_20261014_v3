# MCP Filter Format Migration (2026-09-01)

**Дата:** 2026-09-01
**Контекст:** в этот день разработчики MCP сломали старый формат `?ProjectId=<id>` в URL view и ввели новый стандартный формат `filters={...}` как отдельный параметр.

## TL;DR

| Было (DEPRECATED) | Стало (standard) |
|---------------------|---------------------|
| `viewName = "X?ProjectId=Y"` в URL | `viewName = "X"` + `filters = {"ProjectId": Y}` |
| Работало для 5/7 views (случайно) | Работает для **всех** views |
| Ломалось после каждого деплоя MCP | Стабильно |

## Синтаксис

```python
# DEPRECATED (сломан с 2026-09-01)
resp = mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": f"ProjectHealthCostMy?ProjectId={pid}",  # 500 bigint = text
    "limit": 100
})

# NEW STANDARD
resp = mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "ProjectHealthCostMy",          # имя view без фильтров
    "filters": {"ProjectId": pid},               # фильтры отдельным dict
    "limit": 100
})
```

## Поддерживаемые фильтры по views (live-probe 2026-09-01)

| View | Filters |
|------|---------|
| `ProjectHealthCostMy` | ProjectId, **DateBegin**, **DateEnd**, ProjectProfileId |
| `ProjectResourcePlan` | ProjectId |
| `ProjectBudgetCompleteBusiness` | ProjectId, ContractId, ProgramId, PortfolioId |
| `InContractMyProject` | ProjectId |
| `AllMyPoint` | PortfolioId, ProjectId |
| `NormDayWorkHours` | ProjectId, **StartDate**, **EndDate** |
| `ApprovedBudget` | ActivityId, PortfolioId, **Year** |

**Параметр `filters` — ОБЯЗАТЕЛЬНО dict** (может быть `{}`). `null` или отсутствие → 500.

## Discover supported filters (NEW tool `list_views`)

```python
import re
def get_supported_filters(sid, view_name: str) -> list[str]:
    """Parse Description field to extract supported filters."""
    views = mcp_call(sid, "list_views", {})
    for v in views:
        if v.get("ViewName") == view_name:
            desc = v.get("Description", "")
            # Pattern: "Поддерживает фильтрацию по: A(@A), B(@B)"
            return re.findall(r"@(\w+)", desc)
    return []

# Использование
filters = get_supported_filters(sid, "ProjectHealthCostMy")
# → ['ProjectId', 'DateBegin', 'DateEnd', 'ProjectProfileId']
```

**Live-probe 2026-09-01:** 238 views, `list_views` возвращает все.

## ⚠️ Pitfall #155 (NEW 2026-09-03): `list_views` description неполный — НЕ доверяй ему

**Критически важно:** список фильтров из `list_views` **НЕ полный**. Многие фильтры работают через `get_view`, но **не указаны** в `Description` поля. В результате любая галлюцинация про "таких фильтров нет" — это неправда.

**Live-probe (2026-09-03) нашёл фильтры, которые работают, но НЕ указаны в `list_views`:**

| View | Указано в `list_views` | РЕАЛЬНО работает |
|------|------------------------|------------------|
| `ProjectResourcePlan` | (пусто) | **`ProjectId`, `accountid`** ✅ |
| `ProjectBudgetCompleteBusiness` | (пусто) | **`ProjectId`, `ContractId`, `ProgramId`, `PortfolioId`** ✅ |
| `AllMyPoint` | (пусто) | **`ProjectId`, `PortfolioId`** ✅ |
| `NormDayWorkHours` | `ProjectId, StartDate, EndDate` | ✅ полный |
| `ApprovedBudget` | `ActivityId, PortfolioId, Year` | ✅ полный |
| `InContractMyProject` | `ProjectId` | ✅ полный |

**Правило:** все фильтры из `get_view` Description — **минимум**. Реально может работать **больше**. Чтобы убедиться — **сделай live-call** с фильтром и проверь что вернулось корректное количество строк.

**Правильный подход к проверке галлюцинаций:**

```python
def verify_filter_exists(sid, view_name, filter_name, value):
    """Live-call check: works? Returns 0 rows means filter ignored."""
    try:
        r = mcp_call(sid, "get_view", {
            "entityName": <entity>,
            "viewName": view_name,
            "filters": {filter_name: value},
            "limit": 5,
        })
        return r.get("data", [])
    except Exception:
        return []

# Проверить все 12 используемых view+entity комбинаций
```

**Результат live-проверки (2026-09-03):** ВСЕ 12 view+entity комбинаций существуют и работают корректно. **Галлюцинаций нет**, но **документация фильтров неполная** — это проблема MCP-сервера, не нашего кода.

**Что делать:**
- НЕ **доверять** списку фильтров из `list_views` как полному
- **ВСЕГДА** делать live-probe перед использованием нового фильтра
- При подозрении — сделать write-up для разработчиков MCP о неполных descriptions

## Helper в `mcp_config.py` (production)

```python
# Константы имён view (без URL-параметров)
PROJECT_HEALTH_COST_MY_VIEW = "ProjectHealthCostMy"
PROJECT_RESOURCE_PLAN_VIEW = "ProjectResourcePlan"
PROJECT_BUDGET_VIEW = "ProjectBudgetCompleteBusiness"
IN_CONTRACT_MY_PROJECT_VIEW = "InContractMyProject"
ALL_MY_POINT_VIEW = "AllMyPoint"

# Helpers для фильтров (вместо *_VIEW_FOR lambdas)
PROJECT_HEALTH_COST_MY_FILTERS = lambda pid: {"ProjectId": pid}
PROJECT_RESOURCE_PLAN_FILTERS = lambda pid: {"ProjectId": pid}
PROJECT_BUDGET_FILTERS = lambda pid: {"ProjectId": pid}
IN_CONTRACT_MY_PROJECT_FILTERS = lambda pid: {"ProjectId": pid}
ALL_MY_POINT_FILTERS = lambda pid: {"ProjectId": pid}

# Универсальный wrapper
def get_view_with_filters(sid, entity_name, view_name, filters=None, limit=100, offset=None):
    args = {"entityName": entity_name, "viewName": view_name, "filters": filters or {}, "limit": limit}
    if offset is not None: args["offset"] = offset
    return mcp_call(sid, "get_view", args)
```

## Правила миграции (lesson learned 2026-09-01)

### Правило 1: DEPRECATED код — удалять, не хранить

Когда код помечен `DEPRECATED` и прошёл период тестирования (≥ 1 сессия) — **удалять** его, не оставлять для обратной совместимости.

**Инцидент:** в начале сессии `*_VIEW_FOR` lambdas были помечены `# DEPRECATED` и сохранены в `mcp_config.py`. Пользователь явно попросил: «Удалить _VIEW_FOR лямбды (помечены DEPRECATED)». **DEPRECATED + оставлен = техдолг.**

**Правило для нового кода:**
- Удаляй deprecated через 1 итерацию (одна сессия пользователя)
- Не добавляй комментарии «оставлено для обратной совместимости»
- Если совместимость реально нужна — пиши в `mcp_config.py` явный `__all__` с whitelist, не оставляй всё

### Правило 2: Тесты должны проверять отсутствие deprecated

**Инцидент:** после удаления `*_VIEW_FOR` lambdas тесты должны были упасть, но проверяли их **наличие** (`mcp.PROJECT_*_VIEW_FOR(pid) == "X?ProjectId=..."`). Удаление лямбд привело бы к `AttributeError`, а не к failed test с понятным сообщением.

**Правильный тест (anti-test):**
```python
def test_view_for_lambdas_removed(self):
    """DEPRECATED лямбды *_VIEW_FOR удалены (2026-09-01)."""
    for name in ['PROJECT_RESOURCE_PLAN_VIEW_FOR',
                 'PROJECT_BUDGET_VIEW_FOR',
                 'PROJECT_HEALTH_COST_MY_VIEW_FOR',
                 'ALL_MY_POINT_VIEW_FOR']:
        self.assertFalse(
            hasattr(mcp, name),
            f"{name} должна быть удалена (DEPRECATED с 2026-09-01)"
        )
```

**Паттерн:** `assertFalse(hasattr(...))` для anti-теста. Лучше падать с понятным сообщением, чем с `AttributeError` в random production call.

### Правило 3: Не удалять scripts/ которые уже неактуальны — но убирать

**Инцидент:** в начале сессии в `scripts/` лежали 3 скрипта-проверки переходного периода:
- `test_filters_format.py` — проверял что старый и новый формат оба работают (после перехода — старый не работает)
- `probe_filters_format.py` — manual probe
- `regression_probe.py` — общая регрессия

После перехода **первые два** стали неактуальны. Удалил их как **одноразовые диагностические скрипты**. Оставил `regression_probe.py` как **постоянную утилиту** для CI.

**Правило:** разделяй **диагностические** (одноразовые) и **утилитные** (постоянные) скрипты. Диагностические — удаляй после решения проблемы, иначе они становятся легаси.

### Правило 4: Скрипты-утилиты для очистки тестовых данных

После всех экспериментов осталось 34 тестовых записи в MCP. Создал `/tmp/project-json-design/scripts/delete_attribute_values.py` — **standalone утилиту** для очистки. Использовал для удаления всех 34 (100% успех).

**Паттерн:** когда эксперимент оставляет данные в production-системе — **создай скрипт для их очистки**. Сохрани в `/tmp/<thing>-design/scripts/` (не в скилле — это transient utility).

## Что НЕ сохраняем в скилле (transient)

- Список 34 ID тестовых записей — **session-specific**
- Результаты live-probe (`log.txt`, скриншоты) — **transient**
- Скрипт `delete_attribute_values.py` — остаётся в `/tmp/project-json-design/scripts/` (там, где JSON-модель)
- Письма разработчикам `Письмо_*.md` — **transient**, в `~/.hermes/profiles/fst-control/cache/documents/`

## Что сохраняем в скилле

- Сами `*_FILTERS` lambdas в `mcp_config.py` (production helpers)
- `get_view_with_filters()` универсальный wrapper
- Список views с поддерживаемыми фильтрами (таблица выше)
- Паттерн "test на удаление deprecated" — урок зафиксирован
- Test `test_view_for_lambdas_removed` — в `tests/test_helpers.py`
- В `mcp-server-probing`: pitfall #18 уже зафиксирован
- В `fst-project-health/SKILL.md`: pitfalls #83-#87 зафиксированы

## Связанные ссылки

- `SKILL.md` (pitfalls #83-#87) — подробнее о каждом случае
- `scripts/mcp_config.py` — `*_FILTERS` lambdas и `get_view_with_filters()`
- `tests/test_helpers.py` — anti-test `test_view_for_lambdas_removed`
- `mcp-server-probing` skill (v2.0.0) — pitfall #18 про новый формат
