# MCP live-probe cookbook — Форсайт ПМ Практика

> Практический рецепт live-разведки для неизвестных/проблемных эндпоинтов
> PMForesight MCP (v3.2.4, URL: `https://ppreplica.hera.pmpractice.ru/mcp`).
> Контекст: пользователь просит **«посмотреть, как работает»** какой-то view/сущность
> или **«у нас проблема — попробуй найти выход»**. Здесь — конкретные рецепты probe
> на Python (`scripts/mcp_probe.py`), и что делать с типичными ответами.

## Использование cookbook

Когда нужно проверить что-то на MCP сервере — **не с потолка**, а через
реальные вызовы. Используйте `scripts/mcp_probe.py` для интерактивных
probe-ов прямо в чате. Подробности ниже.

## 1. Базовые команды probe

```bash
# Список всех tools
python3 scripts/mcp_probe.py --tools

# Конкретный tool с args
python3 scripts/mcp_probe.py --tool find_entity --args '{"name":"ИС","limit":50}'
python3 scripts/mcp_probe.py --tool get_view --args '{"entityName":"Project","viewName":"AllProject","limit":5}'
python3 scripts/mcp_probe.py --tool get_entity_data --args '{"entityName":"metamodel","data_id":"Title"}'

# Сырой HTTP-ответ (для диагностики)
python3 scripts/mcp_probe.py --tool ... --raw
```

## 2. Что делать с ответами

### 2.1. HTTP 502 Bad Gateway

**Симптом:** `Error calling tool '...': Ошибка запроса к /view/...:502 Bad Gateway`

**Причина:** nginx перед MCP-эндпоинтом. Это **не** ошибка логики,
а временный сбой upstream.

**Решение:** подождать 10–30 сек и повторить. Сервер живой,
просто MCP upstream ещё не доступен. Это **не** pitfall #16 (MCP-сервер 502).

### 2.2. HTTP 403 Forbidden

**Симптом:** `403 Client Error: Forbidden for url: https://.../view/...`

**Причина:** view существует, но у пользователя нет прав (нет роли в Perm).
Такие view как правило **никогда не откроются** без admin-роли.

**Решение:** для конкретного view — см. **obvious fallbacks** ниже.

### 2.3. `Entity name 'XYZ' not found` или `Конечная точка не найдена`

**Симптом:** `Конечная точка не найдена по адресу https://.../view/AllXyz. Укажите корректный URL`

**Причина:** имя view написано неверно — **CamelCase vs lowercase** имеет значение.
Для MetaModel: `entityName="metamodel"` (lowercase), НЕ `"MetaModel"`.

**Решение:** попробовать разные варианты написания: `AllXyz`, `MyXyz`, `xyz`, `Xyz`. Если
ничего — сущность либо не имеет view, либо нужно уточнить имя у разработчиков.

### 2.4. SQL 500: `оператор не существует: character varying = bigint`

**Симптом:** `500 - оператор не существует: character varying = bigint`

**Причина:** Pydantic-валидация входных данных ушла, но SQL JOIN по PK
**не работает** (тип mismatch в таблицах). Это **баг бэкенда** — обходить только
через другой API.

**Обход:** использовать другую сущность или view. MetaModel-ошибка —
обходится через `get_entity_data` (после фикса 2026-08-07).

### 2.5. Crucial `entityName` — lowercase!

**Pitfall:** `find_entity` НЕ принимает параметр `entityName` (peculiarity API):
```json
"1 validation error for call[find_entity]
entityName: Unexpected keyword argument"
```

**Pitfall:** `get_entity_data` для MetaModel: `entityName="MetaModel"` →
400 Bad Request / «Запись не найдена». Правильно: `entityName="metamodel"` (lowercase).

**Правило:** после проверки `tools/list` — **сначала probe** с lowercase,
потом пробовать CamelCase. Не наоборот.

## 3. Рецепты по задачам

### 3.1. Найти, какие view есть у сущности

```bash
# Через describe_entity
python3 scripts/mcp_probe.py --tool describe_entity \
  --args '{"entityName":"MetaModel","data_id":"new"}'
# Показывает все properties + их типы
```

### 3.2. Получить все данные по проекту (финансы)

```bash
# Приоритетный view для фин. данных
python3 scripts/mcp_probe.py --tool get_view \
  --args '{"entityName":"Project","viewName":"ProjectBudgetCompleteBusiness","limit":2000}'
# 31 столбец: budgetsum, акты/оплаты план/факт/прогноз, контракты, КТ, даты
```

### 3.3. Найти запись по строковому PK

```bash
# MetaModel: PK = Name (text), не integer
python3 scripts/mcp_probe.py --tool get_entity_data \
  --args '{"entityName":"metamodel","data_id":"Title"}'
# {"properties":{"Name":{"value":"Title"},"Value":{"value":"..."}}}
```

### 3.4. Получить конкретное поле по FK

```bash
# Бюджет проекта
python3 scripts/mcp_probe.py --tool get_entity_data \
  --args '{"entityName":"Project","data_id":"4595"}'
# В properties: ProjectBudgetGrade, DirectProjectCostsGrade, PresaleLimit...
```

### 3.5. Найти записи по `name` (find_entity)

```bash
# НО find_entity не привязан к сущности — возвращает всё подряд
python3 scripts/mcp_probe.py --tool find_entity \
  --args '{"name":"ИС","limit":100}'
# Возвращает Contractor, Point, Project, InContract... — без MetaModel!
```

**Важно:** find_entity **не возвращает MetaModel** ни под каким `name`
(проверено 50+ вариантов). Для MetaModel — `get_entity_data` (см. 3.3).

## 4. Типичные «куда смотреть» — везение

| Задача | Где смотреть | API |
|--------|--------------|-----|
| Титул системы | `metaModel` / `Title` | `get_entity_data("metamodel", "Title")` |
| Дата/время сервера | (нету в MetaModel) | `datetime.now()` |
| Список проектов | `Project` view | `get_view(Project, MyProject)` |
| Фин. данные проекта | `ProjectBudgetCompleteBusiness` | `get_view` |
| Бюджет проекта | `Project` поля | `get_entity_data(Project, project_id)` |
| Контракты проекта | `InContractMyProject` | `get_view` (фильтр по ParentFullName) |
| Платежи проекта | `Payments` `AllPayments` | `get_view` (фильтр по activity_name) |
| КТ проекта | `Point` view | `get_view` (фильтр по ParentCode) |
| Трудозатраты | `ResourcePlanning` view | **403** — fallback на `ProjectHealthWorkload` |
| Серверное время MCP | `mcp_init` `serverInfo` | (только name, version) |

## 5. Чего НЕ делать

- **Не верить `tools/list` descriptions** — они могут врать (pitfall #1 в mcp-server-probing).
- **Не пробовать `find_entity` для MetaModel** — принципиально не возвращает.
- **Не ставить `entityName="MetaModel"`** — нужен `"metamodel"` (lowercase).
- **Не полагаться на `Point.PlanSum/ForecastSum/FactSum`** — они часто `None`,
  заполняются только при привязке к `ContractPlanSummariesValue` (403).
- **Не использовать `f-string` с `{CSS}`** — ломает интерполяцию (pitfall #30).
- **Не мутировать scripts/ при драй-ране** — пользователь сказал «ни в коем случае не
  портя генератор» (pitfall #46). Dry-run — в `/tmp/test_*.py`.

## 6. Шаблон поведения при отладке неизвестного

1. **Сначала probe** — не с потолка. `mcp_probe.py` — твой друг.
2. **Открой реальный файл** — не аргументируй из памяти (pitfall #25).
3. **Если ошибка — прочитай её полностью**, не только первую строку.
4. **Если 502/503 — retry через 10–30 сек** (pitfall #16).
5. **Если 403 — это Permission, не Bug**: обходи, не чини.
6. **Если ошибка 500 SQL — обходи другим API**, не правь данные.
7. **Если нашёл рабочий API — обнови skill** (MCP-сервер меняется регулярно).

## 7. Контекстные pointers

- Полная карта MCP-странностей: `references/forsight-mcp-quirks.md` (17 секций + 47 pitfalls)
- Полная карта финансов: `references/project-finance-budget-entities.md` (ProjectBudgetCompleteBusiness как приоритет)
- MetaModel: `references/meta-model-pitfalls.md` (полностью переписан 2026-08-07)
- Архив активных проблем: `Вопросы по MCP 2026_08_07.md` (в корне профиля)
- Общий API / generic probe: skill `mcp-server-probing`

## 8. Частые операции (готовые шаблоны)

```bash
# === Сканирование новой сущности ===
python3 scripts/mcp_probe.py --tool describe_entity \
  --args '{"entityName":"<EntityName>","data_id":"new"}' | head -20

# === Проверка view ===
python3 scripts/mcp_probe.py --tool get_view \
  --args '{"entityName":"<Entity>","viewName":"<ViewName>","limit":3}' | head -10

# === Если view вернул данные — вытащить все ===
python3 scripts/mcp_probe.py --tool get_view \
  --args '{"entityName":"<Entity>","viewName":"<ViewName>","limit":2000}' | \
  python3 -c "import json,sys; r=json.loads(sys.stdin.read()); sc=r['result']['content'][0]['text']; d=json.loads(sc); print(f'rows={len(d.get(\"data\",[]))}'); print('keys:', list(d.get('data',[{}])[0].keys()) if d.get('data') else 'empty')"

# === Если данные ограничены — знать pp-key ===
python3 scripts/mcp_probe.py --tool get_view \
  --args '{"entityName":"<Entity>","viewName":"<ViewName>","limit":5}' | \
  grep -o '"KeyName":"[^"]*"' | head -1
```

Эти шаблоны — рабочая тетрадь. Копируйте, адаптируйте, проверяйте.
