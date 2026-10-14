# JSON отчётов о здоровье проекта в MCP (AttributeValue)

**Дата:** 2026-08-22
**Назначение:** Сохранение JSON-отчётов в MCP для последующего использования (тренды, аналитика).

---

## Зачем это нужно

Skill `fst-project-health` генерирует JSON-отчёты (по модели из `versioned-json-data-model`). Чтобы:
1. **Сохранять историю** — отчёты по разным датам
2. **Строить тренды** — будущий skill `fst-project-trends`
3. **Анализировать** — сравнивать проекты между собой

нужно где-то хранить эти JSON. **MCP-сервер Форсайт** позволяет сохранять произвольные данные через сущность `AttributeValue`.

---

## Какие сущности используются

| Сущность | UUID | Что делает |
|----------|-----|------------|
| `Project` | `46caa4ad-02b8-4d70-a1db-196bab860742` | Родительский объект для DataId |
| `Attribute` | `d78f0b2d-5ec1-4094-9dcb-3bba9f77fc73` | "Данные отчета Здоровье проекта" |
| `AttributeValue` | `cb750276-58b1-4a65-a71d-a81a6aac2727` | Хранилище значения атрибута |

---

## Как записать JSON в AttributeValue

### Полный JSON (если помещается)

```python
mcp_call(sid, "save_entity", {
    "id": "new",
    "entityName": "AttributeValue",
    "data": {
        "DataId": str(project_id),          # "4314" для 504-314
        "EntityId": "46caa4ad-02b8-4d70-a1db-196bab860742",  # Project
        "AttributeId": "d78f0b2d-5ec1-4094-9dcb-3bba9f77fc73",  # AI
        "AttrValue": json.dumps(json_data, ensure_ascii=False),  # ПОЛНЫЙ JSON как строка
    },
})
```

### Split (если JSON > ~1200 Cyrillic chars)

**Почему split:** PostgreSQL b-tree лимит = **2704 bytes**. Кириллица в UTF-8 = **2 байта на букву**. Реальный лимит на `AttrValue` для русского JSON ≈ **1200 символов**.

Разбиваем по секциям:
- `_meta` (маленький, всегда проходит)
- `summary` (~400 chars)
- `metadata` (~200 chars)
- `s4`, `s6`, `s7`, `s8` (маленькие секции)
- `s3` (большой — делим на `s3_part1`, `s3_part2`, ...)
- `s5` (большой — аналогично)

Каждая часть = отдельный `AttributeValue` с разным `AttrValueSource`:

```python
mcp_call(sid, "save_entity", {
    "id": "new",
    "entityName": "AttributeValue",
    "data": {
        "DataId": str(project_id),
        "EntityId": "46caa4ad-02b8-4d70-a1db-196bab860742",
        "AttributeId": "d78f0b2d-5ec1-4094-9dcb-3bba9f77fc73",
        "AttrValueSource": "s3_part1",  # имя части
        "AttrValue": json.dumps(part_data, ensure_ascii=False),
    },
})
```

**Формат части (split):**
```json
{
    "_part_name": "s3_part1",
    "_part_data": {
        "verdict": "Болен",
        "counts": {"critical": 4, "warning": 6, "info": 0},
        "remarks": [
            {"code": "104-318", "name": "...", ...}
        ]
    }
}
```

**Формат полного (full):**
```json
{
    "_meta": {"schema_version": "0.1.0", "project_code": "504-314", ...},
    "summary": {...},
    "sections": {"s3": {...}, "s4": {...}, ...},
    "metadata": {...}
}
```

---

## Как прочитать обратно

```python
resp = mcp_call(sid, "get_view", {
    "entityName": "AttributeValue",
    "viewName": "AttributeValue",
    "limit": 500
})

target_records = []
for row in resp.get("data", []):
    if str(row.get("DataId")) == str(project_id):
        target_records.append(row)

# Парсим каждую запись
parts = {}
for row in target_records:
    raw = row.get("AttrValue", "")
    if not raw:
        continue
    data = json.loads(raw)
    # full JSON?
    if "_meta" in data and "summary" in data and "sections" in data:
        parts["_full"] = data
    # split-format с _part_data
    elif "_part_data" in data and isinstance(data["_part_data"], dict):
        source = data.get("_part_name") or row.get("AttrValueSource")
        parts[source] = data["_part_data"]

# Собираем полный JSON (или берём _full если есть)
if "_full" in parts:
    full_json = parts["_full"]
else:
    full_json = reassemble(parts)  # см. scripts/build_html_from_mcp.py
```

---

## Live-probe замеры (2026-08-22)

| Проект | Полный JSON | Split частей | Успех | Время записи |
|--------|-----------:|-------------:|:-----:|-------------:|
| 504-595 (ProjectId=4595) | 6.3 КБ | — | ✅ | 1.27 сек |
| 504-314 (ProjectId=4314) | 12.5 КБ | 7 частей | ✅ | 5.67 сек (split) |
| 503-434 (ProjectId=3434) | 15.4 КБ | 7 частей | ✅ | 5.67 сек (split) |
| 503-152 (ProjectId=3152) | 59.0 КБ | 9/17 частей | ⚠️ | 7.19 сек (большие s3/s5) |

**Узкое место:** для больших JSON (>15 КБ) некоторые chunks `s3_part1` / `s5_part1` всё равно превышают лимит из-за длинных наименований КТ на русском (UTF-8 = 2 байта/букву).

**Рекомендация для будущего:** делить большие секции на части по **5 строк** (а не 20), чтобы каждый chunk был < 1200 chars.

---

## Скрипты (живые примеры)

| Скрипт | Где | Что делает |
|--------|-----|-----------|
| `scripts/upload_json_to_mcp.py` | `/tmp/project-json-design/scripts/` | Загрузка полного JSON в MCP |
| `scripts/upload_split.py` | `/tmp/project-json-design/scripts/` | Split-загрузка (для больших) |
| `scripts/build_html_from_mcp.py` | `/tmp/project-json-design/scripts/` | Чтение из MCP → MD → HTML |

---

## Связь с versioned-json-data-model

Эта техника — **частный случай** skill `versioned-json-data-model` (Persisting to MCP секция). Там же есть полный playbook из 10 pitfalls (b-tree лимит, форматы записи, `_meta` провинация). Этот файл — **конкретизация** для health-отчётов.

**Принципы:**
1. `_meta.schema_version` — обязательно (для обратной совместимости)
2. `AttrValueSource` — помогает читателю собрать split-format
3. Не делать `delete_entity` — сервер возвращает 500 (append-only assumption)

---

## TODO (когда пользователь одобрит интеграцию в скилл)

1. Добавить шаг "сохранить JSON в MCP" в `scripts/run_all.py` после `rebuild_md`
2. Перенести скрипты `/tmp/project-json-design/scripts/*.py` в `fst-project-health/scripts/`
3. Создать playbook для оператора: "когда загружать, как читать, что делать если не помещается"

Пока НЕ ТРОГАЕМ скилл — ждём явного одобрения.
