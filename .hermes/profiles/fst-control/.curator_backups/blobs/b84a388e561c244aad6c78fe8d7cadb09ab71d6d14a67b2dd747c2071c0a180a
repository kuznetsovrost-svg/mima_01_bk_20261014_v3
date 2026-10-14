# v1.0.0 Session Learnings (2026-09-03)

Финальный документ сессии реализации секции 6 «Показатели проекта» v1.0.0 (16/16 индикаторов). Содержит **уроки сессии** которые помогут следующей сессии работать быстрее.

## Контекст сессии

- **Дата:** 2026-09-03
- **Цель:** Реализовать секцию 6 «Показатели проекта» (16 индикаторов 6.1–6.16), встроить в pipeline, протестировать на 4 реальных проектах, выпустить v1.0.0
- **Результат:** Все 16 индикаторов работают. Pipeline ускорен на -69-79% на 2-м запуске благодаря `get_entity_data` + кеш. Архив `fst-project-health-v1.0.0.tar.gz` создан (524 КБ)

## Workflow правила, выявленные в этой сессии

### 1. "Не торопись" — user style

User сказал "Не торопись" 4+ раз в сессии. Это workflow правило, не просто речь. См. Pitfall #158 в SKILL.md.

**Симптомы**:
- Реализую несколько индикаторов после частичного спека — подожди полного 4-секционного спека
- Спрашиваю "что дальше?" до завершения текущего
- Начинаю код до "Скажу когда сделаю"
- Скаффолжу всю функцию до того, как знаю что будет в step 2/3

**Когда user говорит "Не торопись!"**:
- Стоп + acknowledge: "Принял, жду следующий шаг"
- НЕ preempt следующий вопрос с "Could you clarify Q4?"
- НЕ спрашивать "точно ли?" когда user дает спек

### 2. "Тут у меня неточность" — user self-correction

В 6.14 user отменил Q1 ("только для Пресейл") → "для всех стадий". См. Pitfall #153 в SKILL.md.

**Правило**: не создавай investigation file или changelog; просто updateируй код. Не спрашивай "точно ли изменилось мнение?" — user явно говорит.

### 3. "Добавлю данные — проверь" pattern

В 6.10 user дважды говорил "добавлю в проект 504-595". Оба раза я должен был **подождать**, а не реализовывать на старых данных. См. Pitfall #131.

**Правило**: "Скажу когда сделаю" = wait signal. Не poll, не preempt.

## Технические находки

### A. `get_entity_data` — критическая оптимизация

**Изобретение:** вызов `mcp_call(sid, "get_entity_data", ...)` возвращает ВСЕ свойства сущности одним запросом. Заменил 14+ вызовов `ProjectParameter` на один.

**Параметры**: `entityName` + **`data_id` (snake_case, string)** — НЕ `dataId` и НЕ int.

**Эффект**: -69% (504-595), -79% (503-152) на 2-м запуске.

**Sentinel pattern**: `fetch_with_cache(sid, "Project", "_get_entity_data_", ...)` — sentinel view name, не требующий переписывать `check_*()` функции.

**Где применимо**:
- 6.13 (Бюджет проекта/пресейла) — единственный способ получить `PresaleLimit`
- 6.16 (Метки КП) — ускорение на 30+ секунд
- ВСЕ остальные индикаторы — заменён `ProjectParameter` на `_get_entity_data_`

См. Pitfall #140, #141, #144, #145, #147, #148 в SKILL.md.

### B. `list_views` Description неполный — НЕ доверяй

**Live-probe 2026-09-03** показал: фильтры `ProjectId`, `accountid`, `StartDate`/`EndDate`, `PortfolioId` работают в `ProjectResourcePlan`, `ProjectBudgetCompleteBusiness`, `AllMyPoint` — **но НЕ указаны** в их `Description`.

См. Pitfall #155 в `references/mcp-filter-format-2026-09-01.md`.

**Anti-pattern**: утверждать "таких фильтров нет" на основе `list_views` Description. **ВСЕГДА** делай live-probe перед использованием нового фильтра.

### C. `budgetsum` field is ALWAYS 0

В `ProjectBudgetCompleteBusiness` **никогда** не использовать `budgetsum` — оно всегда 0. Используй приоритет по суммам:

```
payfactsum > payforecastsum > payplansum > actfactsum > actforecastsum > actplansum
```

Per-row, per-period. См. Pitfall #121, #124, #129.

### D. `DirectProjectCostsGrade` ≠ "Лимит на пресейл"

`DirectProjectCostsGrade = 32_000_000` для 504-595 — НЕ лимит пресейла. Лимит = `PresaleLimit = 2_700_000` (5% от бюджета). Имена полей могут вводить в заблуждение. См. Pitfall #130.

### E. Parallel MCP requests → timeout

`ThreadPoolExecutor` или `asyncio` для MCP → `ReadTimeout` (60 сек). MCP-сервер обрабатывает запросы последовательно. **Делай запросы последовательно** (Pitfall #157).

### F. Per-accountid query для cross-project fetch

Когда индикатор требует данные по всем проектам исполнителя (6.7), используй:

```python
# Шаг 1: получить исполнителей текущего проекта с их accountid
# Шаг 2: для КАЖДОГО исполнителя — отдельный запрос с filters={"accountid": <id>}
```

НЕ `filters={}` с большим лимитом. 12 исполнителей × 5-6 сек = 60-72 сек. Приемлемо, **точно** по accountid. См. Pitfall #156.

### G. Per-period priority обязателен, не опционален

"Для каждого ПЕРИОДА каждой строки отдельно!" (user correction в 6.10). Каждый row в `ProjectBudgetCompleteBusiness` = один месяц. Применяй priority pattern **к каждой строке** независимо, потом агрегируй.

**Anti-pattern (был отвергнут)**: `total += row.get("actplansum") + row.get("payplansum")` — суммировал два поля одной строки.

## Паттерны файлов

### 1. Per-indicator thresholds файл (Pitfall #116)

Каждый индикатор имеет **отдельный** `scripts/<thing>_thresholds.py`. НЕ один god-module.

| Файл | Индикатор |
|------|----------|
| `effort_forecast_thresholds.py` | 6.3 |
| `plan_effort_thresholds.py` | 6.4 |
| `overload_thresholds.py` | 6.5 |
| `unfilled_roles_thresholds.py` | 6.6 |
| `cross_activity_overload_thresholds.py` | 6.7 |
| `financial_deadlines_thresholds.py` | 6.8 |
| `act_pay_amounts_thresholds.py` | 6.9 |
| `kp_labels_thresholds.py` | 6.16 |

### 2. Constants file (Pitfall #126, #128)

External reference values (ставка НДС, допуски) в отдельном `*_constants.py`. Не magic numbers inline.

- `vat_constants.py` — `DEFAULT_VAT_RATE = 5.0`, `VAT_TOLERANCE_RUB = 0.0001`
- `vat_calc.py` — формулы расчёта

### 3. Registry file (Pitfall #120)

Domain справочники данных (НЕ threshold policy):

- `lc_stage_kt_registry.py` — обязательные КТ по стадиям ЖЦ
- `point_states.py` — 4 состояния КТ (из `describe_entity`)

## Blocked indicator pattern (Pitfall #135)

Когда индикатор заблокирован (данных нет в MCP):

1. Создай `references/<N>-investigation.md` (НЕ удаляй!)
2. Update spec status to ⏸️
3. Update SKILL body — отметь pending
4. **Продолжай с следующим индикатором** (не блокируй прогресс)
5. User signal: "Предлагаю пока перепрыгнуть к 6.N" = **start now**, не спрашивай

**Live пример**: 6.13 (Бюджет проекта/пресейла) — заблокирован 2026-09-03 из-за отсутствия `PresaleLimit` в views. Создан `references/6-13-budget-presale-investigation.md`. Реализован позже через `get_entity_data` (Pitfall #140).

## Tax indicators: dash vs "Нет" (Pitfall #127)

User (2026-09-03): «В налоговом законодательстве это разные вещи!»

- `"Нет"` = "посчитано, не совпало / не найдено"
- `"-"` = "не вычислялось (не было данных)"

Применимо к 6.11 (НДС наличие) и 6.12 (НДС расчётный). НЕ к 6.10 (где отсутствие = "Нет").

## По указанию user: "v1.0.0" = мажорная версия

- Section 6 «Показатели проекта» — это **new major section**, требует major bump
- Архив `fst-project-health-v1.0.0.tar.gz` = 524 КБ (все 16 индикаторов, CSS, тесты)
- 7/7 tests PASS за 1.17 сек

## Потенциальные будущие улучшения (НЕ выполнено)

1. **6.5 с accountid-фильтром** — сейчас используется `ProjectId` фильтр, можно ускорить (как 6.7) если есть проблема с большими проектами
2. **HTML+CSS рендеринг** секции 6 (есть CSS, рендеринг частично) — можно доработать если user потребует
3. **Per-indicator unit tests** в `tests/test_indicators_v100.py` — есть минимальные, можно расширить

## Архивы

- `/tmp/skill-archives/fst-project-health-v1.0.0.tar.gz` — 524 КБ, full v1.0.0
- `/tmp/skill-archives/fst-project-health.tar.gz` — старый (2026-09-01)
- `/tmp/skill-archives/mcp-server-probing.tar.gz` — related skill
- `/tmp/skill-archives/project-search.tar.gz` — related skill

## Lessons about the user (for memory)

- User работает итеративно: спек → код → проверка → коррекция
- User замечает мелкие ошибки (например `forecast_hours` vs `plan_hours`, "Только не плановая, а прогнозная!")
- User требует **аккуратности** в форматах ("запятая после Да/Нет/Вопрос", "объединение строк а не дублирование")
- User любит **создавать investigation files** для blocked cases (НЕ отменять, сохранять state)
- User явно предпочитает **per-indicator thresholds files** вместо god-module
- User явно требует **constants file** для external reference values
- User даёт signal "Скажу когда сделаю" = **wait**, не preempt
- User делает **self-corrections** (Q1 в 6.14) — НЕ нужно backup файлы, просто update код
