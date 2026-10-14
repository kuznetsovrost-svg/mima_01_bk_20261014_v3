---
name: project-timing-control
description: "Use when the user wants to evaluate a Foresight PM Practice project's health from a schedule standpoint, get a list of timing remarks on its Points (control points), or diagnose delays. Loads when user asks: 'оцени здоровье проекта', 'анализ сроков', 'замечания по срокам', 'проект просрочен', 'project health', 'timing remarks', 'why is the project red', or mentions 'Космодром Жуковский' / 'Жуковский' / 'внедрение ИСУП'. Reads Point view, filters unfinished КТ with PlanDate ≠ ForecastDate, classifies by diff thresholds, and reports aggregate project status."
version: 1.0.0
author: Hermes Agent + Rost
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [mcp, pmpractice, foresight, project-management, schedule, deadline, delay, ru]
    related_skills: [fst-pmpractice, project-search, plan]
---

# Project Timing Control (project-timing-control)

## Overview

Скилл для оценки **здоровья проекта Форсайт ПМ Практики с точки зрения сроков**.
Загружается, когда пользователь спрашивает проект «Форсайт» (космодром Жуковский,
внедрение ИСУП и т.п.), хочет получить список замечаний по срокам или понять,
почему проект «горит красным».

Анализирует сущности **Point** (контрольные точки / этапы) проекта и формирует
два артефакта:

1. **Общую оценку здоровья проекта** (БОЛЕН / ТРЕБУЕТ ВНИМАНИЯ / ЗДОРОВ) по числу критических замечаний.
2. **Список замечаний по срокам** с цветовой кодировкой (Красный/Жёлтый/Синий) и статусами (Критическое/Существенное/Информационное).

## When to Use

Загружай, когда пользователь:

- Спрашивает «насколько проект просрочен», «что с сроками», «здоровье проекта»
- Просит «замечания по срокам», «почему красный», «диагностика проекта»
- Хочет план-факт анализ по КТ (контрольным точкам) проекта
- Упоминает «Форсайт», «ИСУП», проект по Code/ProjectId

**Не загружай** для бытовых задач, не связанных с PM-системой Форсайт.

## Parameters (пороги цветов и статусов)

Все пороги хранятся как **переменные** — пользователь может изменить их в начале
сессии или явно попросить ужесточить/ослабить критерии.

### Пороги для классификации замечания

```python
# Пороги расхождения PlanDate vs ForecastDate (в календарных днях)
REMARK_THRESHOLDS = {
    "critical": {
        "min_diff_days": 10,      # строго больше 10
        "color": "Красный",
        "status": "Критическое",
    },
    "substantial": {
        "min_diff_days": 2,       # строго больше 2, но ≤ 10
        "max_diff_days": 10,
        "color": "Желтый",
        "status": "Существенное",
    },
    "informational": {
        "max_diff_days": 2,       # 0 ≤ diff ≤ 2
        "color": "Синий",
        "status": "Информационное",
    },
}
```

### Пороги для оценки здоровья проекта

```python
# Пороги по количеству критических замечаний
HEALTH_THRESHOLDS = {
    "sick": {
        "min_critical_count": 3,       # ≥ 3 критических → БОЛЕН
        "label": "БОЛЕН",
        "color": "КРАСНЫЙ",
    },
    "attention": {
        "min_critical_count": 1,       # 1 или 2 критических → ТРЕБУЕТ ВНИМАНИЯ
        "max_critical_count": 2,
        "label": "ТРЕБУЕТ ВНИМАНИЯ",
        "color": "ЖЕЛТЫЙ",
    },
    "healthy": {
        "max_critical_count": 0,       # 0 критических → ЗДОРОВ
        "label": "ЗДОРОВ",
        "color": "—",                  # без цвета
    },
}
```

### Дополнительные фильтры (опционально)

```python
# Подтверждающий документ — пока анализ идёт только по КТ, у которых
# паспорт проекта является подтверждающим документом. В текущей реализации
# фильтрация по ConfirmationDocument не реализована (заглушка).
CONFIRMING_DOCUMENT = "паспорт"   # справочное значение

# Сортировка замечаний в выводе
REMARK_SORT = ["plan_date_asc", "diff_desc"]   # сначала по PlanDate, затем по убыванию diff
```

## Алгоритм работы

```
1. ОПРЕДЕЛИТЬ ПРОЕКТ
   ┌─────────────────────────────────────────────────────────┐
   │ Вариант A: пользователь дал ProjectId → использовать его│
   │ Вариант B: пользователь дал Code → поиск через view      │
   │ Вариант C: пользователь дал часть Name → уточнить выбор  │
   │           (см. скилл project-search)                       │
   └─────────────────────────────────────────────────────────┘

2. ПОЛУЧИТЬ ПРОЕКТ
   get_view(Project, MyProject)
   fallback: get_view(Project, AllProject)
   Извлечь: ProjectId, Code, Name

3. ПОЛУЧИТЬ СПИСОК POINT ПРОЕКТА
   get_view(Point, AllMyPoint)
   └─ фильтр по ParentCode == "<project_code>"

4. ОТФИЛЬТРОВАТЬ ЗАМЕЧАНИЯ
   для каждой точки:
   • если нет PlanDate или ForecastDate → пропустить
   • если FactDate заполнена → пропустить (КТ завершена)
   • если PlanDate == ForecastDate → пропустить (нет расхождения)
   • иначе → точка попадает в замечания

5. КЛАССИФИЦИРОВАТЬ КАЖДОЕ ЗАМЕЧАНИЕ
   diff_days = (ForecastDate - PlanDate).days      # в календарных днях
   abs_diff = abs(diff_days)

   if   abs_diff > REMARK_THRESHOLDS["critical"]["min_diff_days"]:
        color = "Красный";  status = "Критическое"
   elif abs_diff > REMARK_THRESHOLDS["substantial"]["min_diff_days"]:
        color = "Желтый";   status = "Существенное"
   else:
        color = "Синий";    status = "Информационное"

6. ПОЛУЧИТЬ ИСПОЛНИТЕЛЯ
   • ResponsibleId (bigint) уже есть в строке view
   • Responsible (display-ФИО) уже есть в строке view
   • отдельный запрос к User API не нужен

7. ОЦЕНИТЬ ЗДОРОВЬЕ ПРОЕКТА
   critical_count = число замечаний с color == "Красный"

   if   critical_count >= HEALTH_THRESHOLDS["sick"]["min_critical_count"]:
        health = "БОЛЕН";            health_color = "КРАСНЫЙ"
   elif critical_count >= HEALTH_THRESHOLDS["attention"]["min_critical_count"]:
        health = "ТРЕБУЕТ ВНИМАНИЯ"; health_color = "ЖЕЛТЫЙ"
   else:
        health = "ЗДОРОВ";           health_color = "—"

8. СФОРМИРОВАТЬ ОТЧЁТ
   Структура вывода — см. ниже «Структура отчёта».
```

## Структура отчёта

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

---

## СПИСОК ЗАМЕЧАНИЙ ПО СРОКАМ

### Условия отбора замечаний
...

### Цветовая кодировка и статус
| Цвет | Статус | Условие |
| ... | ... | ... |

### Сводка по цветам
| Цвет | Кол-во |
| ... | ... |

### Таблица замечаний
|  #  | Цвет | Статус | Code | Name | PlanDate | ForecastDate | FactDate | Исполнитель |
|-----|------|--------|------|------|----------|--------------|----------|--------------|
```

## Пример вызова (Python-style)

```python
mcp__fst_pmpractice__get_view(entityName="Project", viewName="MyProject")
# → найти проект по Code или ProjectId

mcp__fst_pmpractice__get_view(entityName="Point", viewName="AllMyPoint")
# → фильтр по ParentCode

# Локальная обработка:
for point in project_points:
    if not (point.plan and point.forecast): continue
    if point.fact: continue
    if point.plan == point.forecast: continue
    diff = (point.forecast - point.plan).days
    abs_diff = abs(diff)
    if abs_diff > REMARK_THRESHOLDS["critical"]["min_diff_days"]:
        color, status = "Красный", "Критическое"
    elif abs_diff > REMARK_THRESHOLDS["substantial"]["min_diff_days"]:
        color, status = "Желтый", "Существенное"
    else:
        color, status = "Синий", "Информационное"

critical_count = sum(1 for r in remarks if r.color == "Красный")
if critical_count >= HEALTH_THRESHOLDS["sick"]["min_critical_count"]:
    health = "БОЛЕН"
elif critical_count >= HEALTH_THRESHOLDS["attention"]["min_critical_count"]:
    health = "ТРЕБУЕТ ВНИМАНИЯ"
else:
    health = "ЗДОРОВ"
```

## Edge cases

| Случай | Поведение |
|--------|-----------|
| У проекта нет ни одной Point с расхождением дат | health = "ЗДОРОВ", таблица пустая |
| PlanDate пустое, ForecastDate есть | точка пропускается (нельзя вычислить diff) |
| PlanDate == ForecastDate | точка пропускается (нет расхождения) |
| FactDate заполнена | точка пропускается (КТ завершена, замечание неактуально) |
| diff ровно 2 дня | color = "Синий" (порог ">2" строгий) |
| diff ровно 10 дней | color = "Желтый" (порог ">10" для Красного строгий) |
| diff = 11 дней | color = "Красный" |
| Проект имеет >3 критических замечаний | health = "БОЛЕН" (порог ≥ 3 нестрогий) |
| В view нет проекта (нет доступа) | Сообщить пользователю, предложить проверить Code/ProjectId |

## Настройка порогов под нужды пользователя

Если пользователь говорит «ужесточи критерии» / «считай критическим всё, что больше 5 дней»:

```python
REMARK_THRESHOLDS["critical"]["min_diff_days"] = 5
```

Если «для этого проекта 1 критическое = БОЛЕН»:

```python
HEALTH_THRESHOLDS["sick"]["min_critical_count"] = 1
```

Всегда подтверждай изменение порогов пользователю перед применением.

## Verification Checklist

- [ ] Project найден (Code или ProjectId совпадает)
- [ ] Список Point получен и отфильтрован по проекту
- [ ] Для каждого замечания вычислен diff в календарных днях
- [ ] Каждому замечанию присвоены color и status по порогам
- [ ] Исполнитель получен из Responsible / ResponsibleId
- [ ] critical_count вычислен корректно
- [ ] health = "БОЛЕН"/"ТРЕБУЕТ ВНИМАНИЯ"/"ЗДОРОВ" по порогам
- [ ] Таблица отсортирована по PlanDate, затем по убыванию diff
- [ ] Отчёт сформирован по структуре (заголовок → текущая оценка → список)

## Связь с другими скиллами

- **Базовый:** `fst-pmpractice` — форматы вызовов `get_view`, `get_entity_data`, `save_entity`
- **Поиск проекта:** `project-search` — найти ProjectId по Code или части Name
- **Сводка по проекту:** использовать `get_view(Project, MyProject)` для базовой информации о проекте

## Будущие расширения

- Фильтрация по `ConfirmationDocument` (сейчас заглушка — всегда "паспорт")
- Учёт `WBS`-иерархии (агрегация замечаний на уровне WBS-узлов)
- Экспорт отчёта в CSV / Excel
- Уведомления исполнителю через Telegram при критических замечаниях
- Графики (matplotlib) с таймлайном КТ