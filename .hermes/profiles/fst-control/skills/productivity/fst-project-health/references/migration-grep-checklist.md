# Migration rule: после миграции формата MCP-вызовов — `grep` для пропущенных файлов

**Дата:** 2026-09-01 (миграция завершена 2026-09-01)
**Контекст:** Финальный grep во время сессии `2026-09-01` нашёл `build_report_header.py` как единственный файл, использующий `*_VIEW_FOR` без `DEPRECATED` пометки. Все 4 основных production-скрипта (`run_all.py`, `get_effort.py`, `get_project_budget.py`, `mcp_config.py`) были переведены на новый формат `filters={...}` за 1 итерацию, но `build_report_header.py` **был пропущен** — он не импортируется в `run_all.py`, поэтому `tests/run_all_tests.py` (6/6 PASS) **не упал**.

**Live probe (2026-09-01 18:55):** `grep -rn "_VIEW_FOR\b" scripts/ | grep -v DEPRECATED` → нашлось 1 совпадение в `build_report_header.py` (строки 243, 328).

## ⚠️ Финал миграции (2026-09-01, later)

**DEPRECATED lambdas `*_VIEW_FOR` полностью удалены** из `mcp_config.py` (по запросу пользователя). Сейчас:

```bash
# Должен быть пустой результат (только комментарии)
grep -rn "_VIEW_FOR\b" scripts/ tests/ 2>/dev/null \
  | grep -v "# DEPRECATED"
# (пусто)
```

Все production-скрипты используют `*_VIEW` константы + `*_FILTERS` lambdas. Тесты (`test_helpers.py::test_view_for_lambdas_removed`) явно проверяют отсутствие `*_VIEW_FOR` через `assertFalse(hasattr(...))`.

**Live-probe 2026-09-01:** 8/8 успешных удалений тестовых записей через скрипт `delete_attribute_values.py` (использует правильный формат `remove=['AttributeValue|<guid>']`).

## Правило (для будущих миграций)

После любой **массовой миграции формата** (MCP-вызовов, SQL-запросов, API-эндпоинтов):

```bash
# 1. Найти все использования старого формата
grep -rn "<OLD_PATTERN>" scripts/

# 2. Исключить DEPRECATED
grep -rn "<OLD_PATTERN>" scripts/ | grep -v "DEPRECATED"

# 3. Если список НЕ пустой — есть файл, который не перевели
```

**Hard rule (added 2026-09-01):** перед фразой "готово ✅" в чате — **всегда** прогонять grep для не-Deprecated использований. Если есть **непустой** список — файл пропустили. **Применимо к любой class-skill migration** с одного формата на другой.

## Правило (новое, 2026-09-01): **DEPRECATED код — удалять**

Раннее правило: "помечать DEPRECATED и оставить для обратной совместимости".

Новое правило (по запросу пользователя): **"Удалить _VIEW_FOR лямбды (помечены DEPRECATED)"** — DEPRECATED через 1 итерацию (одна полная сессия) **удаляются**, не оставляются.

**Имплементация:**
- Добавлен `test_view_for_lambdas_removed` (anti-test) — `assertFalse(hasattr(mcp, "*_VIEW_FOR"))`
- Удалены `*_VIEW_FOR` lambdas из `mcp_config.py`
- Удалены импорты `*_VIEW_FOR` из `get_effort.py`, `get_project_budget.py`, `build_report_header.py`
- Удалены 3 transient diagnostic scripts: `test_filters_format.py`, `probe_filters_format.py`, `regression_probe.py`

## Почему `tests/run_all_tests.py` не поймал (изначально)

`build_report_header.py` — это **standalone utility**, который вызывается отдельно через `mcp_init` + `get_view`. Он **не вызывается** из `run_all.py` (который делает прямые `mcp_call`). Поэтому:

- `python3 scripts/run_all.py --code 504-314` — проходит
- `tests/run_all_tests.py` — все 6/6 PASS
- **Но** `build_report_header.py` всё ещё вызывал старый формат, и в любой standalone-запуск дал бы 500

**Тестовое покрытие не выявляет standalone-скрипты, которые не в цепочке `run_all.py`.** Всегда делать финальный grep по ВСЕМ `scripts/*.py`.

## Чек-лист для migration (обязательно, ОБНОВЛЕНО)

1. ✅ **До миграции:** `grep` найти все использования старого формата
2. ✅ **Мигрировать** каждый файл (включая standalone utilities!)
3. ✅ **Пометить старые helpers как DEPRECATED** (но не удалять — для совместимости на 1 итерацию)
4. ✅ **Тесты:** `tests/run_all_tests.py` 6/6 PASS
5. ✅ **Прогон pipeline:** `run_all.py --code 504-314 --no-word` — 19-22 сек
6. ✅ **`grep -rn "<OLD>" scripts/ | grep -v DEPRECATED`** — должен быть **пустым**
7. ✅ **Standalone smoke-test:** `python3 scripts/build_report_header.py <ProjectId>` — не падает
8. ✅ **Standalone smoke-test:** `python3 scripts/get_effort.py --project-id 4595` — не падает
9. ✅ **Standalone smoke-test:** `python3 scripts/get_project_budget.py --project-id 4595` — не падает
10. ✅ **Anti-test:** `assertFalse(hasattr(mcp, "<OLD_HELPER>"))` в `tests/`
11. ✅ **Удалить** `*_OLD_HELPER` после 1 итерации (по запросу пользователя)
12. ✅ **Только теперь** — "готово ✅"

## Аналогичные миграции в прошлом

| Дата | Миграция | Файл пропущен? | Какой файл |
|------|----------|----------------|-------------|
| 2026-08-22 | `?ProjectId=<id>` URL → filters | ❌ нет (миграция была неполной) | Неизвестно |
| 2026-09-01 | `?ProjectId=<id>` URL → filters (1 итерация) | ✅ да | `build_report_header.py` |
| 2026-09-01 | DEPRECATED markers → удаление | ❌ нет (после grep) | — |

**Вывод:** после 2026-09-01 — ВСЕГДА использовать grep-checklist (пункт 6) перед "готово ✅".

## Применимость

**Любой class-skill, который переводит production-вызовы с одного формата на другой.** Не только `fst-project-health`. Примеры будущих миграций:
- Замена HTTP API version (`/v1/` → `/v2/`)
- Замена SQL view (`ProjectHealthCostMy` → `ProjectFinanceSummary`)
- Замена OAuth flow (cookie → bearer token)
- Замена DTO format (camelCase → snake_case)

Все они требуют того же grep-checklist + anti-тестов.

## Lessons (4 правила) — зафиксировано в `references/mcp-filter-format-2026-09-01.md`

1. **DEPRECATED код — удалять**, не оставлять «для совместимости» (после 1 итерации)
2. **Anti-тесты** — `assertFalse(hasattr(...))` для проверки отсутствия deprecated
3. **Диагностические скрипты** удалять после решения проблемы
4. **Скрипты-утилиты для очистки** тестовых данных (live в production)
