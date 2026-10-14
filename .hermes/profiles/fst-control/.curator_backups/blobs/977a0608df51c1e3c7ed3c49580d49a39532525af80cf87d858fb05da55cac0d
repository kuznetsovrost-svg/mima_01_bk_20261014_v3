# MCP methods (полный список) и оптимизация через get_entity_data

Дата фиксации: 2026-09-03

## Полный список MCP-методов (12 штук)

Получен через прямой вызов `tools/list` MCP-сервера.

| Метод | Назначение | Ключевые параметры |
|-------|-----------|-------------------|
| `get_user_profile` | Информация о текущем пользователе | — |
| `describe_entity` | JSON-схема + справочники | `entityName`, `data_id`, `show_allowed_values` |
| `save_entity` | Создание/обновление доку |
| `delete_entity` | Удаление (формат: `remove=["Entity\|id"]`) |
| `list_entities` | Список типов сущностей |
| `upload_entity_file` | Загрузка файла документа |
| **`get_entity_data`** | **Значения полей сущности по dataId** | `entityName`, **`data_id` (snake_case, string)** |
| `find_entity` | Быстрый поиск по имени |
| `list_files` | Список файлов документа |
| `get_file_info` | Метаданные файла |
| `list_views` | Список представлений (238) |
| `get_view` | Данные представления (основной) |

## Почему get_entity_data важен

В `describe_entity(Project)` есть поля, которые **НЕ выводятся ни в одном view**:
- `PresaleLimit` — Лимит на пресейл, руб.
- `PresaleBudgetPercentage` — % пресейла от бюджета
- `ProjectLimit` — Допущения/ограничения проекта
- `DirectProjectCostsGrade` — Прямые затраты проекта (оценка)
- `ProjectBudgetGrade` — Бюджет проекта (оценка)

Все эти поля доступны только через `get_entity_data`!

## Паттерн вызова

```python
r = mcp_call(sid, "get_entity_data", {
    "entityName": "Project",
    "data_id": str(project_id),  # ⚠️ snake_case + string!
})
# r["properties"]["PresaleLimit"]["value"] = 2_700_000.0
# r["properties"]["PresaleBudgetPercentage"]["value"] = 5.0
```

⚠️ **Gotcha:** параметр называется `data_id` (snake_case), не `dataId`. Значение — строка.

## Оптимизация: замена ProjectParameter на get_entity_data

### Проблема

Каждый индикатор 6.x делал отдельный запрос к `ProjectParameter` view для получения дат периода, стадии ЖЦ, типа проекта, и т.п.

- 14+ вызовов `ProjectParameter` на один отчёт
- Каждый вызов = 1 HTTP-запрос с TLS-handshake

### Решение

Один вызов `get_entity_data` → все свойства проекта:

```python
# scripts/project_indicators.py::fetch_with_cache
def fetch_with_cache(sid, entity_name, view_name, filters, project_id, limit=1000):
    # Sentinel — оптимизация
    if view_name == "_get_entity_data_" and entity_name == "Project":
        return [_get_project_card_cached(sid, project_id)]
    
    # Обычная логика для views
    ...
```

### Использование в индикаторах

Заменить только `view_name` в вызовах `fetch_with_cache`:

```python
# Было
param_rows = fetch_with_cache(sid, "Project", "ProjectParameter", ...)

# Стало
param_rows = fetch_with_cache(sid, "Project", "_get_entity_data_", ...)
```

### Результат (live-probe 2026-09-03)

| Проект | Без оптимизации | С оптимизацией (1-й) | С кешем (2-й) |
|--------|-----------------:|---------------------:|--------------:|
| 504-595 | ~22 сек | 27.23 сек | **8.40 сек (-69%)** |
| 503-152 | ~70 сек | 41.88 сек | **8.60 сек (-79%)** |

**Эффект:** первый запуск примерно такой же (создаётся кеш), второй запуск **в 3-5 раз быстрее** за счёт дискового кеша `/tmp/.cache_project_card_<pid>.json` (TTL=5 мин).

### Дополнительное исправление

При замене нужно обновить и способ получения project:

```python
# ❌ Старый код (ломается после оптимизации)
param = next(
    (r for r in rows if str(r.get("code", "")).strip() == project["code"]),
    None
)

# ✅ Новый код — param_rows содержит 1 запись = текущий проект
param = param_rows[0] if param_rows else {}
```

## MCP SSE response format

MCP возвращает `application/json, text/event-stream`:

```
event: message
data: {"jsonrpc":"2.0","id":1,"result":{"tools":[...]}}
```

Парсинг:
```python
for line in resp.text.split('\n'):
    if line.startswith('data:'):
        payload = json.loads(line[5:].strip())
        # payload["result"]["content"][0]["text"] — это двойной JSON
```

## Пример: чтение значения свойства

```python
def get_project_property(sid, project_id, property_name):
    r = mcp_call(sid, "get_entity_data", {
        "entityName": "Project",
        "data_id": str(project_id),
    })
    if isinstance(r, dict) and "properties" in r:
        prop = r["properties"].get(property_name, {})
        if isinstance(prop, dict):
            return prop.get("value")
    return None

# Использование
presale_limit = get_project_property(sid, 4595, "PresaleLimit")  # 2_700_000
```

## Альтернатива: get_project_card() с кешем

Для случая когда нужно много свойств — используй `get_project_card()`:

```python
def get_project_card(sid, project_id, project_code=None) -> dict:
    """Получает ВСЕ свойства проекта одним запросом, с кешем 5 мин."""
    # ... кеш в /tmp/.cache_project_card_<pid>.json ...
    # возвращает {"ProjectBudgetGrade": 54_000_000, "PresaleLimit": 2_700_000, ...}
```

## Когда использовать get_entity_data vs get_view

| Ситуация | Использовать |
|----------|-------------|
| Нужен список КТ, бюджет, трудозатраты | `get_view` |
| Нужен один конкретный проект со всеми свойствами | `get_entity_data` |
| Поле есть в модели но не в view | `get_entity_data` (единственный способ) |
| Нужна оптимизация pipeline | `get_entity_data` + кеш |

## Pitfall #154 (NEW 2026-09-03): НЕ делай параллельные MCP-запросы

Когда хочется ускорить множественные запросы (например, для каждого исполнителя проекта по `accountid`):

```python
# ❌ НЕ работает — MCP не выдерживает параллельную нагрузку
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(fetch_user_rows, item): item[0] for item in users}
    for future in as_completed(futures):
        rows = future.result()  # TimeoutError!
```

**Ошибка:** `requests.exceptions.ReadTimeout: HTTPSConnectionPool ... Read timed out (read timeout=60)`.

**Решение:** делай запросы **последовательно** (по одному). MCP-сервер не оптимизирован под параллельные запросы от одного клиента.

```python
# ✅ Последовательно
all_rows = []
for username, accountid in users.items():
    if not accountid: continue
    user_rows = fetch_with_cache(sid, "Project", "ProjectResourcePlan",
                                 filters={"accountid": accountid}, ...)
    all_rows.extend(user_rows)
```

**Альтернатива:** использовать **accountid-based фильтрацию** вместо `ProjectId`-based (Pitfall #155).

## Pitfall #155 (NEW 2026-09-03): per-accountid фильтрация для cross-project queries

Когда индикатор требует данные по **исполнителю во всех его проектах** (например, 6.7 «Суммарная перегрузка»):

**❌ Неправильно:** `get_view(ProjectResourcePlan, filters={})` — получит ВСЕ строки по ВСЕМ проектам. С лимитом 10000 не хватит для пользователей с 200+ проектами.

**✅ Правильно:** `get_view(ProjectResourcePlan, filters={"accountid": <id>})` — получит строки **только для одного исполнителя** во всех его проектах. Количество запросов = число исполнителей (2-15), а не число проектов.

**Реализация в 6.7:**

```python
# Получаем список исполнителей текущего проекта
current_rows = fetch_with_cache(sid, "Project", "ProjectResourcePlan",
                               filters={"ProjectId": project_id}, ...)
# ...extract username -> accountid mapping...

# Для КАЖДОГО исполнителя — отдельный запрос с фильтром по accountid
all_rows = []
for username, accountid in real_users.items():
    if not accountid: continue
    user_rows = fetch_with_cache(sid, "Project", "ProjectResourcePlan",
                                 filters={"accountid": accountid},
                                 project_id=accountid, limit=2000)
    all_rows.extend(user_rows)
```

**Live-probe 2026-09-03:**
- `filters={"accountid": 120872}` (Кузнецов) → 10 строк в 3 проектах. Работает.
- Время: линейно от числа исполнителей (~5 сек на запрос). 12 исполнителей = 60 сек.
