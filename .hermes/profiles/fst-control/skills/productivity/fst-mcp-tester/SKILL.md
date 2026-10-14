---
name: fst-mcp-tester
description: "Read-only тесты всех MCP-методов, которые использует fst-project-health. Замеряет latency, payload-size, record-count, retries. Формирует подробный MD-отчёт в outputs/."
version: 1.0.0
author: ROSTISLAV KUZNETSOV, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [test, mcp, pmpractice, ru, monitoring, latency, payload, read-only]
    related_skills: [fst-project-health, mcp-server-probing]
---

> Дочерний скилл для `fst-project-health` — тестирует все методы MCP, которые `fst-project-health` реально вызывает (`get_view`, `get_entity_data`, `find_entity`, `initialize`). Тест-план строится на основе `references/mcp-methods-playbook.md` родительского скилла и должен синхронизироваться при добавлении новых view/entity.

# fst-mcp-tester

## When to load

- Пользователь просит «проверить работу MCP» / «замерить скорость
  ответов» / «протестировать все методы MCP» / «read-only тесты MCP».
- Нужно понять, какие вызовы самые медленные / самые тяжёлые для
  оптимизации `fst-project-health`.
- После изменения MCP-сервера или сетевой конфигурации — sanity-check.

## CRITICAL: read-only по умолчанию

**Все тесты в этом скилле — read-only.** Используются ТОЛЬКО:

- `initialize` (read session-id)
- `tools/call` с инструментами `get_view`, `get_entity_data`,
  `find_entity` (чтение)

**ЗАПРЕЩЕНО** добавлять в тест-план инструменты, которые могут
модифицировать данные (`save_entity`, `delete_entity`,
`upload_entity_file`, и т.п.). Если нужен тест записи — отдельный
read-write скилл, и только после явного «go» пользователя.

## Quick reference

- **Главный скрипт:** `scripts/run_tests.py`
- **Запуск:** `python3 scripts/run_tests.py [--quick] [--output X.md]`
- **Отчёты:** `outputs/mcp_test_report_<YYYYMMDD_HHMMSS>.md`
- **Тестируемый проект по умолчанию:** `504-595` (id=4595)

## Тестируемые методы

| # | Метод | Назначение | View / Args |
|---|---|---|---|
| T01 | initialize | MCP lifecycle | (без args) |
| T10 | get_view | Project/MyProject | фильтр ProjectId |
| T11 | get_view | Point/AllMyPoint | фильтр ProjectId |
| T12 | get_view | Point/AllFinancePoint | фильтр ProjectId |
| T13 | get_view | Project/ProjectResourcePlan | фильтр ProjectId |
| T14 | get_view | Project/ProjectBudgetCompleteBusiness | фильтр ProjectId |
| T15 | get_view | InContract/InContractBudgetBusiness | фильтр ProjectId |
| T16 | get_view | Project/ApprovedBudget | фильтр ActivityId |
| T17 | get_view | Project/ProjectHealthCostMy | фильтр ProjectId |
| T20 | get_entity_data | Project | data_id=project_id |
| T30 | find_entity | MetaModel | query="Title" |
| T31 | find_entity | MetaModel | query="Version" |

Итого: **12 тестов** (1 lifecycle + 8 view + 1 entity + 2 search).

## Что замеряется

Для каждого теста:

| Метрика | Описание |
|---|---|
| `duration_ms` | полное время от старта до парсинга ответа |
| `status` | `ok` / `error` / `exception` |
| `record_count` | число записей в ответе |
| `payload_bytes` | размер JSON-сериализованного ответа |
| `retries` | сколько попыток потребовалось (макс 3) |
| `error` | текст ошибки (если есть) |

Агрегированные метрики (Executive summary):

- ok / error / exception counts
- avg / median / p95 / min / max latency
- суммарный payload и число записей
- ASCII-гистограмма латентности (20 бакетов)

## Как поменять тестируемый проект

**Это важный раздел для пользователей** (человек или другой агент на
другом сервере могут захотеть тестировать не только 504-595).

### Вариант A: правка скрипта (руками)

Откройте `scripts/run_tests.py`, найдите блок «Конфигурация
тестируемого проекта» и измените:

```python
TEST_PROJECT_CODE = "504-595"   # код проекта
TEST_PROJECT_ID   = 4595        # числовой ID проекта в PMForesight
```

`TEST_PROJECT_ID` можно узнать:

- Из вывода `fst-project-health` (он печатается при старте).
- Из UI PMForesight (URL проекта содержит `projectId=<id>`).
- Через `find_project_by_code.py` из `fst-project-health`.

### Вариант B: переменные окружения (без правки)

```bash
MCP_TEST_PROJECT_CODE=704-724 MCP_TEST_PROJECT_ID=4724 python3 scripts/run_tests.py
```

Полный список env-vars:

| Env | Назначение | По умолчанию |
|---|---|---|
| `MCP_TEST_PROJECT_CODE` | код проекта для отчёта | `504-595` |
| `MCP_TEST_PROJECT_ID` | числовой ID проекта | `4595` |
| `MCP_TEST_DISABLE_LOOKUP` | `1` чтобы не делать lookup (когда ID уже есть) | `0` |
| `PMP_TOKEN` | JWT-токен | (обязательно) |
| `MCP_URL` | URL MCP-сервера | `https://ppreplica.hera.pmpractice.ru/mcp` |

### Вариант C: CLI-флаг (пока не реализовано)

В будущем — `python3 run_tests.py --code 704-724 --project-id 4724`.
Сейчас — только A или B.

## Portable setup

```bash
# 1. Скопировать каталог
scp -r fst-mcp-tester/ user@server:/opt/skills/

# 2. Установить зависимости
cd /opt/skills/fst-mcp-tester
pip install -r requirements.txt

# 3. Заполнить .env
cp .env.example .env
nano .env  # PMP_TOKEN=...

# 4. Запустить
python3 scripts/run_tests.py
```

Приоритет поиска `PMP_TOKEN`:

1. `os.environ["PMP_TOKEN"]`
2. `<каталог скилла>/.env`
3. `~/.hermes/profiles/fst-control/.env`

## Использование в Hermes

Скилл подхватывается автоматически по тегам `test, mcp, monitoring`.

Запросы пользователя → действие:

- «протестируй MCP» → `python3 scripts/run_tests.py`
- «проверь работу методов» → `python3 scripts/run_tests.py`
- «замерь скорость ответов MCP» → `python3 scripts/run_tests.py`
- «сделай read-only тесты MCP» → `python3 scripts/run_tests.py`
- «поменяй проект на 704-724"» → правка `TEST_PROJECT_CODE/ID` в скрипте
  ИЛИ установка env-vars `MCP_TEST_PROJECT_CODE/ID` перед запуском.

## Структура отчёта

| # | Раздел | Содержимое |
|---|---|---|
| 1 | Executive summary | ok/err, avg/p95 latency, total payload |
| 2 | По категориям | сводка по lifecycle/view/entity/search |
| 3 | Детальная таблица | каждый тест — отдельная строка |
| 4 | Гистограмма латентности | ASCII-барчарт по 20 бакетов |
| 5 | Payload-размеры | top-N тяжёлых + байт/запись |
| 6 | Ошибки | подробности с stack trace |
| 7 | Рекомендации | конкретные правки для `fst-project-health` |
| 8 | Сырые данные | JSON для дальнейшей обработки |
| 9 | Артефакты | пути к отчёту |

## Known pitfalls

1. **Первый прогон на крупном проекте** — `get_view` с `limit=1000`
   может превысить `TIMEOUT_TOOLS_CALL=60 c`. Решение:
   `--quick` или увеличить таймаут в скрипте.
2. **Если `PMP_TOKEN` не задан** — `RuntimeError` при старте. Решение:
   заполнить `.env`.
3. **Если проект пуст** (нет КТ/бюджета) — тесты T11–T17 вернут
   `record_count=0`. Это **нормально**, не ошибка.
4. **Между сессиями MCP может закрываться** — если между тестами
   долгий простой (>5 мин), `mcp_init()` будет перевызван автоматически
   только для самого T01. Для остальных тестов используется **одна
   сессия** на весь прогон.
5. **Тест-план может устареть** — `scripts/run_tests.py::build_test_plan`
   хардкодит список view/entity. Когда в родительском скилле
   `fst-project-health` добавляется новый `get_view(Project/SomeView, ...)`
   или `get_entity_data(SomeEntity, ...)`, **тест-план этого скилла не
   узнает** об этом. **Решение:** перед каждым релизом родительского
   скилла прогонять
   `grep -rh "mcp_call\|fetch_with_cache" \
      ~/.hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts/ \
      | grep -oE '"(Project|Point|InContract|Activity|MetaModel|[A-Z][A-Za-z]+)/[A-Za-z][A-Za-z0-9_]+"' \
      | sort -u`
   и сверять с `build_test_plan` — отсутствующие view добавить новым
   кейсом. Альтернатива — генерировать тест-план автоматически из
   `references/mcp-methods-playbook.md` (раздел «Полный список view»).
6. **Read-only — это базовое правило скилла, а не опция.** Не
   добавлять `save_entity` / `delete_entity` / `upload_entity_file` в
   тест-план «чтобы проверить, что они тоже работают». Для записи —
   отдельный read-write скилл, и только после явного «go» пользователя
   с описанием последствий.
7. **Standalone-скрипт НЕ МОЖЕТ импортировать `hermes_tools`** —
   этот модуль доступен **только внутри `execute_code` Hermes Agent**.
   Если standalone-скрипт делает `from hermes_tools import tool_call` —
   падает с `ModuleNotFoundError: No module named 'hermes_tools'`.
   Причина: `hermes_tools` — runtime-инъекция для MCP-вызовов в
   сессии агента, не лежит в `sys.path` обычных процессов.
   **Правило:** любой standalone-скрипт, который хочет звать MCP,
   должен иметь **свой MCP-клиент** через `requests` + SSE-парсер
   (как в этом скилле — `scripts/run_tests.py`). Скопировать
   реализацию `mcp_init()` / `mcp_call()` / `_parse_sse()` из этого
   скилла (около 50 строк), либо импортировать `mcp_config` из
   `fst-project-health/scripts/` (`sys.path.insert` + import).
   **Когда это НЕ применимо:** если скилл **всегда** вызывается
   через Hermes-агента (а не как cron/standalone) — он может
   полагаться на `tool_call`. Но `cron` с `python3 run.py` —
   **не** через агента, поэтому для cron-скиллов это правило
   обязательно.
   **Симптом:** в логах сессии — `ModuleNotFoundError: No module named
   'hermes_tools'` в начале первого standalone-запуска нового скилла.
   Причина — `from hermes_tools import tool_call` в `scripts/*.py`.
   Симптом исправлен в `fst-mcp-tester` v1.0.0 (свой SSE-клиент
   с самого начала).

## Что НЕ входит в скилл

- **Не тестирует** `save_entity`, `delete_entity`, `upload_entity_file`
  — это write-операции, противоречит принципу read-only.
- **Не генерирует нагрузку** (нет параллельных запросов, нет
  stress-test). Только последовательные тесты.
- **Не анализирует содержимое** ответов (только число записей и
  размер). Если нужно — отдельный скилл `fst-mcp-content-validator`.

## References

- `README.md` — краткая инструкция.
- `.env.example` — шаблон токена.
- `requirements.txt` — Python-зависимости.
- `outputs/` — сюда кладутся `.md` отчёты.
- Родственный скилл: `fst-project-health` (для которого мы пишем тесты).