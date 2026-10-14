# MetaModel — рабочий API (РЕШЕНО 2026-08-07)

## Резюме

`MetaModel` («Настройки системы») — это **сущность** с key-value записями.
На 2026-08-07 в ней **3 записи**: `Title`, `Version`, `CoreVersion`.
**Серверного времени в MetaModel нет** — только мета-информация.

## ✅ РАБОТАЕТ: `get_entity_data("metamodel", data_id=<Name>)`

После фикса на сервере (2026-08-07) **get_entity_data** теперь принимает
**строковый** `data_id`. Это единственный надёжный путь к MetaModel.

### Пример вызова

```bash
python3 scripts/mcp_probe.py --tool get_entity_data \
  --args '{"entityName":"metamodel","data_id":"Title"}'
```

```json
{
  "result": {
    "content": [{"type": "text", "text":
      "{\"properties\":{
        \"Name\":{\"value\":\"Title\",\"IsPrimaryKey\":true},
        \"Value\":{\"value\":\"Копия прода для MCP\"}
      }}"...
    }]
  }
}
```

### Что вернет сервер для известных ключей

| `data_id` | `Value` |
|-----------|---------|
| `Title` | `"Копия прода для MCP"` (титул ИС, для раздела 7 «Тех. данные») |
| `Version` | `"Core latest 2022.11.18.1534"` (версия Core) |
| `CoreVersion` | `"2026.8.7.1548"` (production) |
| `CurrentDateTime` / `ServerTime` / `Now` / и т.п. | **400 «Запись не найдена»** |

### Где в коде

- `mcp_config.py` — `METAMODEL_ENTITY = "metamodel"` (lowercase!), `METAMODEL_KEYS = {"title": "Title", "version": "Version", "core_version": "CoreVersion"}`
- `scripts/get_metamodel.py` — CLI-утилита (`python3 scripts/get_metamodel.py --all`)
- `scripts/build_report_header.py` — `get_metamodel_metadata()` собирает 3 ключа после получения `project_name`

### Импортируй из скрипта

```python
import sys
sys.path.insert(0, "scripts")
from get_metamodel import get_metamodel_metadata, get_metamodel_value

# Все 3 ключа сразу
meta = get_metamodel_metadata()
# → {"title": "Копия прода для MCP", "version": "...", "core_version": "..."}

# Один ключ
title = get_metamodel_value("Title")
# → "Копия прода для MCP"
```

---

## ❌ НЕ РАБОТАЕТ: `find_entity` для MetaModel

```bash
python3 scripts/mcp_probe.py --tool find_entity --args '{"name":"Title","limit":50}'
# → {"items":[],"total":0,"limit":50,"offset":0}
```

`find_entity` принципиально **не возвращает MetaModel**:
- Из 152 хитов по `name="ИС"` (по 200 элементов) — **0 MetaModel**.
- Из 50+ других `name` — **0 MetaModel**.
- `find_entity` индексирует сущности `Contractor`, `Point`, `Project`, `InContract`, `Order`, `CourseWork` — **но НЕ MetaModel**.

**Использовать `find_entity` для MetaModel — бесполезно.**

## ❌ НЕ РАБОТАЕТ: `find_entity` с `entityName="metamodel"`

```bash
python3 scripts/mcp_probe.py --tool find_entity \
  --args '{"name":"Title","entityName":"metamodel","limit":50}'
# → 1 validation error for call[find_entity]
#   entityName: Unexpected keyword argument
```

`find_entity` **не принимает** параметр `entityName` — это отдельный pitfall
(см. общий отчёт «Вопросы по MCP 2026_08_07.md», п.2.1).

## ❌ НЕ РАБОТАЕТ: `get_view` для MetaModel

```bash
python3 scripts/mcp_probe.py --tool get_view \
  --args '{"entityName":"metamodel","viewName":"metamodel","limit":3}'
# → Error: Для сущности 'MetaModel' нет доступных представлений.
```

Ни одного view для MetaModel не существует. `get_view` не помогает.

## ⚠️ DEPRECATED: ключи `META_TIME_KEYS` в `mcp_config.py`

```python
META_TIME_KEYS: tuple[str, ...] = (
    "CurrentDateTime", "SystemDate", "ServerTime", "Now",
)
```

Исторически скилл пытался достать **серверное время** из MetaModel.
**На 2026-08-07 НИ ОДНОГО из этих ключей в MetaModel не существует** —
все возвращают «Запись не найдена». Серверного времени в MetaModel нет.

`META_TIME_KEYS` оставлено для обратной совместимости, но **использовать для времени нельзя**.
Время берётся через `datetime.now()` локально (см. `build_report_header.py: get_server_time`).

---

## История изменений

| Дата | Состояние | Что дальше |
|------|-----------|-----------|
| 2026-08-05 | `find_entity` для MetaModel — Pydantic validation error | Не работало |
| 2026-08-06 | `find_entity` ничего не возвращает, `get_view` нет view, `get_entity_data` ломается по SQL | Зафиксировано в обращении к разработчикам |
| 2026-08-07 (фикс разработчиков) | `get_entity_data("metamodel", data_id=<Name>)` работает для `Title` и `Version` | **Рабочий API есть** |
| 2026-08-07 (дополнительно) | Нашли `CoreVersion` через тот же API | 3-я запись |

## Совместимость с предыдущими версиями

В `SKILL.md` pitfall #12 описан старый подход. После live-проверки 2026-08-07
pitfall #12 **РЕШЁН**. Замените в скриптах:

```python
# ❌ Старый подход (НЕ работает):
mcp_call(sid, "find_entity", {"name": "Title", "limit": 1})
# → {"items":[],"total":0}

# ✅ Новый подход (работает):
mcp_call(sid, "get_entity_data", {"entityName": "metamodel", "data_id": "Title"})
# → {"properties":{"Value":{"value":"Копия прода для MCP"}}}
```

Если в вашем коде остался `find_entity` для MetaModel — замените на `get_entity_data("metamodel", data_id=...)`.
