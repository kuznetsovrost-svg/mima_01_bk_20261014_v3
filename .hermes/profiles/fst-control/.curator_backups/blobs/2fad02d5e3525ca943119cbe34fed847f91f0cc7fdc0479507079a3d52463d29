# Каталог скриптов скилла `fst-project-health`

**Версия:** 1.0.0 — 2026-09-06
**Назначение:** единый справочник по всем `.py` файлам в
`~/.hermes/profiles/fst-control/skills/productivity/fst-project-health/scripts/`
(42 скрипта). Для каждого: что делает, к какому разделу отчёта
относится, какие методы MCP вызывает.

Структура:

- **Часть 1.** Основные скрипты (оркестратор, индикаторы, рендер).
- **Часть 2.** Пороги (severity / справочные значения).
- **Часть 3.** CLI-утилиты и прочее.
- **Часть 4.** Отдельная таблица — скрипты со справочными данными и
  критериями определения статуса.

---

## Часть 1. Основные скрипты

| Скрипт | LOC | Назначение | Раздел отчёта | Методы MCP |
|---|---|---|---|---|
| `run_all.py` | 1055 | **Оркестратор** — единая точка входа. Строит все секции отчёта (3–8), кеширует, выгружает MD/HTML/DOCX в `/tmp/project_<code>_report.*` | все разделы (3–8) | `mcp_init`, `mcp_call` (`get_view`, `get_entity_data`) |
| `project_indicators.py` | 2743 | **Все 16 индикаторов** секции «Показатели проекта» (6.1–6.16). Каждый — функция `check_*`, возвращающая `IndicatorResult` (severity + таблица) | раздел 6 | `fetch_with_cache` (через `mcp_call` → `get_view`) |
| `build_report_header.py` | 592 | Шапка отчёта: поиск проекта по коду, карточка, ресурсный план, бюджет, MetaModel (title/version/core_version) | раздел 1 (заголовок) | `mcp_init` (9× в разных функциях), `mcp_call` (`get_view`, `get_entity_data`, `find_entity`) |
| `build_html_report.py` | 737 | **Рендер HTML** из MD. Каноническая структура `report.html` (6 секций по эталону 26), `<details>` per indicator, цветовая палитра секции 6 | рендер всех секций | — (не вызывает MCP) |
| `build_word_report.py` | 810 | **Рендер DOCX** (Форма 1) из MD | рендер всех секций | — |
| `rebuild_report.py` | 85 | Склейка финального MD из `section_*_result.md` файлов | раздел 8 (сводка) | — |
| `find_project_by_code.py` | 267 | Поиск проекта по коду (`504-595` → `project_id`). Используется в CLI-режиме и из `run_all` | раздел 1 | `mcp_init`, `mcp_call` (`get_view`) |
| `mcp_config.py` | 549 | **Центральный модуль MCP**: `mcp_init`, `mcp_call`, `fetch_with_cache`, парсинг JWT для ФИО, таймауты, ENV | все (через обёртки) | — (определяет обёртки) |
| `mcp_probe.py` | 212 | CLI-утилита для прямых `tools/call` MCP-сервера — отладка, probe, рекогносцировка view | — (отладка) | `mcp_call` (через прямые JSON-RPC) |

---

## Часть 2. Пороги и справочные константы

| Скрипт | LOC | Назначение | Раздел | Покрывает |
|---|---|---|---|---|
| `indicator_thresholds.py` | 94 | Общий агрегатор порогов (импортирует остальные `*_thresholds.py`) | раздел 6 | все 16 индикаторов |
| `act_pay_amounts_thresholds.py` | 140 | Пороги для **6.9** «Суммы актов и оплат» (Δ актов vs оплат) | раздел 6 (6.9) | 6.9 |
| `cross_activity_overload_thresholds.py` | 90 | Пороги для **6.7** «Перегрузка исполнителей» (>100%/>110%/>150%) | раздел 6 (6.7) | 6.7 |
| `effort_forecast_thresholds.py` | 82 | Пороги для **6.3** «Прогнозы по ресурсам заданы» | раздел 6 (6.3) | 6.3 |
| `financial_deadlines_thresholds.py` | 103 | Пороги для **6.8** «Соблюдение сроков финансовых КТ» | раздел 6 (6.8) | 6.8 |
| `kp_labels_thresholds.py` | 79 | Пороги для **6.16** «Элементы КП без метки» | раздел 6 (6.16) | 6.16 |
| `overload_thresholds.py` | 111 | Пороги для **6.5** «Перегрузка исполнителей» (по проекту) | раздел 6 (6.5) | 6.5 |
| `plan_effort_thresholds.py` | 72 | Пороги для **6.4** «Плановые трудозатраты заданы» | раздел 6 (6.4) | 6.4 |
| `unfilled_roles_thresholds.py` | 80 | Пороги для **6.6** «Роли с нереализованными прогнозами» | раздел 6 (6.6) | 6.6 |
| `vat_constants.py` | 23 | **Справочные значения по НДС** (ставка 5%, допуск 0.0001₽, формула) | раздел 6 (6.12) | 6.12 |
| `vat_calc.py` | 127 | Расчёт фактической ставки НДС (total/21×5) + проверка допуска | раздел 6 (6.12) | 6.12 |
| `Financial-deviation-threshold.py` | 6 | Пороги для раздела 4 показатель 5 «График платежей» (100К / 1М) | раздел 4 (показатель 5) | 4.5 |
| `finresult-thresholds.py` | 17 | Пороги для раздела 6 (до v1.0.0): Δ тек. стоимости (1М) и Δ фин.результата (2М) | раздел 6 (старая, 3 показателя) | 6 старые |
| `point-overdue-thresholds.py` | 28 | **OVERDUE_THRESHOLDS** — пороги классификации просрочки КТ по дням (1/2/10) | раздел 5 + 3 | 5, 3 |
| `point-timing-health-thresholds.py` | 20 | **HEALTH_THRESHOLDS** — критерии здоровья проекта (0 / 1–2 / ≥3 крит.) | раздел 1 (header) | header circle |
| `point-timing-remark-thresholds.py` | 21 | **REMARK_THRESHOLDS** — пороги замечаний по |Δ| дней (2/10) | раздел 3 | 3 |
| `effort-gap-threshold.py` | 16 | **EFFORT_GAP_THRESHOLD_DAYS = 10** — допустимый разрыв между планом/фактом ТРЗ | раздел 4 (показатель 4) | 4.4 |

---

## Часть 3. CLI-утилиты и точечные проверки (не в основном pipeline)

| Скрипт | LOC | Назначение | Раздел | Методы MCP |
|---|---|---|---|---|
| `get_effort.py` | 373 | CLI для просмотра `ProjectResourcePlan` по проекту | раздел 1 (header) | `mcp_init`, `mcp_call` (`get_view`) |
| `get_project_budget.py` | 309 | CLI для просмотра `ProjectBudgetCompleteBusiness` | раздел 1 (header) | `mcp_init`, `mcp_call` (`get_view`) |
| `get_metamodel.py` | 143 | CLI для значений MetaModel (title/version/core_version) | раздел 7 | `mcp_init`, `mcp_call` (`get_entity_data`) |
| `point_states.py` | 256 | **Справочник** упорядоченных состояний КТ (Point) с порядком перехода | раздел 6 (справочно) | — |
| `lc_stage_kt_registry.py` | 621 | **Справочник обязательных КТ** по стадиям ЖЦ (Пресейл / Инициирование / Подготовка / Реализация / Завершение) | раздел 6 (справочно) | — |
| `Effort-check.py` | 315 | Проверка актуальности трудозатрат (раздел 4 показатель 4) — **hardcoded для 504-595** | раздел 4 (4.4) | (через `mcp__fst_pmpractice__*`) |
| `Payments-graph-check.py` | 138 | Проверка графика платежей (раздел 4 показатель 5) | раздел 4 (4.5) | (через `mcp__fst_pmpractice__*`) |
| `Passport-check.py` | 62 | Проверка наличия паспорта (раздел 4 показатель 3) — учитывает стадию ЖЦ | раздел 4 (4.3) | (через `mcp__fst_pmpractice__*`) |
| `OwnerID-check.py` | 19 | Проверка назначения куратора (Owner) | раздел 4 (4.2) | (через `mcp__fst_pmpractice__*`) |
| `LeaderID-check.py` | 19 | Проверка назначения руководителя (Leader) | раздел 4 (4.1) | (через `mcp__fst_pmpractice__*`) |
| `Fin-result-check.py` | 74 | Альтернативный расчёт фин.результата (через контракты + КТ) — fallback для раздела 6 показатель 1 | раздел 6 (6 стар., 1) | (через `mcp__fst_pmpractice__*`) |
| `Forecasted-financial-result.py` | 24 | Образец: проверка `forecast < 0` (раздел 6 показатель 1) | раздел 6 (6 стар., 1) | (через `mcp__fst_pmpractice__*`) |
| `Forecasted-financial-result-deviation.py` | 29 | Образец: Δ фин.результата > 2М (раздел 6 показатель 3) | раздел 6 (6 стар., 3) | (через `mcp__fst_pmpractice__*`) |
| `Forecasted-financial-value-deviation.py` | 35 | Образец: Δ тек. стоимости > 1М (раздел 6 показатель 2) | раздел 6 (6 стар., 2) | (через `mcp__fst_pmpractice__*`) |
| `Points-forecast-relevance.py` | 50 | Образец: классификация КТ по просрочке ForecastDate | раздел 5 | (через `mcp__fst_pmpractice__*`) |
| `project-health-summary.py` | 35 | Образец сводки по разделу 3 (здоровье проекта по срокам) | раздел 1 (header circle) | (через `mcp__fst_pmpractice__*`) |

---

## Часть 4. Справочные данные и критерии определения статуса

Скрипты, в которых **зафиксированы константы**, определяющие статус
элемента отчёта, либо **справочники** (ставка НДС, списки обязательных КТ,
порядок состояний КТ и т.п.). Эти файлы **не вызывают MCP** и
содержат только данные и эталонные значения.

| Скрипт | Что зафиксировано | Где используется |
|---|---|---|
| `vat_constants.py` | **Ставка НДС 5%**, **допуск 0.0001 ₽**, формула `Сумма / 21 × 5`, сценарии приоритета fact > forecast > plan | `project_indicators.py::check_vat_amount` (раздел 6, индикатор 6.12) |
| `point-timing-remark-thresholds.py` | **REMARK_THRESHOLDS**: пороги замечаний раздела 3 по |Δ| дней — критическое (≥10), существенное (2–10), информационное (0–2) | `build_section_3` (раздел 3) |
| `point-overdue-thresholds.py` | **OVERDUE_THRESHOLDS**: пороги просрочки КТ по дням для раздела 5 — критическое (≥10), существенное (2–9), информационное (=1) | `build_section_5` (раздел 5) |
| `point-timing-health-thresholds.py` | **HEALTH_THRESHOLDS**: здоровье проекта по количеству критических КТ — sick (≥3), attention (1–2), healthy (0) | header circle (раздел 1) |
| `effort-gap-threshold.py` | **EFFORT_GAP_THRESHOLD_DAYS = 10** — допустимый разрыв между планом/фактом трудозатрат | раздел 4 показатель 4 |
| `Financial-deviation-threshold.py` | **PAYMENT_DEVIATION_THRESHOLDS**: Δ актов vs оплат — informational (100К), substantial (1М), critical (≥1М) | раздел 4 показатель 5 |
| `finresult-thresholds.py` | **FINRESULT_THRESHOLDS**: max_value для current_cost_deviation (1М) и end_finresult_decrease (2М) | раздел 6 (до v1.0.0) — показатели 2 и 3 |
| `act_pay_amounts_thresholds.py` | Пороги для 6.9: «Суммы актов и оплат» (severity по Δ) | раздел 6 показатель 6.9 |
| `cross_activity_overload_thresholds.py` | Пороги для 6.7: >100% (инф), >110% (сущ), >150% (крит) | раздел 6 показатель 6.7 |
| `effort_forecast_thresholds.py` | Пороги для 6.3: пропущенные часы прогноза | раздел 6 показатель 6.3 |
| `financial_deadlines_thresholds.py` | Пороги для 6.8: просрочка финансовых КТ | раздел 6 показатель 6.8 |
| `kp_labels_thresholds.py` | Пороги для 6.16: КТ без метки | раздел 6 показатель 6.16 |
| `overload_thresholds.py` | Пороги для 6.5: перегрузка исполнителей в проекте | раздел 6 показатель 6.5 |
| `plan_effort_thresholds.py` | Пороги для 6.4: плановые трудозатраты | раздел 6 показатель 6.4 |
| `unfilled_roles_thresholds.py` | Пороги для 6.6: роли без исполнителей | раздел 6 показатель 6.6 |
| `lc_stage_kt_registry.py` | **Справочник обязательных КТ** по стадиям ЖЦ (Пресейл / Инициирование / Подготовка / Реализация / Завершение / Архив) | раздел 6 показатель 6.2 (проверка стадии ЖЦ) |
| `point_states.py` | **Упорядоченные состояния КТ** (Point) с порядком перехода | раздел 6 (справочно, индикатор 6.2) |
| `Passport-check.py` | **PHASE_ORDER** — порядок стадий ЖЦ: Пресейл(1) / Инициирование(2) / Подготовка(3) / Реализация(4) / Завершение(5) / Архив(6). Паспорт обязателен на стадии ≥2 | раздел 4 показатель 3 |
| `vat_calc.py` | Функция расчёта фактической ставки НДС (total/21×5) + проверка допуска | раздел 6 показатель 6.12 |

---

## Часть 5. Статистика

- **Всего скриптов:** 42
- **Основных (участвуют в pipeline `run_all.py`):** 9 (`run_all`,
  `project_indicators`, `build_report_header`, `build_html_report`,
  `build_word_report`, `rebuild_report`, `find_project_by_code`,
  `mcp_config`, `mcp_probe`)
- **Порогов и констант:** 18 (все в Части 2)
- **CLI-утилит и точечных проверок:** 16 (Часть 3)
- **Скриптов с MCP-вызовами:** 9 (`run_all`, `project_indicators`,
  `build_report_header`, `find_project_by_code`, `get_effort`,
  `get_project_budget`, `get_metamodel`, `mcp_config`, `mcp_probe`)
- **Скриптов без MCP-вызовов (только Python-логика):** 33

---

## Часть 6. Сводка: какой скрипт что считает «Норма / Информационное / Существенное / Критическое»

| Раздел | Скрипт-индикатор | Скрипт-порог |
|---|---|---|
| 1 (header circle) | `run_all.py::compute_verdict()` | `point-timing-health-thresholds.py` |
| 3 (замечания по срокам) | `run_all.py::build_section_3` | `point-timing-remark-thresholds.py` |
| 4 (полнота) | `run_all.py::build_section_4` | `Financial-deviation-threshold.py`, `effort-gap-threshold.py` |
| 5 (актуальность прогнозов) | `run_all.py::build_section_5` | `point-overdue-thresholds.py` |
| 6.1 Юрлицо | `project_indicators.py::check_jurlico` | — |
| 6.2 ЖЦ | `project_indicators.py::check_lifecycle_stage` | `lc_stage_kt_registry.py` |
| 6.3 Прогнозы ТРЗ | `project_indicators.py::check_effort_forecast` | `effort_forecast_thresholds.py` |
| 6.4 Плановые ТРЗ | `project_indicators.py::check_plan_effort` | `plan_effort_thresholds.py` |
| 6.5 Перегрузка исполнителей | `project_indicators.py::check_resource_overload` | `overload_thresholds.py` |
| 6.6 Роли без исполнителей | `project_indicators.py::check_unfilled_roles` | `unfilled_roles_thresholds.py` |
| 6.7 Перегрузка по всем проектам | `project_indicators.py::check_cross_activity_overload` | `cross_activity_overload_thresholds.py` |
| 6.8 Финансовые КТ | `project_indicators.py::check_financial_deadlines` | `financial_deadlines_thresholds.py` |
| 6.9 Акты/оплаты | `project_indicators.py::check_act_pay_amounts` | `act_pay_amounts_thresholds.py` |
| 6.10 Прямые затраты | `project_indicators.py::check_direct_costs` | — |
| 6.11 Наличие НДС | `project_indicators.py::check_vat` | — |
| 6.12 Расчётный НДС | `project_indicators.py::check_vat_amount` | `vat_constants.py`, `vat_calc.py` |
| 6.13 Бюджет | `project_indicators.py::check_budget_limits` | — |
| 6.14 Лимит пресейла | `project_indicators.py::check_presale_limit_spending` | — |
| 6.15 Утверждённый бюджет | `project_indicators.py::check_approved_budget` | — |
| 6.16 Метки КП | `project_indicators.py::check_kp_labels` | `kp_labels_thresholds.py` |