# Финансовые сущности и бюджетирование в Форсайт

> ⚠️ **ЧАСТИЧНО УСТАРЕЛО (2026-08-07):** утверждения о полях
> `Project.PlanSum/ForecastSum/FactSum` (их **нет** в схеме) и
> `Point.PlanSum/ForecastSum/FactSum` (они **часто None** — заполняются
> только при наличии `ContractPlanSummariesValue`) — **неправильные**.
> См. итоговую таблицу в самом конце и `references/forsight-mcp-quirks-discovered-2026-08-07.md`
> (F4, F5, F6, F8). Актуальный источник фин. данных — `ProjectHealthCostMy`
> (view, открыт), `Project.ProjectBudgetGrade` / `DirectProjectCostsGrade`
> (назначение неясно, использовать осторожно).
>
> Подробная карта финансовых сущностей Форсайт ПМ Практики (MCP v3.2.4),
> зафиксированная по результатам live-разбора сущностей проекта 504-595
> (Космодром Жуковский внедрение ИСУП, 2026-08).

## ⚠️ Главное обновление 2026-08-07: `ProjectBudgetCompleteBusiness` — приоритетный View

**Открыт для обычных пользователей** (не 403, в отличие от `ResourcePlanning*`/`StatusReportBudget`).
Содержит **31 столбец** — ВСЯ финансовая информация по проекту:

- `ActivityId` (= ProjectId) — прямая связь
- `contractid` + `contractname` — контракт
- `pointid` + `pointname` — КТ
- `date` — **датированный** акт/оплата
- `budgetsum` — Бюджет базовый
- `actplansum` / `actforecastsum` / `actfactsum` — Акт план/прогноз/факт
- `payplansum` / `payforecastsum` / `payfactsum` — Оплата план/прогноз/факт
- `companyname`, `financesourcename` — юр. лицо и фин. источник
- `budgettype` — тип строки («Доходный контракт», «Расход расчёт по ресурсам», …)

**Решает проблемы 1.3, 1.4, 1.5, 1.6, 1.7** из «Вопросы по MCP 2026_08_07.md»:
- 1.3 — Финрезультат без `as_of_date` → **здесь каждая строка датирована**
- 1.4 — `ProjectBudgetGrade` vs `plan` 8x разница → **здесь `budgetsum`** — точная сумма
- 1.5 — Платежи без `ProjectId` → **здесь `ActivityId` прямая**
- 1.6 — КТ без `ParentFullName` → **здесь `pointid` + `date`**
- 1.7 — `outplan`/`outfact` неясны → **здесь `payplansum/factsum/forecastsum` раздельно**

**Использование:**

```python
from mcp_config import PROJECT_BUDGET_VIEW, mcp_init, mcp_call

sid, _ = mcp_init()
data = mcp_call(
    sid, "get_view",
    {"entityName": "Project", "viewName": PROJECT_BUDGET_VIEW, "limit": 2000},
)
```

**CLI-утилита:** `python3 scripts/get_project_budget.py --project 504-595 [--json] [--rows]`

**Пример для 504-595 (live, 2026-08-07):**

```
📊 Сводка по проекту:
   ProjectId:     4595
   Rows:          12
   Contracts:     1
   ActPlan:          6,572,500.00 ₽
   ActFact:          5,744,415.00 ₽
   PayPlan:          6,572,500.00 ₽
   PayFact:        5,744,415.00 ₽
   Balance:                  0.00 ₽   ← акт = оплата, идеально
```

---

## Старая карта (2026-08-05–06, ниже для истории)

## Главная проблема: **все финансовые view закрыты 403**

На практике для обычного пользователя (без admin-прав) **закрыты view**:

| View | Статус |
|------|--------|
| `ResourcePlanning` | ❌ 403 |
| `ResourcePlanningKp` | ❌ 403 |
| `ResourcePlanSummaries` | ❌ 403 |
| `ContractPlanSummaries` | ❌ 403 |
| `ContractPlanSummariesValue` | ❌ 403 |
| `StatusReportBudget` | ❌ 403 |
| `ApprovedBudget` | ❌ 403 |
| `ActivityFinanceLimit` | ❌ 403 |

Это означает, что через `get_view` получить данные **невозможно** — только через
`get_entity_data(id)` для каждой записи (с предварительным поиском id через
`find_entity`) или через поля самих сущностей (`Project.PlanSum`, `Point.PlanSum` и т.д.).

---

## Карта финансовых сущностей

### Сущности с прямым FK на Activity (привязка к проекту/КТ)

#### `StatusReportBudget` — Бюджет статус-отчёта проекта

**26 полей. Ключевые:**
- `ActivityId → Activity` (FK на проект/КТ)
- `Name` (string)
- `Plan` (numeric) — план
- `Forecast` (numeric) — прогноз
- `Total` (numeric) — сводная бюджетная роспись
- `Limit` (numeric) — лимиты бюджетных обязательств
- `Commitment` (numeric) — учтённые бюджетные обязательства
- `Fulfillment` (numeric) — кассовое исполнение
- `FinanceSourceId → FinanceSource`
- `PlanDate` (timestamp)
- `D_monthId → D_Month` (период)
- `CalendarPeriodId → CalendarPeriod`

**View `StatusReportBudget`** — 403 для обычного пользователя.

⚠️ **Это самая перспективная сущность** для расчёта бюджета проекта.
Содержит и план, и прогноз, и факт по периодам и статьям финансирования.

#### `ApprovedBudget` — Утверждённый бюджет

**8 полей:**
- `ApprovedBudgetId` (PK)
- `ActivityId → Activity` (FK)
- `Year` (integer)
- `Value` (numeric) — сумма бюджета за год

**View `ApprovedBudget`** — 403.

Простейшая сущность: бюджет проекта разбит по годам.

#### `ActivityFinanceLimit` — Значения финансовых лимитов активности

**View 403.** Не изучали детально (название говорит само за себя).

#### `ConsolidatedBudget` / `ConsolidatedBudgetValue` — Сводный бюджет

`ConsolidatedBudgetValue` — 16 полей. **View 403.** Скорее всего содержит сводный
бюджет с разбивкой по периодам и статьям. Не проверено на практике.

#### `ResourcePlanning` — Ресурсное планирование (детально)

**10 полей:**
- `ResourcePlanningId` (PK)
- `ActivityId → Activity` (FK)
- `AccountId → Account` (сотрудник)
- `planning_date` (date)
- `planning_hours` (numeric) — часы
- `planning_hours_kp` (numeric) — часы КП
- `SpecializationId → Specialization`
- `batchid` (uuid)

**View 403.** Детализация: одна запись = один сотрудник + один день.

#### `ResourcePlanningKp` — Прогнозные трудозатраты (по КТ)

**13 полей:**
- `ResourcePlanningKpId` (PK)
- `PointId → Point` (FK на КТ)
- `AccountId → Account`
- `RoleId → Role`
- `SpecializationId → Specialization`
- `planning_date` (snake_case! date)
- `planning_hours` (snake_case! numeric)
- `participation` (snake_case! numeric) — % привлечения
- `manual` (snake_case! boolean)

**View 403.**

#### `resourceplanningfact` — Фактические трудозатраты (по пользователю)

**View `resourceplanningfact_userview`** — содержит фактические затраты,
сгруппированные по пользователю.

### Сущности с FK на Contract

#### `ContractPlanSummaries` — Планирование/итоги по контрактам

**9 полей:**
- `ContractPlanSummariesId` (PK)
- `ActivityId` (Title «Проект» — FK на Activity)
- `RateRub` (numeric) — ставка
- `IsProject` (boolean)
- `CompanyId → Company`

**View 403.**

#### `ContractPlanSummariesValue` — Значения

**16 полей:**
- `ContractPlanSummariesId → ContractPlanSummaries`
- `ContractId` (FK на контракт)
- `FinanceSourceId → FinanceSource`
- `Month` (string) — месяц, год
- `Value` (numeric)
- `PlanAct` / `ForecastAct` / `FactAct` (numeric) — акты
- `PlanPay` / `ForecastPay` / `FactPay` (numeric) — оплаты

**View 403.** Это то, что обычно называют "план-факт по контракту".

### Сущности с суммами, встроенные в Project / Point

#### В `Project` (68 полей)

> ⚠️ **LIVE-CHECK 2026-08-07**: поля `PlanSum` / `ForecastSum` / `FactSum` **НЕ СУЩЕСТВУЮТ** в схеме `Project`. Эти поля есть только в `Point` (КT), и даже там часто `None`. См. `references/forsight-mcp-quirks-discovered-2026-08-07.md` (F5, F6).

Поля с финансовыми данными (проверено через `describe_entity(Project, "4595")`):
- `ProjectBudgetGrade` (numeric) — **бюджет проекта (оценка), руб.**
- `DirectProjectCostsGrade` (numeric) — **прямые затраты проекта (оценка), руб.**
- `ProjectLimit` (numeric) — лимит проекта (назначение неясно)
- `PresaleLimit` (numeric) — лимит на пресейл
- `PresaleBudgetPercentage` (numeric) — % пресейла от бюджета
- `IsUseInResourcePlan` (boolean) — используется в resource plan
- `ProjectProfileId` (FK) — профиль проекта

**ОТСУТСТВУЮТ** (несмотря на эти названия в старых заметках):
- `Project.PlanSum` ❌ — нет в схеме
- `Project.ForecastSum` ❌ — нет в схеме
- `Project.FactSum` ❌ — нет в схеме

**Доступ через `get_entity_data(Project, data_id="4595")`** — открыт.

#### В `Point` (68 полей)

Поля с финансовыми данными (на КТ):
- `PlanSum` — плановая сумма на КТ
- `ForecastSum` — прогнозная сумма
- `FactSum` — фактическая сумма
- `StageSum` — сумма этапа
- `StageSumNumber` — номер этапа
- `PctComplete` — % выполнения

**Доступ через `get_entity_data(Point, data_id="4725")`** — открыт.

### Сущности контрактов

#### `InContract` — Доходный контракт

**43 поля. Ключевые:**
- `InContractId` (PK)
- `RealSum` (numeric) — **сумма контракта**
- `PlanSum` — планируемая сумма
- `ContractorId → Contractor`
- `InContractActivity` (multi-FK на Activity) — **привязка к проектам**

**View `InContractAll`** — открыт, **НО в строке `InContractActivity` = None**.
Это означает, что для получения привязки нужно делать `get_entity_data`
для каждого контракта.

#### `OutcomeContract` — Расходный контракт

**41 поле. Ключевые:**
- `OutcomeContractId` (PK)
- `RealSum` — сумма контракта
- `PlanSum` — планируемая
- `ContractorId → Contractor`
- `OutcomeContractActivity` (multi-FK на Activity) — **привязка к проектам**

Та же история: `OutcomeContractActivity` не приходит в view.

---

## Как получать финансовые данные (обход 403)

### Стратегия 1: через встроенные поля в Project / Point (открыто)

```python
project = mcp__fst_pmpractice__get_entity_data(
    entityName="Project", data_id="4595"
)
props = project["properties"]
budget = props["ProjectBudgetGrade"]["value"]      # 54 000 000
costs = props["DirectProjectCostsGrade"]["value"]  # 32 000 000

point = mcp__fst_pmpractice__get_entity_data(
    entityName="Point", data_id="4725"
)
props = point["properties"]
plan = props["PlanSum"]["value"]        # 2 500 000
forecast = props["ForecastSum"]["value"] # 2 499 990
fact = props["FactSum"]["value"]        # 2 500
```

### Стратегия 2: через `find_entity` + `get_entity_data` (медленно, но открыто)

```python
# 1. Найти все контракты через find_entity по коду проекта
results = mcp__fst_pmpractice__find_entity(name="504-595", limit=50)
in_contracts = [it for it in results["items"]
                if it["entityName"] == "InContract"]

# 2. Для каждого — get_entity_data (там есть InContractActivity)
for c in in_contracts:
    detail = mcp__fst_pmpractice__get_entity_data(
        entityName="InContract", data_id=str(c["id"])
    )
    ica = detail["properties"]["InContractActivity"]["value"] or []
    if any(a["value"] == 4595 for a in ica):
        # это наш контракт
        real_sum = detail["properties"]["RealSum"]["value"]
```

### Стратегия 3: через КТ-оплаты/акты (Point с ParentCode = ContractCode)

```python
points = mcp__fst_pmpractice__get_view(
    entityName="Point", viewName="AllMyPoint", limit=3000
)
contract_points = [
    p for p in points["data"]
    if str(p.get("ParentCode", "")).strip() == "704-724"
]

# В строке view Point нет PlanSum/ForecastSum/FactSum!
# Нужно get_entity_data для каждой КТ
for p in contract_points:
    detail = mcp__fst_pmpractice__get_entity_data(
        entityName="Point", data_id=str(p["PointId"])
    )
    plan = detail["properties"]["PlanSum"]["value"]
    forecast = detail["properties"]["ForecastSum"]["value"]
    fact = detail["properties"]["FactSum"]["value"]
```

### Стратегия 4: через трудозатраты × ставка (если есть)

```python
# ResourcePlanning (часы по сотруднику) × ставка сотрудника
# Ставка — поле Account.StaffRate или Account.HourlyRate (не проверено)
# Это медленно и ненадёжно, лучше использовать суммы КТ (стратегия 3)
```

---

## Что работает, что нет — итоговая таблица

| Источник | Доступ | Содержит |
|----------|--------|----------|
| `Project.ProjectBudgetGrade` | ✅ | Оценка бюджета проекта |
| `Project.DirectProjectCostsGrade` | ✅ | Оценка прямых затрат |
| `Project.PlanSum/ForecastSum/FactSum` | ✅ | Суммы проекта (агрегат) |
| `Point.PlanSum/ForecastSum/FactSum` | ✅ через `get_entity_data` | Суммы по КТ |
| `InContract.RealSum` | ✅ через `find_entity` + `get_entity_data` | Сумма контракта |
| `InContract.InContractActivity` | ✅ через `get_entity_data` (не через view) | Привязка к проектам |
| `OutcomeContract.RealSum` | ✅ через `find_entity` + `get_entity_data` | Сумма расходного контракта |
| `StatusReportBudget.*` | ❌ view 403 | План/факт/прогноз по периодам |
| `ApprovedBudget.Value` | ❌ view 403 | Утверждённый бюджет по годам |
| `ContractPlanSummariesValue.*` | ❌ view 403 | План-факт актов/оплат по контракту |
| `ResourcePlanning/planning_hours` | ❌ view 403 | Часы по сотруднику/дню |
| `ResourcePlanningKp/planning_hours` | ❌ view 403 | Прогнозные часы по КТ |
| `Payments.AllPayments` | ✅ view открыт (но 0 привязок для 504-595) | Платежи |

---

## Рекомендация для скиллов

1. **Не пытаться использовать view `ResourcePlanning*`, `StatusReportBudget`, `ApprovedBudget`** — они 403.
2. **Базовая финансовая сводка** — через `Project.ProjectBudgetGrade` и `Project.DirectProjectCostsGrade`.
3. **Анализ актов/оплат** — через `find_entity(contract_code)` → `get_entity_data(InContract)` → `get_view(Point)` с фильтром `ParentCode = contract_code` → `get_entity_data(Point)` для каждой КТ.
4. **Трудозатраты в денежном выражении** — НЕТ прямого способа через view. Либо использовать `Point.PlanSum`/`FactSum` как прокси, либо требовать admin-прав.
5. **Сравнение с эталоном** — для 504-595 проверено: доход 5 400 000, расход 0 (нет расходных контрактов через `OutcomeContractMyProject`), финансовый результат прогноза = +5 400 000.
