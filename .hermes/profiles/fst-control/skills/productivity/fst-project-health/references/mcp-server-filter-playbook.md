# Playbook для разработчиков MCP-сервера: оптимизация для skill `fst-project-health`

**Дата:** 2026-09-01 (обновлено — новый формат `filters`)
**Кем:** ROSTISLAV KUZNETSOV (skill `fst-project-health`)
**Файл:** `references/mcp-server-filter-playbook.md`
**Связанный skill:** `fst-project-health` v0.13.0+
**Версия:** 1.2

---

## ⚠️ ВАЖНО (2026-09-01): новый формат `filters`!

С 2026-09-01 **рекомендуемый формат** для всех view — через параметр `filters` (НЕ через `?ProjectId=<id>` в URL).

**Подробности:** `references/mcp-filters-format.md`. **Скрипт-проверка:** `scripts/probe_filters_format.py`.

---

## TL;DR

При построении отчётов по скиллу `fst-project-health` мы запрашиваем несколько
views через MCP и фильтруем строки **на клиенте** (Python). Это приводит к передаче
**700–2400 строк JSON по сети**, когда реально нам нужны **~30–50**.

Этот playbook содержит **конкретные запросы** на улучшения MCP-сервера, которые
снимут узкие места. Самые важные (по приоритету):

**⚠️ Используй новый формат `filters` (2026-09-01):**

```python
mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "ProjectHealthCostMy",
    "filters": {"ProjectId": 4595},   # ← отдельный параметр
    "limit": 100
})
```

Live-probe 2026-09-01: работает для **5 view**: `ProjectHealthCostMy`, `ProjectResourcePlan`, `ProjectBudgetCompleteBusiness`, `InContractMyProject`, `AllMyPoint`.

---

## Что уже работает (live-probe 2026-09-01, новый формат)

| View | Фильтр | Результат | Экономия | Когда подтверждено |
|------|--------|-----------|---------:|---------------------|
| `Point/AllMyPoint` | `filters: {"ProjectId": <id>}` | ✅ работает | **−3 сек** | 2026-08-22 |
| `Project/ProjectBudgetCompleteBusiness` | `filters: {"ProjectId": <id>}` | ✅ работает | **−2 сек** | 2026-08-22 |
| `Project/ProjectResourcePlan` | `filters: {"ProjectId": <id>}` | ✅ работает | **−3 сек** | 2026-08-22 |
| **`Project/ProjectHealthCostMy`** | **`filters: {"ProjectId": <id>}`** | **✅ 1 строка за 1.5 сек** | **−40 сек** | **2026-09-01** |

---

## Что НЕ работает — нужны фильтры

### 1. `Project/ProjectHealthCostMy` ✅ ПОЧИНЕНО через `filters`

**Статус:** работает через `filters: {"ProjectId": <id>}`. URL-based (`?ProjectId=`) — сломано с 2026-09-01.

### 2. `Project/ProjectResourcePlan` ✅ ПОЧИНЕНО через `filters`

**Статус:** работает через `filters: {"ProjectId": <id>}`.

---

## Что ещё нужно (по состоянию на 2026-09-01)

### 3. `InContract/InContractMyProject` ⚠️ частично

**Статус:** работает через `filters: {"ProjectId": <id>}` для504-595. Для 503-434/503-152 — 0 строк (доступ).

### 4. `InContract/InContract` (без MyProject) ❌

**Статус:** `filters: {"ProjectId": <id>}` НЕ фильтрует — возвращает те же 42 строки.

### 5. Поле `projectid` в `InContract` ⚠️

**Статус:** всегда `null` в строках. Фильтрация по нему невозможна.

### 6. `Project/MyProject` ⭐ низкий

**Статус:** поддержка `filters: {"ProjectId": <id>}` или `{"MyRoleOnly": true}`.