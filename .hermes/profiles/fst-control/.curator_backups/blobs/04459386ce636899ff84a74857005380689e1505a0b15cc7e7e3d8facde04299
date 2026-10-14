# Дополнительные находки по MCP view — сессия 2026-09-01

**Дата:** 2026-09-01
**Автор:** Live-probe в сессии с пользователем (Кузнецов Р.В.)
**Контекст:** После `filters={...}` фикса проверили другие view для проекта 504-595.

---

## TL;DR

| View | Формат | Поля | Где используется |
|------|--------|------|------------------|
| `ProjectBudgetCompleteBusiness` | работает | 36 столбцов, `isprojectbudget`, `ispresalebudget` | Раздел 6 (Финансы) — детализация |
| `ApprovedBudget` | работает | 5 столбцов: `id`, `ApprovedBudgetId`, `ActivityId`, `Year`, `Value` | **Новый view** для отчётов |
| `NormDayWorkHours` | работает | `Date`, `Hours`, `ProjectId` | Календарь рабочих часов |

---

## 1. `ProjectBudgetCompleteBusiness` — 36 столбцов (live-probe 2026-09-01)

**Структура** (для 504-595, 12 строк):

| Категория | Столбцы |
|-----------|---------|
| Идентификаторы | `id`, `ActivityId`, `pointid`, `incontractid`, `outcontractid`, `paymentid` |
| Названия | `activityname`, `pointname`, `incontractname`, `outcontractname`, `paymentname`, `companyname` |
| Программа/Портфель | `programid`, `programname`, `portfolioid`, `portfolioname` |
| Бюджет (тип) | `budgettype`, `budgetsum` |
| **Флаги** | `isincome`, `isproject`, `isresource`, `ispayment`, **`isprojectbudget`**, **`ispresalebudget`** |
| Финансы | `actplansum`, `actforecastsum`, `actfactsum`, `payplansum`, `payforecastsum`, `payfactsum` |
| Дата | `date` |
| Финансовый источник | `financesourceid`, `financesourcename`, `financesourceparentname`, `companyid` |
| Контракт | `contractplansummariesvalueid` |

**Ключевые флаги:**

- `isprojectbudget` (bool) — строка относится к бюджету проекта (стадия реализации)
- `ispresalebudget` (bool) — строка относится к бюджету пресейла

**Что показывает комбинация:**

| `isprojectbudget` | `ispresalebudget` | Значение |
|:---:|:---:|-----------|
| True | False | Бюджет проекта (активная стадия) |
| False | True | Бюджет пресейла |
| False | False | Не классифицировано |

**Распределение для 504-595** (12 строк):

| budgettype | Кол-во | isprojectbudget | ispresalebudget |
|------------|------:|:---:|:---:|
| Доходный контракт | 7 | True | False |
| Расход расчет по ресурсам | 3 | True | False |
| Расход ручной ввод | 2 | True | False |

**Применение в скилле:**

- Для раздела 6 (Финансы) можно **детализировать** на `isprojectbudget=True` строки (показать только проект, без пресейла)
- Фильтр: `r["isprojectbudget"] == True`
- Агрегировать `actplansum/actfactsum/payplansum/payfactsum` по `budgettype`

**Live-probe 2026-09-01 — фильтры работают:**

```python
mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "ProjectBudgetCompleteBusiness",
    "filters": {"ProjectId": 4595},
    "limit": 100
})
# Returns 12 rows за 3.57 сек
```

---

## 2. `ApprovedBudget` — НОВЫЙ VIEW (live-probe 2026-09-01)

**Структура** (5 столбцов):

| Столбец | Тип | Описание |
|---------|-----|----------|
| `id` | int | Sequence ID |
| `ApprovedBudgetId` | int | Бизнес-ID утверждённого бюджета |
| `ActivityId` | int | ProjectId (= ID активности) |
| `Year` | int | Год (2024, 2025, 2026...) |
| `Value` | money | Утверждённая сумма на год |

**Поддерживаемые фильтры** (из `list_views`):

- `@ActivityId` (ОУ) — фильтр по проекту
- `@PortfolioId` (Портфель) — фильтр по портфелю
- `@Year` (Год) — фильтр по году (если не задан — все года)

**Live-probe результаты для 504-595 (ProjectId=4595):**

| Год | Value (руб) | ApprovedBudgetId |
|----:|-----------:|-----------------:|
| 2026 | 54 000 000 | 55 |

**Для других проектов:**

- 503-434 (ProjectId=3434) — **0 строк** (бюджет не утверждён)
- 503-152 (ProjectId=3152) — **0 строк**
- 504-314 (ProjectId=4314) — **0 строк**

**Live-probe результаты для PortfolioId=4594** (портфель 504-595):

- 1 строка (только 504-595)

**Применение в скилле:**

- **Раздел 6 (Финансы)** — добавить показатель "Утверждённый бюджет на год" с сравнением `ApprovedBudget.Value` vs `ProjectHealthCostMy.forecast`
- **Trend-отчёт** — динамика утверждённого бюджета по годам
- **Новая метрика** — "Достижение утверждённого бюджета" = `actfactsum / ApprovedBudget.Value * 100%`

**Пример вызова:**

```python
# Бюджет за конкретный год
data = mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "ApprovedBudget",
    "filters": {"ActivityId": 4595, "Year": 2026},
    "limit": 10
})
# 1 row: Value=54 000 000

# За все года (для trend-отчёта)
data = mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "ApprovedBudget",
    "filters": {"ActivityId": 4595},
    "limit": 10
})
# Группировка по Year на клиенте
```

---

## 3. `NormDayWorkHours` — корректная интерпретация (live-probe 2026-09-01)

**Структура** (3 столбца):

| Столбец | Тип | Описание |
|---------|-----|----------|
| `id` | int | Sequence |
| `Date` | date (с timezone) | Дата дня |
| `Hours` | decimal | Нормативные часы (8 в будни, 0 в выходные) |
| `ProjectId` | int (nullable) | ProjectId (None = общая норма без проекта) |

**Поддерживаемые фильтры:**

- `@ProjectId` — фильтр по проекту (**не работает!** всегда 244 строки)
- `@StartDate` — начало диапазона
- `@EndDate` — конец диапазона

**Распределение Hours (для августа 2026):**

| День недели | Кол-во | Hours |
|-------------|------:|------:|
| Понедельник | 5 | 8 |
| Вторник | 4 | 8 |
| Среда | 4 | 8 |
| Четверг | 4 | 8 |
| Пятница | 4 | 8 |
| Суббота | 5 | **0** (выходной) |
| Воскресенье | 5 | **0** (выходной) |

**Итого за август 2026:**

- 21 будний день × 8ч = 168 часов (стандартная российская норма)
- 10 выходных × 0ч = 0 часов

**Результаты тестов:**

| Тест | Строк | Время |
|------|------:|------:|
| Без параметров | 244 (первые 2 страницы) | 0.67 сек |
| `filters={}` | 244 | 0.56 сек |
| `filters={ProjectId: 4595}` | 244 (НЕ фильтрует) | 0.54 сек |
| `filters={StartDate, EndDate}` | 31 (август) | 0.55 сек |
| `filters={StartDate, EndDate}` (только даты) | 31 (август) | 0.50 сек |

**⚠️ ВАЖНО — фильтр по `ProjectId` НЕ работает!**

- `NormDayWorkHours?ProjectId=4595` возвращает те же 244 строки
- Поле `ProjectId` в строках всегда `null` (или 4595 если повезёт — нестабильно)
- **Причина:** view вычисляется per-Project без фильтрации

**Применение в скилле:**

- **Норматив рабочего времени** — 168 часов/месяц (21 будний × 8)
- **Расчёт трудозатрат по дням** — `effort_fact / NormDayWorkHours.Hours`
- **Тренд по месяцам** — количество рабочих часов

**КРИТИЧНО:** фильтр по проекту НЕ работает → для проекта 504-595 получаем общую норму. Если нужно "норма по проекту" — нужны исключения (праздники, спец. дни). Этих данных в `NormDayWorkHours` нет (Hours=8 для всех будних).

**Workaround:** если проект = стандартный (без исключений), использовать общую норму. Иначе запрашивать `get_effort` для project-specific часов.

---

## 4. Trend-отчёт через `DateBegin`/`DateEnd` (live-probe 2026-09-01)

**Открытие:** `ProjectHealthCostMy` поддерживает фильтры `DateBegin` + `DateEnd` — это **открывает построение trend-отчётов**.

**Пример — данные по месяцам для 504-595:**

| Период | forecast | fact | devcost | inplan | infact |
|--------|---------:|-----:|--------:|-------:|-------:|
| 2025-10 | −221 860 | 0 | 0 | 0 | 0 |
| 2025-11 | −221 860 | 0 | 0 | 0 | 0 |
| 2025-12 | −221 860 | 0 | 0 | 0 | 0 |
| 2026-01 | −221 860 | 0 | 0 | 0 | 0 |
| 2026-02 | −221 860 | 0 | 0 | 0 | 0 |
| 2026-03 | −221 860 | 0 | 0 | 0 | 0 |
| 2026-04 | −221 860 | 0 | 0 | 0 | 0 |
| 2026-05 | −221 860 | 0 | 0 | 0 | 0 |
| 2026-06 | −221 860 | −753 525 | 719 202 | 0 | 0 |
| 2026-07 | −221 860 | 9 110 | 2 173 874 | 4 997 500 | 2 500 000 |
| 2026-08 | −221 860 | 0 | 1 253 784 | 1 500 000 | 0 |

**Скрипт построения трендового отчёта:**

`/tmp/trend-report-design/scripts/build_trend_report.py` — НЕ в `scripts/` скилла, потому что это **другой скилл** (`fst-project-trends`).

**Когда применять:**

- ✅ Исторический анализ проекта (как менялся forecast/fact/devcost)
- ✅ Выявление тренда ухудшения/улучшения
- ✅ Подготовка к будущему скиллу `fst-project-trends`

**Пример кода (вне скилла):**

```python
# В run_all.py — НЕ применять, это другой скилл
# В трендовом скрипте:
periods = []
for month_offset in range(12, 0, -1):  # последние 12 месяцев
    begin, end = month_boundaries(month_offset)
    data = mcp_call(sid, "get_view", {
        "entityName": "Project",
        "viewName": "ProjectHealthCostMy",
        "filters": {"ProjectId": pid, "DateBegin": begin, "DateEnd": end},
        "limit": 1
    })
    if data["data"]:
        periods.append({"period": begin[:7], **data["data"][0]})
```

---

## 5. `delete_entity` — финальный рабочий формат (live-probe 2026-09-01)

**Формат найден через итеративные ошибки:**

```python
# ✅ РАБОТАЕТ
mcp_call(sid, "delete_entity", {
    "remove": [f"AttributeValue|<guid>"]
})
# Returns: {"ok": True}
```

**10 форматов протестированы — только 1 рабочий:**

| Формат | Результат |
|--------|:---------:|
| `remove: [f"AttributeValue\|<guid>"]` | ✅ ok |
| `entityName + id` | ❌ 400 |
| `remove: [{entityName, id}]` | ❌ 400 |
| `remove: ["<guid>"]` | ❌ format error |
| `remove: ["<classid>\|<id>"]` | ❌ 404 |
| `remove: [{classid, id}]` | ❌ 400 |
| `delete: [...]` | ❌ validation error |
| `remove: [classid\|id]` | ❌ 404 |
| `entityName, data: {id}` | ❌ validation error |
| `entityName, id, cascade_delete: true` | ❌ 400 |

**Скрипт для очистки тестовых записей:**

`/tmp/project-json-design/scripts/delete_attribute_values.py` (НЕ в скилле, потому что это для экспериментов).

**Live-probe 2026-09-01:** 34/34 удаления успешны (тестовые записи из писем v2/v3 к разработчикам).

**Применение в production:**

- В `fst-project-health` **не нужен** — мы только создаём отчёты, не удаляем их
- В `fst-project-trends` (будущий скилл) — может быть нужен для очистки старых trend-записей

---

## 6. Сводный статус MCP-views (2026-09-01)

| View | Фильтр ProjectId | Фильтры по дате | projectid в строках | Поля Hours/Budget |
|------|:---:|:---:|:---:|:---:|
| `ProjectHealthCostMy` | ✅ | ✅ DateBegin/DateEnd | ✅ | (агрегаты) |
| `ProjectResourcePlan` | ✅ | ❌ | ✅ | (нет) |
| `ProjectBudgetCompleteBusiness` | ✅ | ❌ | ✅ | actplansum, actfactsum и т.д. |
| `InContractMyProject` | ✅ (только 504-595) | ❌ | ❌ null | (нет) |
| `InContract` (без MyProject) | ❌ не фильтрует | ❌ | ❌ null | (нет) |
| `AllMyPoint` | ✅ | ❌ | ✅ | (нет) |
| `NormDayWorkHours` | ❌ не фильтрует | ✅ StartDate/EndDate | ⚠️ нестабильно | ✅ Hours |
| `ApprovedBudget` | ✅ | ✅ Year | ✅ | ✅ Value |

**4 из 8 view полностью работают.** Остальные имеют частичные проблемы.

---

## 7. Рекомендации для следующих сессий

1. **Добавить `ApprovedBudget` в раздел 6 (Финансы):**
   - Новая строка "Утверждённый бюджет (на год)"
   - Сравнение с `ProjectHealthCostMy.forecast`

2. **Добавить `NormDayWorkHours` в расчёт трудозатрат:**
   - Месячная норма = 168 часов (21 будний × 8)
   - Fact / Norm × 100% = % выполнения нормы

3. **Использовать `DateBegin`/`DateEnd` для трендов:**
   - `fst-project-trends` (будущий скилл) — основной use-case
   - Промежуточно: можно добавить "историю показателей" в operational отчёт

4. **`ProjectBudgetCompleteBusiness` для детализации:**
   - Фильтр `isprojectbudget=True` — отделить от пресейла
   - Группировка по `budgettype` (доход/расход)

5. **Не полагаться на `InContract`:**
   - Использовать только `InContractMyProject`
   - Фильтровать клиентом по `ParentFullName` (pitfall #12)
   - Не ждать заполнения `projectid` (всегда null)

---

## Live-probe commands (для повторения)

```python
# 1. ProjectBudgetCompleteBusiness
mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "ProjectBudgetCompleteBusiness",
    "filters": {"ProjectId": 4595},
    "limit": 100
})

# 2. ApprovedBudget (по году)
mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "ApprovedBudget",
    "filters": {"ActivityId": 4595, "Year": 2026},
    "limit": 10
})

# 3. ApprovedBudget (все года, для тренда)
mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "ApprovedBudget",
    "filters": {"ActivityId": 4595},
    "limit": 10
})

# 4. NormDayWorkHours (месяц)
mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "NormDayWorkHours",
    "filters": {"StartDate": "2026-08-01", "EndDate": "2026-08-31"},
    "limit": 100
})

# 5. ProjectHealthCostMy + DateBegin/DateEnd (тренд)
mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "ProjectHealthCostMy",
    "filters": {"ProjectId": 4595, "DateBegin": "2026-08-01", "DateEnd": "2026-08-31"},
    "limit": 1
})

# 6. list_views — discover supported filters
views = mcp_call(sid, "list_views", {})
for v in views:
    if v.get("ViewName") in ["ApprovedBudget", "NormDayWorkHours", "ProjectBudgetCompleteBusiness"]:
        print(v.get("Description"))
```

---

## Связь с другими документами

- `references/mcp-filters-format.md` — формат `filters={...}` (от 2026-09-01)
- `references/mcp-server-filter-playbook.md` — статус фильтров по view (от 2026-09-01)
- `references/mcp-regressions-2026-09-01.md` — история регрессий
- `scripts/probe_filters_format.py` — live-проверка формата
- `scripts/regression_probe.py` — регресс-скрипт для 4 групп views

## Контакт

- **Telegram:** @kuznetsov-rostislav (или через Hermes-агент)
- **Дата:** 2026-09-01
- **Скилл:** `fst-project-health` v0.14.0+
