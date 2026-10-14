# Procedure: `scripts/run_all.py` — single-command pipeline (live-probe 2026-08-21)

## Когда использовать

Когда пользователь говорит: «построй отчёт по проекту `<code>`», «запусти pipeline для `<code>`», «отчёт здоровья по `<code>`».

**Один CLI** строит все 5 артефактов (MD, HTML, WORD, плюс промежуточные `section_*_result.md`).

## Usage

```bash
# Полный pipeline (MD + HTML + WORD):
python3 scripts/run_all.py --code 503-434

# Без WORD:
python3 scripts/run_all.py --code 504-595 --no-word

# Только некоторые секции (для отладки):
python3 scripts/run_all.py --code 503-152 --sections 3,4,5

# Произвольный проект (любой из MyProject/AllProject):
python3 scripts/run_all.py --code 700-XXX
```

## Что делает `run_all.py`

| Шаг | Действие | Скрипт/функция |
|-----|----------|-----------------|
| 1 | Поиск `ProjectId` по `Code` | `find_project` (MyProject + AllProject) |
| 2 | Сохранение `/tmp/proj_<code>.json` | `get_entity_data(Project, pid)` |
| 3 | Секция 3 (Сроки КТ) | inline `classify_relevance` (НЕ из файла) |
| 4 | Секция 4 (Полнота) | `get_project_effort`, `get_project_budget` |
| 5 | Секция 5 (Прогнозы) | inline `classify_relevance` (НЕ из файла) |
| 6 | Секция 6 (Финансы) | `get_view(ProjectHealthCostMy)` + `FINRESULT_THRESHOLDS` |
| 7 | Секция 7 (Тех. данные) | `get_metamodel_metadata(sid=sid)` |
| 8 | Секция 8 (Сводка) | reads `/tmp/section_3..7_result.md` |
| 9 | Сборка MD | `rebuild_report.py <code> <name> <pid>` |
| 10 | Сборка HTML | `build_html_report.py --code <code>` |
| 11 | Сборка WORD | `build_word_report.py --code <code>` |

## Live-bugs (исправлено в run_all.py)

### Bug #64: `ProjectId` vs `id` в `MyProject` view

В views `MyProject` и `AllProject` поле `id` — это **внутренний sequence**, не ProjectId. Правильное поле — **`ProjectId`**.

```python
# ❌ Неправильно — даёт 2 для 503-434:
pid = target.get("id") or target.get("ProjectId")

# ✅ Правильно — даёт 3434:
pid = target.get("ProjectId") or target.get("id")
```

Без этого `get_entity_data(Project, "2")` возвращает ошибку вместо данных 503-434.

### Bug #65: Справочные выдержки не импортируются

Файлы `Passport-check.py`, `Effort-check.py`, `Points-forecast-relevance.py`, `Forecasted-financial-result*.py`, `Fin-result-check.py`, `Payments-graph-check.py` — **справочные выдержки** для SKILL.md, а не модули.

Они вызывают **заглушки** `mcp__fst_pmpractice__get_view(...)` для документации. `importlib.util.spec_from_file_location()` падает на NameError.

**Решение:** скопировать нужную функцию (например, `classify()` из `Points-forecast-relevance.py`) **inline** в `run_all.py`. Не пытайся импортировать.

### Bug #66: Ключи `FINRESULT_THRESHOLDS`

```python
# ❌ KeyError: 'forecast_negative', 'devcost_deviation'
FINRESULT_THRESHOLDS["forecast_negative"]["max_value"]
FINRESULT_THRESHOLDS["devcost_deviation"]["min_value"]

# ✅ Правильно:
FINRESULT_THRESHOLDS["current_cost_deviation"]["max_value"]    # = 1_000_000
FINRESULT_THRESHOLDS["end_finresult_decrease"]["max_value"]     # = 2_000_000
```

### Bug #67: `Passport-check.py` — `phase_requires_passport = phase_num >= 2`

Не `<= 2` (как было в v1), а `>= 2`. Пресейл — паспорт необязателен. Инициирование+ — обязателен.

### Bug #68: `get_metamodel_metadata(sid=None)` — нужен `sid`

Без передачи `sid` создаётся **новая** MCP-сессия на каждый вызов. Это ~10-30 сек overhead на сессию.

```python
# ❌ Плохо:
data = get_metamodel_metadata()  # каждый раз новая сессия

# ✅ Хорошо:
sid, _ = mcp_init()
data = get_metamodel_metadata(sid=sid)  # переиспользует сессию
```

### Bug #69: `importlib.util + exec_module` НЕ запускает `if __name__ == "__main__"`

In-process вызов через `importlib.util.spec_from_file_location` + `exec_module` загружает модуль, но **не вызывает** код под `if __name__ == "__main__"`. Симптом: `run_all.py` падает с `RuntimeError: HTML не создан` хотя `build_html_report.py --code <code>` отдельно создаёт файл.

**Решение:** явно вызвать `m.main()` после `exec_module` + **ОБЯЗАТЕЛЬНО** зарегистрировать модуль в `sys.modules` ДО `exec_module` (для `@dataclass`):

```python
spec = importlib.util.spec_from_file_location("build_html_report", str(path))
m = importlib.util.module_from_spec(spec)
sys.modules["build_html_report"] = m       # ← ОБЯЗАТЕЛЬНО ДО exec_module
spec.loader.exec_module(m)
result = m.main()                          # ← ОБЯЗАТЕЛЬНО вызвать явно
```

Применяется в `build_html()` и `build_word()` в `run_all.py`.

### Bug #76: «Актуальность прогнозов» = ТОЛЬКО по `forecast_date` vs `today`

В `build_section_5()` действуют **только три правила**:

1. Если `fact_date` есть → строка **не выводится** (работа закрыта).
2. Если `forecast_date >= today` → строка **не выводится** (прогноз в будущем).
3. Если `forecast_date < today` → `overdue_days = today - forecast_date`, классификация по overdue_days.

**`PlanDate` НЕ участвует** в просрочке. **`diff = forecast - plan` НЕ участвует** в классификации. Это ТОЛЬКО для `build_section_5()` (раздел 5). В `build_section_3()` (раздел 3 «Замечания по срокам») — другая логика: замечания = любые КТ с `forecast != plan`.

**Регрессия (пользователь поймал 2026-08-21 на 503-434):** строки 104-208, 104-209 (forecast=2026-08-31) **НЕ должны** быть в разделе 5.

## Поддержка нескольких projectID

Все скрипты pipeline принимают `code` и `pid` как параметры:

| Скрипт | CLI аргумент |
|--------|--------------|
| `build_html_report.py` | `--code <code>` |
| `build_report_header.py` | `<pid>` positional |
| `rebuild_report.py` | `<code> <name> <pid>` |
| `find_project_by_code.py` | `<code>` |
| `build_word_report.py` | `--code <code>` |
| `get_effort.py` | `--project <code>` / `--project-id <pid>` |
| `get_project_budget.py` | `--project <code>` / `--project-id <pid>` / `--activity-id <pid>` |
| `get_metamodel.py` | `--title` / `--version` / `--core-version` / `--key <Name>` / `--all` |

**Запрещено хардкодить** `504-595` / `4595` / `503-152` / `3152` / `3434` в реальных скриптах pipeline. Это разрешено **ТОЛЬКО** в справочных выдержках.

## Время выполнения (benchmark 2026-08-21)

| Проект | ProjectId | КТ | Время |
|--------|-----------|-----|------:|
| 504-595 | 4595 | — | ~50 сек |
| 503-434 | 3434 | 34 | ~50 сек |
| 503-152 | 3152 | 1 100+ | ~80 сек |

**Боттлнек:** Sections 4-7 (5 разных `mcp_call`). Section 3 — доминирует для больших проектов (load 1100+ КТ).

## Multi-project case

`run_all.py` перезаписывает `/tmp/section_*_result.md` на каждом запуске. Для multi-project case в одной сессии — **не запускайте `run_all.py` параллельно** (будут гонки). Запускайте последовательно с разными `--code`.

**Convention** (per `pitfall #37`): для multi-project — переименовывайте `section_*_result.md` с суффиксом:
```bash
python3 scripts/rebuild_report.py "503-152" "ФРП" 3152 "_503-152"
# reads /tmp/section_3_503-152_result.md, NOT /tmp/section_3_result.md
```

`run_all.py` пока **не поддерживает** `section_suffix` — он пишет в `section_3_result.md` (без суффикса). Если нужно multi-project в одной сессии — переименовывай вручную или переделай `run_all.py`.

## Файлы, которые `run_all.py` создаёт

```
/tmp/proj_<code>.json                          # данные проекта (build_html_report требует)
/tmp/section_3_result.md                        # Сроки КТ
/tmp/section_4_result.md                        # Полнота
/tmp/section_4_data.json                       # (вспомогательный)
/tmp/section_5_result.md                        # Прогнозы
/tmp/section_5_data.json                       # (вспомогательный)
/tmp/section_6_result.md                        # Финансы
/tmp/section_6_data.json                       # (вспомогательный)
/tmp/section_7_result.md                        # Тех. данные
/tmp/section_7_data.json                       # (вспомогательный)
/tmp/section_8_result.md                        # Сводка
/tmp/project_<code>_report.md                  # финальный MD
/tmp/project_<code>_report.html                # финальный HTML
/tmp/project_<code>_report_WORD-форма1.docx     # финальный WORD (если не --no-word)
```

## Защита от FIGMA-изменений (повторный hard rule)

`fst-project-health/` — **production** skill. Не добавляй FIGMA/HTML-bridge workflows в этот скилл. Используй `figma-api-import` или создай отдельный скилл.

Если клиент просит «добавь FIGMA-bridge в fst-project-health» — **не делай**, предложи отдельный скилл в `skills/creative/figma-bridge/` (или подобное).
