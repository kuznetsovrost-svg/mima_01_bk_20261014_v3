# Live-probe `filters={...}` и новых view (2026-09-01)

**Дата:** 2026-09-01
**Источник:** live-probes из skill `fst-project-health` v0.9.0+

Этот документ — **детальная live-probe матрица** для нового стандарта MCP
`filters={...}` и связанных view. Основной playbook в
`references/mcp-filters-format.md`, здесь — подтверждающие данные.

---

## 1. Live-probe матрица (все 4 проекта)

| Проект | ProjectId | `get_view(filters={ProjectId})` | Строк | Время | Подтверждено |
|--------|----------:|-------------------------------|------:|------:|:---:|
| 504-595 | 4595 | `ProjectHealthCostMy` | 1 | 1.42 | ✅ |
| 503-434 | 3434 | `ProjectHealthCostMy` | 1 | 1.30 | ✅ |
| 503-152 | 3152 | `ProjectHealthCostMy` | 1 | 1.64 | ✅ |
| 504-314 | 4314 | `ProjectHealthCostMy` | 1 | 1.34 | ✅ |

**Вывод:** `ProjectHealthCostMy` стабильно возвращает **1 строку** для любого
проекта, время **1.3-1.6 сек**. Регрессия (bigint = text) исправлена.

---

## 2. Live-probe: `ProjectHealthCostMy` с `DateBegin`/`DateEnd`

Это открывает **трендовые отчёты** — получаем данные на разные даты:

| Период | fact | devcost | inplan | infact | outplan | outfact |
|--------|----:|--------:|-------:|-------:|-------:|--------:|
| 2025-12 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-06 | −753 525 | 719 202 | 0 | 0 | 0 | 753 525 |
| 2026-07 | 9 110 | 2 173 874 | 4 997 500 | 2 500 000 | 0 | 2 490 890 |
| 2026-08 | 0 | 1 253 784 | 1 500 000 | 0 | 75 000 | 0 |
| Весь год | −744 415 | 4 146 860 | 6 497 500 | 2 500 000 | 75 000 | 3 244 415 |

**Фильтр:** `DateBegin: '2026-08-01', DateEnd: '2026-08-31'`
**Возвращает:** 1 строку с агрегатами за этот период.

**Использование:** `build_trend_report.py` в `/tmp/trend-report-design/` строит
графики `forecast`/`fact`/`devcost` по месяцам на основе этих данных.

---

## 3. Live-probe: `NormDayWorkHours` (Pitfall #20 — ИСПРАВЛЕН)

Ранее Pitfall #17 в `mcp-server-probing/SKILL.md` описывал `NormDayWorkHours`
как TRAP (возвращал данные о проектах). **2026-09-01 — ИСПРАВЛЕНО.**

### Новые данные (live-probe 2026-09-01)

| Запрос | Строк | Структура | Результат |
|--------|------:|-----------|-----------|
| `NormDayWorkHours` без фильтра | 100 | `id, Date, Hours, ProjectId` | ✅ правильная структура |
| `NormDayWorkHours?ProjectId=4595` | 100 | `id, Date, Hours, ProjectId` | ✅ все ProjectId=4595 |
| `?ProjectId + StartDate + EndDate` | 31 | `id, Date, Hours, ProjectId` | ✅ 31 день августа |
| `StartDate + EndDate` (без ProjectId) | 31 | `id, Date, Hours, ProjectId` | ✅ 31 день |

### Семантика Hours

**Корректная:** будни = 8, выходные = 0.

| День недели | Дней | Hours |
|-------------|----:|------:|
| Monday | 5 | 8ч |
| Tuesday | 4 | 8ч |
| Wednesday | 4 | 8ч |
| Thursday | 4 | 8ч |
| Friday | 4 | 8ч |
| **Saturday** | 5 | **0ч** (выходной) |
| **Sunday** | 5 | **0ч** (выходной) |

**Итого:** 21 будний × 8ч + 10 выходных × 0ч = **168 часов** в месяце
(стандартная российская норма).

**⚠️ НЕ ПУТАЙ:** `Hours=0` для выходных — **это правильное** поведение,
а не баг. Если `Hours=0` для будних — это праздник (проверь через
`mcp_config.METAMODEL_KEYS`).

---

## 4. Live-probe: `InContractMyProject` (Pitfall #21 — НЕ исправлен)

### Текущее состояние (2026-09-01)

| Запрос | Строк | Результат |
|--------|------:|-----------|
| `InContractMyProject` без фильтра | 9 | ✅ работает |
| `?ProjectId=4595` (504-595) | 1 | ✅ договор 704-724 |
| `?ProjectId=3434` (503-434) | **0** | ❌ нет доступа |
| `?ProjectId=3152` (503-152) | **0** | ❌ нет доступа |

**⚠️ Гипотеза:** доступ пользователя к договорам определяется его ролью
в проекте. У текущего пользователя (user_id=120872) есть доступ только
к проекту 504-595 (где он Куратор). Для остальных — view возвращает 0.

### Структура строк (MyProject)

Все 9 строк имеют заполненные поля:

| # | Code | ProjectId | ParentFullName |
|---|------|-----------|----------------|
| 1 | 701-611 | 1610 | 501-610. ФГК Сопровождение 2023-2026 |
| 2 | 701-611 | 4034 | 504-034. ФГК Сопровождение 2026-2027 |
| 3 | 704-130 | 3447 | 503-447. Upside ИСУП ПМФ 2026 |
| 4 | 704-177 | 3447 | 503-447. Upside ИСУП ПМФ 2026 |
| 5 | **704-724** | **4595** | 504-595. Космодром Жуковский внедрение ИСУП |
| 6 | 701-691 | 1682 | 501-682. ФГК Адаптация ИС УПД |
| 7 | 701-127 | 1083 | 501-083. Вологда 2025 Сопровождение |
| 8 | 701-231 | 740 | 500-740. Самрук Казына Констракшн... |
| 9 | 701-232 | 740 | 500-740. Самрук Казына Констракшн... |

**Раньше `projectid` был `null`** — теперь заполняется корректно.

---

## 5. Live-probe: `InContract` (без MyProject) — 6 строк для 504-595

Это **другой** view (`InContract`, не `InContractMyProject`). Возвращает
**все КТ контракта**:

| # | InContractId | InContractName | LinkedActivityId |
|---|--------------|----------------|------------------:|
| 1 | 4724 | 704-724. Контракт... | 4595 |
| 2-6 | (другие КТ) | ... | 4595 |

**Фильтр работает:** `?ProjectId=4595` → 6 строк (только для 504-595).
Для 503-434/503-152/504-314 — 0 строк (нет доступа или нет данных).

**22 столбца** в ответе:
`id, InContractId, InContractName, LinkedActivityId, LinkedActivityName,
ProgramId, ProgramName, PortfolioId, PortfolioName, ActPlanDate,
ActForecastDate, ActFactDate, PayPlanDate, PayForecastDate, PayFactDate,
ActPlanSum, ActForecastSum, ActFactSum, PayPlanSum, PayForecastSum, PayFactSum`

---

## 6. Live-probe: `ProjectBudgetCompleteBusiness`

| Проект | Строк | `isprojectbudget` | `ispresalebudget` |
|--------|------:|:------------------:|:------------------:|
| 504-595 | 12 | True (все 12) | False (все 12) |

**12 строк** для 504-595:
- 7 строк "Доходный контракт"
- 3 строки "Расход расчет по ресурсам"
- 2 строки "Расход ручной ввод"

**Ключевые флаги:**
- `isprojectbudget=True` — бюджет проекта (не пресейла)
- `ispresalebudget=False` — НЕ пресейл

**Использование:** `ApprovedBudget.Year=2026, Value=54 000 000` (из другого view)
против `ProjectBudgetCompleteBusiness` (по КТ) — это **разные агрегаты**.

---

## 7. Live-probe: `ApprovedBudget`

| Проект | Год | Value (₽) |
|--------|----:|----------:|
| 504-595 | 2026 | **54 000 000** |

**5 столбцов:** `id, ApprovedBudgetId, ActivityId, Year, Value`.

**Фильтры:** `ActivityId`, `PortfolioId`, `Year`.

**Другие проекты** (503-434, 503-152, 504-314) — **0 строк** (нет утверждённого бюджета).

---

## 8. Live-probe: `delete_entity` формат (Pitfall #15)

10 форматов протестировано, **только один** рабочий:

```python
# ✅ РАБОТАЕТ:
mcp_call(sid, "delete_entity", {
    "remove": [f"AttributeValue|<AttributeValueId>"]
})
# Returns: {"ok": True}
```

**Все остальные форматы** возвращают 500 или 400 ошибки.

**Live-probe:** 34/34 успешных удалений (включая 33 тестовых + 1 тестовую).

**Скрипт:** `/tmp/project-json-design/scripts/delete_attribute_values.py`
поддерживает `--ids <id1> <id2>...`, `--from-file ids.txt`, `--interactive`,
`--dry-run`, `--no-verify`.

---

## 9. B-tree 2704 лимит — ИСПРАВЛЕН

**Live-probe 2026-09-01 (после исправления разработчиками):**

| JSON | Размер | Статус |
|------|-------:|:------:|
| v0.1.0_504-595.json | 5 342 bytes | ✅ OK |
| v0.1.0_504-314.json | 10 435 bytes | ✅ OK |
| v0.1.0_503-434.json | 12 986 bytes | ✅ OK |
| v0.1.0_503-152.json | 50 559 bytes | ✅ OK |

**Все 4 JSON загружены успешно** через `save_entity` с `AttrValue=<JSON>`.

**Было (2026-08-22):**
```
500 - размер строки индекса (8080) больше предельного для btree версии 4 размера (2704)
```

**Стало (2026-09-01):** нет ошибок, лимит снят.

**Workaround больше не нужен** (split-via-`AttrValueSource`). Если опять
сломается — `/tmp/project-json-design/scripts/delete_attribute_values.py`
позволяет очистить 33+ записей за раз.

---

## 10. Live-probe: `MyProject` vs `AllProject`

| View | Всего | С `UserAccount=120872` | С `ProjectProfileId=1` |
|------|------:|-----------------------:|----------------------:|
| `MyProject` | 11 | 11 | 11 |
| `AllProject` | 109 | 109 | 109 |

**`UserAccount` не фильтрует** — обе цифры одинаковые. Возможно фильтр не
подключен или показывает все доступные пользователю проекты.

**ProjectProfileId=1** ("Базовый") — 11/11 для MyProject, 109/109 для AllProject.
Тоже не фильтрует (все проекты — базовые).

**Вывод:** фильтры `UserAccount` и `ProjectProfileId` указаны в `list_views`
как поддерживаемые, но реально не применяются к нашему пользователю.
Клиентская фильтрация (по `MyRole` или `Code`) надёжнее.

---

## 11. Changelog

| Дата | Что добавлено |
|------|---------------|
| 2026-09-01 | Первая версия. Live-probe матрица для 4 проектов, NormDayWorkHours fix, InContractMyProject fix (Pitfall #21), delete_entity fix (Pitfall #15), B-tree fix (Pitfall #15). |
</file_content>