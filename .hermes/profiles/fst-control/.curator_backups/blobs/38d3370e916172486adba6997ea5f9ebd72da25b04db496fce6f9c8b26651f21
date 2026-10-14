# Зависимости скилла fst-project-health

**Версия:** v1.0.14 (2026-09-04)

---

## 🔗 Связанные скиллы (related skills)

### 1. `project-search` (встроен в каталог скилла)

| Поле | Значение |
|---|---|
| Расположение | `fst-project-health/project-search/` |
| Версия | 2.0.0 |
| Назначение | Поиск проекта в PMForesight по коду, имени или частичному совпадению |
| Когда используется | Первый шаг: пользователь говорит «отчёт по 504-595» → скилл находит `ProjectId` |
| Связь с `fst-project-health` | **Встроен как submodule** в каталог скилла |

**Пример потока:**
```
Пользователь: "Отчёт по Космодром Жуковский"
  → project-search: ищет проект по имени
  → находит ProjectId=4595, Code=504-595
  → fst-project-health: строит отчёт по этому проекту
```

**Файл:** `project-search/SKILL.md`

### 2. `mcp-server-probing` (в Hermes-профиле)

| Поле | Значение |
|---|---|
| Расположение | `~/.hermes/profiles/fst-control/skills/mcp-server-probing/` |
| Версия | 2.7.0 |
| Назначение | Отладка MCP-сервера, 36 Pitfall'ов по MCP |
| Когда используется | При сбоях в MCP-запросах, странных данных, непонятных форматах ответов |
| Связь с `fst-project-health` | **Используется при разработке** (отладка индикаторов, исследования view) |

**Ключевые Pitfall'ы из mcp-server-probing, которые использует fst-project-health:**
- #15 b-tree 2704 (формат списочных view)
- #18 `filters={}` формат (вместо `?Field=Value` в URL)
- #19 `list_views` для обнаружения view
- #22 namespace DEPRECATED
- #27 `get_view` только read-access
- #31 `get_entity_data` optimization (все свойства за 1 запрос)
- #32 `accountid` работает, `StartDate` НЕ работает в ProjectResourcePlan
- #33 parallel MCP requests таймаут (60 сек) — используем sequential
- #34 sentinel `_get_entity_data_`
- #35 cache key должен совпадать с entity

**Файл:** `mcp-server-probing/SKILL.md`

### 3. `proposal-to-mcp-developers-accountid-date-filter.md` (документ)

| Поле | Значение |
|---|---|
| Расположение | `~/.hermes/profiles/fst-control/skills/proposal-to-mcp-developers-accountid-date-filter.md` |
| Назначение | Запрос к разработчикам MCP — добавить `accountid` и `StartDate/EndDate` фильтры |
| Статус | ✅ **ЗАКРЫТ** (2026-09-03) — разработчики добавили фильтры |
| Связь | Исторически привёл к Pitfall #32 в mcp-server-probing |

---

## 📦 Python-зависимости (requirements.txt)

```python
# Минимум для работы скилла:
requests>=2.28.0      # HTTP-запросы к MCP-серверу PMForesight
python-docx>=1.0.0    # Генерация .docx (WORD-отчёт)
```

Установка: `pip install -r requirements.txt`

### Внутренние модули (в `scripts/`)

| Модуль | Назначение |
|---|---|
| `mcp_config.py` | MCP-клиент (handshake, calls, JWT, ENV) |
| `find_project_by_code.py` | Поиск проекта по коду |
| `get_effort.py` | Загрузка трудозатрат |
| `get_metamodel.py` | Загрузка метаданных системы |
| `get_project_budget.py` | Загрузка бюджета |
| `project_indicators.py` | 16 индикаторов секции 6 |
| `run_all.py` | Оркестратор (9-шаговый pipeline) |
| `build_html_report.py` | Генерация HTML |
| `build_word_report.py` | Генерация .docx |
| `build_report_header.py` | Сборка MD-секций |
| `rebuild_report.py` | Сборка MD из секций |
| `project_health_summary.py` | Сводный вердикт |

### Thresholds (справочники порогов)

| Файл | Для какого индикатора |
|---|---|
| `indicator_thresholds.py` | Общие пороги |
| `unfilled_roles_thresholds.py` | 6.6 (роли) |
| `cross_activity_overload_thresholds.py` | 6.7 (перегрузка исполнителей) |
| `financial_deadlines_thresholds.py` | 6.8 (просрочка финансовых КТ) |
| `act_pay_amounts_thresholds.py` | 6.9 (суммы актов/оплат) |
| `overload_thresholds.py` | Общие (overload) |
| `effort_forecast_thresholds.py` | 6.3, 6.4 (трудозатраты) |
| `plan_effort_thresholds.py` | 6.4 (плановые трудозатраты) |
| `financial_deadlines_thresholds.py` | 6.8 (сроки) |
| `kp_labels_thresholds.py` | 6.16 (метки КП) |
| `finresult-thresholds.py` | 6.7 (фин.результат) |
| `Financial-deviation-threshold.py` | 6.x (отклонения) |
| `point-overdue-thresholds.py` | 6.5, 6.7 (просрочка) |
| `point-timing-health-thresholds.py` | 6.5 (здоровье по срокам) |
| `point-timing-remark-thresholds.py` | 6.x (замечания) |
| `Forecasted-financial-result.py` | 6.x (прогноз фин.результата) |
| `Forecasted-financial-result-deviation.py` | 6.x (отклонение прогноза) |
| `Forecasted-financial-value-deviation.py` | 6.x (отклонение стоимости) |
| `effort-gap-threshold.py` | 6.x (разрыв трудозатрат) |
| `vat_constants.py` | 6.12 (ставка НДС 5%) |
| `vat_calc.py` | 6.12 (формулы НДС) |
| `act_pay_amounts_thresholds.py` | 6.9 (акты/оплаты) |

### Справочники

| Файл | Назначение |
|---|---|
| `point_states.py` | Состояния КТ (16 штук) |
| `lc_stage_kt_registry.py` | Реестр КТ по стадиям ЖЦ |

---

## 🔌 Внешние зависимости

### MCP-сервер (PMForesight)

| Поле | Значение |
|---|---|
| URL | `https://ppreplica.hera.pmpractice.ru/mcp` |
| Версия | 3.2.4 |
| Токен | `PMP_TOKEN` (JWT, берётся из `.env` или env-переменной) |

### Системные требования

- Python 3.11+ (использует `Path | None`, walrus)
- Linux/macOS/Windows
- Доступ к интернету (MCP)
- 1 GB RAM (для кешей и DOCX-генерации)

---

## 📚 Документация (references/)

| Файл | Назначение |
|---|---|
| `playbook.md` | Главный playbook для коллег (v1.0.14) |
| `SKILL.md` | Главное описание скилла |
| `project-indicators-architecture.md` | Архитектура индикаторов |
| `project-indicators-spec.md` | Спецификация индикаторов |
| `mcp-call-patterns.md` | Паттерны вызова MCP |
| `mcp-filters-format.md` | Формат фильтров MCP |
| `mcp-live-probe-cookbook.md` | Рецепт MCP-probe |
| `mcp-methods-and-optimization.md` | Методы и оптимизация MCP |
| `mcp-sse-parsing-and-utf8.md` | SSE-парсинг и UTF-8 |
| `mcp-view-discovery-cookbook.md` | Обнаружение views |
| `mcp-server-filter-playbook.md` | Плейбук фильтров MCP |
| `mcp-regression-2026-08-27.md` | Регрессии августа |
| `mcp-regression-2026-08-31.md` | Регрессии августа |
| `mcp-regressions-2026-09-01.md` | Регрессии сентября |
| `html-report-pitfalls-v1001.md` | Типичные баги рендера HTML |
| `html-report-pitfalls.md` | Pitfall'ы рендера |
| `html-report-recovery.md` | Восстановление HTML |
| `html-report-structure-etalon-26.md` | Структура эталонного отчёта |
| `html-report-v1003-section6-architecture.md` | Архитектура секции 6 (v1.0.3) |
| `html-report-v1004-section6-architecture.md` | Архитектура секции 6 (v1.0.4) |
| `html-report-workflow.md` | Workflow построения HTML |
| `indicator-pitfall-workflow.md` | Workflow Pitfall'ов индикаторов |
| `indicator-resource-pattern.md` | Паттерн ресурсных индикаторов |
| `indicator-6-1-jurlico.md` | 6.1 (юрлицо) |
| `indicator-6-2-modeling-steps.md` | 6.2 (стадии ЖЦ) |
| `indicator-6-7-cross-activity.md` | 6.7 (перегрузка) |
| `indicator-6-9-act-pay-amounts.md` | 6.9 (суммы актов) |
| `indicator-6-10-direct-costs.md` | 6.10 (прямые затраты) |
| `indicator-6-11-vat.md` | 6.11 (НДС) |
| `indicator-6-12-vat-amount-format.md` | 6.12 (формат НДС) |
| `indicator-6-12-vat-amount.md` | 6.12 (НДС) |
| `indicator-6-13-budget.md` | 6.13 (бюджет) |
| `indicator-6-14-presale-spending.md` | 6.14 (расход пресейла) |
| `indicator-6-16-kp-labels.md` | 6.16 (метки КП) |
| `6-7-accountid-date-filter-optimization.md` | Оптимизация 6.7 |
| `6-13-budget-presale-investigation.md` | Расследование 6.13 |
| `bug-78-tbl-kt-column-widths.md` | Баг #78 (ширины колонок) |
| `bug-79-html-indicator-unknown.md` | Баг #79 (unknown indicator) |
| `contract-binding-via-parentfullname.md` | Связь через ParentFullName |
| `discovery-2026-09-01.md` | Открытие 1 сентября |
| `effort-data-403-recipe.md` | Рецепт для 403 на трудозатратах |
| `forsight-mcp-quirks.md` | Особенности PMForesight MCP |
| `forsight-mcp-quirks-discovered-2026-08-07.md` | Особенности августа |
| `html-report-section6-indicators-bug-2026-09-03.md` | Баг рендера секции 6 |
| `indicator-6-8-*.md` | Заметки по 6.8 |
| `md-report-conventions.md` | Конвенции MD-отчёта |
| `meta-model-pitfalls.md` | Pitfall'ы мета-модели |
| `migration-grep-checklist.md` | Чек-лист миграции |
| `multi-view-fallback-pattern.md` | Паттерн fallback view |
| `run-all-pitfalls-2026-08-22.md` | Pitfall'ы run_all |
| `section-6-html-rendering-iteration-2026-09-03.md` | Итерации рендера |
| `testing-recipe.md` | Рецепт тестов |
| `trend-report-via-date-filters.md` | Тренд-отчёт через фильтры |
| `v1-0-0-session-learnings.md` | Уроки v1.0.0 |
| `word-report-procedure.md` | Процедура Word-отчёта |
| `transport-and-portability.md` | Переносимость |
| `section-6-backlog-2026-09-03.md` | Backlog секции 6 |
| `mcp-token-jwt-extract.md` | Извлечение JWT |
| `json-to-mcp-persistence.md` | JSON → MCP персистентность |
| `jc-stage-indicator-allowlist.md` | Whitelist индикаторов ЖЦ |

---

## 🧪 Тесты (tests/)

| Файл | Тестов | Покрывает |
|---|---:|---|
| `test_vat_logic.py` | 9 | 6.12 НДС (формула, периоды, формат) |
| `test_section_7_format.py` | 6 | Секция 7 (6 строк, JWT) |
| `test_section_8_indicators.py` | 10 | 16 индикаторов, whitelist, ▼ |
| `test_template_structure.py` | 7 | Шаблон (порядок, дубли) |
| `test_env_candidates.py` | 11 | ENV_FILE_CANDIDATES (portable) |
| `test_jwt_parsing.py` | 11 | JWT displayname |
| `test_indicators_v100.py` | — | 16 индикаторов секции 6 |
| `test_no_hardcode.py` | — | Хардкод project_id |
| `test_imports.py` | — | Импорты модулей |
| `test_helpers.py` | — | Helpers mcp_config |
| `test_run_all.py` | — | CLI run_all.py |
| `test_pipeline_integration.py` | — | Subprocess-based |
| `test_skill_md_integrity.py` | — | SKILL.md |
| `run_all_tests.py` | — | Оркестратор тестов |

**Итого: 54+ теста** (все зелёные)

---

## 🌐 Соседние скиллы в Hermes-профиле

| Скилл | Связь |
|---|---|
| `autonomous-ai-agents` | Можно делегировать построение отчёта подагенту |
| `software-development` | Методология разработки (pitfalls, v1.0.x) |
| `hermes-gateway-troubleshooting` | Если MCP не отвечает — диагностика |
| `mcp-server-probing` | Уже описан выше |
| `feature-decomposition-workflow` | При добавлении нового индикатора — декомпозиция |
| `fst-pmpractice-skill-authoring` | Стандарты создания скиллов в PM Practice |

---

## 🔄 Поток зависимостей

```
User → Hermes → fst-project-health
                       │
                       ├─→ project-search (submodule, v2.0.0)
                       │
                       ├─→ mcp-server-probing (при отладке)
                       │
                       ├─→ MCP-сервер PMForesight v3.2.4
                       │      ├─ get_view (Project, Point, InContract, MyProject, etc.)
                       │      ├─ get_entity_data (метаданные)
                       │      ├─ list_views (обнаружение)
                       │      └─ Auth via PMP_TOKEN (JWT)
                       │
                       ├─→ requirements.txt
                       │      ├─ requests
                       │      └─ python-docx
                       │
                       └─→ pytest (тесты)
                              ├─ unittest
                              └─ ast-парсинг кода
```

---

## 📋 Чеклист переносимости

Для работы скилла на другом сервере нужны:

- [x] Python 3.11+
- [x] `pip install -r requirements.txt` (requests, python-docx)
- [x] `.env` с `PMP_TOKEN=<jwt-токен>`
- [x] Доступ к `https://ppreplica.hera.pmpractice.ru/mcp`
- [x] Каталог скилла (со всеми .py, .css, .html, .md)
