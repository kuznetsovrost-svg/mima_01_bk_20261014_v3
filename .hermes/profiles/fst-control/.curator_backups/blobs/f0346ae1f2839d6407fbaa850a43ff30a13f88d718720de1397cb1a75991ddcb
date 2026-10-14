# MCP API Quirks — проверенные факты о fst-pmpractice

Это condensed knowledge bank с конкретными примерами из реальных сессий.
Не дублируй upstream-доки — пиши только то, что реально помогло или помешало.

## IdFieldName — не всегда bigint

Большинство сущностей имеют `IdFieldName = "<Entity>Id"` (bigint, но
передаётся строкой цифр в `data_id` / `id`). **Проверяй `IdFieldName`
в `describe_entity` перед первым вызовом.**

Исключения, найденные в работе:

| Entity | IdFieldName | Тип | Как передавать id |
|--------|-------------|-----|-------------------|
| Point | `PointId` | bigint | `"1686"` |
| Project | `ProjectId` | bigint | `"1682"` |
| Activity | `ActivityId` | bigint | `<число строкой>` |
| **MetaModel** | **`Name`** | **text** | **само имя строкой, например `"SomeSettingName"`** |

`MetaModel` (Настройки системы) — это служебная таблица с 2 полями
(`Name` = PK, `Value` = значение), обе `IsReadonly=true` через MCP.
Редактируется только через UI Форсайт.

## MetaModel — schema vs Pydantic runtime mismatch

`describe_entity` для `MetaModel` возвращает схему, в которой `IdFieldName = "Name"`
(строка-тип). Это **противоречит runtime-валидатору Pydantic на уровне MCP-обёртки**:

```python
# describe_entity(MetaModel) → IdFieldName: "Name", Name: {type: "text", ...}
# Но:
get_entity_data(MetaModel, data_id="Title")
# → 1 validation error for call[get_entity_data]
#   data_id: Input should be a valid integer, unable to parse string
#   as an integer [type=int_parsing, input_value='Title', input_type=str]
```

**Симптом**: вместо ожидаемого 404 «запись не найдена» получаешь ошибку
валидации `int_parsing` — Pydantic не пропускает строку, хотя схема
описывает PK как text.

**Workaround'и, которые тоже не работают**:
- `data_id` числовой (`"0"`, `"1"`, `"2"`) → 404 «запись не найдена»
- `list_views(MetaModel)` → возвращает **пустой массив** (у этой сущности
  нет view, нельзя обнаружить ключи)
- `describe_entity(MetaModel, defaultProperties={...})` → `allowed_values: {}`,
  `defaultProperties: null` (нет подсказок)
- `save_entity(MetaModel, id="new")` → `409 Нет доступа создания сущности
  'Настройки системы'`

**Другие сущности ведут себя нормально** — проверял на Point, Project,
Activity, Risk. Проблема только у MetaModel.

**Практический вывод**: для чтения записей `MetaModel` через MCP
нужен либо доступ администратора через UI Форсайт, либо прямой SQL в БД.
Через MCP список записей получить нельзя.

## save_entity — документация vs реальность

Документация (`describe_entity` → tools/list) говорит:

```
- entityName: Системное имя сущности
- data_id: Идентификатор записи
- defaultProperties: Значения полей по умолчанию
```

Реальный API:

```json
{
  "name": "save_entity",
  "arguments": {
    "entityName": "Point",
    "id": "1686",            // не data_id!
    "data": {"Description": "..."}  // не fields / defaultProperties!
  }
}
```

`id` принимает строку цифр (PK) **ИЛИ литерал `"new"`** для создания.

### Симптом ошибки

Если назвал параметры по доке:

```
"4 validation errors for call[save_entity]
 data_id  Unexpected keyword argument
 fields   Unexpected keyword argument
 id       Missing required argument
 data     Missing required argument"
```

### Конкретный успешный вызов (UPDATE)

```bash
REQUEST:
{
  "jsonrpc": "2.0", "id": 4, "method": "tools/call",
  "params": {"name": "save_entity", "arguments": {
    "entityName": "Point",
    "id": "1686",
    "data": {"Description": "Амстердам-экспресс 2026_07_20"}
  }}
}

RESPONSE:
{
  "id": 1686, "PointId": 1686, "Name": "Результаты работ приняты",
  "Description": "Амстердам-экспресс 2026_07_20",
  "ChangeDate": "2026-07-20T17:58:43.843023+03:00",
  "ChangeAuthorId": 120872,
  ...
}
```

## Code vs PointId — реальные примеры

| Что | Тип | Пример |
|-----|-----|--------|
| `Code` | human-readable articlе | `"101-686"` |
| `PointId` | bigint PK в БД | `1686` |

Code формата `<project>-<num>` — для человека, не для API.

`describe_entity(Point, data_id="101-686")` → **400** «Не удалось привести '101-686' к bigint».

Только `describe_entity(Point, data_id="1686")` (PK как строка цифр) работает.

## Поиск записи по Code — единственный путь через view

```python
view = mcp__fst_pmpractice__get_view(entityName="Point", viewName="AllMyPoint")
target = next((r for r in view["data"] if r.get("Code") == "101-686"), None)
if target:
    point_id = target["PointId"]
    # теперь используй point_id для describe_entity / save_entity
```

## Живые id, которые проверены в работе

| Сущность | Id | Code | Имя |
|----------|-----|------|-----|
| Point | 1686 | 101-686 | «Результаты работ приняты» |
| Point.ProjectId (FK) | 1682 | 501-682 | «ФГК Адаптация ИС УПД» |
| Project | 1682 | 501-682 | «ФГК Адаптация ИС УПД» |
| Project | 4034 | 504-034 | «ФГК Сопровождение 2026-2027» |
| Project | 1610 | 501-610 | «ФГК Сопровождение 2023-2026» |
| Project | 1083 | 501-083 | «Вологда 2025 Сопровождение» |
| Текущий пользователь | 120872 | — | Кузнецов Ростислав Владимирович, tekora-c\rkuznetsov, rkuznetsov@pmpractice.ru |

Эти id можно использовать для smoke-теста: `describe_entity(Point, data_id="1686")`
должен сработать.

## describe_entity — два режима

| Вызов | Что вернёт |
|-------|------------|
| `describe_entity(entityName="Point")` | Схема + дефолтные значения для новой записи |
| `describe_entity(entityName="Point", data_id="1686")` | Схема + текущие значения записи |

В обоих случаях ответ: `{"classid", "classname", "classtitle", "entityname", "IdFieldName", "properties": {<Field>: {Title, type, kind, IsRequired, value, ...}}}`

Реальное значение поля у тебя в руках:
`response.properties.<FieldName>.value` — это **актуальное** значение, не схема.

## show_allowed_values — реальное поведение

Сервер принимает параметр, **но реальный смысл имеет только для SingleSelect / MultiSelect**.

Для текстовых полей (`Description`, `Name`) возвращает пустой объект
`allowed_values: {}` — потому что у свободного текста нет справочника.

Для `SingleSelectField` (например `ProjectId`, `PointTypeId`) сервер подгружает
список доступных значений (но только для тех полей, что ты перечислил в
`show_allowed_values`).

## Форматы дат — `dd.MM.yyyy`, не ISO

| Тип в БД | Формат значения | Пример |
|----------|-----------------|--------|
| `date` | `dd.MM.yyyy` | `"31.07.2026"` |
| `timestamp without time zone` | `dd.MM.yyyy HH:mm:ss` или ISO 8601 | `"31.07.2026 18:00:00"` |

В ответах сервер возвращает ISO 8601 с timezone (`2026-07-31T00:00:00+03:00`).
А на вход (`save_entity`) — лучше `dd.MM.yyyy` (proven).

## userId для `PMP_TOKEN`

- Читается из `~/.hermes/profiles/fst-control/.env` → `PMP_TOKEN=***
- Передаётся в `Authorization: Bearer $PMP_TOKEN`
- Сервер **не** принимает `Bearer` в самом значении токена (нужно убрать если есть)
- Срок жизни — обычно дни/недели; при 401 — обновить

## Диагностика серверных ошибок

### HTTP 500 на одной сущности

```
Error calling tool 'describe_entity':
Ошибка запроса к /entity/Project/new?referencesAsObjects=false:
500 — An exception was thrown while activating
PMPractice.Foresight.Controllers.EntityDataController
→ PMPractice.Services.EntityService
```

**Диагноз**: DI-контейнер не смог активировать EntityService для Project.
**Не наша ошибка**, не пробуй ещё раз с другими параметрами.
**Workaround**: работай со связанными сущностями (Point, Activity, Risk)
или попроси пользователя подождать 5-30 минут.

### HTTP 500 на view

```
Error calling tool 'list_views':
Ошибка запроса к /Api/View/List:
500 — An exception was thrown while activating
PMPractice.Foresight.Controllers.ViewController
→ PMPractice.Services.SnapshotService
→ PMPractice.Services.SnapshotUtilsService
→ PMPractice.Services.EntityService
```

**Диагноз**: тоже EntityService, но через стек ViewController.
При `EntityService` Project упал — упадёт и `list_views`,
и `get_view(Project, *)` для **всех 14** view проекта.

### HTTP 500 на ВСЕ операции — сломан корневой EntityService

Когда `EntityService` не активируется вообще, ломается гораздо больше,
чем кажется. Симптомы (наблюдалось 2026-07-21, ~2 часа):

| Endpoint | Состояние |
|----------|-----------|
| `initialize` | ✅ работает |
| `tools/list` | ✅ работает (метаданные без обращения к EntityService) |
| `list_entities` | ✅ работает (справочник из памяти) |
| `get_user_profile` | ❌ 500 (идёт через DocumentFileService → EntityService) |
| `describe_entity(*)` | ❌ 500 |
| `get_entity_data(*)` | ❌ 500 |
| `get_view(*)` | ❌ 500 |
| `list_views(*)` | ❌ 500 |
| `save_entity(*)` | ❌ 500 (предположительно) |
| `delete_entity(*)` | ❌ 500 (предположительно) |

**Hermes говорит `enabled`**, но фактически tools не работают.

**Workaround**: ждать 30-60 минут (вероятно деплой/перезапуск), затем
проверить через `hermes mcp test fst_pmpractice`. Без EntityService
чтение/запись данных невозможны — только `list_entities` и `tools/list`.

## Pydantic validation errors — диагностический паттерн

Pydantic на уровне MCP-обёртки иногда выдаёт ошибки с префиксом
`N validation errors for call[<tool>]` — это **не ошибка сервера,
а локальная валидация параметров перед отправкой**. Проверяй:

| Сообщение | Значит |
|-----------|--------|
| `id: Missing required argument` | Параметр называется `id`, не `data_id` |
| `data: Missing required argument` | Параметр называется `data`, не `fields` |
| `data_id: Unexpected keyword argument` | Используешь старое имя параметра |
| `Input should be a valid integer` | Серверная схема говорит string, но Pydantic ожидает int — MetaModel-баг |
| `Missing required argument` | Забыл обязательный параметр (часто `entityName`) |

Если видишь `N validation errors for call` — это **НЕ** серверная 500.
Это локальная ошибка Pydantic, исправляется переименованием параметров.
