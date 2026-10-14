# View `Point/AllFinancePoint` для 6.8 (просроченные финансовые КТ)

**Pitfalls:** #214 (правильный view), #216 (иерархия), #217 (не путать с AllMyPoint).

## Зачем

До v1.0.11 индикатор 6.8 «Соблюдение сроков финансовых КТ» использовал
**`InContractBudgetBusiness`** — там были **финансовые сущности** (Акты,
Оплаты) с внутренними ID типа «Акт-4724», «Оплата-4724». Это не КТ
проекта — а пользователь хочет видеть именно КТ (`104-XXX`).

Правильный view — **`Point/AllFinancePoint`** с фильтром `ProjectId=<id>`.
Возвращает КТ типа `point` с `ParentEntityName="InContract"`.

## Probe-рецепт

```python
from mcp_config import mcp_init, mcp_call

sid, _ = mcp_init()
resp = mcp_call(sid, 'list_views', {'entityName': 'Point'})
# resp = [
#   {"ViewName": "PointParameter", ...},
#   {"ViewName": "PointToMeToDo", ...},
#   {"ViewName": "PointFromMe", ...},
#   {"ViewName": "MyAssignmentPoint", ...},
#   {"ViewName": "AllPoint", ...},
#   {"ViewName": "PointHealthDeadline", ...},
#   {"ViewName": "AllMyPoint", ...},            # ← НЕ для 6.8
#   {"ViewName": "MyFinancePoint", ...},         # только для меня
#   {"ViewName": "AllFinancePoint", ...},        # ← ДЛЯ 6.8
# ]

resp = mcp_call(sid, 'get_view', {
    'entityName': 'Point',
    'viewName': 'AllFinancePoint',
    'filters': {'ProjectId': 4595},
    'limit': 50,
})
rows = resp.get('data', [])
```

## Структура строки (504-595, реальный probe 2026-09-04)

| Поле | Значение | Комментарий |
|---|---|---|
| `Code` | `104-732` | Код КТ в формате `NNN-NNN` |
| `Name` | `Акт по 2-му блоку работ подписан` | Наименование |
| `PlanDate` | `2026-08-21T00:00:00+03:00` | ISO 8601 |
| `ForecastDate` | `2026-08-21T00:00:00+03:00` | ISO 8601 |
| `FactDate` | `None` | Нет факта = потенциально просрочена |
| `PlanSum` | `1500000.0` | Плановая сумма (для справки) |
| `ForecastSum` | `1500000.0` | Прогнозная сумма (для справки) |
| **`ParentEntityName`** | **`InContract`** | **ГЛАВНЫЙ признак** для 6.8 |
| `ParentActivity` | `704-724. Контракт на разработку ИСУП для ТЛК "Космодром Жуковский"` | Имя контракта |
| `ParentId` | `4724` | ID контракта |
| `PointId` | `4732` | Уникальный ID КТ |
| `PointType` | `None` (или не заполнен) | Тип КТ |
| `IndicatorColor` | `#ff5940` | Цвет индикатора просрочки |
| `IndicatorTitle` | `Просрочено` | Уже посчитанный статус |

## Условие «просрочена» (Pitfall #216)

```python
from datetime import date, datetime

def parse_iso(s):
    if not s:
        return None
    return datetime.fromisoformat(s.replace('Z', '+00:00')).date()

today = date.today()
overdue = []
for r in rows:
    fcst = parse_iso(r.get('ForecastDate'))
    fact = parse_iso(r.get('FactDate'))
    if fcst and not fact and fcst < today:
        diff = (today - fcst).days
        overdue.append({
            'code': r['Code'],
            'name': r['Name'],
            'plan': r['PlanDate'][:10] if r.get('PlanDate') else '',
            'forecast': r['ForecastDate'][:10] if r.get('ForecastDate') else '',
            'diff': diff,
            'severity': classify_financial_delay(diff, cfg),
        })
```

## Сравнение с AllMyPoint

| | `AllMyPoint` | `AllFinancePoint` |
|---|---|---|
| Назначение | КТ уровня проекта (трудозатраты) | Финансовые КТ (акты/оплаты) |
| `ParentEntityName` | `Project` | `InContract` |
| Используется в | 6.3, 6.4 (просрочки трудозатрат) | **6.8 (просрочки фин. КТ)** |
| `IndicatorTitle` | `Просрочено` / `В работе` / т.д. | `Просрочено` (часто) |
| `PlanSum` / `ForecastSum` | (нет) | `1500000.0` и т.п. |

**Не путать!** Это две разные сущности в одной таблице `Point`, но
возвращаемые разными view'ами.

## Иерархия (для понимания структуры)

```
Проект (504-595, parent)
  └─ Контракт (704-724, InContract, parent = Project)
     └─ КТ (104-732, Point, parent = InContract) ← это в AllFinancePoint

vs.

Проект (504-595, parent)
  └─ КТ (104-714, Point, parent = Project) ← это в AllMyPoint
```

## Реализация в `check_financial_deadlines()`

```python
# В run_all.py / project_indicators.py
rows = fetch_with_cache(
    sid, "Point", "AllFinancePoint",     # ← заменили InContractBudgetBusiness
    filters={"ProjectId": project_id},
    project_id=project_id, limit=500,
)
# rows уже содержит только КТ с parent=InContract (по дизайну view'а)
# Не нужно фильтровать по ParentEntityName — он всегда InContract для этого view.
```

## Колонки таблицы 6.8 (Pitfall #215)

По правилу пользователя: «состав колонок должен соответствовать таблице
в секции "Замечания по срокам"»:

| # | Код | Наименование | План | Прогноз |

**БЕЗ** колонки «Δ дн» — это в секции 5 «Актуальность прогнозов».

`col_names_ru` в `build_html_report.py` уже содержит:
```python
"plan": "План", "forecast": "Прогноз", "diff": "Δ дн."
```

Для 6.8 колонки `diff` не используется — но и не нужно её специально
убирать (просто не добавляем `diff` в строки `overdue_rows`).
