# Проверка корректности графика платежей (Indicator 5)

> Подробный алгоритм + live-пример для проекта 504-595 / контракт 704-724.
> Зафиксировано в `SKILL-FST-HOWPROJET.md` v0.8 (2026-08-01).

## Уровень показателя

**Показатель на уровне ПРОЕКТА**, а не контракта. К проекту может быть
привязано **несколько контрактов** (через `InContractActivity` или
`OutcomeContractActivity`). Для каждого контракта считаем Δ отдельно,
затем **складываем дельты** — и сравниваем суммарную Δ с порогами.

## Архитектурные особенности Форсайт

⚠️ **Акты и оплаты в Форсайт — это КТ (Point)**, а не отдельные сущности.
Контракт `InContract` / `OutcomeContract` — это «корневая» КТ (ActivityId),
а его акты/оплаты — дочерние КТ (`ParentId` = `ActivityId` контракта).

⚠️ **Связь контракт ↔ проект** — через `InContractActivity` (multi) или
`OutcomeContractActivity` (multi), а **НЕ** через `ParentId` контракта.
`ParentId` указывает на портфель/вышестоящий объект.

`ContractPlanSummaries` / `ContractPlanSummariesValue` — **служебный агрегат**
для отчётности, а не первичный источник данных. Эти views закрыты 403 для
обычных пользователей, поэтому работаем через `Point`.

## Формула «эффективной суммы»

Для каждой КТ (акта или оплаты):

```
effective_sum = FactSum if FactSum > 0 else ForecastSum
```

Смысл: если КТ уже выполнена (факт > 0) — берём факт; если нет — берём прогноз.

## Полный алгоритм

```python
THRESHOLDS = {
    "informational": 100_000,
    "substantial": 1_000_000,
}

def effective_sum(point_props):
    """Берём FactSum если > 0, иначе ForecastSum."""
    fact = float(point_props.get("FactSum", {}).get("value") or 0)
    forecast = float(point_props.get("ForecastSum", {}).get("value") or 0)
    if fact > 0:
        return fact
    if forecast > 0:
        return forecast
    return 0

# 1. Найти проект и его ActivityId
projects = mcp__fst_pmpractice__get_view(entityName="Project", viewName="MyProject")
project = next(p for p in projects["data"] if p["Code"] == "504-595")
project_activity_ids = {project["ActivityId"]}

# 2. Найти ВСЕ контракты, привязанные к проекту
contracts = []

# 2a. InContract (доходные)
ic_view = mcp__fst_pmpractice__get_view(
    entityName="InContract", viewName="InContractMyProject"
)
for c in ic_view["data"]:
    ica = c.get("InContractActivity") or []
    if any(a.get("value") in project_activity_ids for a in ica):
        contracts.append({"type": "InContract", "id": c["id"], "code": c["Code"]})

# 2b. OutcomeContract (расходные)
oc_view = mcp__fst_pmpractice__get_view(
    entityName="OutcomeContract", viewName="OutcomeContractMyProject"
)
for c in oc_view["data"]:
    oca = c.get("OutcomeContractActivity") or []
    if any(a.get("value") in project_activity_ids for a in oca):
        contracts.append({"type": "OutcomeContract", "id": c["id"], "code": c["Code"]})

# 3. Загрузить все КТ
points_view = mcp__fst_pmpractice__get_view(
    entityName="Point", viewName="AllMyPoint", limit=3000
)

# 4. Посчитать Δ для каждого контракта, сложить
total_delta = 0
contract_results = []

for contract in contracts:
    code = contract["code"]
    contract_points = [
        p for p in points_view["data"]
        if str(p.get("ParentCode", "")).strip() == code
    ]

    act_sum = 0
    pay_sum = 0
    for p in contract_points:
        detail = mcp__fst_pmpractice__get_entity_data(
            entityName="Point", data_id=str(p["PointId"])
        )
        name = (detail["properties"].get("Name", {}).get("value") or "").lower()
        es = effective_sum(detail["properties"])
        if "акт" in name:
            act_sum += es
        elif "оплат" in name or "платеж" in name or "платёж" in name:
            pay_sum += es

    delta_c = abs(act_sum - pay_sum)
    total_delta += delta_c
    contract_results.append({
        "code": code,
        "acts": act_sum,
        "pays": pay_sum,
        "delta": delta_c
    })

# 5. Вердикт
if total_delta == 0:
    result = "Да"
    detail = f"Δ = 0 ₽ по {len(contracts)} контрактам"
elif total_delta < THRESHOLDS["informational"]:
    result = "Нет/Информационное замечание"
    detail = f"Δ = {total_delta:,.2f} ₽ (< 100 тыс.)"
elif total_delta < THRESHOLDS["substantial"]:
    result = "Нет/Существенное замечание"
    detail = f"Δ = {total_delta:,.2f} ₽ (100 тыс.–1 млн)"
else:
    result = "Нет/Критическое замечание"
    detail = f"Δ = {total_delta:,.2f} ₽ (> 1 млн)"
```

## Live-пример: проект 504-595 / контракт 704-724

**Источник контракта:** `find_entity("704-724")` → `InContract id=4724`,
`RealSum=5 400 000 ₽`, привязан через `InContractActivity=[{value: 4595}]`.

### Акты контракта (ParentCode=704-724)

| Code | Name | PlanSum | ForecastSum | FactSum | Берём | Сумма |
|------|------|---------|-------------|---------|-------|-------|
| 104-725 | Акт по 1-му блоку работ | 2 500 000 | 2 499 990 | 2 500 | **Fact** | 2 500 |
| 104-731 | Акт по 1-му блоку (доплата) | 2 497 500 | 2 497 500 | 2 497 500 | **Fact** | 2 497 500 |
| 104-732 | Акт по 2-му блоку работ | 1 500 000 | 1 500 000 | 0 | **Forecast** | 1 500 000 |
| **Σ актов** | | | | | | **4 000 000** |

### Оплаты контракта (ParentCode=704-724)

| Code | Name | PlanSum | ForecastSum | FactSum | Берём | Сумма |
|------|------|---------|-------------|---------|-------|-------|
| 104-726 | Оплата по 1-му блоку | 2 500 000 | 2 500 000 | 2 500 | **Fact** | 2 500 |
| 104-730 | Промежуточная оплата | 2 497 500 | 2 497 500 | 2 497 500 | **Fact** | 2 497 500 |
| 104-733 | Оплата по 2-му блоку | 1 500 000 | 1 500 000 | 0 | **Forecast** | 1 500 000 |
| **Σ оплат** | | | | | | **4 000 000** |

### Расчёт

```
Δ_contract(704-724) = |4 000 000 − 4 000 000| = 0 ₽
Δ_project = 0 ₽ (один контракт)
```

**Результат: Да** (корректно).

## ⚠️ Pitfall'ы

1. **Складываем абсолютные Δ** — не «сначала Σ актов минус Σ оплат». Если у одного
   контракта +5 млн, у другого −5 млн — суммарная Δ = 10 млн, не 0.
2. **Не путать `InContract` и `OutcomeContract`** — это разные сущности.
   Проверять обе.
3. **Связь через `InContractActivity`, не `ParentId`** — ParentId указывает на
   портфель (для 704-724 это `Портфель экспериментальных проектов`, ActivityId=4594).
4. **`FactSum` может быть `None`** — в КТ `104-732` и `104-733` факта ещё нет, поэтому
   берём `ForecastSum` (по правилу).
5. **Странность в данных 104-725/104-726**: `PctComplete=100` при `FactSum=2 500`
   (а не 2 500 000). Это значит, что Форсайт считает КТ завершённой по последнему
   траншу, а не по полной сумме. Алгоритм работает корректно, но **данные спорные** —
   стоит перепроверить в UI Форсайт.
6. **Медленный обход** — для каждой КТ нужно `get_entity_data`. На проекте с N
   контрактами × M КТ получается N×M запросов. Для больших проектов оптимизировать
   (например, через пагинацию `get_view` с `filters={"ParentId": contract_id}` если
   такая поддержка появится).
