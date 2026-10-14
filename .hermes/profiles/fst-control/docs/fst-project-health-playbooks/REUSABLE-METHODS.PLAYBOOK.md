# PLAYBOOK — переиспользуемые методы семейства fst-project-health

**Дата PLAYBOOK:** 2026-09-24
**Назначение:** каталог методов, которые можно вызвать из своего кода, с указанием скилла, параметров и операций.

---

## 1. Скилл `fst-project-health`

### 1.1. `run_all.py::main()` — главный pipeline live-сборки

- **Импорт:** `from run_all import main` (или CLI: `python3 run_all.py ...`).
- **Назначение:** собрать MD + HTML отчёт по MCP в реальном времени.
- **Параметры CLI:**
  - `--code <PROJECT_CODE>` (обязательный, можно несколько).
  - `--no-cache` (опционально).
  - `--generator <NAME>` (по умолчанию `fst-project-health`).
- **Что берёт из MCP:** проект целиком (карточка, КТ, бюджет, ресурсы, показатели) — через `find_project_by_code`, `lc_stage_kt_registry`, `get_effort`, `get_project_budget`, `project_indicators`.
- **Операции с данными:** параллельный опрос MCP → склейка секций в MD → сборка HTML.
- **Когда переиспользовать:** когда нужна **полная** сборка отчёта.

### 1.2. `build_html_report.py::build_html_report()` — MD → HTML

- **Импорт:** `from build_html_report import build_html_report`.
- **Назначение:** парсит MD → HTML.
- **Параметры:**
  - `md_path: Path` — путь к MD.
  - `generator: str = ""` — для front-matter.
  - `snapshot_timestamp: str = ""` — для шапки «Слепок от:».
- **Что берёт из MCP:** ничего (работает локально по MD).
- **Операции с данными:** парсинг pipe-таблиц, YAML, HTML-комментариев; рендеринг через Jinja.
- **Когда переиспользовать:** когда **MD уже есть**, нужно только HTML.

### 1.3. `rebuild_report.py::rebuild_report()` — склейка секций

- **Импорт:** `from rebuild_report import rebuild_report`.
- **Назначение:** склеить `/tmp/section_*_result.md` в финальный MD + YAML.
- **Параметры:**
  - `--sections-dir <DIR>` — где секции (по умолчанию `/tmp`).
  - `--output <PATH>` — куда (по умолчанию `/tmp/project_<code>_report.md`).
  - `--generator <NAME>` — для front-matter.
- **Что берёт из MCP:** ничего.
- **Операции:** склейка текста, добавление YAML.
- **Когда переиспользовать:** для восстановления MD из секций (например, после частичного сбоя).

### 1.4. `rebuild_report.py::_build_front_matter()` — YAML

- **Импорт:** `from rebuild_report import _build_front_matter`.
- **Назначение:** собрать YAML front-matter.
- **Параметры:** `generator`, `project_code`, `project_id`, `timestamp: Optional[str]`, `skill_version`, `schema_version`, `source_skill`, `source_skill_version`.
- **Когда переиспользовать:** в скриптах, которые создают MD вручную.

### 1.5. `mcp_config.py::get_mcp_client()` — MCP-клиент

- **Импорт:** `from mcp_config import get_mcp_client`.
- **Назначение:** создать SSE-клиент к PMForesight MCP.
- **Параметры:** нет (берёт из env / `~/.config/pmp/mcp.json`).
- **Что берёт из MCP:** устанавливает соединение.
- **Когда переиспользовать:** в любом скрипте, которому нужен MCP.

### 1.6. `find_project_by_code.py::find_project()` — код → ProjectId

- **Импорт:** `from find_project_by_code import find_project`.
- **Назначение:** код проекта → числовой ProjectId.
- **Параметры:** `code: str`.
- **Что берёт из MCP:** запрос `mcp__fst_pmpractice__find_entity("project", ...)`.
- **Когда переиспользовать:** в начале любого скрипта, работающего с MCP.

### 1.7. `project_indicators.py::get_indicators()` — 16 показателей

- **Импорт:** `from project_indicators import get_indicators`.
- **Назначение:** получить 16 показателей проекта (раздел 6).
- **Параметры:** `project_id: int`.
- **Что берёт из MCP:** данные по каждому показателю (16 вызовов).
- **Операции:** вычисление вердиктов (здоров/требует внимания/болен) по порогам.
- **Когда переиспользовать:** для анализа только показателей, без полного отчёта.

### 1.8. `lc_stage_kt_registry.py::get_kt_registry()` — реестр КТ

- **Импорт:** `from lc_stage_kt_registry import get_kt_registry`.
- **Назначение:** получить все КТ проекта.
- **Параметры:** `project_id: int`.
- **Что берёт из MCP:** реестр КТ (один вызов).
- **Когда переиспользовать:** для работы с КТ без полного отчёта.

### 1.9. `get_project_budget.py::get_budget()` — бюджет

- **Импорт:** `from get_project_budget import get_budget`.
- **Назначение:** план/факт/прогноз по бюджету.
- **Параметры:** `project_id: int`.
- **Что берёт из MCP:** бюджет проекта.
- **Когда переиспользовать:** для финансового анализа.

### 1.10. `get_effort.py::get_effort()` — трудозатраты

- **Импорт:** `from get_effort import get_effort`.
- **Назначение:** план/факт/прогноз по трудозатратам.
- **Параметры:** `project_id: int`.
- **Что берёт из MCP:** трудозатраты.
- **Когда переиспользовать:** для анализа ресурсов.

---

## 2. Скилл `fst-project-health-word`

### 2.1. `build_word_report.py::main()` — CLI

- **Импорт:** `python3 build_word_report.py ...`.
- **Параметры:** `--md PATH`, `--code CODE`, `--output PATH`, `--generator NAME`.

### 2.2. `build_word_report.py::parse_md_to_data()` — MD → data

- **Импорт:** `from build_word_report import parse_md_to_data`.
- **Назначение:** парсит MD в data-словарь.
- **Параметры:** `md_path: Path`.
- **Возвращает:** `dict` с полями `project_code`, `project_id`, `verdict`, `section_3` … `section_9`, `generator`, `snapshot_timestamp`, `summary_text`.
- **Когда переиспользовать:** для программной работы со структурой отчёта, без сборки DOCX.

### 2.3. `build_word_report.py::build_word_report_from_data()` — data → DOCX

- **Импорт:** `from build_word_report import build_word_report_from_data`.
- **Назначение:** собирает DOCX из data-словаря.
- **Параметры:** `data: dict`.
- **Возвращает:** `Document` (python-docx).
- **Когда переиспользовать:** когда хотим **модифицировать** отчёт перед сохранением.

### 2.4. `build_word_report.py::_parse_section()` — парсинг одной секции

- **Импорт:** `from build_word_report import _parse_section`.
- **Назначение:** парсит одну секцию MD.
- **Параметры:** `sec_text: str`, `expected_cols: int`.

### 2.5. `build_word_report.py::_parse_indicators_from_md()` — 16 показателей

- **Импорт:** `from build_word_report import _parse_indicators_from_md`.
- **Назначение:** парсит 16 показателей + вложенные таблицы.
- **Параметры:** `sec_text: str`.

### 2.6. `build_word_from_snapshot.sh` — bash-обёртка

- **Назначение:** цепочка `fetch_snapshot + build_word`.
- **Параметры:** коды проектов через пробел.

---

## 3. Скилл `fst-project-health-snap-md`

### 3.1. `run_snap_md.py::main()` — CLI

- **Импорт:** `python3 run_snap_md.py ...`.
- **Параметры:** `--code`, `--codes`, `--no-log`, `--log-dir`.

### 3.2. `run_snap_md.py::run_one()` — для одного проекта

- **Импорт:** `from run_snap_md import run_one`.
- **Назначение:** собрать MD и загрузить в MCP для одного проекта.
- **Параметры:** `code: str`, `log: RunLogger`.
- **Что берёт из MCP:** проект через `run_all.py` + записывает файл через `upload_entity_file`.
- **Операции:** subprocess `run_all.py` → read MD → upload.
- **Когда переиспользовать:** для интеграции в свои скрипты массовой генерации.

### 3.3. `logging_utils.py::RunLogger` — структурированный логгер

- **Импорт:** `from logging_utils import RunLogger`.
- **Назначение:** header/body/trailer для массовых операций.
- **Параметры:** `enabled: bool = True`, `log_dir: Path = ...`.
- **Методы:**
  - `log_header(account, role, action, args)`.
  - `log_body(code, ok, type, http_code, message, raw)`.
  - `log_trailer()`.
- **Когда переиспользовать:** в **любом** скрипте массовых операций (не только слепки).

### 3.4. `rotate_logs.py::rotate()` — ротация логов

- **Импорт:** `from rotate_logs import rotate`.
- **Назначение:** архивация логов (30/180 дней).
- **Когда переиспользовать:** для любых лог-файлов с такой политикой.

---

## 4. Скилл `fst-project-health-from-md-snapshot`

### 4.1. `fetch_snapshot.py::main()` — CLI

- **Импорт:** `python3 fetch_snapshot.py ...`.
- **Параметры:** `--code`, `--last`, `--exact`, `--nearest`, `--first`, `--pick`, `--list`, `--no-log`.

### 4.2. `fetch_snapshot.py::download_md()` — скачивание MD

- **Импорт:** `from fetch_snapshot import download_md`.
- **Назначение:** скачивает MD по physicalFileId.
- **Параметры:** `physical_file_id: str`, `target_path: Path`.
- **Что берёт из MCP:** `resources/read file://download-file/<id>`.
- **Retry:** 3 попытки с новой MCP-сессией.
- **Когда переиспользовать:** в любых скриптах скачивания файлов из MCP.

### 4.3. `fetch_snapshot.py::select_snapshot()` — выбор снапшота

- **Импорт:** `from fetch_snapshot import select_snapshot`.
- **Назначение:** выбирает снапшот из списка по режиму.
- **Параметры:** `files: list`, `mode: str`, `target_ts: Optional[str]`.

### 4.4. `fetch_snapshot.py::list_md_snapshots()` — список снапшотов

- **Импорт:** `from fetch_snapshot import list_md_snapshots`.
- **Назначение:** возвращает список всех `.MD` в карточке.
- **Параметры:** `code: str`.

### 4.5. `build_html.py::main()` — CLI

- **Импорт:** `python3 build_html.py ...`.
- **Параметры:** `--md PATH`, `--output PATH`, `--code CODE`.

### 4.6. `run.py::run()` — цепочка fetch+build

- **Импорт:** `from run import run`.
- **Назначение:** fetch → build_html.
- **Параметры:** `code: str`, `mode: str`, `target_ts: Optional[str]`.

### 4.7. `logging_utils.py::RunLogger` (расширенный)

- **Дополнительные поля** (по сравнению с snap-md):
  - `file_id`, `bytes_received`, `sha256`.
- **Когда переиспользовать:** для массового скачивания из MCP.

---

## 5. Скилл `fst-project-health-tests`

### 5.1. `run_all_tests.py::main()` — CLI

- **Импорт:** `python3 run_all_tests.py ...`.
- **Параметры:** `--group`, `--log`, `--log-dir`, `--project`.

### 5.2. `run_all_tests.py::TestRunner.run()` — запуск одной группы

- **Импорт:** `from run_all_tests import TestRunner`.
- **Назначение:** запуск одной группы тестов.
- **Параметры:** `group: str`.

### 5.3. `_helpers.py::_transient_safe` (декоратор)

- **Импорт:** `from _helpers import _transient_safe`.
- **Назначение:** обёртка с retry для устойчивости к MCP flake.
- **Когда переиспользовать:** в **любых** MCP-тестах.

### 5.4. `_helpers.py::_retry_mcp()`

- **Импорт:** `from _helpers import _retry_mcp`.
- **Назначение:** retry для MCP-вызовов.
- **Параметры:** `fn: Callable`, `max_attempts: int = 3`, `delay: int = 2`.

### 5.5. `_helpers.py::_is_transient()`

- **Импорт:** `from _helpers import _is_transient`.
- **Назначение:** определяет транзиентные ошибки.

### 5.6. `_helpers.py::_is_mcp_bug()`

- **Импорт:** `from _helpers import _is_mcp_bug`.
- **Назначение:** определяет, баг ли это MCP (vs наш код).

### 5.7. `scripts/rotate_logs.py::rotate()`

- **Политика:** 100/400 дней (отличается от других скиллов!).

---

## 6. Сводная таблица по переиспользованию

| Метод | Скилл | Что делает | Где вызывается |
|---|---|---|---|
| `run_all.py::main()` | fst-project-health | Главный pipeline | CLI / cron |
| `build_html_report.py::build_html_report()` | fst-project-health | MD → HTML | CLI / run_all / from-md-snapshot |
| `rebuild_report.py::rebuild_report()` | fst-project-health | Склейка секций | Из run_all |
| `find_project_by_code::find_project()` | fst-project-health | Код → ID | Везде |
| `project_indicators::get_indicators()` | fst-project-health | 16 показателей | Из run_all |
| `parse_md_to_data()` | fst-project-health-word | MD → dict | Из build_word_report |
| `build_word_report_from_data()` | fst-project-health-word | dict → DOCX | Из build_word_report |
| `_parse_indicators_from_md()` | fst-project-health-word | Парсинг показателей | Из parse_md_to_data |
| `run_one()` | fst-project-health-snap-md | Один снапшок | Из run_snap_md |
| `RunLogger` | snap-md / from-md-snapshot / tests | Структурированный лог | Из всех массовых |
| `rotate()` | все 3 | Ротация логов | Из cron |
| `download_md()` | fst-project-health-from-md-snapshot | Скачивание MD | Из fetch_snapshot |
| `select_snapshot()` | fst-project-health-from-md-snapshot | Выбор снапшота | Из fetch_snapshot |
| `list_md_snapshots()` | fst-project-health-from-md-snapshot | Список снапшотов | Из fetch_snapshot |
| `run.py::run()` | fst-project-health-from-md-snapshot | Цепочка fetch+build | Из CLI/cron |
| `_transient_safe` | fst-project-health-tests | Retry-decorator | В MCP-тестах |
| `_retry_mcp()` | fst-project-health-tests | Retry wrapper | В MCP-тестах |

---

## 7. Паттерны импорта

### 7.1. Программный импорт из своего скрипта

```python
import sys
from pathlib import Path

SKILL = Path.home() / ".hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts"
sys.path.insert(0, str(SKILL))

from run_all import main as run_health
from build_html_report import build_html_report
```

### 7.2. Через CLI (bash)

```bash
PYTHONPATH=$HOME/.hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts \
    python3 -c "from run_all import main; main()"
```

---

## 8. Зависимости (для импорта)

| Скилл | Зависимости |
|---|---|
| fst-project-health | requests, python-dotenv, MCP-клиент |
| fst-project-health-word | python-docx>=1.0.0 |
| fst-project-health-snap-md | (всё от fst-project-health) |
| fst-project-health-from-md-snapshot | requests, MCP-клиент |
| fst-project-health-tests | (зависит от всех остальных) |
