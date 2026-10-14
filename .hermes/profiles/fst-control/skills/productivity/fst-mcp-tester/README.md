# fst-mcp-tester

Скилл для read-only тестирования всех методов MCP, которые использует
`fst-project-health`. По итогам прогона формирует подробный MD-отчёт с
замерами времени, объёмов payloads и рекомендациями по оптимизации.

## Зачем

- Проверить, что все MCP-методы (`initialize`, `tools/call` с `get_view`,
  `get_entity_data`, `find_entity`) отвечают ожидаемо.
- Получить реальные метрики: латентность, число записей, размер
  payload, ретраи — для тюнинга `TIMEOUT_TOOLS_CALL` и кешей.
- Безопасно: **не модифицирует данные** на стороне MCP.

## Использование

```bash
cd ~/.hermes/profiles/fst-control/skills/productivity/fst-mcp-tester
pip install -r requirements.txt
cp .env.example .env
nano .env  # вписать PMP_TOKEN

# Полный прогон
python3 scripts/run_tests.py

# Быстрый (без замера payload-размера)
python3 scripts/run_tests.py --quick

# Свой путь к отчёту
python3 scripts/run_tests.py --output ./my_report.md
```

## Как поменять тестируемый проект

Откройте `scripts/run_tests.py` и в блоке «Конфигурация тестируемого
проекта» измените:

```python
TEST_PROJECT_CODE = "504-595"   # код проекта (например, "704-724")
TEST_PROJECT_ID   = 4595        # числовой ID проекта в PMForesight
```

Или через переменные окружения (без правки скрипта):

```bash
MCP_TEST_PROJECT_CODE=704-724 MCP_TEST_PROJECT_ID=4724 python3 scripts/run_tests.py
```

`project_id` можно узнать из `fst-project-health` через поиск по коду
(`find_project_by_code.py`) или через UI PMForesight.

## Структура

```
fst-mcp-tester/
├── SKILL.md            # описание скилла для Hermes Agent
├── README.md           # этот файл
├── .env.example        # шаблон токена (без секретов)
├── requirements.txt    # Python-зависимости
├── scripts/
│   └── run_tests.py    # основной скрипт (тест-план + замеры + отчёт)
├── templates/          # (заготовка под будущие шаблоны)
└── outputs/            # сюда кладутся .md-отчёты
```

## Что попадает в отчёт

1. **Executive summary** — сводная статистика (ok/error/exception,
   avg/median/p95, total payload).
2. **Результаты по категориям** — lifecycle / view / entity / search.
3. **Детальная таблица** — каждый тест с таймингами, числом записей,
   размером payload, текстом ошибки.
4. **ASCII-гистограмма** — распределение латентности по 20 бакетам.
5. **Сводка по payload'ам** — самые тяжёлые ответы + среднее байт/запись.
6. **Ошибки и предупреждения** — подробный вывод с stack trace.
7. **Рекомендации по оптимизации** — на основе реальных замеров.
8. **Сырые данные** — JSON для дальнейшей обработки.

## Переносимость

Скилл portable — работает и в Hermes-профиле `fst-control`, и автономно
в любом каталоге. `PMP_TOKEN` ищется в порядке:

1. `os.environ["PMP_TOKEN"]`
2. `<каталог скилла>/.env`
3. `~/.hermes/profiles/fst-control/.env`