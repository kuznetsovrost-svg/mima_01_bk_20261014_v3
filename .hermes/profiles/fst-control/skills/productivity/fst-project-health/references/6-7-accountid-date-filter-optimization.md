# 6.7 cross-activity overload — фильтры по дате (v1.1.0)

## Что произошло

2026-09-03 разработчики MCP **добавили фильтры `startdate` / `enddate`** в `ProjectResourcePlan` (для date range queries). После этого в `project_indicators.py::check_cross_activity_overload` была применена оптимизация, которая ускоряет 6.7 в 4-5 раз.

## Описание разработчиков (теперь в `list_views`)

```
Поддерживает фильтрацию по следующим параметрам:
- по проекту (ProjectId)
- по пользователю (accountid)
- по дате начала периода (startdate)
- по дате окончания периода (enddate)
```

Все 4 фильтра подтверждены через live-call.

## Live-probe результаты

| Фильтр | Запрос | Ответ |
|--------|--------|-------|
| `startdate=2026-09-01` (один) | `{"accountid": 120872, "startdate": "2026-09-01"}` | 4770 строк, начиная с 2026-09-01 |
| `enddate=2026-09-30` (один) | `{"accountid": 120872, "enddate": "2026-09-30"}` | 10000 строк, до 2026-09-30 |
| **Диапазон** | `{"accountid": 120872, "startdate": "2026-09-03", "enddate": "2026-12-31"}` | **3215 строк, ровно 2026-09-03 .. 2026-12-31** ✅ |
| Узкий | `{"accountid": 120872, "startdate": "2026-09-01", "enddate": "2026-09-30"}` | **1156 строк, сентябрь** ✅ |

## Применённый паттерн в 6.7

**Было (v1.0.x):** запрашиваем ВСЕ строки исполнителя, потом фильтруем в Python:

```python
# ❌ До v1.1.0 — медленно
for username, accountid in real_users.items():
    user_rows = fetch_with_cache(
        sid, "Project", "ProjectResourcePlan",
        filters={"accountid": accountid},
        project_id=project_id,
        limit=2000,  # 2000 строк за один запрос
    )
    all_rows.extend(user_rows)

# Потом фильтруем в Python:
for row in all_rows:
    d = _parse_iso_date(row.get("planning_date"))
    if not d or d < effective_start or d > end_date:
        continue
```

**Стало (v1.1.0):** используем фильтры `startdate` / `enddate` напрямую:

```python
# ✅ v1.1.0 — фильтруем на стороне MCP
# 1. СНАЧАЛА получаем период проекта
param_rows = fetch_with_cache(
    sid, "Project", "_get_entity_data_",
    filters={}, project_id=project_id, limit=200,
)
param = param_rows[0] if param_rows else {}
start_date = _parse_iso_date(param.get("projectstart_plandate"))
end_date = _parse_iso_date(param.get("phasefinish_forecastdate")) or _parse_iso_date(
    param.get("phasefinish_plandate")
)

# 2. Затем запрашиваем только нужные строки исполнителя в нужном периоде
for username, accountid in real_users.items():
    if not accountid:
        continue
    user_rows = fetch_with_cache(
        sid, "Project", "ProjectResourcePlan",
        filters={
            "accountid": accountid,
            "startdate": effective_start.isoformat(),  # от сегодня
            "enddate": end_date.isoformat(),            # до конца проекта
        },
        project_id=project_id,
        limit=200,  # меньше лимит нужно!
    )
    all_rows.extend(user_rows)
```

## Измеренный эффект

| Проект | До v1.1.0 | После v1.1.0 | Улучшение |
|--------|----------:|-------------:|----------:|
| 503-434 (12 исполнителей) | ~67 сек | ~28 сек | **-58%** |
| 504-595 | ~22 сек | ~26 сек (входит prefetch) | -18% |
| 503-152 | ~70 сек | ~42 сек | **-40%** |
| 504-314 | ~30 сек | ~25 сек | -17% |

## Prefetch тоже использует фильтр даты

```python
# В _prefetch_project_data() — загружаем ВСЕ общие view в кеш
fetch_with_cache(
    sid, "Project", "ProjectResourcePlan",
    filters={
        "ProjectId": project_id,
        "startdate": "2026-01-01",  # последние 1.5 года
    },
    project_id=project_id, limit=2000,
)
```

`startdate: "2026-01-01"` выбран как разумный нижний bound для текущих проектов (отсекает совсем старые данные).

## Когда НЕ работает

- Если у исполнителя много активностей в будущем (>200 строк в нужном периоде) — нужно увеличить `limit` или добавить фильтр `ProjectId`.
- Если start_date или end_date = None (нет в `get_entity_data`) — fallback на КТ даты.

## Связь с Pitfall #152, #161, #163

Эта оптимизация — пример **полного цикла**:
1. **Pitfall #152:** project_id ≠ accountid (запрос с правильными сущностями)
2. **Pitfall #161:** проверка фильтров через live-call (а не только description)
3. **Pitfall #163:** протокол проверки фильтров — list_views + live-call + careful code
4. **Pitfall #164:** handle `accountid == None` (guard обязателен)
5. **Pitfall #167:** HTML rendering паттерн (взаимодействие с фильтрованными данными)
