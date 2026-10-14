# Playbook: методы MCP, используемые в скилле `fst-project-health`

**Версия:** 1.0.0 — 2026-09-06
**Назначение:** единый справочник по всем инструментам MCP-сервера
`ppreplica.hera.pmpractice.ru`, которые скилл `fst-project-health` вызывает
при построении отчёта «Здоровье проекта». По каждому методу указано: что
это, в какой секции/показателе применяется, с какими параметрами, и в каких
скриптах он встречается.

---

## Часть 1. Общий обзор транспорта и сессии

### 1.1. Протокол: MCP (Model Context Protocol) через SSE/HTTP

Сервер PMForesight MCP (`ppreplica.hera.pmpractice.ru:443`) реализует
MCP-2024-11-05 поверх `POST https://…/mcp` с `Content-Type: application/json`
и `Accept: application/json, text/event-stream`. Ответ приходит в формате
**Server-Sent Events** (SSE): поток строк вида

```
event: message
data: {"jsonrpc":"2.0","id":1,"result":{...}}

```

Внутри каждого SSE-сообщения — обычный JSON-RPC 2.0 envelope. Парсер
отбрасывает префикс `data: ` и скармливает остаток в `json.loads`.

### 1.2. Жизненный цикл сессии

1. **`initialize`** → получить `mcp-session-id` из заголовка ответа.
2. **`notifications/initialized`** (без ответа) — best-effort, можно не ждать.
3. **`tools/call`** — все дальнейшие вызовы инструментов с заголовком
   `mcp-session-id: <sid>`.

Реализация — `scripts/mcp_config.py::mcp_init()` + `mcp_call()`. Каждая
сессия — одна HTTP-сессия с `requests.Session()`. Переиспользовать сессию
**обязательно** — это даёт +30 % производительности (Pitfall из
`references/run-all-pitfalls-2026-08-22.md`).

### 1.3. Двойное кодирование `result.content[0].text`

Сервер возвращает JSON-результат **дважды сериализованным**: `result` —
это `{content: [{type: "text", text: "<JSON-строка>"}]}`. Чтобы получить
Python-объект, делаем `json.loads(result["content"][0]["text"])`.

Реализация — `mcp_config.py::mcp_call()`, последняя строка тела функции.
**Не пытаться** парсить `result` напрямую — там будет строка.

### 1.4. Таймауты

| Параметр | Константа | Где | Значение |
|---|---|---|---|
| HTTP read для `initialize` | `TIMEOUT_INITIALIZE` | `mcp_config.py:154` | 30 с |
| HTTP read для `tools/call` | `TIMEOUT_TOOLS_CALL` | `mcp_config.py:155` | 60 с |
| `notifications/initialized` | литерал `10` | `mcp_config.py:415` | 10 с |

**При больших проектах** (504-595 — тысячи строк в
`ProjectResourcePlan` / `ProjectBudgetCompleteBusiness`) дефолтные 60 с
могут быть недостаточны: `get_entity_data` падает с `ReadTimeoutError`.
Два способа увеличить таймаут (см. подробнее в SKILL.md, раздел
«Common workflows → Large projects»):

1. **`mcp_call(timeout=180, …)`** — параметр `timeout` уже поддержан
   в `mcp_config.py::mcp_call(timeout: int = TIMEOUT_TOOLS_CALL)`.
2. **`sed` константы** в `mcp_config.py`: `TIMEOUT_TOOLS_CALL: int = 60`
   → `TIMEOUT_TOOLS_CALL: int = 180`. После правки — удалить
   `__pycache__` (Pitfall #199).

### 1.5. Авторизация

Заголовок `Authorization: Bearer <PMP_TOKEN>`. Токен — JWT, поля
payload используются для:

- **Аутентификация** — каждая сессия.
- **`displayname`** — ФИО текущего пользователя в секции 7 отчёта
  (Pitfall #213). Парсится через `get_current_user_from_token()`.

Файл `.env` ищется в порядке (Pitfall #225):

1. `<каталог скилла>/.env` (portable-режим).
2. `~/.hermes/profiles/fst-control/.env` (Hermes-режим).
3. `os.environ["PMP_TOKEN"]` (если уже выставлен в shell).

---

## Часть 2. Сводная таблица: методы MCP, используемые скиллом

| # | Метод MCP | Сигнатура (как вызываем) | Скрипты, где встречается |
|---|---|---|---|
| 1 | `initialize` | `mcp_init()` → `(sid, serverInfo)` | `mcp_config.py` + все скрипты-индикаторы |
| 2 | `notifications/initialized` | внутри `mcp_init()` после успешного init | `mcp_config.py` |
| 3 | `tools/call` с инструментом `get_view` | `mcp_call(sid, "get_view", args)` | `run_all.py`, `project_indicators.py`, `build_report_header.py`, `get_effort.py`, `get_project_budget.py`, `find_project_by_code.py`, `mcp_config.py` |
| 4 | `tools/call` с инструментом `get_entity_data` | `mcp_call(sid, "get_entity_data", args)` | `run_all.py`, `project_indicators.py`, `build_report_header.py`, `get_metamodel.py`, `mcp_config.py` |
| 5 | `tools/call` с инструментом `find_entity` | `mcp_call(sid, "find_entity", args)` | `build_report_header.py` |
| 6 | `tools/call` с инструментом `get_user_profile` | вызывается для логов (аккаунт/роль), НЕ для отчёта | `fetch_snapshot.py`, `run_snap_md.py` |
| 7 | `tools/call` с инструментом `upload_entity_file` | загрузка MD/JSON в карточку проекта | `run_snap_md.py::upload_to_mcp`, `run_snapshot.py::upload_to_mcp` |
| 8 | `tools/call` с инструментом `list_files` | список файлов в категории документа карточки | `fetch_snapshot.py::list_snapshots` |
| 9 | `resources/read` (uri `file://download-file/{physicalFileId}`) | скачивание MD из MCP как base64-blob | `fetch_snapshot.py::download_md` |
| 10 | `tools/call` с инструментом `get_file_info` | метаданные (mimeType, contentMode=bytes/url) | `fetch_snapshot.py::download_md` (fallback при пустом blob) |

**Round-trip pattern (NEW, 2026-09-24):** для любой записи файла в MCP
через `upload_entity_file` канонический тест — **записать → прочитать
обратно → sha256 должен совпасть байт-в-байт**. Реализация в
`fst-project-health-snap-md` / `fst-project-health-from-md-snapshot`:
загрузка через `upload_entity_file` + чтение через `list_files` →
`get_file_info` → `resources/read file://download-file/{physicalFileId}`.
Если hash'ы не совпали — MCP сервер модифицирует содержимое при
передаче (на PMForesight этого не наблюдается, но проверять обязательно
каждый раз при смене версии MCP или формата файла).

Остальные (`list_views`, `list_entities`, `describe_entity`,
`save_entity`, `delete_entity`, `list_prompts`, `get_prompt`) —
используются интерактивно через `mcp__fst_pmpractice__*` инструменты в
режиме отладки.

---

## Часть 3. По методу

### 3.1. `initialize`

**Что это (по спецификации MCP-2024-11-05):** инициализация сессии
клиента и сервера. Клиент передаёт свою версию протокола и capabilities,
сервер возвращает свой `serverInfo` (имя, версия) и `mcp-session-id`.

**Где используется в скилле:** первый шаг любого скрипта, который
ходит в MCP. Без `initialize` сервер не выдаст `session-id` и отклонит
все `tools/call`.

**Параметры вызова:**

```python
mcp_init()  # в mcp_config.py:373-420
# читает токен из env, отправляет:
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "fst-project-health", "version": "1.0"},
    },
}
# → возвращает (sid: str, serverInfo: dict)
```

**Возвращает:**

- `str` — `mcp-session-id` (из заголовка HTTP-ответа).
- `dict` — `serverInfo` сервера (например, `{"name": "pmp-mcp", "version": "x.y.z"}`).
  Внимание: это **сервер**, не пользователь. Для ФИО пользователя
  используется JWT (см. `get_current_user_from_token`, Pitfall #213).

**Скрипты:** `scripts/mcp_config.py` (определение); все остальные
скрипты (`run_all.py`, `project_indicators.py`, `build_report_header.py`,
`get_effort.py`, `get_project_budget.py`, `find_project_by_code.py`,
`get_metamodel.py`) делают `from mcp_config import mcp_init, mcp_call`
и стартуют через `sid, _ = mcp_init()`.

**Edge cases:**

- Если сервер не вернул `mcp-session-id` → исключение `McpConnectionError`.
- `notifications/initialized` отправляется **best-effort** (без raise) —
  сервер не обязан на него отвечать.

---

### 3.2. `notifications/initialized`

**Что это:** уведомление (без `id`, без ожидания), которое клиент
отправляет серверу после успешного `initialize`. Подтверждает, что
клиент готов к работе.

**Где используется:** внутри `mcp_init()` сразу после получения
`mcp-session-id`.

**Скрипты:** `mcp_config.py:411-417`.

**Edge cases:** `requests.RequestException` глотается — уведомление
не критично для работы.

---

### 3.3. `get_view`

**Что это (по MCP-серверу PMForesight):** загружает данные представления
(view) для указанной сущности. View — это плоская проекция
сущности с преднастроенным набором колонок и фильтрами.

**Где используется:** основной метод чтения данных. ~70 % всех вызовов
MCP в скилле.

**Параметры (как вызываем):**

```python
mcp_call(sid, "get_view", {
    "entityName": "<Entity>",      # обязательно
    "viewName":   "<View>",        # обязательно
    "filters":    {...},           # опц., см. ниже
    "limit":      N,           # опц., default 1000
    "offset":     N,           # опц., default 0
})
```

**Поддерживаемые фильтры:** зависят от view. Практически всегда
поддерживается `ProjectId` (число). Другие фильтры — см.
`list_views(entityName=...)` интерактивно.

**Что возвращает:** `{"result": [...строки...]}` или
`{"data": [...]}` — зависит от view. Большинство view возвращает
список словарей, где ключи — это системные имена колонок (`PlanDate`,
`ForecastDate`, `FactDate`, `BudgetType`, и т.п.).

**Куда в скилле — по разделам отчёта (в порядке, как они идут в отчёте):**

> Детали по каждому разделу — см. **Часть 7** (подробный обход разделов
> в каноническом порядке: 1 → 3 → 4 → 5 → 6 → 7 → 8) и **Часть 3.3**
> (полный разбор 16 индикаторов раздела 6).

| Раздел отчёта | View, которые вызываются | Скрипт + функция |
|---|---|---|
| Заголовок / поиск проекта по коду | `Project/MyProject`, `Project/AllProject` | `find_project_by_code.py::find_project` |
| Заголовок / шапка отчёта | `Project/MyProject`, `MetaModel` (через `find_entity` + `get_entity_data`) | `build_report_header.py::build_report_header`, `get_metamodel_metadata` |
| Заголовок / ресурсный план | `Project/ProjectResourcePlan` | `build_report_header.py::get_effort_summary` |
| Заголовок / бюджет | `Project/ProjectBudgetCompleteBusiness` | `build_report_header.py::get_project_budget_summary` |
| Заголовок / карточка проекта | `Project` (через `get_entity_data`) | `build_report_header.py::get_project_name_by_id` |
| Раздел 3 «Замечания по срокам» | `Point/AllMyPoint` | `run_all.py::load_project_points` → `build_section_3` |
| Раздел 4 «Полнота заполнения проекта» | `Project/ProjectHealthCostMy` + `Project` (через `get_entity_data`) | `run_all.py::build_section_4` |
| Раздел 5 «Актуальность прогнозов» | `Point/AllMyPoint` (уже загружены в разделе 3) | `run_all.py::build_section_5` |
| Раздел 6 «Финансовый статус» (до v1.0.0) | `Project/ProjectHealthCostMy` | `run_all.py::build_section_6` |
| **Раздел 6 «Показатели проекта» (16 индикаторов)** | разные view по каждому показателю | `project_indicators.py::check_*` (см. таблицу ниже) |
| Раздел 7 «Технические данные отчёта» | `MetaModel` (title/version/core_version) | `build_report_header.py::get_metamodel_metadata`, `get_server_time` |
| Раздел 8 «Сводка по разделам 3–7» | — (агрегация уже собранных данных) | `run_all.py::build_section_8` |

**Полный список view, вызываемых из `project_indicators.py`** (через
обёртку `fetch_with_cache(sid, entity, view, filters, project_id)`):

| View | Entity | Назначение | Показатели |
|---|---|---|---|
| `_get_entity_data_` (алиас для `get_entity_data`) | Project | карточка проекта (метаданные) | 6.1, 6.2, 6.3, 6.4, 6.5, 6.7, 6.15, 6.16 |
| `AllMyPoint` | Point | все КТ уровня проекта (`ParentEntityName=Project`) | 6.2, 6.3, 6.4, 6.5, 6.7, 6.13, 6.14, 6.15, 6.16 |
| `AllFinancePoint` | Point | финансовые КТ (`ParentEntityName=InContract`) | 6.8 (Pitfall #214) |
| `ProjectResourcePlan` | Project | ресурсный план (план/прогноз по исполнителям и периодам) | 6.3, 6.4, 6.5, 6.6, 6.7, 6.13, 6.14 |
| `ProjectBudgetCompleteBusiness` | Project | бюджет проекта (план/факт/прогноз по статьям) | 6.10, 6.11, 6.12, 6.13, 6.14, 6.16 |
| `MyProject` | Project | расширенная карточка проекта | 6.8, 6.9, 6.15 |
| `InContractBudgetBusiness` | InContract | финансовый поток по контрактам | 6.9 (акты/оплаты) |
| `ApprovedBudget` | Project | утверждённый бюджет по годам | 6.13 (Pitfall по году) |

**Подробности по показателям:**

#### 6.1 «Юрлицо проекта/пресейла указано»

- Метод: `get_view` НЕ вызывается напрямую; читает
  `presale_juridicalperson` из карточки проекта
  (через `get_entity_data`, см. ниже).

#### 6.2 «Актуальность состояния ЖЦ»

- `Point/AllMyPoint` — КТ уровня проекта.
- `_get_entity_data_` — карточка проекта (стадия ЖЦ).

#### 6.3 «Прогнозы по ресурсам заданы»

- `Project/ProjectResourcePlan` — `forecast_hours` за каждый месяц.
- `Point/AllMyPoint` — связь КТ с месяцами.

#### 6.4 «Плановые трудозатраты заданы»

- `Project/ProjectResourcePlan` — `plan_hours` за каждый месяц.
- `Point/AllMyPoint` — связь КТ с месяцами.

#### 6.5 «Прогнозы ресурсов на исполнителя не превышают 100%»

- `Project/ProjectResourcePlan` — нормативы по ролям.
- `Point/AllMyPoint` — трудозатраты по КТ.

#### 6.6 «Есть нереализованные прогнозы по ролевым ресурсам»

- `Project/ProjectResourcePlan` — `forecast_hours` по ролям без
  привязки к исполнителю.

#### 6.7 «Есть исполнители у которых прогноз в сумме с др.активностями > 100%»

- `Project/ProjectResourcePlan` — `forecast_hours` с фильтром по
  `projectid` (lowercase! Pitfall #196) и по всем проектам.
- `Point/AllMyPoint` — для уточнения «по проекту отчёта».

#### 6.8 «Соблюдение сроков финансовых КТ»

- `Point/AllFinancePoint` — финансовые КТ с
  `ParentEntityName=InContract` (Pitfall #216).
- `Project/MyProject` — для дат контрактов.

#### 6.9 «Суммы актов и оплат»

- `Project/MyProject` — карточка проекта.
- `InContract/InContractBudgetBusiness` — финансовый поток.

#### 6.10 «В бюджете указаны прямые затраты»

- `Project/ProjectBudgetCompleteBusiness` — статьи бюджета с
  `budgettype="Прямые затраты"`.

#### 6.11 «В затратах указан НДС»

- `Project/ProjectBudgetCompleteBusiness` — статьи с
  `financesourceid` (НДС).

#### 6.12 «Сумма НДС расчётная»

- `Project/ProjectBudgetCompleteBusiness` — `budgettype="Доходный
  контракт"` + `budgettype="Расход ручной ввод"` с `fs=128`
  (статья 611-13).

#### 6.13 «Бюджет проекта/пресейла»

- `Project/ProjectBudgetCompleteBusiness` — лимиты.
- `Project/ApprovedBudget` — утверждённые суммы по годам.

#### 6.14 «Расход лимита пресейла»

- `Project/ProjectBudgetCompleteBusiness` — фактический расход по
  пресейлу.

#### 6.15 «У проекта есть утверждённый бюджет»

- `Project/ApprovedBudget` — записи по годам.

#### 6.16 «Проставлены метки для отнесения КТ к проекту или пресейлу»

- `Point/AllMyPoint` — наличие меток `IsPresale` и т.п.
- `Project/ProjectBudgetCompleteBusiness` — статьи с метками.

**Скрипты:** `run_all.py`, `project_indicators.py`,
`build_report_header.py`, `get_effort.py`, `get_project_budget.py`,
`find_project_by_code.py`, `mcp_config.py`.

**Edge cases:**

- При первом запуске (без кэша) `get_view` для крупного проекта
  (504-595 — несколько тысяч строк `ProjectResourcePlan`) может
  упасть по таймауту 60 с → увеличить `TIMEOUT_TOOLS_CALL` до 180.
- Фильтры передаются **как поля верхнего уровня** в JSON-RPC, не
  как `params.filters`. Сервер сам разбирает, что именно фильтровать.
- `get_view` без `filters` иногда возвращает **лимит строк** меньше,
  чем реально в системе (Pitfall из `references/mcp-filters-format.md`).
  Всегда фильтровать по `ProjectId`/`ActivityId`.

---

### 3.4. `get_entity_data`

**Что это (по MCP-серверу PMForesight):** возвращает полную запись
сущности по её `dataId` (числовой идентификатор). Используется, когда
нужны поля, **не выведенные** в view (Pitfall #211 — например,
`PresaleLimit`, `PresaleBudgetPercentage`, `DirectProjectCostsGrade`,
`presale_juridicalperson`).

**Где используется:** точечное чтение свойств, которых нет в view.
~20 % всех вызовов.

**Параметры:**

```python
mcp_call(sid, "get_entity_data", {
    "entityName": "<Entity>",   # обязательно
    "data_id":    "<int_id>",   # обязательно (именно data_id, не id!)
})
```

**Возвращает:** словарь всех атрибутов сущности (включая
системные: `Id`, `Name`, `Code`, `CreatedOn`, `ModifiedOn`, и т.д.).

**Куда в скилле:**

| Секция / показатель | Скрипт + функция |
|---|---|
| Заголовок отчёта (метаданные проекта) | `build_report_header.py::build_header` |
| Раздел 1 «Замечания по срокам» (доп. свойства) | `run_all.py::save_project_json`, `build_section_4` |
| 6.1 «Юрлицо проекта/пресейла» | `project_indicators.py::check_jurlico` через `_get_project_card_cached` |
| 6.2 «Актуальность ЖЦ» | `project_indicators.py::check_lifecycle_stage` |
| 6.3, 6.4 (метаданные для расчёта) | `_get_project_card_cached` |
| 6.5, 6.7 (метаданные) | `_get_project_card_cached` |
| 6.15, 6.16 (метаданные) | `_get_project_card_cached` |
| Поиск `MetaModel` (для подписей полей) | `get_metamodel.py::get_metamodel_entity` |

**Скрипты:** `run_all.py`, `project_indicators.py`,
`build_report_header.py`, `get_metamodel.py`, `mcp_config.py`
(обёртки `get_project_property`, `_get_project_card_cached`).

**Edge cases:**

- **Pitfall #159:** `project_id=accountid` — разные сущности, всегда
  проверять правильность поля. `accountid` — это идентификатор
  счёта/контракта, `projectid` — проекта.
- **Pitfall #211:** в `get_project_card` исторически возвращалось
  поле `name` проекта вместо ФИО пользователя → баг «N/A» в строке 1
  секции 7. **Не использовать** `project["name"]` как ФИО. Для
  пользователя — JWT (`get_current_user_from_token`).
- Для очень крупных сущностей возвращает много полей (несколько сотен),
  парсинг JSON может занимать 1–2 секунды — допустимо.

---

### 3.5. `find_entity`

**Что это (по MCP-серверу PMForesight):** быстрый поиск сущностей по
названию. Возвращает первые N совпадений.

**Где используется:** редко. Один раз — для `MetaModel`.

**Параметры:**

```python
mcp_call(sid, "find_entity", {
    "entityName": "MetaModel",
    "query":      "<имя поля или сущности>",
    "limit":      1,
})
```

**Куда в скилле:**

- `build_report_header.py` — поиск записи в `MetaModel` (метаданные
  полей) для подписей заголовков и единиц измерения.

**Скрипты:** `build_report_header.py`.

**Edge cases:**

- `find_entity` по `MetaModel` возвращает `data_id` записи; затем
  делается `get_entity_data(data_id)` для полной схемы поля.

---

### 3.6. `get_user_profile` — для логов, не для отчёта (Pitfall #213)

**Почему:** метод возвращает профиль пользователя **владельца сессии**,
но на практике (PMForesight MCP) возвращает `{Id, Account, FullName,
Name, Phone}` — **без ФИО** в человеческом формате и **без
role/permissions**. Используется только для логов
(`get_user_role_via_mcp()` в `fst-project-health-snap-md` и
`fst-project-health-from-md-snapshot`), в отчёте ФИО пользователя
**не используется**.

**Правильный способ получить ФИО в отчёте:** распарсить JWT-токен
`PMP_TOKEN` через `scripts/mcp_config.py::get_current_user_from_token()`
— взять `payload["displayname"]` или
`payload["http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname"]`.

Подробности — `references/mcp-token-jwt-extract.md`.

**Скрипты:** вызывается из `logging_utils.py::get_user_role_via_mcp(sid_func)`
в обоих snapshot-скиллах. В production-пути скилла отчёта
`fst-project-health` — **не вызывается**.

### 3.7. `upload_entity_file` — запись файла в карточку (NEW, 2026-09-24)

**Что это (по MCP-серверу PMForesight):** загружает файл-документ в
карточку сущности. Используется `fst-project-health-snap-md` и
`fst-project-health-snapshot` для архивации отчётов в карточке проекта
(категория «Документы ИИ», `documentId=70139`).

**Параметры:**

```python
mcp_call(sid, "upload_entity_file", {
    "entityName": "Project",                     # имя сущности
    "dataId": str(project_id),                   # числовой ID
    "documentId": 70139,                        # категория документа
    "uploadedFileName": "Слепок ...-504-595-2026-09-24_13-28-03.MD",
    "uploadedFileContentBase64": <base64 bytes>,
    # activityPhaseId — НЕ передавать, если категория не привязана к стадии ЖЦ
})
```

**Ключевые правила:**

- **`documentId`** — категория документа. Для «Документы ИИ» в
  карточке проекта = `70139`. Узнать: `get_view("Document", "DocumentView")`.
- **`dataId`** — **строка**, не число (хотя значение числовое).
  Передавать как `str(project_id)`.
- **`uploadedFileContentBase64`** — файл целиком в base64. Кодировать
  через `base64.b64encode(content).decode("ascii")`.
- **`uploadedFileName`** — с расширением (`.MD`, `.JSON` — **заглавными**
  буквами, как принято в PMForesight).
- **`activityPhaseId`** — **НЕ передавать** для категории «Документы
  ИИ» (она привязана ко всем стадиям ЖЦ). Передавать только если
  категория явно требует привязки к стадии.
- **Удаление** загруженного файла через `delete_entity` пользовательским
  токеном **НЕ работает** (защита MCP). Удалять только вручную через
  UI PMForesight.
- **Round-trip обязателен**: после `upload_entity_file` канонический
  тест — `list_files` + `resources/read` + SHA256 должен совпасть
  байт-в-байт (см. Round-trip pattern выше).

**Скрипты:** `run_snap_md.py::upload_to_mcp`, `run_snapshot.py::upload_to_mcp`.

### 3.8. `list_files` — список файлов в категории (NEW, 2026-09-24)

**Что это:** возвращает массив файлов, прикреплённых к категории
документа в карточке сущности. Используется `fetch_snapshot.py` для
получения списка MD-снимков в карточке проекта.

**Параметры:**

```python
mcp_call(sid, "list_files", {
    "documentId": 70139,      # категория документа
    "dataId": str(project_id),
    "className": "Project",   # имя класса сущности
})
```

**Возвращает:** **массив** напрямую, не обёрнутый в dict:

```python
[
    {"physicalFileId": "...", "url": "/api/file/get/...", "name": "...",
     "fileSize": 14210, "isLink": False},
    ...
]
```

**Pitfall #237 NEW:** `list_files` возвращает массив **напрямую**, не
`{"items": [...]}`. При чтении:

```python
raw = mcp_call(sid, "list_files", ...)
items = raw if isinstance(raw, list) else raw.get("items", [])
```

Не предполагать `raw.get("items", [])` — это даст пустой список.

**Скрипты:** `fetch_snapshot.py::list_snapshots`.

### 3.9. `resources/read` — скачивание файла (NEW, 2026-09-24)

**Что это (по спецификации MCP):** чтение ресурса по URI. Для скачивания
файлов из MCP используется URI формата
`file://download-file/{physicalFileId}`.

**Параметры (JSON-RPC формат, НЕ tools/call):**

```python
payload = {
    "jsonrpc": "2.0", "id": 1, "method": "resources/read",
    "params": {"uri": f"file://download-file/{physicalFileId}"}
}
r = requests.post(URL, json=payload, headers=H, timeout=60)
```

**Возвращает:** `result.contents[0].blob` — base64-кодированное содержимое
файла. Декодировать через `base64.b64decode(blob)`.

**Pitfall #237 NEW:** если `blob` пустой — проверить `contentMode` через
`get_file_info(physicalFileId)`. Если `contentMode="url"`, blob будет
пуст, а в `contents[0].text` будет URL — скачивать через
`requests.get(url)`.

**Скрипты:** `fetch_snapshot.py::download_md`.

### 3.10. `get_file_info` — метаданные файла (NEW, 2026-09-24)

**Что это:** возвращает метаданные физического файла по его GUID
(`physicalFileId`).

**Параметры:**

```python
mcp_call(sid, "get_file_info", {"physicalFileId": "..."})
```

**Возвращает:** `{physicalFileId, fileName, fileSize, mimeType, url,
contentMode}`. `contentMode="bytes"` означает, что blob будет в
`resources/read`; `contentMode="url"` — файл большой (>10 МБ), надо
скачивать по `url`.

**Скрипты:** `fetch_snapshot.py::download_md` (fallback при пустом blob).

---

## Часть 4. Обёртки скилла над MCP-методами

Все 4 метода выше обёрнуты в Python-хелперы в `scripts/mcp_config.py`
для удобства и кеширования.

### 4.1. `mcp_init() -> (sid, serverInfo)`

См. описание `initialize` (Часть 3.1).

### 4.2. `mcp_call(sid, tool_name, arguments, *, token=None, timeout=60) -> dict`

Обёртка над `tools/call`. Распаковывает двойное кодирование,
обрабатывает `isError`, возвращает dict.

**Файл:** `scripts/mcp_config.py:423-468`.

### 4.3. `fetch_with_cache(sid, entity, view, filters, project_id, limit) -> list`

Обёртка над `get_view` с межзапусковым кешем (5 мин TTL).
Файлы кеша: `/tmp/.cache_run_all_<project_id>.json`.

**Файл:** `scripts/project_indicators.py:495-540`.

### 4.4. `_get_project_card_cached(sid, project_id) -> dict`

Обёртка над `get_entity_data` для проекта. Кеш в
`/tmp/.cache_project_card_<project_id>.json`.

**Файл:** `scripts/project_indicators.py:530-540`.

### 4.5. `get_project_property(sid, project_id, property_name)`

Узкая обёртка над `get_entity_data` для одного свойства.

**Файл:** `scripts/mcp_config.py:471-499`.

### 4.6. `get_project_card(sid, project_id)`

Обёртка над `get_entity_data` для всей карточки.

**Файл:** `scripts/mcp_config.py:519-545`.

### 4.7. `get_view_with_filters(sid, entity, view, filters, limit)`

Обёртка над `get_view` без кеша (для разовых вызовов в `mcp_probe.py`
и `find_project_by_code.py`).

**Файл:** `scripts/mcp_config.py:100-115`.

---

## Часть 5. Как добавить новый метод MCP

1. **Проверить** через `tool_describe` (см. `mcp__fst_pmpractice__*` в
   доступных инструментах Hermes) — какие параметры поддерживает.
2. **Probe** через `scripts/mcp_probe.py` — реальный вызов, посмотреть
   формат ответа (Pitfall #224).
3. **Добавить обёртку** в `scripts/mcp_config.py` если нужно
   (по образцу `mcp_call`).
4. **Использовать** в `project_indicators.py::check_*` через
   `fetch_with_cache` (для `get_view`) или напрямую через `mcp_call`
   (для `get_entity_data`/`find_entity`).
5. **Покрыть тестом** в `tests/test_*.py` (Pitfall #44 из SKILL.md).
6. **Записать** в этот playbook (новый раздел в Части 3).

---

## Часть 7. Подробности по разделам отчёта (в каноническом порядке)

Подразделы Части 7 идут в том же порядке, что и разделы отчёта:
**1 → 3 → 4 → 5 → 6 → 7 → 8**. Раздел 2 в отчёте отсутствует.

Раздел 6 (16 индикаторов) уже подробно расписан в **Части 3.3**
(секция «Куда в скилле — по разделам отчёта»). В Части 7 ниже для
раздела 6 — **краткая сводка** с указателями на Часть 3.3.

---

### 7.1. Раздел 1 «Заголовок отчёта»

**Назначение:** шапка отчёта — название проекта, код (`504-595`), URL
MCP-сервера, серверное время, статус сессии. Без неё отчёт не имеет
«титульного листа».

**Что собирается:**

| Поле шапки | Источник | Метод MCP |
|---|---|---|
| Код проекта (например, `504-595`) | ввод пользователя | — |
| `project_id` (числовой) | поиск по коду | `get_view` (`Project/MyProject` или `Project/AllProject`) |
| Название проекта | карточка проекта | `get_entity_data(Project, data_id=project_id)` |
| Серверное время | `datetime.now()` + `MetaModel` (DEPRECATED, см. ниже) | `find_entity(MetaModel)` + `get_entity_data` (не работает) |
| Версия скилла | `fst_project_health.__version__` | — (из исходников) |
| Версия MCP-сервера | `serverInfo` из `mcp_init()` | `initialize` (ответ содержит `serverInfo.name/version`) |
| Версия Core («ПМ «Форсайт»») | `MetaModel` (поле `CoreVersion`) | `find_entity` + `get_entity_data` |

**Скрипт:** `scripts/build_report_header.py`. Точка входа —
`build_report_header(project_id)`.

**Функции и их MCP-вызовы:**

| Функция | Что делает | Метод MCP + параметры |
|---|---|---|
| `get_project_name_by_id(sid, project_id)` | возвращает `{name, code, …}` | `get_entity_data("Project", data_id=project_id)` |
| `get_metamodel_metadata(sid)` | собирает title/version/core_version | `find_entity("MetaModel", query=<key>, limit=1)` → `get_entity_data("MetaModel", data_id=<pk>)` |
| `get_server_time(sid, server_info)` | текущее время Форсайт-сервера | `_get_metamodel_value("ServerTime")` — DEPRECATED, fallback на `datetime.now()` |
| `get_effort_summary(sid, project_id)` | сводка по ресурсам для шапки | `get_view("Project", "ProjectResourcePlan", filters={"ProjectId": project_id})` |
| `get_project_budget_summary(sid, project_id)` | сводка по бюджету для шапки | `get_view("Project", "ProjectBudgetCompleteBusiness", filters={"ProjectId": project_id})` |

**Параметры вызовов — образцы:**

```python
# Найти проект по коду
mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName":   "MyProject",          # или "AllProject"
    "filters":    {"ProjectCode": "504-595"},  # или поиск по коду через find_entity
    "limit":      1,
})

# Карточка проекта
mcp_call(sid, "get_entity_data", {
    "entityName": "Project",
    "data_id":    str(project_id),       # именно data_id (Pitfall #159)
})

# МетаМодель (для title/version)
mcp_call(sid, "find_entity", {
    "entityName": "MetaModel",
    "query":      "Title",               # или "Version", "CoreVersion"
    "limit":      1,
})
# → получить pk записи → затем get_entity_data по pk

# Ресурсный план (для шапки)
mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName":   "ProjectResourcePlan",
    "filters":    {"ProjectId": project_id},
    "limit":      1000,
})

# Бюджет (для шапки)
mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName":   "ProjectBudgetCompleteBusiness",
    "filters":    {"ProjectId": project_id},
    "limit":      1000,
})
```

**Edge cases:**

- **Pitfall #159 (`accountid` vs `projectid`):** в шапке проекта
  `project_id` берётся из результата `find_project`; **не путать** с
  `accountid` контракта. Всегда проверять поле по типу.
- **DEPRECATED:** `MetaModel` не содержит серверного времени (проверено
  2026-08-07). Функции `_try_metamodel_time`, `META_TIME_KEYS`
  оставлены для обратной совместимости, но возвращают `None`. Реальное
  серверное время — `datetime.now()` локально. Это поведение
  задокументировано в `references/metamodel-endpoint.md`.
- **Pitfall #213:** в шапке **не использовать** `project["name"]` как
  ФИО пользователя. ФИО — из JWT через `get_current_user_from_token()`.

**Скрипты:** `scripts/build_report_header.py` (основной),
`scripts/get_metamodel.py` (вспомогательный).

---

### 7.3. Раздел 3 «Замечания по срокам»

**Назначение:** найти все КТ проекта с проблемами по срокам
(просрочены, нет прогноза, дата в прошлом). Это **первый** раздел
отчёта с конкретными строками.

**Что собирается:** список КТ со столбцами: `# | Код | Наименование |
План | Прогноз | Δ дн | Тип замечания`. Источник — все КТ уровня
проекта.

**MCP-метод:** только `get_view("Point", "AllMyPoint", filters={"ProjectId": project_id})`.

**Скрипт:** `scripts/run_all.py`. Цепочка:

1. `load_project_points(sid, project_id)` → вызывает MCP.
2. `build_section_3(points)` → формирует Markdown с логикой severity.

**Параметры:**

```python
mcp_call(sid, "get_view", {
    "entityName": "Point",
    "viewName":   "AllMyPoint",
    "filters":    {"ProjectId": project_id},   # ОБЯЗАТЕЛЬНО
    "limit":      1000,                        # крупные проекты — поднять
})
# Возвращает все КТ с ParentEntityName="Project"
# Используемые поля: Code, Name, PlanDate, ForecastDate, FactDate, PointTagName, …
```

**Edge cases:**

- **Pitfall #217:** для раздела 3 используется `AllMyPoint`
  (parent=Project), НЕ `AllFinancePoint`. Финансовые КТ в разделе 3
  появляться **не должны** — они идут в 6.8.
- **Без фильтра по ProjectId** view может вернуть тысячи строк по
  всем проектам организации (Pitfall из `mcp-filters-format.md`) —
  всегда фильтровать.
- **Просроченные КТ без прогноза:** `PlanDate < today AND
  ForecastDate IS NULL AND FactDate IS NULL` — отдельный класс
  тяжести (Критическое).
- **Fix 2026-08-21:** класс тяжести учитывает **реальную** просрочку
  (разницу `today - PlanDate`), а не просто факт просрочки.

**Колонки таблицы** (канон из эталона 26):

| # | Код | Наименование | План | Прогноз | Δ дн |

(`Δ дн` — добавлено в v1.0.4 по требованию пользователя.)

---

### 7.4. Раздел 4 «Полнота заполнения проекта»

**Назначение:** проверить, что все обязательные поля проекта заполнены
(юрлицо, титул, этап ЖЦ, методология, бюджет, и т.п.). Возвращает
таблицу с не-заполненными полями.

**Что собирается:**

- Сводка по полноте полей карточки (через `get_entity_data`).
- Сводка по полноте бюджета (через `get_view`).

**MCP-методы:**

1. `get_entity_data("Project", data_id=project_id)` — карточка для проверки заполненности.
2. `get_view("Project", "ProjectHealthCostMy", filters={"ProjectId": project_id})` — сводка полноты по health-cost view.

**Скрипт:** `scripts/run_all.py::build_section_4`.

**Параметры:**

```python
# Карточка проекта
mcp_call(sid, "get_entity_data", {
    "entityName": "Project",
    "data_id":    str(project_id),
})
# Поля: Name, Code, JuridicalPerson, PresaleJuridicalPerson,
#        LifeCycleStage, Methodology, IsPresale, и др.

# Health-cost view
mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName":   "ProjectHealthCostMy",
    "filters":    {"ProjectId": project_id},
    "limit":      100,
})
```

**Edge cases:**

- **Pitfall #211:** в ранних версиях в строку «Пользователь» попадало
  `project["name"]` (название проекта) — баг «N/A». **Не повторять**;
  ФИО пользователя — из JWT.
- View `ProjectHealthCostMy` может не возвращать данные, если в проекте
  ещё не было ни одной статьи бюджета — тогда строк в разделе 4
  меньше. Это **нормально**, не ошибка.
- **Pitfall #202:** в `templates/report.html` исторически были дубли
  секции 4 (с разными заголовками: «Полнота заполнения КТ» +
  «Полнота заполнения проекта»). Канонический заголовок — **«Полнота
  заполнения проекта»** (Pitfall #203).

**Колонки таблицы:** `# | Поле | Значение | Статус заполнения`.

---

### 7.5. Раздел 5 «Актуальность прогнозов»

**Назначение:** сравнить прогнозные даты КТ с текущей датой и
классифицировать по размеру просрочки (0–7 дн, 8–30 дн, > 30 дн).

**Что собирается:** список КТ, у которых `ForecastDate < today AND
FactDate IS NULL`. Группируется по `Δ = today - ForecastDate`.

**MCP-метод:** `get_view("Point", "AllMyPoint", filters={"ProjectId": project_id})`
— те же данные, что в разделе 3. **НЕ делается отдельный вызов** —
используется кеш раздела 3 (см. `load_project_points`).

**Скрипт:** `scripts/run_all.py::build_section_5`.

**Параметры:**

```python
# Те же, что в 7.3. Кешируется по project_id в /tmp/.
mcp_call(sid, "get_view", {
    "entityName": "Point",
    "viewName":   "AllMyPoint",
    "filters":    {"ProjectId": project_id},
    "limit":      1000,
})
```

**Edge cases:**

- **Пользовательская корректировка 2026-08-21:** актуальность
  проверяется **только** по `ForecastDate`, не по `PlanDate`. Если
  плановая дата прошла, но есть прогноз в будущем — это **не**
  просрочка раздела 5.
- **Кеш `__pycache__`:** если меняли `build_section_5`, обязательно
  удалить `__pycache__` перед повторным запуском (Pitfall #199).
- **Pitfall #202:** канонический заголовок — «**Актуальность
  прогнозов**» (не «прогнозов по проекту» — был старый дубль).

**Колонки таблицы:** `# | Код | Наименование | План | Прогноз | Δ дн`
(Δ дн = `today - ForecastDate`).

---

### 7.6. Раздел 6 «Показатели проекта» (16 индикаторов) — сводка

**Назначение:** основной диагностический раздел отчёта. 16 индикаторов
по `IndicatorResult`. Каждый индикатор вызывает свой набор view.

**Полная таблица индикаторов (6.1–6.16), используемых view, скриптов и
Pitfall'ов** — в **Части 3.3**, раздел «Куда в скилле — по разделам
отчёта» → строка «Раздел 6 «Показатели проекта»».

**Скрипты:** `scripts/project_indicators.py` (16 функций `check_*`),
обёртки `fetch_with_cache` и `_get_project_card_cached` в
`scripts/mcp_config.py`.

**Ключевые view** (все подробности — Часть 3.3):

- `Project/_get_entity_data_` (через `get_entity_data`) — карточка проекта
  для 6.1, 6.2, 6.3, 6.4, 6.5, 6.7, 6.15, 6.16.
- `Point/AllMyPoint` — КТ уровня проекта для 6.2–6.5, 6.7, 6.13–6.16.
- `Point/AllFinancePoint` — финансовые КТ для **6.8** (Pitfall #214).
- `Project/ProjectResourcePlan` — ресурсный план для 6.3–6.7, 6.13, 6.14.
- `Project/ProjectBudgetCompleteBusiness` — бюджет для 6.10–6.14, 6.16.
- `Project/MyProject` — расширенная карточка для 6.8, 6.9, 6.15.
- `InContract/InContractBudgetBusiness` — финансовый поток для 6.9.
- `Project/ApprovedBudget` — утверждённый бюджет для 6.13, 6.15.

**Edge cases (сводка, детали — Часть 3.3):**

- **Pitfall #196:** `projectid` в `ProjectResourcePlan` — lowercase.
- **Pitfall #217:** `AllMyPoint` ≠ `AllFinancePoint`. Для 6.8 — только
  `AllFinancePoint` (Pitfall #214).
- **Pitfall #198:** `table=[]` vs `table=None` — для серого ▼.
- **Pitfall #211:** для 6.1 не использовать `project["name"]` как ФИО.

---

### 7.7. Раздел 7 «Технические данные отчёта»

**Назначение:** справочная секция в конце отчёта — кто построил, на
какой версии MCP, в какое время. По эталону 26: 6 строк.

**Что собирается:** 6 строк метаданных (Pitfall #211).

| # | Строка | Источник | Метод MCP |
|---|---|---|---|
| 1 | Пользователь | JWT → `displayname` | `get_current_user_from_token()` (НЕ MCP) |
| 2 | Титул системы | `MetaModel.Title` | `find_entity` + `get_entity_data` |
| 3 | URL MCP-сервера | константа `MCP_URL` | — |
| 4 | Версия скилла | `fst_project_health.__version__` | — |
| 5 | Версия MCP | `serverInfo.version` (из `initialize`) | `initialize` |
| 6 | Версия Core (ПМ «Форсайт») | `MetaModel.CoreVersion` | `find_entity` + `get_entity_data` |

**Скрипт:** `scripts/run_all.py::build_section_7`.

**Параметры:**

```python
# 1. Пользователь — из JWT, НЕ из MCP
from mcp_config import get_current_user_from_token
user = get_current_user_from_token()
# → например "Кузнецов Ростислав Владимирович"

# 2. Титул системы
mcp_call(sid, "find_entity", {"entityName": "MetaModel", "query": "Title", "limit": 1})
# → pk → mcp_call(sid, "get_entity_data", {"entityName": "MetaModel", "data_id": pk})

# 5. Версия MCP — из serverInfo
sid, server_info = mcp_init()
mcp_version = server_info.get("version", "—")

# 6. Версия Core
mcp_call(sid, "find_entity", {"entityName": "MetaModel", "query": "CoreVersion", "limit": 1})
```

**Edge cases:**

- **Pitfall #211 / #213:** строка 1 — **никогда** не брать
  `project["name"]` (это название проекта, не пользователь).
  Правильный путь — JWT.
- **Pitfall #211:** fallback-список строк в `render_tbl5_tech` ДОЛЖЕН
  совпадать с тем, что формирует `build_section_7()` — иначе позиции
  не совпадут. Текущий канон — 6 строк в порядке (Пользователь,
  Титул, URL, Версия скилла, Версия MCP, Версия Core).
- **Pitfall #27:** ярлык строки 6 — «Версия Core» или «Версия Core
  (ПМ «Форсайт»)» — оба варианта встречаются в эталоне 26.

---

### 7.8. Раздел 8 «Сводка по разделам 3–7»

**Назначение:** финальный агрегатор — таблица «раздел → кол-во
замечаний по severity». Считается из уже собранных
`/tmp/section_*_result.md`. **Не делает MCP-вызовов**.

**Скрипт:** `scripts/run_all.py::build_section_8`.

**Edge cases:**

- Если раздел не собран (например, нет точек 3) — в сводке будет
  «нет данных». Это **нормально**.
- Если в `/tmp/` остались старые `section_*_result.md` от предыдущего
  запуска (другого проекта) — сводка смешается. **Очищать `/tmp/`**
  перед запуском для нового проекта, или использовать уникальные
  имена файлов (текущая реализация — `/tmp/section_X_result.md`,
  без project_id — Pitfall: при параллельных запусках смешиваются).

---

## Часть 8. Сводка всех view по разделам (для быстрого поиска)

| Раздел | View (entity/viewName) | Фильтр | Лимит | Скрипт |
|---|---|---|---|---|
| 1 (шапка) | `Project/MyProject` или `Project/AllProject` | `ProjectCode=<code>` или `ProjectId=<id>` | 1–10 | `find_project_by_code.py` |
| 1 (шапка) | `Project/_get_entity_data_` (алиас) | — | — | `build_report_header.py` |
| 1 (шапка) | `MetaModel` (через `find_entity`) | — | 1 | `build_report_header.py` |
| 1 (шапка) | `Project/ProjectResourcePlan` | `ProjectId=<id>` | 1000 | `build_report_header.py` |
| 1 (шапка) | `Project/ProjectBudgetCompleteBusiness` | `ProjectId=<id>` | 1000 | `build_report_header.py` |
| 3 | `Point/AllMyPoint` | `ProjectId=<id>` | 1000 | `run_all.py::load_project_points` |
| 4 | `Project/ProjectHealthCostMy` | `ProjectId=<id>` | 100 | `run_all.py::build_section_4` |
| 4 | `Project/_get_entity_data_` | — | — | `run_all.py::build_section_4` |
| 5 | `Point/AllMyPoint` (тот же кеш, что в разделе 3) | `ProjectId=<id>` | 1000 | `run_all.py::build_section_5` |
| 6 (старая) | `Project/ProjectHealthCostMy` | `ProjectId=<id>` | 100 | `run_all.py::build_section_6` |
| 6.1–6.16 | (см. таблицу в Части 3.3) | — | — | `project_indicators.py` |
| 7 | `MetaModel` (через `find_entity`) | — | 1 | `build_report_header.py::get_metamodel_metadata` |
| 8 | — (агрегация) | — | — | `run_all.py::build_section_8` |

---

## Часть 9. Чек-лист перед коммитом изменений по MCP (расширенный)

- [ ] Все новые `get_view` фильтруются по `ProjectId` (Pitfall #193).
- [ ] `projectid` в `ProjectResourcePlan` — lowercase (Pitfall #196).
- [ ] Для финансовых КТ — `Point/AllFinancePoint`, не
      `InContractBudgetBusiness` (Pitfall #214, #217).
- [ ] Таймаут увеличен, если проект крупный (504-595).
- [ ] Кеш `__pycache__` удалён после правки `mcp_config.py`
      (Pitfall #199).
- [ ] Тесты добавлены в `tests/` (Pitfall #44).
- [ ] Playbook обновлён (этот файл).

---

## Часть 10. Назначения разделов и показателей

> Назначения взяты из `references/playbook.md` (главный playbook для
> коллег, автор — ROSTISLAV KUZNETSOV, v1.0.14) и скорректированы по
> результатам наших сессий 2026-08–2026-09. Ниже — **только
> назначения**, без данных/интерпретации (они подробно расписаны
> в `playbook.md`).

### Раздел 1 «Заголовок отчёта»

**Назначение:** шапка отчёта — круглый индикатор общего здоровья (Проект
болен / Требует внимания / Здоров) + метаданные (Target, дата создания,
версия MCP). Считывается одним взглядом — ответ на вопрос «всё ли в
порядке?».

### Раздел 3 «Замечания по срокам»

**Назначение:** показать **КТ с нарушением сроков** (план/прогноз в
прошлом). Это **основной сигнал тревоги для РП** — что в проекте
уже сорвано по датам. Раздел открывается по умолчанию.

### Раздел 4 «Полнота заполнения проекта»

**Назначение:** проверить, что в карточке проекта заполнены **ключевые
поля** (куратор, РП, паспорт, трудозатраты, платежи). Без полноты
карточки остальные отчёты ненадёжны — аналитик не сможет принять
решение.

### Раздел 5 «Актуальность прогнозов»

**Назначение:** показать КТ с **полным набором данных** (план +
прогноз, факт или без) и **рассчитать просрочку в днях**. Отвечает на
вопрос «на сколько дней сорван срок?».

### Раздел 6 «Показатели проекта» (16 индикаторов)

**Назначение:** **главный раздел** отчёта — 16 ключевых показателей
здоровья проекта. Каждый индикатор отвечает на один конкретный вопрос
РП/куратора. Раздел открывается по умолчанию. Внутри:

- **6.1 Юрлицо проекта/пресейла указано** — для договоров нужно заполненное юрлицо.
- **6.2 Актуальность состояния ЖЦ** — стадия ЖЦ проекта должна соответствовать реальной фазе работ.
- **6.3 Прогнозы по ресурсам заданы** — на ближайшие месяцы должны быть `forecast_hours` по исполнителям.
- **6.4 Плановые трудозатраты заданы** — плановые часы на каждый месяц должны быть заполнены.
- **6.5 Прогнозы ресурсов на исполнителя не превышают 100%** — нет перегрузки одного человека в одном месяце.
- **6.6 Есть нереализованные прогнозы по ролевым ресурсам** — найти роли (не ФИО), по которым прогноз не привязан к сотруднику (справочная).
- **6.7 Есть исполнители, у которых прогноз в сумме с др. активностями > 100%** — найти перегруженных по всем проектам, не только по текущему.
- **6.8 Соблюдение сроков финансовых КТ** — финансовые КТ (привязанные к контрактам) не должны быть просрочены.
- **6.9 Суммы актов и оплат** — финансовая дисциплина: Σ актов ≈ Σ оплат.
- **6.10 В бюджете указаны прямые затраты** — статья «Прямые затраты» должна иметь ненулевую сумму.
- **6.11 В затратах указан НДС** — наличие НДС (статья 611-13) в бюджете.
- **6.12 Сумма НДС расчётная** — **проверить правильность** ручного указания НДС (формула `Сумма / 21 × 5`).
- **6.13 Бюджет проекта/пресейла** — наличие утверждённого бюджета + лимит пресейла (5%).
- **6.14 Расход лимита пресейла** — потрачено ≤ лимита пресейла.
- **6.15 У проекта есть утверждённый бюджет** — на каждый год периода проекта есть утверждённая сумма.
- **6.16 Проставлены метки для отнесения КТ к проекту или пресейлу** — у КТ проставлена метка `kp_label`.

### Раздел 7 «Технические данные отчёта»

**Назначение:** справочная секция для аудита — **кто** строил, **от
чьего токена**, на какой версии системы. По эталону 26: 6 строк.

### Раздел 8 «Сводка по разделам 3–7»

**Назначение:** финальный агрегатор — таблица «раздел → кол-во
замечаний по severity». Считывается в один взгляд: где больше всего
проблем.

---

**Полные описания** (4 секции: назначение / получение данных /
интерпретация / вывод) — в `references/playbook.md` (автор —
ROSTISLAV KUZNETSOV, v1.0.14).