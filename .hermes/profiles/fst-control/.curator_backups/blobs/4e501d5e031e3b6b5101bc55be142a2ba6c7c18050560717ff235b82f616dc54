# Привязка контракт↔проект в Форсайт — через `ParentFullName`, не через `InContractActivity`

> Зафиксировано 2026-08-05 при отладке `fst-project-health` против проекта
> `504-595` (ProjectId=4595). Контракт `704-724` был привязан к проекту,
> но фильтр через `InContractActivity` молча возвращал 0.

## TL;DR

В строках view `InContractMyProject` и `OutcomeContractMyProject` поля
`InContractActivity` **НЕТ**. Оно появляется только в ответе
`get_entity_data(InContract, data_id=<id>)`. Для массовой фильтрации
используй строковое поле `ParentFullName` формата
`"<project_code>. <project_name>"`.

## Live-repro (проект 504-595)

### Запрос через view

```python
view = mcp__fst_pmpractice__get_view(
    entityName="InContract", viewName="InContractMyProject"
)
# view["data"] — 5 строк. Среди них контракт 704-724:
contract = next(r for r in view["data"] if r["Code"] == "704-724")
print(contract.keys())
# dict_keys(['id', 'InContractId', 'IndicatorId', 'IndicatorTitle',
#            'Code', 'Number', 'Name', 'ContractTypeName',
#            'StartPlanDate', 'FinishPlanDate', 'PlanSum', 'RealSum',
#            'ContractorName', 'ActivityPhaseName', 'ParentFullName',
#            'ConclusionDate'])
#                         ^^^^^^^^^^^^^^^^
#                         Это поле и есть привязка к проекту.
print(contract["ParentFullName"])
# '504-595. Космодром Жуковский внедрение ИСУП '   # ← с пробелом на конце
print(contract.get("InContractActivity"))
# None                                              # ← ключа нет!
```

### Запрос через `get_entity_data` (тот же контракт)

```python
detail = mcp__fst_pmpractice__get_entity_data(
    entityName="InContract", data_id="4724"
)
print(detail["properties"]["InContractActivity"]["value"])
# [{"value": 4595, "display": null}]                # ← вот тут оно есть
```

## Правильный фильтр

```python
def contract_belongs_to_project(row, project_code: str) -> bool:
    """Фильтр контрактов проекта по ParentFullName в view."""
    parent_full = (row.get("ParentFullName") or "").strip()
    if not parent_full:
        return False
    return parent_full.startswith(f"{project_code}.")
```

```python
PROJECT_CODE = "504-595"

# InContract (доходные)
ic = mcp__fst_pmpractice__get_view(
    entityName="InContract", viewName="InContractMyProject"
)["data"]
in_contracts = [c for c in ic if contract_belongs_to_project(c, PROJECT_CODE)]

# OutcomeContract (расходные)
oc = mcp__fst_pmpractice__get_view(
    entityName="OutcomeContract", viewName="OutcomeContractMyProject"
)["data"]
out_contracts = [c for c in oc if contract_belongs_to_project(c, PROJECT_CODE)]
```

## Почему так, а не иначе

В Форсайт view (агрегаты) оптимизированы для UI — показывают только
те колонки, которые нужны для отображения списка. `InContractActivity`
это MultiSelectField со списком ActivityId; для UI он не нужен, поэтому
view его не отдаёт. Полные данные — через `get_entity_data`, но это
N+1 (по запросу на каждый контракт).

Для массовых операций (фильтрация «какие контракты у проекта»)
`ParentFullName` — это **денормализованное строковое представление**
связи, специально для UI. Оно формируется на стороне Форсайт и его
парсить — это **поддерживаемый контракт**, не хак.

## Неправильный фильтр (тот что даёт 0 контрактов)

```python
# ❌ НЕПРАВИЛЬНО — InContractActivity в view нет
project_activity_ids = {project["ActivityId"]}  # = {4595}
contracts = []
for c in ic_view["data"]:
    ica = c.get("InContractActivity") or []  # ← всегда []
    if any(a.get("value") in project_activity_ids for a in ica):  # ← никогда True
        contracts.append(c)
# → []
```

Это и был оригинальный код в `Payments-graph-check.py` v0.1.0.
Молча возвращал 0, не падал с ошибкой. После исправления — 1 контракт
(704-724), `RealSum=5 400 000 ₽`, 6 КТ (3 акта + 3 оплаты), Δ = 0 ₽.

## Когда всё-таки нужен `InContractActivity` через `get_entity_data`

Только если тебе нужны **точные `ActivityId` контракта** (например,
для привязки `ResourcePlanning`, которая идёт через `ActivityId`,
не через `ParentCode`). Тогда делай отдельный
`get_entity_data(InContract, data_id=<InContractId>)` на каждый
контракт — это и есть N+1, медленно но точно.

В `fst-project-health` это не нужно: для раздела 4 показателя 5 и
раздела 6 показателя 2 достаточно `ParentFullName` + КТ по
`ParentCode`.

## Verification Checklist

- [ ] Фильтр `contract_belongs_to_project(row, code)` возвращает `True` для контрактов, привязанных к проекту `code`
- [ ] `ParentFullName` имеет формат `<code>. <name>` (с точкой-разделителем)
- [ ] `.strip()` применён — `ParentFullName` оканчивается пробелом
- [ ] Проверено: фильтр через `InContractActivity` для view возвращает 0 (не должен использоваться для массовых операций)

## История

- **2026-08-05** — находка при отладке `fst-project-health` против
  проекта 504-595. Оригинальный `Payments-graph-check.py` давал
  `Контрактов: 0`. После переключения на `ParentFullName` —
  `Контрактов: 1` (код 704-724, АО ЦентрКосмодромСтрой, RealSum 5.4 млн).
  Занесено в `fst-pmpractice` SKILL.md (pitfall #21) и в
  `fst-project-health` SKILL.md (Hard rule).
