# Playbook скилла `fst-mcp-tester`

**Версия:** 1.0.0 — 2026-09-06
**Автор:** ROSTISLAV KUZNETSOV (постановка), Hermes Agent (реализация)
**Для кого:** коллеги и другие агенты, которые хотят проверить работу
MCP-методов PMForesight без модификации данных.

---

## 📖 Назначение скилла

`fst-mcp-tester` — это **read-only** набор тестов для всех методов MCP,
которые скилл `fst-project-health` вызывает при построении отчёта
о здоровье проекта. Назначение:

1. **Sanity-check** — все методы MCP, нужные `fst-project-health`,
   реально отвечают.
2. **Метрики** — замерить латентность, размер payload'ов, число записей
   для тюнинга таймаутов и кешей.
3. **Рекомендации по оптимизации** — на основе замеров подсказать, какие
   вызовы стоит кешировать, какие — переписать с меньшим `limit`.
4. **Безопасность** — **не модифицирует данные** на стороне MCP. Никаких
   `save_entity`, `delete_entity`, `upload_entity_file` — только чтение.

---

## 🧪 Тестируемые методы MCP

Всего **12 кейсов** (по состоянию на v1.0.0). Источник — реальные вызовы
из `fst-project-health/scripts/` (run_all.py, project_indicators.py,
build_report_header.py, find_project_by_code.py).

| # | Метод | View / Args | Назначение в `fst-project-health` | Категория |
|---|---|---|---|---|
| T01 | `initialize` | (без args) | Получить `mcp-session-id` + `serverInfo` | lifecycle |
| T10 | `tools/call: get_view` | `Project/MyProject`, фильтр `ProjectId` | Карточка проекта для разделов 6.8, 6.9, 6.15 | view |
| T11 | `tools/call: get_view` | `Point/AllMyPoint`, фильтр `ProjectId` | Все КТ уровня проекта для разделов 3, 5, 6.2–6.5, 6.7, 6.13–6.16 | view |
| T12 | `tools/call: get_view` | `Point/AllFinancePoint`, фильтр `ProjectId` | Финансовые КТ (parent=InContract) для раздела 6.8 | view |
| T13 | `tools/call: get_view` | `Project/ProjectResourcePlan`, фильтр `ProjectId`, `limit=1000` | Ресурсный план (план/прогноз часов) для разделов 6.3–6.7, 6.13, 6.14 | view |
| T14 | `tools/call: get_view` | `Project/ProjectBudgetCompleteBusiness`, фильтр `ProjectId`, `limit=500` | Бюджет проекта (план/факт/прогноз) для разделов 6.10–6.14, 6.16 | view |
| T15 | `tools/call: get_view` | `InContract/InContractBudgetBusiness`, фильтр `ProjectId` | Финансовый поток по контрактам для раздела 6.9 | view |
| T16 | `tools/call: get_view` | `Project/ApprovedBudget`, фильтр `ActivityId` | Утверждённый бюджет по годам для разделов 6.13, 6.15 | view |
| T17 | `tools/call: get_view` | `Project/ProjectHealthCostMy`, фильтр `ProjectId` | Финансовое здоровье для раздела 6 (до v1.0.0) | view |
| T20 | `tools/call: get_entity_data` | `Project`, `data_id=project_id` | Полная карточка проекта для раздела 1 (шапка) | entity |
| T30 | `tools/call: find_entity` | `name="MetaModel"` | Поиск сущности MetaModel для раздела 7 | search |
| T31 | `tools/call: find_entity` | `name="Title"` | Поиск значения MetaModel.Title для раздела 7 | search |

### Что **не тестируется** (по дизайну)

- ❌ `save_entity`, `delete_entity`, `upload_entity_file` — это write-операции.
- ❌ `list_views`, `list_entities`, `describe_pro` — это служебные
  методы discovery, `fst-project-health` их не вызывает в production-пути.
- ❌ `get_user_profile` — заменено на JWT-парсинг в `fst-project-health`
  (Pitfall #213).
- ❌ Параллельная нагрузка / stress-test — тесты последовательные.

---

## 🚀 Рекомендованный порядок использования

### Сценарий 1: «Проверить MCP после деплоя / обновления»

```
1. cd ~/.hermes/profiles/fst-control/skills/productivity/fst-mcp-tester
2. убедиться, что .env заполнен (PMP_TOKEN)
3. python3 scripts/run_tests.py
4. открыть outputs/mcp_test_report_<timestamp>.md
5. посмотреть секцию 6 «Ошибки» — если есть, разбираться
6. посмотреть секцию 7 «Рекомендации» — применить к fst-project-health
```

### Сценарий 2: «Подобрать TIMEOUT_TOOLS_CALL для крупного проекта»

```
1. cd ~/.hermes/profiles/fst-control/skills/productivity/fst-mcp-tester
2. поменять TEST_PROJECT_CODE/TEST_PROJECT_ID на нужный проект
   (см. секцию «Как поменять проект» ниже)
3. python3 scripts/run_tests.py
4. в outputs/...md → секция 1 «Executive summary» → строка «Max»
   покажет максимальную латентность → выставить TIMEOUT_TOOLS_CALL = max * 1.5
5. если хочется p99 — добавить замер (сейчас только p95)
```

### Сценарий 3: «Какие view самые тяжёлые для оптимизации кеша»

```
1. python3 scripts/run_tests.py --quick  # быстрее, без payload-size
2. открыть outputs/...md → секция 5 «Payload-размеры»
3. отсортированы по убыванию — top-3 это кандидаты на кеширование
4. проверить, что для них в fst-project-health/scripts/project_indicators.py
   уже используется fetch_with_cache (должно быть)
```

### Сценарий 4: «Диагностика ретраев»

```
1. python3 scripts/run_tests.py
2. если в секции 3 «Детальная таблица» есть строки с retries > 0 —
   значит были таймауты
3. секция 6 «Ошибки» покажет stack trace
4. увеличить TIMEOUT_TOOLS_CALL в mcp_config.py или уменьшить limit
```

### Сценарий 5: «Прогнать на другом сервере»

```
1. скопировать каталог fst-mcp-tester/ на другой сервер
2. cd /opt/skills/fst-mcp-tester
3. pip install -r requirements.txt
4. cp .env.example .env && nano .env  # заполнить PMP_TOKEN
5. python3 scripts/run_tests.py
   (или с переменными окружения для тестового проекта)
```

---

## 🔧 Как поменять проект для тестирования

> **Важно для пользователей и других агентов:** это может сделать
> человек руками или другой агент на другом сервере. По умолчанию —
> проект `504-595` (тот же, что использует `fst-project-health` в
> текущих сессиях).

### Способ A: правка скрипта (руками)

Откройте `scripts/run_tests.py`, найдите блок **«Конфигурация
тестируемого проекта»** (строки ~36–39) и измените:

```python
TEST_PROJECT_CODE = "504-595"   # код проекта (например, "704-724")
TEST_PROJECT_ID   = 4595        # числовой ID проекта в PMForesight
```

Где взять `TEST_PROJECT_ID`:

- Из вывода `fst-project-health` (он печатается при старте).
- Из UI PMForesight (URL проекта содержит `projectId=<id>`).
- Через CLI-утилиту `fst-project-health/scripts/find_project_by_code.py`.

### Способ B: переменные окружения (без правки)

```bash
MCP_TEST_PROJECT_CODE=704-724 MCP_TEST_PROJECT_ID=4724 python3 scripts/run_tests.py
```

Полный список env-vars:

| Env | Назначение | По умолчанию |
|---|---|---|
| `MCP_TEST_PROJECT_CODE` | код проекта для отчёта | `504-595` |
| `MCP_TEST_PROJECT_ID` | числовой ID проекта | `4595` |
| `MCP_TEST_DISABLE_LOOKUP` | `1` чтобы не делать lookup (когда ID уже есть) | `0` |
| `PMP_TOKEN` | JWT-токен PMForesight | (обязательно) |
| `MCP_URL` | URL MCP-сервера | `https://ppreplica.hera.pmpractice.ru/mcp` |

### Способ C: CLI-флаг (планируется)

```bash
python3 scripts/run_tests.py --code 704-724 --project-id 4724
```

Пока **не реализовано** — используйте способ A или B.

---

## 📊 Что замеряется

### Per-test метрики

| Метрика | Описание |
|---|---|
| `duration_ms` | полное время от старта до парсинга ответа |
| `status` | `ok` / `error` / `exception` |
| `record_count` | число записей в ответе |
| `payload_bytes` | размер JSON-сериализованного ответа |
| `retries` | сколько попыток потребовалось (макс 3) |
| `error` | текст ошибки (если есть) |

### Агрегированные метрики (Executive summary)

- ok / error / exception counts
- avg / median / p95 / min / max latency
- суммарный payload и число записей
- ASCII-гистограмма латентности (20 бакетов)

---

## 📁 Структура отчёта

Файл: `outputs/mcp_test_report_<YYYYMMDD_HHMMSS>.md`.

| # | Раздел | Содержимое |
|---|---|---|
| 1 | Executive summary | ok/err, avg/p95 latency, total payload |
| 2 | По категориям | сводка по lifecycle/view/entity/search |
| 3 | Детальная таблица | каждый тест — отдельная строка |
| 4 | ASCII-гистограмма | распределение латентности |
| 5 | Payload-размеры | top-N тяжёлых + байт/запись |
| 6 | Ошибки | подробности с stack trace |
| 7 | Рекомендации | конкретные правки для `fst-project-health` |
| 8 | Сырые данные | JSON для дальнейшей обработки |
| 9 | Артефакты | пути к отчёту |

---

## 🚨 Известные pitfalls

1. **Первый прогон на крупном проекте** — `get_view` с `limit=1000`
   может превысить `TIMEOUT_TOOLS_CALL=60 с`. Решение:
   `--quick` или увеличить таймаут в скрипте.
2. **Если `PMP_TOKEN` не задан** — `RuntimeError` при старте. Решение:
   заполнить `.env`.
3. **Если проект пуст** (нет КТ/бюджета) — тесты T11–T17 вернут
   `record_count=0`. Это **нормально**, не ошибка.
4. **SSE-парсер** берёт **первую** `data:`-строку (не конкатенирует
   все) — иначе многострочные JSON ломаются (Pitfall из
   `fst-project-health`).
6. **`find_entity` не принимает `entityName`** — только `name`,
   `limit`, `offset`. Это **не** то же, что `get_view` /
   `get_entity_data`, где `entityName` обязателен.
7. **Между сессиями MCP может закрываться** — если между тестами
   долгий простой (>5 мин), `mcp_init()` будет перевызван автоматически
   только для самого T01. Для остальных тестов используется **одна
   сессия** на весь прогон.

---

## 🔗 Связанные скиллы

- **`fst-project-health`** — для которого мы пишем тесты. Использует
  все методы MCP, перечисленные выше.
- **`project-search`** — для поиска проекта по коду
  (`find_project_by_code.py`).

---

## 📚 История изменений

- **v1.0.0** (2026-09-06) — первый релиз. 12 тест-кейсов.
  Исправлены 2 бага в ходе первого прогона (SSE-парсер и сигнатура
  `find_entity`).

---

*Сгенерировано для скилла `fst-mcp-tester`.*
*Автор playbook: Hermes Agent. Постановка: ROSTISLAV KUZNETSOV.*