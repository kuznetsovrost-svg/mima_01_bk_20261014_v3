# MCP filters format: `filters={...}` (новый стандарт 2026-09-01)

**Дата:** 2026-09-01
**Кем:** ROSTISLAV KUZNETSOV (skill `fst-project-health`)
**Связанный pitfall:** #18, #19 в `mcp-server-probing`
**Связанный skill:** `mcp-server-probing` (главный), `fst-project-health` (применение)

---

## TL;DR

**С 2026-09-01 MCP-сервер Форсайт ввёл новый стандартный формат фильтрации:**

```python
# ✅ НОВЫЙ СТАНДАРТ (с 2026-09-01):
mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "ProjectHealthCostMy",  # имя view БЕЗ фильтра
    "filters": {"ProjectId": 4595},     # фильтр отдельным параметром
    "limit": 100
})

# ❌ СТАРЫЙ (DEPRECATED с 2026-09-01):
mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "ProjectHealthCostMy?ProjectId=4595",  # фильтр в URL
    "limit": 100
})
```

**Преимущества нового формата:**
1. **Работает для ВСЕХ view** (URL-формат поддерживался только для некоторых)
2. **Не ломается** при изменении внутренней структуры view на сервере
3. **Документирован** через `list_views` (см. ниже)
4. **Типизирован** — сервер знает формат и валидирует

---

## Live-probe подтверждения (2026-09-01, PMForesight)

| View | Старый URL-формат | Новый `filters={...}` |
|------|-------------------|----------------------|
| `ProjectHealthCostMy?ProjectId=` | ❌ 500 bigint = text | ✅ **1 строка за 1.5 сек** |
| `ProjectResourcePlan?ProjectId=` | ⚠️ работает | ✅ работает |
| `ProjectBudgetCompleteBusiness?ProjectId=` | ⚠️ работает | ✅ работает |
| `InContractMyProject?ProjectId=` | ⚠️ работает частично | ✅ работает |
| `AllMyPoint?ProjectId=` | ✅ работает | ✅ работает |
| `Project/ProjectHealthCostMy` (без фильтра) | ❌ 500 | ❌ 500 (view всё ещё сломан) |
| `NormDayWorkHours?ProjectId=` | ❌ возвращает чужие данные | ❌ не работает |

**Главный выигрыш:** `ProjectHealthCostMy` — был сломан 4 дня, теперь работает всегда.

---

## Полный список фильтров по view (live-probe 2026-09-01)

Получить все фильтры можно через `list_views`:

```python
views = mcp_call(sid, "list_views", {})  # возвращает list из 238 словарей
for v in views:
    print(f"{v['ViewName']:35s} | {v['entityName']:15s} | {v.get('Description', '')[:100]}")
```

| View | Фильтры |
|------|---------|
| `ProjectHealthCostMy` | `ProjectId`, `DateBegin`, `DateEnd`, `ProjectProfileId` |
| `ProjectResourcePlan` | `ProjectId` |
| `ProjectBudgetCompleteBusiness` | `ProjectId`, `ContractId`, `ProgramId`, `PortfolioId` |
| `InContractMyProject` | `ProjectId` |
| `AllMyPoint` | `PortfolioId`, `ProjectId` |
| `NormDayWorkHours` | `ProjectId`, `StartDate`, `EndDate` |
| `MyProject` | `UserAccount`, `ProjectProfileId` |
| `AllProject` | `UserAccount`, `ProjectProfileId` |
| `ApprovedBudget` | `ActivityId`, `PortfolioId`, `Year` |

---

## Критическое открытие: `DateBegin`/`DateEnd` в `ProjectHealthCostMy`

Это открывает **трендовые отчёты**:

```python
# Данные на 2026-08-31 (за август)
data = mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "ProjectHealthCostMy",
    "filters": {
        "ProjectId": 4595,
        "DateBegin": "2026-08-01",
        "DateEnd": "2026-08-31"
    },
    "limit": 100
})
# Returns 1 row: {forecast: -221860, fact: 0, devcost: 1253784, ...}
```

**Использование:** строить графики `forecast`, `fact`, `devcost` по месяцам.

---

## Правила и gotchas

### ✅ Правильно

```python
# Фильтр в отдельном параметре
mcp_call(sid, "get_view", {
    "entityName": "...",
    "viewName": "...",  # БЕЗ ?ProjectId= в URL
    "filters": {"ProjectId": 4595},
    "limit": 100
})
```

### ❌ Неправильно

```python
# 1. Фильтр в имени view (DEPRECATED)
"viewName": "ProjectHealthCostMy?ProjectId=4595"  # ← может сломаться

# 2. Передавать filters=null
"filters": None  # ← ошибка валидации

# 3. Пропускать filters
# arguments без "filters"  # ← для некоторых view обязательно

# 4. Передавать filters={} с пустым dict для view без фильтров
# В некоторых случаях пустой dict может вызвать 500 — пробуй опускать параметр
```

### Что делать если фильтр не работает

1. **Проверить** что фильтр в списке поддерживаемых (`list_views`)
2. **Probe** через `list_views` какие поля view принимает
3. **Fallback** на пагинацию + локальный фильтр (pitfall #11)
4. **Fallback** на альтернативный view (например, `AllProject` вместо `MyProject`)

---

## Пример: `mcp_config.py` helpers (в skill `fst-project-health`)

```python
# В mcp_config.py:
PROJECT_HEALTH_COST_MY_VIEW = "ProjectHealthCostMy"
PROJECT_HEALTH_COST_MY_FILTERS = lambda project_id: {"ProjectId": project_id}

PROJECT_RESOURCE_PLAN_VIEW = "ProjectResourcePlan"
PROJECT_RESOURCE_PLAN_FILTERS = lambda project_id: {"ProjectId": project_id}

ALL_MY_POINT_VIEW = "AllMyPoint"
ALL_MY_POINT_FILTERS = lambda project_id: {"ProjectId": project_id}

# ... и т.д.

def get_view_with_filters(sid, entity_name, view_name, filters=None, limit=100, offset=None):
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
```

**Использование в run_all.py:**

```python
# ❌ Старый (DEPRECATED):
view_name = PROJECT_HEALTH_COST_MY_VIEW_FOR(project["project_id"])  # = "ProjectHealthCostMy?ProjectId=4595"
resp = mcp_call(sid, "get_view", {"entityName": "Project", "viewName": view_name, "limit": 100})

# ✅ Новый:
resp = mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": PROJECT_HEALTH_COST_MY_VIEW,
    "filters": PROJECT_HEALTH_COST_MY_FILTERS(project["project_id"]),
    "limit": 100
})
```

---

## Связь с другими pitfalls

- **#18** (mcp-server-probing): основное описание нового формата `filters={...}`
- **#19** (mcp-server-probing): `list_views` — discover available filters
- **#13** (mcp-server-probing): старый формат `?FieldName=<value>` в URL (DEPRECATED)
- **#16** (mcp-server-probing): TRAP — фильтр может молча игнорироваться (проверять содержимое!)
- **#17** (mcp-server-probing): TRAP — view может возвращать данные другой сущности
- **#15** (mcp-server-probing): b-tree 2704 лимит (теперь ИСПРАВЛЕН разработчиками, поддерживает до ~50 КБ JSON)

---

## Что изменилось 2026-09-01 (timeline)

| Дата | Событие |
|------|---------|
| 2026-08-08 | `?ProjectId=<id>` URL-формат начал работать для `AllMyPoint` |
| 2026-08-22 | `?ProjectId=<id>` работает для `ProjectBudgetCompleteBusiness` |
| 2026-08-26 | `?ProjectId=<id>` починено для `ProjectHealthCostMy` (109 → 1 строка) |
| 2026-08-27 | **РЕГРЕССИЯ**: `ProjectHealthCostMy` ломается при любом вызове |
| 2026-08-28 | Восстановлено частично |
| **2026-09-01** | **Новый формат `filters={...}`** — стандартный, работает для всех view |
| **2026-09-01** | **B-tree лимит ИСПРАВЛЕН** — можно загружать JSON до ~50 КБ |

---

## Чек-лист при обновлении кода на новый формат

- [ ] Заменить все `*_VIEW_FOR(pid)` (DEPRECATED) на `*_VIEW` + `*_FILTERS(pid)`
- [ ] Использовать helper `get_view_with_filters()` для единообразия
- [ ] Удалить `*_VIEW_FOR` лямбды из `mcp_config.py` (после тестирования)
- [ ] Обновить тесты — заменить проверки `*_VIEW_FOR` на проверки `*_VIEW` + `*_FILTERS`
- [ ] Добавить тест `test_filters_handle_int` для проверки `*_FILTERS(pid)`
- [ ] Добавить тест `test_view_for_lambdas_removed` (если удалены)
- [ ] Обновить `references/view-filter-playbook.md` — пометить старый формат как DEPRECATED

---

## Live-probe команды (для повторения)

```bash
# Получить список всех view с фильтрами
python3 /root/.hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts/mcp_probe.py --tool list_views 2>&1 | head -50

# Проверить новый формат на 504-595
python3 -c "
import sys, importlib.util
spec = importlib.util.spec_from_file_location('mcp_config', '/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts/mcp_config.py')
mcp_config = importlib.util.module_from_spec(spec)
sys.modules['mcp_config'] = mcp_config
spec.loader.exec_module(mcp_config)
sid, _ = mcp_config.mcp_init(client_name='probe-filters')
r = mcp_config.mcp_call(sid, 'get_view', {
    'entityName': 'Project',
    'viewName': 'ProjectHealthCostMy',
    'filters': {'ProjectId': 4595},
    'limit': 100
})
print('Rows:', len(r.get('data', [])))
print('First row:', r.get('data', [{}])[0])
"
```

---

## Changelog

| Дата | Что изменилось |
|------|----------------|
| **2026-09-01** | Первая версия. Зафиксирован переход на стандартный формат `filters={...}`. Live-probe подтвердил работу для 5+ views. B-tree лимит ИСПРАВЛЕН. delete_entity формат найден. |
