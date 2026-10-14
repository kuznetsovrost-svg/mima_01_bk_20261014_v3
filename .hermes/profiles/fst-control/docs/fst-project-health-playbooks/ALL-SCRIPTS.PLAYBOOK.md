# PLAYBOOK — все скрипты семейства fst-project-health

**Дата PLAYBOOK:** 2026-09-24
**Назначение:** единый справочник по всем скриптам с указанием скилла, LOC, размера, времени выполнения.

---

## 1. fst-project-health (40 скриптов)

### 1.1. Главные (pipeline)

| Скрипт | LOC | Размер | Назначение | Когда запускается | Время |
|---|---|---|---|---|---|
| `scripts/run_all.py` | 1072 | 48 KB | Главный оркестратор: live-сборка отчёта | Пользователь явно или cron | 19–52 сек |
| `scripts/build_html_report.py` | 1015 | 49 KB | Парсит MD → HTML | Из `run_all.py` или вручную (`--md`) | 1 сек (без MCP) |
| `scripts/rebuild_report.py` | 238 | 10 KB | Склеивает секции MD + YAML front-matter | Из `run_all.py` | <1 сек |

### 1.2. MCP и поиск

| Скрипт | LOC | Размер | Назначение |
|---|---|---|---|
| `scripts/mcp_config.py` | 549 | 24 KB | Конфиг MCP-соединения (URL, JWT, кэш) |
| `scripts/mcp_probe.py` | 212 | 8 KB | Диагностика MCP (initialize, list, ping) |
| `scripts/find_project_by_code.py` | 267 | 12 KB | Код проекта → ProjectId |
| `scripts/get_metamodel.py` | 143 | 5 KB | Метамодель проекта |

### 1.3. Сбор данных

| Скрипт | LOC | Размер | Назначение |
|---|---|---|---|
| `scripts/lc_stage_kt_registry.py` | 621 | 33 KB | Реестр КТ (статусы, планы, прогнозы, исполнители) |
| `scripts/project_indicators.py` | 2743 | 115 KB | **Большой модуль** — 16 показателей проекта |
| `scripts/point_states.py` | 256 | 10 KB | Состояния точек КТ |
| `scripts/get_effort.py` | 373 | 16 KB | Трудозатраты (план/факт/прогноз) |
| `scripts/get_project_budget.py` | 309 | 12 KB | Бюджет проекта |
| `scripts/Passport-check.py` | 62 | 3 KB | Паспорт проекта (базовая инфо) |
| `scripts/build_report_header.py` | 592 | 25 KB | Шапка отчёта (метаданные, вердикт, сводка) |

### 1.4. Пороги и проверки

| Скрипт | LOC | Размер | Назначение |
|---|---|---|---|
| `scripts/indicator_thresholds.py` | 94 | 3 KB | Пороги для показателей |
| `scripts/point-timing-health-thresholds.py` | 20 | 0.8 KB | Пороги для сроков (здоров) |
| `scripts/point-timing-remark-thresholds.py` | 21 | 0.8 KB | Пороги для замечаний по срокам |
| `scripts/point-overdue-thresholds.py` | 28 | 1 KB | Пороги для просрочек |
| `scripts/Points-forecast-relevance.py` | 50 | 2 KB | Актуальность прогнозов |
| `scripts/effort_forecast_thresholds.py` | 82 | 3 KB | Прогноз трудозатрат |
| `scripts/effort-gap-threshold.py` | 16 | 1 KB | Разрыв план/факт по трудозатратам |
| `scripts/plan_effort_thresholds.py` | 72 | 3 KB | План по трудозатратам |
| `scripts/unfilled_roles_thresholds.py` | 80 | 3 KB | Незаполненные роли |
| `scripts/overload_thresholds.py` | 111 | 4 KB | Перегрузка |
| `scripts/cross_activity_overload_thresholds.py` | 90 | 3 KB | Перекрёстная перегрузка активностями |
| `scripts/financial_deadlines_thresholds.py` | 104 | 4 KB | Финансовые сроки |
| `scripts/kp_labels_thresholds.py` | 80 | 3 KB | Метки КП |
| `scripts/act_pay_amounts_thresholds.py` | 141 | 4 KB | Суммы оплат |
| `scripts/finresult-thresholds.py` | 17 | 1 KB | Финансовый результат (порог) |
| `scripts/Financial-deviation-threshold.py` | 6 | 0.4 KB | Отклонение финансов |
| `scripts/Forecasted-financial-result.py` | 24 | 0.8 KB | Прогноз финансового результата |
| `scripts/Forecasted-financial-result-deviation.py` | 29 | 1.5 KB | Отклонение прогноза |
| `scripts/Forecasted-financial-value-deviation.py` | 35 | 1.3 KB | Отклонение прогнозной стоимости |

### 1.5. Проверки (checks)

| Скрипт | LOC | Размер | Назначение |
|---|---|---|---|
| `scripts/Effort-check.py` | 315 | 15 KB | Проверка трудозатрат |
| `scripts/Fin-result-check.py` | 74 | 3 KB | Проверка финансового результата |
| `scripts/Payments-graph-check.py` | 138 | 5 KB | График платежей |
| `scripts/LeaderID-check.py` | 19 | 0.5 KB | Лидер проекта |
| `scripts/OwnerID-check.py` | 19 | 0.5 KB | Владелец проекта |
| `scripts/project-health-summary.py` | 35 | 1.7 KB | Краткая сводка |

### 1.6. Прочее

| Скрипт | LOC | Размер | Назначение |
|---|---|---|---|
| `scripts/vat_calc.py` | 128 | 5 KB | Расчёт НДС |
| `scripts/vat_constants.py` | 24 | 1 KB | Константы НДС |

---

## 2. fst-project-health-word (2 скрипта)

| Скрипт | LOC | Размер | Назначение | Когда запускается | Время |
|---|---|---|---|---|---|
| `scripts/build_word_report.py` | 1155 | 55 KB | Парсит MD → DOCX | Пользователь явно или из `build_word_from_snapshot.sh` | 2 сек |
| `scripts/build_word_from_snapshot.sh` | 46 | 1.7 KB | Цепочка `fetch_snapshot → build_word` | Пользователь явно | 5–10 сек на проект |

---

## 3. fst-project-health-snap-md (3 скрипта)

| Скрипт | LOC | Размер | Назначение | Когда запускается | Время |
|---|---|---|---|---|---|
| `scripts/run_snap_md.py` | 572 | 25 KB | Генерация MD-слепка в MCP | Пользователь или cron | 19–52 сек на проект |
| `scripts/logging_utils.py` | 270 | 12 KB | `RunLogger` для массовых операций | Импортируется в `run_snap_md` | 0 |
| `scripts/rotate_logs.py` | 188 | 8 KB | Ротация логов (30/180 дней) | cron ежедневно | 1 сек |

---

## 4. fst-project-health-from-md-snapshot (5 скриптов)

| Скрипт | LOC | Размер | Назначение | Когда запускается | Время |
|---|---|---|---|---|---|
| `scripts/fetch_snapshot.py` | 598 | 24 KB | Извлечение MD из MCP, 5 режимов | Пользователь явно | 1–2 сек |
| `scripts/build_html.py` | 142 | 5 KB | HTML из MD (тонкий wrapper) | Пользователь явно | 1 сек |
| `scripts/run.py` | 141 | 5 KB | Цепочка fetch+build | Пользователь или cron | 2–3 сек |
| `scripts/logging_utils.py` | 243 | 10 KB | `RunLogger` для извлечения | Импортируется | 0 |
| `scripts/rotate_logs.py` | 188 | 8 KB | Ротация логов (30/180 дней) | cron ежедневно | 1 сек |

---

## 5. fst-project-health-tests (10 скриптов)

| Скрипт | LOC | Размер | Назначение | Когда запускается | Время |
|---|---|---|---|---|---|
| `run_all_tests.py` | 219 | 10 KB | Главный тест-раннер (НЕ pytest) | Пользователь или cron | ~5 мин (все группы) |
| `tests/_helpers.py` | 102 | 4 KB | Утилиты (`_transient_safe`, retries) | Импортируется | 0 |
| `tests/test_project.py` | 66 | 2 KB | Конфиг тестового проекта | Импортируется | 0 |
| `tests/test_01_regression.py` | 122 | 4 KB | Уровень 1 — регрессия (3 теста) | `run_all_tests.py` | ~22 сек |
| `tests/test_02_mcp.py` | 571 | 22 KB | Уровень 2 — MCP (17 тестов) | `run_all_tests.py` | ~2 мин |
| `tests/test_03_snap_md.py` | (9 тестов) | — | Уровень 3 — snap-md (9 тестов) | `run_all_tests.py` | ~50 сек |
| `tests/test_04_from_md.py` | (15 тестов) | — | Уровень 4 — from-md-snapshot (15 тестов) | `run_all_tests.py` | ~50 сек |
| `tests/test_05_cross_skill.py` | (4 теста) | — | Уровень 5 — cross-skill (4 теста) | `run_all_tests.py` | ~50 сек |
| `tests/test_06_invariants.py` | (6 тестов) | — | Уровень 6 — инварианты (6 тестов) | `run_all_tests.py` | ~45 сек |
| `scripts/rotate_logs.py` | 188 | 8 KB | Ротация логов (100/400 дней) | cron ежедневно | 1 сек |

---

## 6. Сводная таблица

| Скилл | Скриптов | Общий LOC | Общий размер |
|---|---|---|---|
| fst-project-health | 40 | ~9 200 LOC | ~440 KB |
| fst-project-health-word | 2 | ~1 200 LOC | ~57 KB |
| fst-project-health-snap-md | 3 | ~1 030 LOC | ~46 KB |
| fst-project-health-from-md-snapshot | 5 | ~1 312 LOC | ~57 KB |
| fst-project-health-tests | 10 | ~1 700 LOC | ~80 KB |
| **ИТОГО** | **60** | **~14 500 LOC** | **~680 KB** |

---

## 7. Прецеденты по характерному времени

| Операция | Время | Примечание |
|---|---|---|
| `run_all.py` (live, 1 проект) | 19–52 сек | Зависит от MCP |
| `build_html_report.py --md` | 1 сек | Без MCP |
| `build_word_report.py --md` | 2 сек | Без MCP |
| `run_snap_md.py` (1 проект) | 19–52 сек | Тот же pipeline + upload |
| `fetch_snapshot.py --last` | 1–2 сек | 1 HTTP-запрос |
| `run.py` (цепочка) | 2–3 сек | fetch + build |
| `build_word_from_snapshot.sh` (1 проект) | 5–10 сек | fetch + word |
| `run_all_tests.py` (все группы) | ~5 мин | Включает MCP-тесты |
| `run_all_tests.py --group invariants` | ~45 сек | Без MCP |
