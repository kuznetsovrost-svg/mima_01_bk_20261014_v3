# Форсайт MCP — подводные камни и архитектурные находки

Зафиксировано при первых живых прогонах `fst-project-health` против MCP
`https://ppreplica.hera.pmpractice.ru/mcp` (версия **3.2.4**, август 2026).
Это **не environment-dependent failures** — это контракт API Форсайт,
который будет тем же завтра. Каждый pitfall ниже стоил минимум одного
заблокированного запроса в реальной сессии.

---

## 1. Привязка контракт↔проект — НЕ через `InContractActivity` {#parentfullname-is-the-link}

**Симптом:** фильтр контрактов проекта возвращает 0 строк, хотя контракты
привязаны и видны в view.

**Корень:** в view `InContractMyProject` и `OutcomeContractMyProject`
поля `InContractActivity` (MultiSelectField) **НЕТ**. Оно появляется
только в ответе `get_entity_data(InContract, data_id=<id>)`.

**Как делать правильно:**

В строке view связь с проектом закодирована в строковом поле
`ParentFullName` формата `"<project_code>. <project_name>"`. Пример для
проекта 504-595:

```python
contract_row["ParentFullName"] == "504-595. Космодром Жуковский внедрение ИСУП "
```

То есть фильтр:

```python
def contract_belongs_to_project(row, project_code: str) -> bool:
    parent_full = (row.get("ParentFullName") or "").strip()
    return parent_full.startswith(f"{project_code}.")
```

**Когда всё-таки нужен `InContractActivity`:** только если тебе нужны
точные `ActivityId` контракта (например, для привязки `ResourcePlanning`,
которая идёт через `ActivityId`, не через `ParentCode`). Тогда делай
отдельный `get_entity_data(InContract, data_id=<InContractId>)` на каждый
контракт (это и есть N+1 — медленно, но точно).

**Замечание о V04 / Payments-graph-check.py:** оригинальная логика

```python
ica = c.get("InContractActivity") or []
if any(a.get("value") in project_activity_ids for a in ica):
    ...
```

даёт **ложный ноль** для проектов с привязанными контрактами. На реальных
данных 504-595 это давало `Контрактов: 0` при том что в `InContractAll`
контракт 704-724 был, а в `InContractMyProject` он тоже был — но строка
view не содержит `InContractActivity`.

---

## 50. **`?ProjectId=<id>` в имени view — server-side фильтр** (live-probe 2026-08-07)

**Проблема (была):** Pitfall #48 — `ProjectResourcePlan` возвращает 20000-30000 строк без server-side фильтрации по `projectid`. Чтобы получить данные конкретного проекта, нужно было перебирать offset до 600000. `ProjectBudgetCompleteBusiness` тоже без server-side фильтра. Клиентский фильтр через `activity_name.startswith(code + " ")` (pitfall #49) — медленный и ненадёжный (если проект в хвосте данных — не находим).

**Решение (live-probe 2026-08-07):** MCP поддерживает передачу `?ProjectId=<id>` **прямо в имени view** при вызове `get_view`. Это работает как **server-side фильтр** — возвращает только нужный проект.

**Пример для 504-595 (ProjectId=4595):**

```python
# ProjectResourcePlan с server-side фильтром — 149 строк, без сканирования!
data = mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "ProjectResourcePlan?ProjectId=4595",  # ← фильтр!
    "limit": 500,
})

# ProjectBudgetCompleteBusiness с server-side фильтром — 12 строк
data = mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "ProjectBudgetCompleteBusiness?ProjectId=4595",
    "limit": 500,
})
```

**Подтверждённые view с server-side фильтром (live-probe 2026-08-07 + 2026-08-21):**

- ✅ `ProjectResourcePlan?ProjectId=<id>` — 149 строк для 504-595 (2026-08-07)
- ✅ `ProjectBudgetCompleteBusiness?ProjectId=<id>` — 12 строк для 504-595 (2026-08-07)
- ✅ `Point/AllMyPoint?ProjectId=<id>` — **34 строки** для 503-434 (было 702 без фильтра) (2026-08-21). ВНИМАНИЕ: фильтрует по **ActivityId (= ProjectId)**, не по коду. Helper в `mcp_config.py`: `ALL_MY_POINT_VIEW_FOR(project_id) = lambda pid: f"AllMyPoint?ProjectId={pid}"`.
- ❌ `Point/AllMyPoint?ProjectCode=<code>` и `?ParentCode=<code>` — НЕ работают (2026-08-21)
- ❌ `ProjectHealthCostMy?ProjectId=<id>` — НЕ работает, 2000 строк (2026-08-21, нужен server-side фильтр — см. `references/mcp-server-filter-playbook.md`)
- ❌ `ProjectResourcePlan?ProjectId=<id>` формально принимает параметр, но для 503-434 возвращает 2390 строк (поле `activityid` lowercase, а не `ActivityId`) (2026-08-21, fallback — клиентский фильтр через `activity_name`)
- ❌ `MyProject?ProjectId=<id>` и `AllProject?ProjectId=<id>` — НЕ работают (2026-08-21, всегда возвращают полный список)
- ⚠️ Остальные view пока не подтверждены, но вероятно работают аналогично

**Discovery workflow (live-probe 2026-08-21):** для каждой новой view сначала пробуй `?ProjectId=<id>`, затем `?ActivityId=<id>`, затем `?ProjectCode=<id>`, затем `?<AnyField>=<id>`. Если ни один не работает — добавляй запрос в `references/mcp-server-filter-playbook.md`.

**Использование в скилле:**
- `mcp_config.PROJECT_RESOURCE_PLAN_VIEW_FOR(project_id)` — `lambda`, возвращает `f"ProjectResourcePlan?ProjectId={project_id}"`
- `mcp_config.PROJECT_BUDGET_VIEW_FOR(project_id)` — аналогично
- `mcp_config.ALL_MY_POINT_VIEW_FOR(project_id)` — `lambda`, возвращает `f"AllMyPoint?ProjectId={project_id}"`
- `get_effort.py` и `get_project_budget.py` — поддержка `--project-id <id>` для CLI
- `build_report_header.py → get_effort_summary() / get_project_budget_summary()` — теперь используют server-side фильтр
- `run_all.py → build_section_3() / build_section_5()` — используют `load_project_points()` с ALL_MY_POINT_VIEW_FOR (702 → ~30 строк)

**Результат:** вместо сканирования 600000 строк с offset — **149 строк сразу**. Вместо клиентской фильтрации `activity_name.startswith(...)` — **0 строк** для хвостовых проектов (504-595 раньше было 10 строк по ошибке — оказалось в хвосте, теперь 149 строк). Скорость в **~4000x быстрее** (149 строк vs 600000 строк + клиентский фильтр).

**Чек-лист:** перед тем как делать клиентскую фильтрацию через `startswith(activity_name)` или scan-offset — попробуй `?ProjectId=<id>` в имени view. Сервер фильтрует быстрее и точнее. Если фильтр не работает (`total=0`) — возможно view **не поддерживает** этот фильтр (например, для некоторых views `ProjectId` не имеет смысла как фильтр). Fallback — клиентский фильтр.

---
