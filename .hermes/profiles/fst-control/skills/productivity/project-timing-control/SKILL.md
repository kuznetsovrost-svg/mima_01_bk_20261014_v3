---
name: project-timing-control
description: "Use when the user asks about Foresight PM Practice project health by schedule, project diagnostics, timing remarks on КТ (контрольные точки), overdue/красный project status, project 'health', or wants a list of Points (control points) with PlanDate vs ForecastDate drift classification (Красный/Жёлтый/Синий → Критическое/Существенное/Информационное). Loads when user says: 'оцени здоровье проекта', 'анализ сроков', 'замечания по срокам', 'покажи замечания по проекту', 'project БОЛЕН / ТРЕБУЕТ ВНИМАНИЯ / ЗДОРОВ', 'timing remarks', 'почему проект красный'. Reads Point view, filters unfinished КТ, classifies by diff thresholds, optionally checks for Паспорт attachment, and reports aggregate project status with a Markdown report deliverable."
version: 2.0.0
changelog:
  - "2.0.0 (2026-09-01): MAJOR UPDATE. Migrated to standard `filters={...}` format. Live-probe 2026-09-01: `get_view({entityName: ..., viewName: ..., filters: {ProjectId: ...}, limit: 100})` works for all views. Replaces deprecated `mcp__fst_pmpractice__get_view` namespace and `?Field=value` URL format. See `references/mcp-filters-format.md` in `mcp-server-probing` skill.
author: Hermes Agent + Rost
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [mcp, pmpractice, foresight, project-management, schedule, deadline, delay, ru, diagnostics, report]
    related_skills: [fst-pmpractice, plan]
---

# Project Timing Control (project-timing-control)

## Overview

Скилл для оценки **здоровья проекта Форсайт ПМ Практики с точки зрения сроков**.
Загружается, когда пользователь хочет:

- Узнать, насколько проект «просрочен» (БОЛЕН / ТРЕБУЕТ ВНИМАНИЯ / ЗДОРОВ)
- Получить список замечаний по срокам его контрольных точек (Point)
- Классифицировать расхождения PlanDate vs ForecastDate по цветам
- Получить итоговый markdown-отчёт с исполнителями и ссылками

Анализирует сущности **Point** проекта и формирует два артефакта:

1. **Общую оценку здоровья проекта** по числу критических замечаний.
2. **Список замечаний по срокам** с цветовой кодировкой и статусами.

## Когда использовать

Загружай, когда пользователь:

- Просит «оценить здоровье проекта», «проанализировать сроки»
- Просит «замечания по срокам», «почему красный», «диагностика проекта»
- Хочет план-факт анализ по КТ (контрольным точкам) проекта
- Упоминает «Форсайт», «ИСУП», проект по Code/ProjectId

**Не загружай** для бытовых задач или проектов вне Форсайт.

## Parameters (пороги цветов и статусов)

Все пороги хранятся как **переменные**. Пользователь может их менять
явной просьбой («ужесточи критерии», «для этого проекта 1 критическое = БОЛЕН»).

### Пороги классификации замечания (по diff = `|ForecastDate - PlanDate|` дней)

```python
REMARK_THRESHOLDS = {
    "critical":      {"min_diff_days": 10, "color": "Красный",  "status": "Критическое"},
    "substantial":   {"min_diff_days": 2,  "max_diff_days": 10,
                      "color": "Желтый",   "status": "Существенное"},
    "informational": {"max_diff_days": 2,   "color": "Синий",    "status": "Информационное"},
}
```

Логика (строгие границы):
- `|diff| > 10` → Красный / Критическое
- `2 < |diff| ≤ 10` → Желтый / Существенное
- `0 ≤ |diff| ≤ 2` → Синий / Информационное

### Пороги оценки здоровья проекта (по числу критических)

```python
HEALTH_THRESHOLDS = {
    "sick":      {"min_critical_count": 3, "label": "БОЛЕН",            "color": "КРАСНЫЙ"},
    "attention": {"min_critical_count": 1, "max_critical_count": 2,
                  "label": "ТРЕБУЕТ ВНИМАНИЯ", "color": "ЖЕЛТЫЙ"},
    "healthy":   {"max_critical_count": 0, "label": "ЗДОРОВ",           "color": "—"},
}
```

Логика:
- `critical_count ≥ 3` → БОЛЕН (КРАСНЫЙ)
- `1 ≤ critical_count ≤ 2` → ТРЕБУЕТ ВНИМАНИЯ (ЖЕЛТЫЙ)
- `critical_count = 0` → ЗДОРОВ

### Дополнительные параметры (опционально)

```python
# Какой подтверждающий документ считать "правильным"
CONFIRMING_DOCUMENT = "паспорт"   # справочное значение

# Сортировка замечаний в выводе
REMARK_SORT = ["plan_date_asc", "diff_desc"]   # сначала по PlanDate, затем по убыванию diff
```

## ⚠️ Архитектурная особенность: как Point связаны с Project

В этом скилле фильтрация по проекту делается через поле `ParentCode` в строке
view `AllMyPoint`. Это работает, но важно понимать архитектуру Форсайт:

```
Project
  └─ Activity  ← реальный «контейнер» всех дочерних сущностей
       ├─ Point     (КТ привязаны к Activity, не напрямую к Project)
       ├─ Payments
       ├─ Risk
       └─ DocumentFile
```

⚠️ **Парадокс имён:** в схеме `Point` есть поле **`ProjectId`**, но **это FK
на `Activity`, не на `Project`**! Это историческое наследие Форсайт, когда Activity
и Project были одной сущностью. Поэтому фильтр `WHERE ProjectId = 4595` на самом
деле фильтрует по `ActivityId`.

### Что это значит для скилла

| Ситуация | Что делать |
|----------|-----------|
| Фильтр по `ParentCode` (как сейчас) | ✅ Работает для Point (есть в view) |
| Получить список `ActivityId` проекта | ❌ В публичном API нет прямого пути. Обходной — через `ParentId` в строках Point |
| Фильтр по `ProjectId` напрямую | ⚠️ Фильтрует по `ActivityId`, **не по `ProjectId`** — может вернуть данные других проектов, если у них тот же ActivityId |

### Способы фильтрации (по убыванию надёжности)

1. **`ParentCode == "<project_code>"`** в строке view — надёжно, используется сейчас
2. **`ProjectId` в схеме** — надёжно, но **в схеме, а не в строке view**
3. **JOIN через `ParentId` → `Activity`** — надёжно, но нужен список ActivityId

### Если нужно получить список `ActivityId` проекта

```python
view = mcp_call(sid, "get_view", {
    "entityName": "Point",
    "viewName": "AllMyPoint",
    "filters": {},
    "limit": 100,
})
activity_ids = {r["ParentId"] for r in view["data"] if r.get("ParentCode") == "<project_code>"}
# Использовать для фильтрации Payments, Risk и т.д.
```

Подробнее см. секцию «Архитектура связей: проект → Activity → Point/Payment/Document»
в базовом скилле `fst-pmpractice`.

## Алгоритм работы

```
1. ОПРЕДЕЛИТЬ ПРОЕКТ
   ┌────────────────────────────────────────────────────────┐
   │ A: пользователь дал ProjectId → использовать напрямую │
   │ B: пользователь дал Code → поиск через get_view       │
   │ C: пользователь дал часть Name → уточнить выбор       │
   │           (загрузить fst-pmpractice/project-search)      │
   └────────────────────────────────────────────────────────┘

2. ПОЛУЧИТЬ ПРОЕКТ
   get_view(Project, MyProject)
   fallback: get_view(Project, AllProject)
   Извлечь: ProjectId, Code, Name

3. ПОЛУЧИТЬ СПИСОК POINT ПРОЕКТА
   get_view(Point, AllMyPoint)
   fallback: "PointToMeToDo", "MyAssignmentPoint"
   └─ фильтр: r["ParentCode"] == "<project_code>"
      (или r["ProjectId"] == <project_id>)

4. ОТФИЛЬТРОВАТЬ ЗАМЕЧАНИЯ
   для каждой точки проверить:
   • PlanDate и ForecastDate оба заполнены
   • FactDate пустая (КТ не завершена)
   • PlanDate ≠ ForecastDate
   • иначе → пропустить

5. КЛАССИФИЦИРОВАТЬ ПО DIFF
   diff_days = (ForecastDate - PlanDate).days     # календарных
   abs_diff = abs(diff_days)

   if   abs_diff > REMARK_THRESHOLDS["critical"]["min_diff_days"]:
        color = "Красный";  status = "Критическое"
   elif abs_diff > REMARK_THRESHOLDS["substantial"]["min_diff_days"]:
        color = "Желтый";   status = "Существенное"
   else:
        color = "Синий";    status = "Информационное"

6. ПОЛУЧИТЬ ИСПОЛНИТЕЛЯ
   • ResponsibleId (bigint) уже в строке view
   • Responsible (display-ФИО) уже в строке view
   • отдельный запрос к User API НЕ нужен

7. ОЦЕНИТЬ ЗДОРОВЬЕ ПРОЕКТА
   critical_count = count(remark.color == "Красный")

   if   critical_count ≥ HEALTH_THRESHOLDS["sick"]["min_critical_count"]:
        health = "БОЛЕН";            health_color = "КРАСНЫЙ"
   elif critical_count ≥ HEALTH_THRESHOLDS["attention"]["min_critical_count"]:
        health = "ТРЕБУЕТ ВНИМАНИЯ"; health_color = "ЖЕЛТЫЙ"
   else:
        health = "ЗДОРОВ";           health_color = "—"

8. (ОПЦИОНАЛЬНО) ПРОВЕРИТЬ НАЛИЧИЕ ПАСПОРТА
   get_view(DocumentFile, DocumentFileViewAll)
   └─ фильтр: "<project_code>" in DataName AND "паспорт" in DocumentName
   → прикрепить к отчёту как отдельную секцию «Контекст проекта»

9. СФОРМИРОВАТЬ ОТЧЁТ (см. ниже структуру)
```

## Структура отчёта (Markdown)

```markdown
# Общая оценка здоровья проекта <Name> с точки зрения сроков

> Составлено: <дата>

С точки зрения оценки состояния по срокам КТ проекта, подтверждающим
документом для которых является паспорт:

- Данный проект **БОЛЕН**, цвет **КРАСНЫЙ**
  в том случае, если имеется три или более КТ, отбираемых для критических замечаний
- Данный проект **ТРЕБУЕТ ВНИМАНИЯ**, цвет **ЖЕЛТЫЙ**
  в том случае если имеется не более двух КТ, отбираемых для критических замечаний
- Данный проект **ЗДОРОВ**, если в нем на данный момент нет ни одной КТ,
  отбираемых для критических замечаний

## Текущая оценка

**Проект:** <Name> (Code=<code>, ProjectId=<id>)

**Состояние:** <health> (цвет: <health_color>)
**Критических замечаний:** <critical_count>
**Всего замечаний:** <total_remarks>
**Паспорт проекта:** <есть/нет>

---

## СПИСОК ЗАМЕЧАНИЙ ПО СРОКАМ

### Условия отбора замечаний
В таблицу попадают только те Point, у которых:
1. `PlanDate ≠ ForecastDate`
2. `FactDate` не заполнена (КТ ещё не завершена)

### Цветовая кодировка и статус
| Цвет | Статус | Условие |
|------|--------|---------|
| **Красный** | Критическое | `\|ForecastDate − PlanDate\| > 10` дней |
| **Желтый** | Существенное | `2 < diff ≤ 10` дней |
| **Синий** | Информационное | `0 ≤ diff ≤ 2` дня |

### Сводка по цветам
| Цвет | Кол-во |
|------|--------|
| Красный | <N> |
| Желтый | <N> |
| Синий | <N> |

### Таблица замечаний
|  #  | Цвет | Статус | Code | Name | PlanDate | ForecastDate | FactDate | Исполнитель |
|-----|------|--------|------|------|----------|--------------|----------|--------------|
|   1 | Красный | Критическое | `104-721` | ЧТЗ согласовано | 2026-07-15 | 2026-07-27 | — | Кузнецов Р. В. (id=120872) |
```

Если пользователь сказал «пришли как файл» — отчёт сохраняется в
`/tmp/<project_code>_здоровье.md` или подобное имя и отправляется через
`MEDIA:/abs/path`.

## Пример вызова (Python-style)

```python
# Получить проект
proj_view = mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "MyProject",
    "filters": {},
    "limit": 100,
})
project = next(p for p in proj_view["data"] if p["Code"] == "504-595")

# Получить все КТ проекта
pt_view = mcp_call(sid, "get_view", {
    "entityName": "Point",
    "viewName": "AllMyPoint",
    "filters": {},
    "limit": 100,
})
points = [r for r in pt_view["data"] if str(r.get("ParentCode", "")).strip() == project["Code"]]

# Отфильтровать замечания
remarks = []
for p in points:
    plan = parse_date(p.get("PlanDate"))
    forecast = parse_date(p.get("ForecastDate"))
    if not plan or not forecast: continue
    if p.get("FactDate"): continue
    if plan == forecast: continue

    diff_days = (forecast - plan).days
    diff_abs = abs(diff_days)
    if diff_abs > REMARK_THRESHOLDS["critical"]["min_diff_days"]:
        color, status = "Красный", "Критическое"
    elif diff_abs > REMARK_THRESHOLDS["substantial"]["min_diff_days"]:
        color, status = "Желтый", "Существенное"
    else:
        color, status = "Синий", "Информационное"

    remarks.append({
        "code": p["Code"], "name": p.get("pointname") or p.get("Name"),
        "plan": plan, "forecast": forecast, "fact": p.get("FactDate"),
        "diff": diff_days, "color": color, "status": status,
        "responsible_name": p.get("Responsible"),
        "responsible_id": p.get("ResponsibleId"),
    })

critical = sum(1 for r in remarks if r["color"] == "Красный")
if critical >= HEALTH_THRESHOLDS["sick"]["min_critical_count"]:
    health = "БОЛЕН"
elif critical >= HEALTH_THRESHOLDS["attention"]["min_critical_count"]:
    health = "ТРЕБУЕТ ВНИМАНИЯ"
else:
    health = "ЗДОРОВ"
```

## Edge cases

| Случай | Поведение |
|--------|-----------|
| У проекта нет ни одной Point с расхождением дат | health = "ЗДОРОВ", таблица пустая |
| PlanDate пустое, ForecastDate есть | пропускается (нельзя вычислить diff) |
| PlanDate == ForecastDate | пропускается |
| FactDate заполнена | пропускается (КТ завершена) |
| diff ровно 2 дня | color = "Синий" (порог `>2` строгий) |
| diff ровно 10 дней | color = "Желтый" (порог `>10` для Красного строгий) |
| diff = 11 дней | color = "Красный" |
| `critical_count ≥ 3` | health = "БОЛЕН" (порог нестрогий) |
| В view нет проекта | Сообщить, предложить проверить Code/ProjectId |
| Проект без Паспорта | Секция «Паспорт проекта: нет» в отчёте, **не меняет** health |
| Запрос по части Name | Несколько совпадений → попросить уточнить Code |

## Настройка порогов под нужды пользователя

Если пользователь говорит «ужесточи критерии» / «считай критическим всё, что больше 5 дней»:

```python
REMARK_THRESHOLDS["critical"]["min_diff_days"] = 5
```

Если «для этого проекта 1 критическое = БОЛЕН»:

```python
HEALTH_THRESHOLDS["sick"]["min_critical_count"] = 1
```

**Всегда подтверждай изменение порогов пользователю перед применением.**

## Verification Checklist

- [ ] Project найден (Code или ProjectId совпадает)
- [ ] Список Point получен и отфильтрован по проекту (по ParentCode или ProjectId)
- [ ] Для каждого замечания вычислен diff в календарных днях
- [ ] Каждому замечанию присвоены color и status по `REMARK_THRESHOLDS`
- [ ] Исполнитель получен из `Responsible` / `ResponsibleId` строки view
- [ ] `critical_count` вычислен корректно
- [ ] `health` присвоен по `HEALTH_THRESHOLDS`
- [ ] Таблица отсортирована по PlanDate, затем по убыванию diff
- [ ] (Опц.) Паспорт проекта проверен через `DocumentFile`
- [ ] Отчёт оформлен по структуре (заголовок → оценка → список)
- [ ] (Если «пришли как файл») файл сохранён и отправлен через `MEDIA:`

## Рабочий пример (проверенный на проекте 504-595)

**Запрос:** «Оцени здоровье проекта 504-595»

**Результат:** Найдено 3 замечания (2 Критических, 1 Существенное),
`critical_count = 2 < 3`, поэтому проект **ТРЕБУЕТ ВНИМАНИЯ**.

| Code | Name | PlanDate | ForecastDate | Δ | Цвет |
|------|------|----------|--------------|---|------|
| 104-721 | ЧТЗ согласовано | 2026-07-15 | 2026-07-27 | +12 | Красный |
| 104-719 | Первый блок работ принят Заказчиком | 2026-07-24 | 2026-08-06 | +13 | Красный |
| 104-722 | Подписан протокол согласования по 1-му блоку работ | 2026-07-24 | 2026-07-27 | +3 | Желтый |

## Связь с другими скиллами

- **Базовый:** `fst-pmpractice` — форматы вызовов `get_view`, `get_entity_data`, `save_entity`
- **Поиск проекта:** `project-search` — найти ProjectId по Code или части Name
- **Сводка по проекту:** использовать `get_view(Project, MyProject)` для базовой информации о проекте
- **`references/project-architecture.md`** — подробная ASCII-диаграмма связей
  сущностей Форсайт. Обязательно прочти, если нужно работать с другими
  дочерними сущностями (Payments, Risk, DocumentFile) — там описаны
  подводные камни и шаблон `get_project_children()`.
- **Сводка по проекту:** использовать `get_view(Project, MyProject)` для базовой информации

## Будущие расширения

- Фильтрация по подтверждающему документу (сейчас `CONFIRMING_DOCUMENT = "паспорт"` — справочное, фильтрация в самих points пока не работает)
- Учёт WBS-иерархии (агрегация замечаний на уровне WBS-узлов)
- Экспорт отчёта в CSV / Excel
- Уведомления исполнителю через Telegram при критических замечаниях
- Графики таймлайна КТ (matplotlib)
- Поддержка нескольких проектов одновременно (сводная таблица)
