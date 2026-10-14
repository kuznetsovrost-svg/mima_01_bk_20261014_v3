# Transport & Portability — MCP-подключение и переносимость скилла

Связка между `scripts/mcp_config.py` (централизованный MCP-клиент) и тем, как
этот скилл переносится между Hermes/OpenClaw-инстансами.

## 1. Архитектура MCP-подключения

Когда скилл делает **любой** вызов к Форсайт, у нас **три** точки конфигурации:

| Слой | Где живёт | Что меняется редко |
|------|-----------|---------------------|
| **Hermes-MCP-клиент** (через `mcp__fst_pmpractice__*` в агенте) | `~/.hermes/profiles/fst-control/config.yaml → mcp_servers.fst_pmpractice` | URL инстанса (prod/dev/replica) |
| **Python-скрипты** (напрямую через `requests`) | `scripts/mcp_config.py` — **единая точка истины** для всех 3 исполняемых скриптов | URL, таймауты, заголовки |
| **Токен** | `PMP_TOKEN` в `os.environ` (загружается из `~/.hermes/profiles/fst-control/.env` для CLI-утилит) | Ротация JWT |

### `mcp_config.py` — почему он существует

До рефакторинга (2026-08-05) **каждый** из трёх исполняемых скриптов имел свою копию:

- `MCP_URL = "https://ppreplica.hera.pmpractice.ru/mcp"` (захардкожен 3 раза)
- `_require_token()` или `load_token()` (3 разных реализации)
- Парсинг SSE-ответа (3 копии одной и той же логики с pitfall #2, #3)
- Логика `initialize → notifications/initialized` (3 копии)

`mcp_config.py` объединил всё это. Теперь:

```python
from mcp_config import (
    MCP_URL,                    # URL сервера
    META_TIME_KEYS,             # ключи MetaModel для серверного времени
    ENV_FILE,                   # путь к .env (для CLI-утилит)
    require_token,              # бросает RuntimeError если PMP_TOKEN нет
    load_token_from_env_file,   # парсит .env напрямую (fallback для CLI)
    resolve_token,              # стратегия: --token → env → .env
    headers_for_call,           # стандартные заголовки (Accept: SSE обязательно)
    parse_sse_response,         # UTF-8 + полное тело (НЕ stream+iter_lines)
    mcp_init,                   # handshake: initialize → notifications/initialized
    mcp_call,                   # tools/call с парсингом двойного кодирования
    McpConnectionError,         # единое исключение
)
```

### Где URL всё ещё захардкожен

**`mcp_config.py` — единственное место, где зашит URL.** Если переходим с replica на prod:

```bash
# В scripts/mcp_config.py
MCP_URL: str = "https://prodserver.hera.pmpractice.ru/mcp"   # ← поменять здесь
```

Все три скрипта (`find_project_by_code.py`, `build_report_header.py`, `mcp_probe.py`) подхватят через импорт.

`mcp_probe.py` дополнительно позволяет переопределить URL через `--url` (для ad-hoc проверок):

```bash
python3 scripts/mcp_probe.py --url https://staging.../mcp --tools
```

## 2. Pitfalls реализованные в `mcp_config.py`

Эти pitfalls раньше были размазаны по коду скриптов. Теперь — централизованно:

| # | Pitfall | Где реализован в `mcp_config.py` |
|---|---------|----------------------------------|
| #2 | UTF-8 | `parse_sse_response()` форсирует `resp.encoding = "utf-8"` |
| #3 | SSE-парсинг | `parse_sse_response()` читает полное тело, не `stream=True + iter_lines` |
| #7 | Lazy token | `require_token()` падает только при вызове, не при импорте модуля |
| — | Двойное JSON-кодирование | `mcp_call()` парсит `result.content[0].text` одним `json.loads` |

Если добавляется новый скрипт — он **должен** импортировать `mcp_config` и **не** дублировать эту логику.

## 3. Файлы скриптов по группам

### Реально вызываемые (импортируются как модули)

| Файл | Что делает | Импортирует `mcp_config`? |
|------|-----------|---------------------------|
| `find_project_by_code.py` | Поиск проекта по `Code` | ✅ Да |
| `build_report_header.py` | `Name` + серверное время | ✅ Да |
| `mcp_probe.py` | CLI-утилита для прямых вызовов | ✅ Да (но `urllib` для HTTP-уровня) |

### Справочные выдержки (НЕ импортируются — псевдокод для агента)

17 файлов: `point-timing-*-thresholds.py`, `point-overdue-thresholds.py`, `effort-gap-threshold.py`, `OwnerID-check.py`, `LeaderID-check.py`, `Passport-check.py`, `Effort-check.py`, `Payments-graph-check.py`, `Points-forecast-relevance.py`, `Forecasted-*.py`, `Fin-result-check.py`, `Financial-deviation-threshold.py`, `finresult-thresholds.py`, `project-health-summary.py`.

Эти файлы **не запускаются** напрямую. Агент читает их как образец при написании `/tmp/run_section_N.py`. Если нужно запустить пороги как код — используй `importlib.util.spec_from_file_location()` (pitfall #5).

## 4. Переносимость скилла (Перенос-скиллов-01)

Подробный разбор в `Перенос-скиллов-01.md` в корне профиля. Здесь — краткая сводка.

### Что упаковать в архив для переноса на другой Hermes-инстанс

```
fst-project-health.tar.gz
└── skills/productivity/fst-project-health/
    ├── SKILL.md                      (точка входа с триггерами и pitfalls)
    ├── references/                   (pitfalls, схемы, recipes)
    │   ├── forsight-mcp-quirks.md
    │   ├── mcp-sse-parsing-and-utf8.md
    │   ├── contract-binding-via-parentfullname.md
    │   ├── project-health-cost-view.md
    │   ├── project-architecture.md
    │   ├── project-finance-budget-entities.md
    │   ├── mcp-api-quirks.md
    │   └── project-search-workflow.md
    └── scripts/
        ├── mcp_config.py             ← ЦЕНТРАЛЬНЫЙ, единая точка истины
        ├── find_project_by_code.py   ← вызываемый
        ├── build_report_header.py    ← вызываемый
        ├── mcp_probe.py              ← вызываемый
        └── <17 справочных выдержек>  ← псевдокод, читается агентом
```

В **отдельный архив** — `project-search` (зависимость из `related_skills`).

### Что НЕ коммитить (если в Git)

```gitignore
.env
.env.bak.*
auth.json
*.lock
*.pid
.hermes_history
cache/
logs/
audio_cache/
image_cache/
images/
.curator_backups/
__pycache__/
```

### Smoke-тест после разворачивания

```bash
# 1. MCP подключение
python3 ~/.hermes/profiles/<profile>/skills/productivity/fst-project-health/scripts/mcp_probe.py --tools | head

# 2. Поиск проекта (должен вернуть dict)
python3 ~/.hermes/profiles/<profile>/skills/productivity/fst-project-health/scripts/find_project_by_code.py 504-595

# 3. Заголовок отчёта
python3 -c "
import sys
sys.path.insert(0, '~/.hermes/profiles/<profile>/skills/productivity/fst-project-health/scripts')
from build_report_header import build_report_header
h = build_report_header(4595)
print(h['project_name'], h['server_time_str'])
"
```

Если все три проходят — скилл перенесён корректно.

## 5. Версионирование изменений

Каждое значимое изменение структуры — bump version в frontmatter:

| Что изменилось | Version |
|----------------|---------|
| Создание скилла | 0.1.0 |
| V04 → V05 контракт-фильтр `ParentFullName` | 0.2.0 |
| Добавлены pitfalls #10, #11, #12 | 0.3.0 |
| Рефакторинг: `mcp_config.py` как единая точка истины + этот reference | 0.4.0 |

(История рефакторингов зафиксирована в git-коммитах и в этом reference.)
