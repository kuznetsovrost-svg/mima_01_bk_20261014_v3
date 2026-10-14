# MCP Call Patterns — рабочие форматы для fst-project-health

**Дата обновления:** 2026-09-01
**Автор:** ROSTISLAV KUZNETSOV
**Назначение:** Конкретные рабочие форматы вызовов MCP-сервера Форсайт. Каждый формат проверен live-probe в продакшене.

---

## 1. Стандартный формат `get_view` с `filters={...}` (РЕКОМЕНДУЕТСЯ)

```python
mcp_call(sid, "get_view", {
    "entityName": "Project",      # или "Point", "InContract"
    "viewName": "<имя view>",
    "filters": {"ProjectId": 4595},
    "limit": 100,
    "offset": 0
})
```

**Когда использовать:** ВСЕГДА. Это единственный стабильный формат.

**Что работает с filters (проверено 2026-09-01):**

| View | Filters | Результат |
|------|---------|-----------|
| `ProjectHealthCostMy` | `ProjectId`, `DateBegin`, `DateEnd`, `ProjectProfileId` | 1 строка за 1.3 сек |
| `ProjectResourcePlan` | `ProjectId` | N строк за 1.4 сек |
| `ProjectBudgetCompleteBusiness` | `ProjectId`, `ContractId`, `ProgramId`, `PortfolioId` | N строк за 3.5 сек |
| `InContractMyProject` | `ProjectId` | N строк за 0.8 сек |
| `AllMyPoint` | `ProjectId`, `PortfolioId` | N строк за 0.8 сек |
| `NormDayWorkHours` | `ProjectId`, `StartDate`, `EndDate` | 31-365 строк за 0.5 сек |

---

## 2. Старый формат `?ProjectId=<id>` в URL — DEPRECATED

```python
# ❌ НЕ ИСПОЛЬЗОВАТЬ (ломается после изменений сервера)
mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "ProjectHealthCostMy?ProjectId=4595",  # параметр в URL
    "limit": 100
})
```

**Что происходит:** Работало до 2026-08-26, потом периодически ломалось. Сейчас (2026-09-01) возвращает ошибку `bigint = text`.

---

## 3. list_views — discover filters automatically

```python
views = mcp_call(sid, "list_views", {})
# Возвращает 238 views с полями:
# - ViewName
# - Title
# - Description (содержит список поддерживаемых фильтров в формате "@FilterName")
# - entityName

# Пример: для ProjectHealthCostMy
{
    "ViewName": "ProjectHealthCostMy",
    "Title": "Проекты\\Здоровье по стоимости (все доступные)",
    "Description": "Поддерживает фильтрацию по следующим параметрам: Проекту(@ProjectId), Отчетному периоду(@DateBegin, @DateEnd), Профилю(@ProjectProfileId)",
    "entityName": "Project"
}
```

**Когда использовать:** Когда не уверен какие фильтры поддерживает view. Парсить `@(\w+)` из Description.

---

## 4. save_entity — create и update

```python
# CREATE
r = mcp_call(sid, "save_entity", {
    "id": "new",  # литерал "new"
    "entityName": "AttributeValue",
    "data": {
        "DataId": "4595",   # string обязательно
        "EntityId": "46caa4ad-02b8-4d70-a1db-196bab860742",  # Project entity
        "AttributeId": "d78f0b2d-5ec1-4094-9dcb-3bba9f77fc73",  # target attribute
        "AttrValue": '{"test":"json"}'  # JSON as string
    }
})
# Возвращает: {"id": "<uuid>", ...} (id можно использовать для update)

# UPDATE
r = mcp_call(sid, "save_entity", {
    "id": "<existing-uuid>",  # ID существующей записи
    "entityName": "AttributeValue",
    "data": {
        "AttrValue": '{"updated":"json"}'  # только обновляемые поля
    }
})
```

---

## 5. delete_entity — правильный формат

```python
# ✅ РАБОТАЕТ (с 2026-09-01):
r = mcp_call(sid, "delete_entity", {
    "remove": [f"AttributeValue|<id>"]  # формат "EntityName|id"
})
# Возвращает: {"ok": True}

# ❌ НЕ работает:
r = mcp_call(sid, "delete_entity", {
    "entityName": "AttributeValue",
    "id": "<id>"  # дает 400 ошибку "Запись ..."
})

# ❌ Не работает:
r = mcp_call(sid, "delete_entity", {
    "remove": [{"entityName": "AttributeValue", "id": "<id>"}]  # дает 400
})
```

**Проверка удаления:**
```python
r = mcp_call(sid, "get_entity_data", {
    "entityName": "AttributeValue",
    "data_id": "<id>"
})
# Если _error — запись удалена ✅
```

---

## 6. AttributeValue — лимит b-tree

**Лимит:** ~2704 байт на composite индекс `ix_attributevalue_data_entity_attribute`  
**Исправлено:** 2026-09-01 (теперь JSON любого размера сохраняется одной записью)

**UUID сущностей (Project):**
- `EntityId` для Project = `46caa4ad-02b8-4d70-a1db-196bab860742`
- `AttributeId` для "Данные отчета Здоровье проекта" = `d78f0b2d-5ec1-4094-9dcb-3bba9f77fc73`

---

## 7. Инициализация сессии

```python
sid, server_info = mcp_init(client_name="<unique-name>")
# server_info: {"name": "PMForesight MCP", "version": "3.2.4"}

# НЕ закрывать сессию явно — она переиспользуется через pipeline
```

---

## 8. НЕ делай так

| ❌ Неправильно | Почему |
|----------------|--------|
| `viewName = "View?ProjectId=123"` | Ломается после изменений сервера |
| `get_view` без `entityName` | Возвращает метаданные вместо данных |
| `filters={"projectid": 123}` (lowercase) | Не работает — только `ProjectId` |
| `save_entity` без `EntityId` | Не знает к какой сущности привязать |
| `delete_entity` без `EntityName` в `remove` | 400 "Не указано имя сущности" |

---

## 9. Быстрая проверка view

```python
# "Работает ли вообще view X?"
r = mcp_call(sid, "get_view", {
    "entityName": "<entity>", "viewName": "<view>",
    "filters": {},  # без фильтров
    "limit": 5
})
if '_error' in r:
    print(f"❌ {r['_error'][:200]}")
elif rows := r.get('data', []):
    print(f"✅ {len(rows)} строк, keys: {list(rows[0].keys())[:5]}")
```