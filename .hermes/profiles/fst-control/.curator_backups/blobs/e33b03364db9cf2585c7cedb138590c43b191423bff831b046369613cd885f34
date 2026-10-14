# Point/AllFinancePoint — финансовые КТ в иерархии Проект→Контракт→КТ

**Контекст:** открытие 2026-09-04 при переделке индикатора 6.8 «Соблюдение
сроков финансовых КТ» в скилле `fst-project-health`. Изначально 6.8 брал
данные из `InContract/InContractBudgetBusiness`, что давало строки
типа «Акт-4724» / «Оплата-4724» — это были **ID финансовых КТ**, а не
**КТ проекта**, как ожидал пользователь.

**Решение:** через `list_views(entityName="Point")` обнаружен view
`AllFinancePoint`, возвращающий **КТ типа `point` с
`ParentEntityName="InContract"`** — то есть КТ, привязанные к
контрактам (а не к проекту напрямую, как в `AllMyPoint`).

## Иерархия

```
Project (504-595, ProjectId=4595)
  └─ InContract (704-724, InContractId=4724, parent = Project через Activity)
       └─ Point (104-732, type=point, ParentEntityName=InContract)
          ├─ Code: 104-732
          ├─ Name: "Акт по 2-му блоку работ подписан"
          ├─ PlanDate, ForecastDate, FactDate
          ├─ PlanSum, ForecastSum, FactSum
          └─ ParentId: 4724 (InContract)
```

## View и фильтр

```python
mcp_call(sid, "get_view", {
    "entityName": "Point",
    "viewName": "AllFinancePoint",
    "filters": {"ProjectId": 4595},
    "limit": 50
})
```

⚠️ **Поддерживает только фильтр `ProjectId`** (как и `AllMyPoint`).

## Все View для Point (9 штук)

Из `list_views(entityName="Point")` на 2026-09-04:

| View | Title | Фильтры |
|---|---|---|
| `PointParameter` | Этапы / Работы / КТ\\Параметры объектов КП | `ProjectId` |
| `PointToMeToDo` | Мне на выполнение | `ProjectId` |
| `PointFromMe` | У меня на контроле | `ProjectId` |
| `MyAssignmentPoint` | Мои назначения | `ProjectId` |
| `AllPoint` | Все | `ProjectId` |
| `PointHealthDeadline` | Здоровье по срокам | `ActivityId` (multi-FK) |
| `AllMyPoint` | Все мои | `PortfolioId`, `ProjectId` |
| **`AllFinancePoint`** | **Все финансовые КТ** | **`ProjectId`** |
| `MyFinancePoint` | Мои финансовые КТ | `ProjectId` |

## Отличие от `AllMyPoint`

| Поле | `AllMyPoint` | `AllFinancePoint` |
|---|---|---|
| **ParentEntityName** | `Project` | **`InContract`** |
| Что возвращает | КТ уровня проекта | Финансовые КТ (привязанные к контрактам) |
| Где используется | 6.3, 6.4 (трудозатраты), раздел 3 (КТ сроки) | **6.8 (финансовые КТ)**, проверка Δ актов/оплат |
| Code | `104-714` (управленческие) | `104-732` (финансовые) |
| Поле `PlanDate` / `ForecastDate` | да | да |

## Поля в AllFinancePoint (на 2026-09-04)

```
Code, Name, PlanDate, ForecastDate, FactDate,
PlanSum, ForecastSum, FactSum,
ParentActivity, ParentCode, ParentEntityName, ParentId,
MyRole, ParentsRole, Owner, OwnerId,
Responsible, ResponsibleId,
PointId, PointLevel, PointLevelId, PointTagName, PointType, PointTypeId,
PortfolioId, PortfolioIds,
StartFactDate, StartForecastDate, StartPlanDate,
IndicatorColor, IndicatorId, IndicatorOrder, IndicatorTitle,
pcdColor, pcdId, pcdName, pcdTitle,
id, approvingdocumentid, AdditionalAgreement, ApprovingDocument
```

## Применение в skills

### fst-project-health (6.8)

Используется в `project_indicators.py::check_financial_deadlines`:

```python
rows = fetch_with_cache(
    sid, "Point", "AllFinancePoint",
    filters={"ProjectId": project_id},
    project_id=project_id, limit=200,
)

for row in rows:
    plan_date = _parse_iso_date(row.get("PlanDate"))
    forecast_date = _parse_iso_date(row.get("ForecastDate"))
    fact_date = _parse_iso_date(row.get("FactDate"))

    # Просрочена: forecast_date < today AND факта нет
    if not forecast_date or forecast_date >= today:
        continue
    if fact_date is not None:
        continue

    diff = (today - forecast_date).days
    # severity: ≥10 critical, ≥2 substantial, ≥1 informational
```

### project-payment-schedule

⚠️ **Важно для project-payment-schedule:** скилл сейчас работает через
`get_entity_data` для каждого контракта (медленно, +N запросов). Можно
**оптимизировать** через `AllFinancePoint`:

```python
points = mcp_call(sid, "get_view", {
    "entityName": "Point",
    "viewName": "AllFinancePoint",
    "filters": {"ProjectId": project_id},
    "limit": 1000,
}).get("data", [])

for p in points:
    # PlanSum, ForecastSum, FactSum уже здесь — не нужен get_entity_data
    p_name = (p.get("Name") or "").lower()
    if "акт" in p_name:
        # Это акт
        act_sum += effective_sum(p)
    elif "оплат" in p_name or "платёж" in p_name:
        # Это оплата
        pay_sum += effective_sum(p)

def effective_sum(p):
    fact = p.get("FactSum") or 0
    fc = p.get("ForecastSum") or 0
    return fact if fact > 0 else fc
```

⚠️ Эта оптимизация **не применена** в `project-payment-schedule` (на 2026-09-04),
но может быть полезна для ускорения. См. SKILL Pitfall #214.

## Связанные Pitfall'ы

- **#214** (fst-project-health) — правильный view для 6.8 — `Point/AllFinancePoint`,
  НЕ `InContractBudgetBusiness`.
- **#216** — иерархия `Project → InContract → Point` для финансовых КТ.
- **#217** — `AllMyPoint ≠ AllFinancePoint` (не путать!).
- **#224** — MCP probe ОБЯЗАТЕЛЕН при смене источника данных индикатора.

## Как был найден

```bash
# 1. list_views чтобы найти кандидаты
python3 -c "
from mcp_config import mcp_init, mcp_call
sid, _ = mcp_init()
resp = mcp_call(sid, 'list_views', {'entityName': 'Point'})
for v in resp:
    print(v.get('ViewName'), '|', v.get('Title'))
"

# Результат:
# PointParameter | Этапы / Работы / КТ\Параметры объектов КП
# ...
# AllFinancePoint | Этапы / Работы / КТ\Все финансовые КТ  ← ЭТО!
# MyFinancePoint   | Этапы / Работы / КТ\Мои финансовые КТ
```

Подробный рецепт probe — `references/mcp-live-probe-cookbook.md`.
</content>