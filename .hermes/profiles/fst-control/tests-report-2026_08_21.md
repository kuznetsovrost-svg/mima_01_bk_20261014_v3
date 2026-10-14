# Отчёт о самотестировании скилла `fst-project-health`

**Дата:** 2026-08-21
**Тестировщик:** ROSTISLAV KUZNETSOV (через Hermes-агент)
**Версия скилла:** 0.9.0

---

## TL;DR

✅ **6 из 6 тестов PASS (0 FAIL)** за **1.272 сек**.
✅ **Все 10 production скриптов импортируются** без ошибок.
✅ **Нет хардкода project_code/project_id** в production скриптах.
✅ **SKILL.md целостен**: версия >= 0.9.0, FIGMA в production отсутствует.
✅ **CLI run_all.py работает** — все аргументы (--code, --no-html, --no-word, --sections, --timing).
✅ **Pipeline работает** для 503-434: 67.46 сек end-to-end (MD + HTML).

---

## Тесты (всего 38 подтестов в 6 файлах)

### 1. `test_no_hardcode.py` ✅ PASS (0.075 сек)

**Проверяет:** отсутствие хардкода `504-595` / `4595` в production скриптах.

**Что исключается из проверки:**
- docstrings и комментарии
- help-тексты argparse (примеры для пользователя)
- f"..." строковые литералы с примерами
- print() с примерами
- Справочные выдержки (`*-check.py`, `*-thresholds.py`)

**Production скрипты (10):**
- build_html_report.py ✅
- build_report_header.py ✅
- build_word_report.py ✅
- rebuild_report.py ✅
- find_project_by_code.py ✅
- run_all.py ✅
- get_effort.py ✅
- get_project_budget.py ✅
- get_metamodel.py ✅
- mcp_config.py ✅

### 2. `test_imports.py` ✅ PASS (0.211 сек)

**Проверяет:** все 10 production модулей импортируются через `importlib.util.spec_from_file_location`.

**ВАЖНО:** для корректной работы `@dataclass` модуль **должен** регистрироваться в `sys.modules` ДО `exec_module`:
```python
sys.modules[name] = m  # ← обязательно!
spec.loader.exec_module(m)
```

### 3. `test_helpers.py` ✅ PASS (0.157 сек)

**Проверяет:** helpers в `mcp_config.py`:
- `ALL_MY_POINT_VIEW_FOR(3434)` → `"AllMyPoint?ProjectId=3434"` ✅
- `PROJECT_BUDGET_VIEW_FOR(4595)` → `"ProjectBudgetCompleteBusiness?ProjectId=4595"` ✅
- `PROJECT_RESOURCE_PLAN_VIEW_FOR(3434)` → `"ProjectResourcePlan?ProjectId=3434"` ✅
- `mcp_init`, `mcp_call`, `parse_sse_response` — импортируемые ✅
- `META_TIME_KEYS` существует ✅

### 4. `test_run_all.py` ✅ PASS (0.160 сек)

**Проверяет:** структуру `run_all.py` (оркестратор):
- `parse_date` обрабатывает ISO, null, invalid ✅
- `build_section_3..8` существуют ✅
- `build_html` / `build_word` используют `importlib` (in-process, не subprocess) ✅
- `main()` принимает `--code` (required), `--no-html`, `--no-word`, `--sections`, `--timing` ✅
- `cache_get` / `cache_put` существуют с TTL=300 сек ✅

### 5. `test_pipeline_integration.py` ✅ PASS (0.606 сек)

**Проверяет:** CLI скриптов через `subprocess`:
- `run_all.py --help` ✅
- `run_all.py` без `--code` → падает с ошибкой ✅
- `build_html_report.py --help` ✅
- `build_html_report.py --ls` ✅
- `build_word_report.py --help` ✅
- `rebuild_report.py` без аргументов → показывает usage ✅

### 6. `test_skill_md_integrity.py` ✅ PASS (0.064 сек)

**Проверяет:** SKILL.md целостен:
- Frontmatter `---\\nname: fst-project-health` ✅
- Версия `>= 0.9.0` (после FIGMA-отката) ✅
- Нет FIGMA-bridge функционала (только в правилах/предупреждениях) ✅
- Hard rule о не-трогании SKILL.md/scripts/templates/references ✅
- Упоминание производительности pipeline ✅
- Ссылки на references/* процедуры ✅
- Все 4 формата вывода (MD, HTML, MD Форма 2, WORD Форма 1) ✅

---

## Замеры времени (live-benchmark, 503-434, 2026-08-21)

### Тесты (быстро)

| Тест | Время |
|------|------:|
| test_helpers.py | 0.157 сек |
| test_imports.py | 0.211 сек |
| test_no_hardcode.py | 0.075 сек |
| test_pipeline_integration.py | 0.606 сек |
| test_run_all.py | 0.160 сек |
| test_skill_md_integrity.py | 0.064 сек |
| **TOTAL тестов** | **1.272 сек** |

### Pipeline run_all.py для 503-434 (после оптимизаций 2026-08-08)

| Стадия | Время | Узкое место? |
|--------|------:|:------------|
| find_project (MyProject + AllProject) | 3.76 сек | Сетевой round-trip |
| save_project_json (get_entity_data) | 2.54 сек | Сетевой round-trip |
| load_project_points (AllMyPoint?ProjectId=) | 0.98 сек | ✅ оптимизировано |
| load_project_entity (get_entity_data) | 2.56 сек | Сетевой round-trip |
| section_3 (сроки КТ) | 0.00 сек | ✅ из кэша |
| section_4 (Effort + Budget + Entity) | 9.64 сек | Effort/Budget N+1 |
| section_5 (прогнозы) | 0.00 сек | ✅ из кэша |
| section_6 (ProjectHealthCostMy) | **44.69 сек** | **❌ 2000 строк** |
| section_7 (MetaModel) | 3.24 сек | 1 запрос |
| section_8 (сводка) | 0.00 сек | ✅ |
| rebuild_md (склейка) | 0.04 сек | ✅ |
| build_html (in-process) | 0.00 сек | ✅ |
| **TOTAL pipeline** | **67.46 сек** | |

### Сравнение ДО/ПОСЛЕ оптимизаций

| Этап | До | После | Разница |
|------|---:|------:|--------:|
| **Текущая версия (с оптимизациями)** | 80 сек | **67.46 сек** | **−12.5 сек (−16%)** |
| С ожидаемым `?ProjectId=` для ProjectHealthCostMy | — | **~28 сек** | **−40 сек (−59%)** |

---

## Процедура самотестирования

После обновления скилла — запускать:

```bash
python3 tests/run_all_tests.py --report
```

**Результат:** 6/6 PASS, 1.272 сек.

Опционально — полная проверка pipeline:

```bash
python3 scripts/run_all.py --code 503-434 --no-word --timing
```

**Результат:** 67.46 сек для одного проекта.

---

## Файлы

```
fst-project-health/
├── tests/
│   ├── run_all_tests.py            # Оркестратор тестов (1.3 сек на 6 файлов)
│   ├── test_no_hardcode.py         # Хардкод project_code/project_id
│   ├── test_imports.py             # Импорт всех production модулей
│   ├── test_helpers.py             # Helpers mcp_config.py
│   ├── test_run_all.py             # Структура run_all.py
│   ├── test_pipeline_integration.py # CLI через subprocess
│   ├── test_skill_md_integrity.py  # SKILL.md целостность
│   └── test_report.json            # Последний JSON-отчёт (создаётся через --report)
└── scripts/
    └── run_all.py                  # Оркестратор pipeline (67 сек на 503-434)
```

---

## Вердикт

✅ **Skill `fst-project-health` v0.9.0 прошёл самотестирование (6/6 PASS, 1.3 сек).**
✅ **Pipeline работает корректно на 503-434 за 67.46 сек.**
✅ **Нет хардкода, нет FIGMA-bridge функционала, SKILL.md целостен.**

⚠️ **Узкое место:** `section_6 = 44.69 сек` (ProjectHealthCostMy, 2000 строк). Решается **только** добавлением `?ProjectId=<id>` на стороне MCP-сервера. Playbook — `references/mcp-server-filter-playbook.md`.

🎯 **После исправления MCP-сервера:** прогнозируемое время pipeline **~28 сек** (−59% от текущего).

---

## Запуск тестов: рекомендация

После **любого изменения** скилла запускать:

```bash
python3 tests/run_all_tests.py --report
```

Если все 6 PASS — можно публиковать изменения. Если есть FAIL — смотреть детальный stderr (test_report.json содержит `stderr_tail`).

Для CI/CD (по желанию):

```bash
python3 tests/run_all_tests.py --report && python3 scripts/run_all.py --code 503-434 --no-word
# exit code 0 = OK, 1 = FAIL
```

Время: ~70 сек total (1.3 тесты + 67 pipeline).
