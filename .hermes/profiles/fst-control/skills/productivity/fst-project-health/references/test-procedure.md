# Self-test procedure: `tests/` подкаталог

**Дата:** 2026-08-21
**Live-probe:** 6/6 PASS за 1.3 сек на момент создания.

## Когда запускать

**Обязательно** после любого изменения в любом из:
- `scripts/build_html_report.py` или `scripts/build_word_report.py`
- `scripts/run_all.py`
- `scripts/mcp_config.py` (особенно helpers вроде `*_VIEW_FOR(project_id)`)
- `templates/report.html` или `templates/report.css`
- `SKILL.md` (frontmatter, version, hard rule)
- любого скрипта в `scripts/`, который может содержать хардкод

## Как запускать

```bash
cd /root/.hermes/profiles/fst-control/skills/productivity/fst-project-health/tests

# Полный прогон + JSON-отчёт
python3 run_all_tests.py --report

# Без JSON-отчёта (только stdout)
python3 run_all_tests.py

# Пропустить subprocess-based тесты (быстрее, без вызова CLI скриптов)
python3 run_all_tests.py --fast
```

**Ожидаемый результат:** 6/6 PASS, ~1.3 сек. JSON-отчёт в `tests/test_report.json`.

## Что проверяет каждый тест

| # | Тест | Проверяет | Время |
|---|------|-----------|------:|
| 1 | `test_no_hardcode.py` | `\b504-595\b` / `"data_id": 4595` в production-коде (исключая help-тексты argparse, docstrings, f-strings с примерами, `print(...)` с примерами, справочные `*-check.py` / `*-thresholds.py`) | ~80мс |
| 2 | `test_imports.py` | все 10 production модулей через `importlib.util.spec_from_file_location` с `sys.modules[name] = m` ДО `exec_module` (иначе `@dataclass` падает на `__module__`) | ~210мс |
| 3 | `test_helpers.py` | `ALL_MY_POINT_VIEW_FOR(3434)` = `"AllMyPoint?ProjectId=3434"`, и др.; `mcp_init`/`mcp_call` импортируются; **новое (регрессия Bug #71):** `status_class("Синий")` = `"status-info"`, `status_class("Желтый")` / `"Жёлтый"` = `"status-warning"`, `status_class("Красный")` = `"status-critical"` | ~150мс |
| 4 | `test_run_all.py` | структура `run_all.py`: `parse_date` обрабатывает ISO/null/invalid; `build_section_3..8` существуют; `build_html` / `build_word` используют `importlib` (НЕ subprocess); `main()` имеет `--code`/`--no-html`/`--no-word`/`--sections`/`--timing`; `cache_get`/`cache_put` существуют с TTL=300 сек | ~160мс |
| 5 | `test_pipeline_integration.py` | subprocess-based: `run_all.py --help` работает; `run_all.py` без `--code` падает; `build_html_report.py --help` / `--ls`; `build_word_report.py --help`; `rebuild_report.py` без аргументов → usage | ~610мс |
| 6 | `test_skill_md_integrity.py` | frontmatter `---\nname: fst-project-health`; version >= 0.9.0; нет FIGMA-bridge функционала (только в правилах/предупреждениях); hard rule о не-трогании присутствует; упоминание производительности pipeline; ссылки на `references/*`; все 4 формата вывода (MD / HTML / MD Форма 2 / WORD Форма 1) | ~60мс |

## Регрессионные проверки для Bug #70-#73

Эти 4 бага были исправлены в `build_html_report.py` + `run_all.py` + `templates/report.css` 2026-08-21. После изменения этих файлов — обязательно выполнить 3 проверки:

```bash
cd /root/.hermes/profiles/fst-control/skills/productivity/fst-project-health

# 1. Indicator НЕ должен быть unknown ("Нет данных")
python3 scripts/run_all.py --code 504-314 --no-word
grep 'data-status=' /tmp/project_504-314_report.html | head -1
#   Ожидаемо: <div class="report-indicator-circle" data-status="sick">  (или attention/healthy)
#   НЕ: data-status="unknown"

# 2. Подсветка строк (Bug #71)
grep -c 'status-warning\|status-info\|status-critical' /tmp/project_504-314_report.html
#   Ожидаемо: ≥ 8 (включая вложенные tr)
#   НЕ: 0 (тогда status_class не работает)

# 3. Данные в разделе 7 (Bug #73)
grep -A 1 'Значение' /tmp/project_504-314_report.html | grep -v '—' | head -5
#   Ожидаемо: 3 непустых значения (Title, CoreVersion, Version)
#   НЕ: все прочерки
```

Если хотя бы одна проверка падает — **не коммитить изменения**, откатить и починить.

## Подводные камни тестов

### `@dataclass` + `importlib.util`

`get_effort.py`, `get_project_budget.py` используют `@dataclass`. Если забыть `sys.modules[name] = m` ДО `exec_module(m)`, получаем:
```
AttributeError: 'NoneType' object has no attribute '__dict__'
```
**Фикс:**
```python
spec = importlib.util.spec_from_file_location(name, str(path))
m = importlib.util.module_from_spec(spec)
sys.modules[name] = m  # ← ОБЯЗАТЕЛЬНО до exec_module
spec.loader.exec_module(m)
```

### `unittest.assertRegex` не поддерживает флаги

`assertRegex(text, regex)` использует `re.search` **без флагов** (без `re.MULTILINE`!). Для многострочных regex:
```python
# ❌ Не работает:
self.assertRegex(content, r"^name:\s+fst-project-health", re.MULTILINE)

# ✅ Работает:
m = re.search(r"^name:\s+fst-project-health", content, re.MULTILINE)
self.assertIsNotNone(m, "msg")
```

### Help-тексты argparse vs хардкод

`argparse.add_argument(..., help="Код проекта (например, 504-595)")` — **НЕ хардкод** для `test_no_hardcode.py`. Regex `strip_comments_and_docstrings()` убирает:
- `help="...504-595..."` (любые 504-595 / 503-434 / 503-152 в help-текстах)
- `f"..."` строки с примерами
- `print(...504-595...)` строки
- docstrings и однострочные комментарии

Если тест падает на строке типа `parser.add_argument("--code", type=str, help="Код проекта (например, 504-595)")` — это **false positive**. Проверь что regex покрывает нужные формы.

### `exec_module(m)` не вызывает `m.main()`

`importlib.util.spec_from_file_location(...).exec_module(m)` выполняет **весь код модуля, кроме** `if __name__ == "__main__":`. Для CLI-скриптов это означает: `main()` **не вызывается автоматически**. Если `run_all.py` запускает `build_html_report.py` через `exec_module(m)` для оптимизации — нужно **явно** вызвать `m.main()`:
```python
spec.loader.exec_module(m)
result = m.main()  # ← без этого build_html_report ничего не делает
```

## Тест при FIGMA-экспериментах (отдельный скилл!)

**Запрещено** добавлять FIGMA-тесты в `fst-project-health/tests/`. Если работа над FIGMA round-trip идёт в отдельном скилле (`skills/creative/figma-bridge/` или подобном) — тесты должны быть там.

`fst-project-health/tests/` — только для production отчётов о здоровье проектов.

## Добавление нового теста

При появлении новой ошибки в pipeline:
1. Воспроизведи минимально (1 проект, 1 команда).
2. Посмотри **какой файл** сломался (`build_html_report.py` / `run_all.py` / скрипт X).
3. Добавь `test_*.py` файл под `tests/` (по конвенции: `test_<функция_которую_проверяем>.py`).
4. Включи в `tests/run_all_tests.py` (он автоматически подхватывает `test_*.py` через `glob`).
5. Обнови `SKILL.md` → секцию `## Self-testing convention` — добавь строку в таблицу.

**Чек-лист:**
- [ ] Тест использует `importlib.util` правильно (`sys.modules[name] = m` ДО `exec_module`).
- [ ] Тест НЕ зависит от MCP (никаких сетевых вызовов внутри теста).
- [ ] Тест быстрый (<1 сек на прогон).
- [ ] При падении — `AssertionError` сообщение информативно (с конкретным значением, не «False is not true»).

## Файлы тестов

```
fst-project-health/tests/
├── run_all_tests.py            # Оркестратор (1.3 сек на 6 файлов)
├── test_no_hardcode.py         # Хардкод project_code/project_id (исключает help-тексты argparse)
├── test_imports.py             # Импорт всех production модулей
├── test_helpers.py             # Helpers mcp_config.py + status_class
├── test_run_all.py             # Структура run_all.py
├── test_pipeline_integration.py # CLI через subprocess
├── test_skill_md_integrity.py  # SKILL.md целостность
└── test_report.json            # Последний JSON-отчёт (создаётся через --report)
```

**Итого:** 6 test-файлов, ~38 подтестов, **1.3 сек** total runtime.