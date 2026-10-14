---
name: project-payment-schedule
description: "Use when the user wants to see the payment schedule (график платежей) for a specific Foresight PM Practice project, asks 'когда платежи', 'график платежей', 'payment schedule', 'платежи проекта', 'бюджет по месяцам', or needs to plan/forecast cash flow. Reads Payments entity filtered by project's Activities, groups by month, returns cumulative total and per-contractor breakdown. Also covers correctness of payment schedule (сверка план/факт актов и оплат по контракту)."
version: 1.4.0
author: Hermes Agent + Rost
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [mcp, pmpractice, foresight, payment, schedule, finance, budget, ru, view-discovery]
    related_skills: [fst-pmpractice, project-search, project-timing-control, project-effort-analysis, fst-project-health]
---

# Project Payment Schedule (project-payment-schedule)

## Overview

Скилл для получения **графика платежей по проекту Форсайт ПМ Практики** и для
**проверки корректности грифика** (сведение план/факт актов и оплат по контракту).
Загружается, когда пользователь спрашивает:

- «Покажи платежи по проекту»
- «График платежей проекта»
- «Когда платежи?»
- «Бюджет проекта по месяцам»
- «Cash flow по проекту X»
- «Корректность грифика платежей»
- «Сравнение актов и оплат по контракту»

## When to Use

Загружай, когда пользователь:
- Просит показать платежи по конкретному проекту
- Хочет cash-flow / бюджет по месяцам
- Упоминает «график платежей», «когда оплаты», «платёжный календарь»
- Спрашивает про корректность грифика платежей, сведение актов и оплат

**Не загружай** для получения финансовых лимитов / бюджета проекта (для этого есть
`ActivityFinanceLimit`, `ApprovedBudget`).

## ⚠️ ВАЖНО: для финансового здоровья проекта используй `ProjectHealthFostMy`

View **`ProjectHealthFostMy`** (Здоровье по стоимости) — это **UI-форма «Бюджет
проекта, руб.»**. 15 колонок. Включает в себя **все 4 потока** (оплаты
доход/расход план/факт + трудозатраты план/факт) и аргегатры по
окончанию проекта.

⚠️ **Если в отчёте нужна оценка фин.здоровья проекта** (Forecast < 0? Δ > 1 М?),
не считай вручную через Payments/IND — **используй `ProjectHealthFostMy`**.
Поля УЖЕ посчитывают:

- `Plan` = «Плановый» фин.результат (только план)
- `Forecast` = «Реальный» фин.результат (факт + проноз по незакрытым + трудозатраты)
- `deviation` = `Forecast − Plan`
- `Fact` = тек. фин.результат (inFact − outFact)

Это и есть «Плановый» и «Реальный» в понимании пользователя.
Подробный алгоритм — в `project-completeness-check/references/financial-status-indicators.md`.

## ⚠️ Архитектурная особенность: акты и оплаты — это КТ

⚠️ **В Форсайт акты и оплаты по контракту хранятся как КТ (PointContract)**, а не
как отдельные сущности. У каждой КТ есть поля `PlanSum`, `ForecastSum`, `FactSum`.

⚠️ **Связь контракт↔проект идёт через `InContractActivity` / `OutcomeContractActivity`**
(multi-FK на Activity), а не через `ParentId` (как в обычных сущностях). У одного
контракта может быть несколько проектов.

⚠️ **В строке view `InContractAll` поле `InContractActivity` = None** — для получения
привязки нужно делать `get_entity_data` для каждого контракта.

```
Project
  ├─ Activity (Id=4595)
  └─ InContract/OutcomeContract
       ├─ InContractActivity = [{value: 4595}]  # привязка к проекту
       └─ Point (конкретный акт/оплата)
            └─ ParentId = ActivityId контракта (Id=4724 для InContract 704-724)
            └─ PlanSum / ForecastSum / FactFund  # суммы в рублях
```

## ⚠️ v1.4.0 NEW: альтернатива `get_entity_data` для каждой КТ

⚠️ **Раньше:** для получения `PlanSum`/`ForecastSum`/`FactFund` каждой КТ
нужно было `get_entity_data` для каждой (медленно, +N запросов).

✅ **С 2026-09-04 (открытие из fst-project-health v1.0.11):** для финансовых КТ
есть **view `Point/AllFinancePoint`** — возвращает **КТ типа `point` с
`ParentEntityName="InContract"`** уже с полями `PlanSum`, `ForecastSum`,
`FactSum` БЕЗ дополнительных `get_entity_data`.

```python
# Вместо N вызовов get_entity_data — 1 запрос:
points = mfp__fst_pmpractice__get_view(
    entityName="Point",
    viewName="AllFinancePoint",
    filters={"ProjectId": project_id},
    limit=1000,
).get("data", [])

for p in points:
    name = (p.get("Name") or "").lower()
    plan = p.get("PlanSum") or 0
    fc = p.get("ForecastSum") or 0
    fact = p.get("FactSum") or 0
    effective = fact if fact > 0 else fc

    if "акт" in name:
        act_sum += effective
    elif "оплат" in name or "платёж" in name:
        pay_sum += effective
```

⚠️ **`AllFinancePoint` ≠ `AllMyPoint`:**
- `AllMyPoint` — КТ уровня проекта (`ParentEntityName=Project`). Управленческие КТ.
- **`AllFinancePoint` — финансовые КТ (parent=InContract).** Это то что нужно для платежей.

⚠️ **Применение в fst-project-health:** индикатор 6.8 «Соблюдение сроков
финансовых КТ» переписан на `AllFinancePoint` (раньше использовал
`InContractBudgetBusiness`, что давало «Акт-4724» вместо реальных КТ).
Подробности — `fst-project-health/references/point-allfinancepoint-view.md`.

## Parameters

```python
DEFAULT_FILTERS = {
    "is_project_only": True,
    "include_zero_sum": False,
    "date_from": None,
    "date_to": None,
}
DEFAULT_GROUPING = "month"          # "month" | "quarter" | "year"
DEFAULT_SORT = "date_ing"
```

## Алгоритм работы (основной — график платежей)

⚠️ **Важная арфитектурная особенность Форсайт:** у `Payments` **нет прямого FK
на Project** — только на `Activity**. Стандарратный путь: **Project → Activity → Payments**.

```
1. ОПРЕДЕЛИТЬ ПРОЕКТ
   A: ProjectId → напрямую
   B: Code → get_view(Project, MyProject), фильтр по Code
   C: часть Name → уточнить (см. project-search)
   Извлечь: ProjectId, Name, Code

2. ПОЛУЧИТЬ СПИСОК ActivityId ПРОЕКТА (обходной путь через Point view)
   point_view = mfp__fst_pmpractice__get_view(
       entityName="Point", viewName="AllMyPoint"
   )
   activity_ids = set()
   for r in point_view["data"]:
       if str(r.get("ParentCode", "")).strip() == "<project_code>":
           activity_ids.add(r.get("ParentId"))

3. ПОЛУЧИТЬ ПЛАТЕЖИ
   get_view(Payments, AllPayments)
   fallback: get_view(Payments, MyPayments)

4. ОТФИЛЬТРОВАТЬ
   для каждого платежа:
   • if ActivityId в списке из шага 2 → оставить
   • if is_project_only и IsProject==False → исключить
   • if not include_zero_sum и SumRub==0 → исключить
   • date / contractor filters

5. СГРУППИРОВАТЬ ПО МЕСЯЦМ
6. ПОСЧИТАТЬ НАРАСТАЮЩИЙ ИТОГ
7. СФОРНИРОВАТЬ ОТЧЁТ
```

⚠️ **В строке view `Payments` (AllPayments) нет поля `ActivityId`** — фильтровать
нужно через подстроку в `ActivityName` (формат `"<code>. <name>"`). В этом скилле
это сделано через `startswith(r["ActivityName"], "<project_code>")`.

##Ингоритм: Проверка корректности грифика платежей проекта

Это отдельный сценарий: показатель «Корректность заполнения грифика платежей проекта»
(Δ_project между Σ актов и Σ оплат, с порогами 100 тыс / 1 млн руб.).

⚠️ **Показатель на уровне ПРОЕКТА**, а не контракта. К проекту может быть
привязано несколько контрактов через `InContractActivity`/`OutcomeContractActivity`.
Для каждого контракта считаем Δ_contract, затем **складываем АБСОЛЮТНЫЕ Δ** по
всем контрактам → Δ_project.

⚠️ **Смешанная логика сумм:** для каждой КТ (акта/оплаты) `effective_sum =
FactFund if FactFund > 0 else ForecastFund`. Это покрывает случаи, когда часть
актов уже выполнена (факт), а часть — только запланирована (прогноз).

```
1. Получить все контракты проекта:
   in_contracts = []
   ic_all = get_view(InContract, InContractAll, limit=1000)
   for c in ic_all.data:
       detail = get_entity_data(InContract, data_id=str(c.InContractId))
       ica = detail.properties.InContractActivity.value or []
       if any(a.value == <project_activity_id> for a in ica):
           in_contracts.append(detail)

   oc_all = get_view(OutcomeContract, OutcomeContractAll, limit=1000)
   for c in oc_all.data:
       detail = get_entity_data(OutcomeContract, data_id=str(c.OutcomeContractId))
       oca = detail.properties.OutcomeContractActivity.value or []
       if any(a.value == <project_activity_id> for a in oda):
           out_contracts.append(detail)

2. Получить все КТ контрактов (акты/оплаты):
   # ⚠️ РЕКОМЕНДАЦИЯ v1.4.0: использовать AllFinancePoint вместо AllMyPoint
   # (возвращает финансовые КТ с parent=InContract + поля PlanSum/ForecastSum/FactSum
   #  без необходимости get_entity_data для каждой КТ)
   points = get_view(Point, AllFinancePoint, filters={"ProjectId": project_id}, limit=1000).data

   # Старый способ (с get_entity_data для каждой КТ):
   # points = get_view(Point, AllMyPoint, limit=3000).data

   для каждого контракта:
       contract_points = [p for p in points
                         if str(p.get("ParentCode", "")).strip() == contract.Code]
       # Разделить по имени
       acts = [p for p in contract_points if "Акт"  in (p.get("Name") or "")]
       pays = [p for p in contract_points if "Оплат" in (p.get("Name") or "")
                                           or "Платёж" in (p.get("Name") or "")]

3. Получить суммы каждой КТ:
   # С AllFinancePoint — сразу из view (без get_entity_data):
   effective_sum(p) = p.get("FactSum", 0) if p.get("FactSum", 0) > 0 else p.get("ForecastSum", 0)

   # Старый способ (с get_entity_data):
   # detail = get_entity_data(Point, data_id=str(p.PointId))
   # effective_sum(p) = FactFund if FactFund > 0 else ForecastFund

4. Для каждого контракта:
       delta_c = |Σ актов_effective − Σ оплат_effective|
       total_delta += delta_c

5. Вердикт:
       if total_delta == 0: result = "Да"
       elif total_delta < 100_000: result = "Нет/Информационное замечание"
       elif total_delta < 1_000_000: result = "Нет/Существенное замечание"
       else: result = "Нет/Критическое замечание"
```

⚠️ **Складываем АБСОЛЮТНЫЕ дельты** — расхождения по разным контрактам не
компенсируют друг друга.

```python
THICRETH_THRESHOLDS = {
    "information": 100_000,
    "substantial": 1_000_000,
}
```

## Структура отчёта

### График платежей

```markdown
# График платежей проекта <Name>

> Составлено: <дата>
> Проект: <Name> (Code=<code>, ProjectId=<id>)
> Период: с <date_from> по <date_to>
> Всего платежей: <count>
> Общая сумма: <sum> руб.

## Сводка по месяцам

|  Месяц   | Кол-во| Сумма, руб   | Контрагенты                  | Нарастающий итог |
|----------|------|---------------|-------------------------------|------------------|
| 2026-01  |  3   | 1,500,000.00  | ПАО Банк ПСБ, ООО «Рога и Копыта» |   1,500,000.00 |
```

### Корректность грифика платежей

```markdown
| # | Показатель | Результат | Деталь |
|---|------------|-----------|--------|
| N | Корректность заполнения грифика платежей проекта | Да/Нет[статус] | Δ_project = X ₽ по M контрактам |
```

Где:
- `Δ_project = 0` → **Да**
- `Δ_project < 100_000` → **Нет/Информационное замечание**
- `Δ_project < 1_000_000` → **Нет/Существенное замечание**
- `Δ_project ≥ 1_000_000` → **Нет/Критическое замечание**

## Пример вызова (основной график)

```python
projects = mfp__fst_pmpractice__get_view(
    entityName="Project", viewName="MyProject"
).data
project = next(p for p in projects if p.Code == "504-595")

activities = mfp__fst_pmpractice__get_view(
    entityName="Activity", viewName="..."
).data
activity_ids = [a.ActivityId for a in activities if a.ProjectId == project.ProjectId]

all_payments = mfp__fst_pmpractice__get_view(
    entityName="Payments", viewName="AllPayments"
).data

payments = [p for p in all_payments if p.ActivityId in activity_ids]

from collections import defaultdict
by_month = defaultdict(lambda: {"sum": 0, "count": 0, "contractors": set()})
for p in payments:
    month = p.Date[:7]
    by_month[month]["sum"] += float(p.SumRub)
    by_month[month]["count"] += 1
    by_month[month]["contractors"].add(p.ContractorName)

cumulative = 0
for month in sorted(by_month):
    cumulative += by_month[month]["sum"]
    by_month[month]["cumulative"] = cumulative
```

## Пример вызова (проверка корректности)

```python
INDIFF_THRESHOLDS = {"information": 100_000, "substantial": 1_000_000}

# 1. Контракты проекта
in_contracts = []
ic_all = mfp__fst_pmpractice__get_view(
    entityName="InContract", viewName="InContractAll", limit=1000)
for c in ind_all.data:
    detail = mfp__fst_pmpractice__get_entity_data(
        entityName="InContract", data_id=str(c["InContractId"]))
    if any(a.get("value") == 4595 for a in (detail["properties"]["InContractActivity"]["value"] or [])):
        in_contracts.append(detail)

# 2. КТ контрактов (РЕКОМЕНДАЦИЯ v1.4.0: AllFinancePoint)
points = mfp__fst_pmpractice__get_view(
    entityName="Point", viewName="AllFinancePoint",
    filters={"ProjectId": project_id},
    limit=1000,
).get("data", [])
income_codes = {c["properties"]["Code"]["value"] for c in in_contracts}

total_delta = 0
for contract in in_contracts:
    code = contract["properties"]["Code"]["value"]
    contract_points = [p for p in points if str(p.get("ParentCode", "")).strip() == code]

    act_sum = pay_sum = 0
    for p in contract_points:
        # С AllFinancePoint — поля уже здесь:
        name = (p.get("Name") or "").lower()
        fact = float(p.get("FactSum") or 0)
        fc = float(p.get("ForecastSum") or 0)
        effective = fact if fact > 0 else fc
        if "акт" in name:
            act_sum += effective
        elif "оплат" in name or "платёж" in name:
            pay_sum += effective

    total_delta += abs(act_sum - pay_sum)

if total_delta == 0:
    result = "Да"
elif total_delta < INDDIFF_THRESHOLDS["information"]:
    result = "Нет/Информационное замечание"
elif total_delta <INDDIFF_THRESHOLDS["substantial"]:
    result = "Нет/Существенное замечание"
else:
    result = "Нет/Критическое замечание"
```

## Edge cases

| Случай | Поведение |
|--------|-----------|
| У проекта нет ни одного Activity | Сообщить пользователю |
| У проекта нет ни одного платежа | Таблица пустая |
|У проекта несколько контрактов | Складываем дельты по всем (при фofided) |
|`ActivityId` в строке view `Payments` не виден | Фильтровать через подстроку в `ActivityName` (`startswith(r["ActivityName"], "<project_code>")`) |
|Платежи с `SumRub=null` | Считать как 0 |
|Платежи с `Date=null` | В группу «без даты» |
|🔴 **`InContractActivity` приходит только через `get_entity_data`**, не через view | Не пытайся фильтровать по этому полю из строки view — там оно `None` |
|🔴 **В view `Payments` нет поля `ActivityId`** | Используй `ActivityName` (формат `<code>. <name>`) для фильтрации |
|🔴 **ResourcePlanning* view** 403 | Используй альтернативу: `Project.ProjectBudgetGrade`, `Point.PlanFund` |
|🆕 **Использовать `AllFinancePoint` для финансовых КТ** | `AllMyPoint` возвращает КТ уровня проекта, `AllFinancePoint` — привязанные к контрактам (parent=InContract) |

## Verification Checklist

- [ ] Project найден
- [ ] ActivityId проекта получен
- [ ] Все платежи получены
- [ ] Фильтр применён
- [ ] Группировка и нарастающий итог корректны
- [ ] Для корректности: все контракты перебраны, Δ для каждого посчитан, Δ_project = Σ Δ
- [ ] v1.4.0+: используется `AllFinancePoint` для финансовых КТ (не `AllMyPoint`)

## Связь с другими скиллами

- **Базовый:** `fst-pmpractice` — формат вызовов, pitfall #14 (naming conventions), indfall #19 (save_entity для ResourcePlanningKp тихо не обновляет)
- **Поиск проекта:** `project-search`
- **Анализ сроков:** `project-timing-control`
- **Бюджет:** `fst-pmpractice/references/project-finance-budget-entities.md` — карта финансовых сущностей Форсайт с обходом 403 (загружай когда задача про бюджет/контракты/финансы)
- **Архитектура:** `fst-pmpractice/references/project-architecture.md`
- **Скилл отчёта о здоровье:** `fst-project-health` — также использует `Point/AllFinancePoint` (индикатор 6.8). См. `fst-project-health/references/point-allfinancepoint-view.md`.

## Будущие расширения

- Оптимизация через `AllFinancePoint` (см. ⚠️ секция выше) — НЕ применена в скилле, но может ускорить с N+1 запросов до 1 запроса для проектов с большим числом КТ.
- Экспорт в CSV / Excel
- Графики (matplotlib) с timeline платежей
- Связь с этапами проекта
- Прогноз будущих платежей
- Уведомления о приближающихся сроках

## История изменений

- **v1.4.0** — **Добавлена рекомендация: использовать view `Point/AllFinancePoint`**
  вместо `AllMyPoint` + `get_entity_data` для каждой КТ. Это **открытие 2026-09-04**
  из скилла `fst-project-health` v1.0.11 (Pitfall #214, #217). С `AllFinancePoint`
  получаем финансовые КТ с полями `PlanSum`/`ForecastSum`/`FactSum` одним запросом.
  ⚠️ Рекомендация НЕ реализована в коде скилла — только документирована как
  будущая оптимизация.
- **v1.3.0** — **Добавлен критический indfall: view `ProjectHealthFostMy` — это
  и есть ID-форма «Бюджет проекта, руб.»**. Ранее в скилле собирали финансы
  вручную через Payments/IND, что было рудиментально лишнимм. Теперь
  подсчёт финансового здоровья (Forecast < 0, deviation > 1М) делается через
  view. Ссылка на подробный алгоритм в
  `project-completeness-check/references/financial-status-indicators.md`.
- **v1.2.0** — обновлён алгоритм проверки корректности графика: проект-уровневая
  агрегация через `InContractActivity`/`OutcomeContractActivity` (multi-FK),
  смешанная `Effective_sum = FactFund if >0 else ForecastFund`, складываем
  абсолютные Δ по всем контрактам.
- **v1.0.0** — первая публикация.