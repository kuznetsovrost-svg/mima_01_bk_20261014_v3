---
name: project-effort-plan
description: "Use when the user wants to plan/schedule effort hours (запланировать трудозатраты) for a specific Foresight PM Practice project on a specific date or Point. Loads when user says 'запланируй часы', 'plan hours', 'назначь ресурс', 'спланируй загрузку', 'resource planning', 'forecast effort'. Reads ResourcePlanningKp entity (forecast), needs PointId (FK to specific control point), uses AccountId from get_user_profile."
version: 2.0.0
changelog:
  - "2.0.0 (2026-09-01): MAJOR UPDATE. Migrated to standard `filters={...}` format. Live-probe 2026-09-01: `get_view({entityName: ..., viewName: ..., filters: {ProjectId: ...}, limit: 100})` works for all views. Replaces deprecated `mcp__fst_pmpractice__get_view` namespace and `?Field=value` URL format. See `references/mcp-filters-format.md` in `mcp-server-probing` skill.
author: Hermes Agent + Rost
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [mcp, pmpractice, foresight, effort, planning, forecast, resource-planning, ru]
    related_skills: [fst-pmpractice, project-search, project-effort-write, project-effort-analysis, project-architecture]
---

# Project Effort Plan (project-effort-plan)

## Overview

Скилл для **планирования трудозатрат** в системе Форсайт ПМ Практики.
Загружай, когда пользователь говорит:

- «Запланируй N часов на КТ X проекта Y»
- «Спланируй загрузку сотрудника на КТ»
- «Назначь ресурс на проект»
- «Resource planning для проекта 504-595»
- «Forecast hours»

В отличие от `project-effort-write` (факт), этот скилл работает с **прогнозом**
через сущность `ResourcePlanningKp` — часы привязываются к **конкретному Point (КТ)**.

## ⚠️ Отличие от project-effort-write

| Скилл | Сущность | Назначение |
|-------|----------|------------|
| `project-effort-write` | `ResourcePlanning` | **Факт** — «я отработал N часов» |
| `project-effort-plan` | `ResourcePlanningKp` | **Прогноз** — «планирую N часов на КТ» |
| `project-effort-analysis` | (будущий) | Анализ plan vs fact |

⚠️ Архитектурная связь:
```
Project
  └─ Activity
       └─ Point (конкретная КТ)
            └─ ResourcePlanningKp (PointId FK)
```

⚠️ У `ResourcePlanningKp` **FK на Point**, не на Activity/Project напрямую.
Поэтому нужно знать конкретный `PointId`.

## When to Use

Загружай, когда пользователь:
- Хочет **спланировать** часы сотрудника на конкретную КТ
- Указывает: `project + point + hours + date + (account)`
- Говорит «назначь», «спланируй», «прогноз»

**Не загружай** для:
- Записи **факта** трудозатрат → `project-effort-write`
- Просмотра трудозатрат → `project-effort-analysis` / `ProjectHealthWorkload`

## Parameters

| Параметр | Обязательный | Описание | Пример |
|----------|---------------|----------|--------|
| `project_code` или `project_id` | ✅ | Код или ProjectId | `"504-595"` |
| `point_code` или `point_id` | ✅ | Код КТ (`"104-708"`) или `PointId` (`4708`) | `"104-708"` |
| `date` | ✅ | Дата в формате `dd.MM.yyyy` | `"25.07.2026"` |
| `hours` | ✅ | Количество часов (numeric) | `4` или `4.5` |
| `account_id` | ❌ | FK на сотрудника. По умолчанию = текущий пользователь | `120872` |
| `role_id` | ❌ | FK на Role | bigint |
| `specialization_id` | ❌ | FK на Specialization | uuid |
| `participation` | ❌ | % привлечения (по умолчанию = 100) | `100` или `50` |
| `manual` | ❌ | `true` — ручное планирование, `false` — авто | `true` |

### Автоматические параметры

- `AccountId` — из `get_user_profile`
- `planning_date` — из параметра `date`
- `planning_hours` — из параметра `hours`

## Алгоритм работы

```
1. ОПРЕДЕЛИТЬ ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ
   mcp__fst_pmpractice__get_user_profile() → AccountId

2. ОПРЕДЕЛИТЬ ПРОЕКТ
   A: ProjectId → напрямую
   B: Code → get_view(Project, MyProject) фильтр по Code
   C: только Name → уточнить (project-search)

3. ОПРЕДЕЛИТЬ PointId
   A: PointId → напрямую
   B: Code → get_view(Point, AllMyPoint фильтр по Code

4. ВАЛИДАЦИЯ: PointId должен принадлежать этому проекту
   point = get_view(Point, AllMyPoint
   target = next(r for r in point.data if r.PointId == <point_id>)
   if target.ParentCode != <project_code>: СТОП

5. ПОДТВЕРДИТЬ С ПОЛЬЗОВАТЕЛЕМ
   - Проект + КТ
   - Дата + часы
   - Сотрудник
   - % привлечения

6. ЗАПИСАТЬ через save_entity (⚠️ snake_case!)
   save_entity(
       entityName="ResourcePlanningKp",
       id="new",
       data={
           "PointId": <point_id>,
           "AccountId": <account_id>,
           "planning_date": "<dd.MM.yyyy>",
           "planning_hours": <hours>,
           # опционально:
           "RoleId": <role_id>,
           "SpecializationId": "<uuid>",
           "participation": <percent>,
           "manual": <true|false>
       }
   )

7. ВЕРИФИКАЦИЯ
   Сервер вернёт запись с ResourcePlanningKpId.
   Проверить: planning_hours, planning_date, PointId, AccountId.
   ⚠️ Не верь "успеху" при update через save_entity с существующим id!

8. ОТЧЁТ ПОЛЬЗОВАТЕЛЮ
```

## Структура записи ResourcePlanningKp

⚠️ **Имена полей в API — snake_case** (`planning_date`), а не CamelCase как в Point/Project.

| Поле | Что заполняем | Пример |
|------|---------------|--------|
| `PointId` | FK на Point (КТ) | `4708` |
| `AccountId` | FK на сотрудника | `120872` |
| `planning_date` | Дата (snake_case!) | `"15.07.2026"` |
| `planning_hours` | Часы (snake_case!) | `20.0` |
| `RoleId` | Опционально | `bigint` |
| `SpecializationId` | Опционально | `"uuid"` |
| `participation` | % привлечения (snake_case!) | `100` |
| `manual` | Ручное планирование (snake_case!) | `true` |

⚠️ **Не заполняем**: `ResourcePlanningKpId`, `CreationDate`, `ChangeDate`, `CreationAuthorId`, `ChangeAuthorId`.

## Пример вызова

```python
profile = mcp__fst_pmpractice__get_user_profile()
account_id = profile["Id"]

projects = mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "MyProject",
    "filters": {},
    "limit": 100,
})
project = next(p for p in projects["data"] if p["Code"] == "504-595")

points = mcp_call(sid, "get_view", {
    "entityName": "Point",
    "viewName": "AllMyPoint",
    "filters": {},
    "limit": 100,
})
point = next(p for p in points["data"] if p["Code"] == "104-708")

if point["ParentCode"] != project["Code"]:
    raise ValueError("Point не принадлежит проекту")

result = mcp__fst_pmpractice__save_entity(
    entityName="ResourcePlanningKp",
    id="new",
    data={
        "PointId": point["PointId"],
        "AccountId": account_id,
        "planning_date": "15.07.2026",
        "planning_hours": 4.5,
        "participation": 100,
        "manual": True
    }
)
```

## Edge cases

| Случай | Поведение |
|--------|-----------|
| Пользователь не залогинен | СТОП |
| Проект не найден | Fallback на AllProject |
| КТ не найдена по Code | СТОП |
| КТ не принадлежит проекту | СТОП |
| `hours <= 0` или `hours > 24` | Спросить подтверждение |
| `date` в прошлом более 30 дней | Предупредить |
| 🔴 **`save_entity` с существующим `id` для `ResourcePlanningKp` НЕ обновляет поля** | Сервер при PATCH-вызове притворяется успешным — обновляет `ChangeDate`/`ChangeAuthorId`, но `planning_hours` остаётся прежним. **Workaround:** `delete_entity` → `save_entity(id="new"`. **Всегда верифицируй через `get_entity_data`** — не верь ChangeDate! |
| 🔴 **CamelCase вместо snake_case** | `"PlanningDate"` вместо `"planning_date"` → `409 — Не заполнены обязательные поля [Дата]`. См. pitfall #14 в `fst-pmpractice`. |
| ⚠️ **JSON-RPC `-32602` при `id="new"`** | Повторный вызов через 1-2 секунды проходит. Не путай с `isError: true`. |
| ⚠️ **View `ResourcePlanningKp` запрещён 403** | Используй `find_entity` + `get_entity_data` (ResourcePlanningKpView закрыт для обычного пользователя) или просто `save_entity(id="new"` и `get_entity_data` для проверки. |

## ⚠️ Различие plan vs fact

| Аспект | Plan (ResourcePlanningKp) | Fact (ResourcePlanning) |
|--------|---------------------------|---------------------------|
| Когда | На будущее / планирование | По факту отработки |
| Кому | Конкретный Point (КТ) | Конкретный день (Activity) |
| Связь | `PointId` (FK на Point) | `ActivityId` (FK на Activity) |
| Доп. поля | `RoleId`, `SpecializationId`, `Participation`, `Manual` | `SpecializationId`, `planning_hours_kp` |
| Изменение | `ChangeDate`, `ChangeAuthorId` | `batchid`, `ChangeDate`, `ChangeAuthorId` |

⚠️ **ResourcePlanning** (fact) скорее всего **тоже использует snake_case** для тех же полей — но это не проверено эмпирически. При первом запуске `project-effort-write` обязательно подтвердить через `describe_entity`.

## Формат отчёта пользователю

```
✅ Запланировано:

  Проект:        Космодром Жуковский внедрение ИСУП (504-595)
  КТ:            Пресейл открыт (104-708)
  Дата:          25.07.2026
  Часы:          4.5
  % привлечения: 100
  Исполнитель:   Кузнецов Ростислав Владимирович (id=120872)
  Ручное план.:  true
  ResourcePlanningKpId: 12345
```

## Verification Checklist

- [ ] `get_user_profile` вернул `Id`
- [ ] Проект найден
- [ ] `PointId` найден и принадлежит проекту (ParentCode == project.Code)
- [ ] Пользователь подтвердил планирование
- [ ] **Используются snake_case имена полей**
- [ ] `save_entity` вернул запись с `ResourcePlanningKpId`
- [ ] **В ответе `planning_hours` = запрошенное значение** (не верь «успеху» — проверь!)
- [ ] Для **update**: использован `delete_entity` + `save_entity(id="new"`, либо подтверждено через `get_entity_data`, что поля реально изменились
- [ ] Сообщили пользователю `ResourcePlanningKpId`

## Связь с другими скиллами

- **Базовый:** `fst-pmpractice` — формат `save_entity`, `get_user_profile`, pitfall #14 (naming conventions)
- **Поиск проекта:** `project-search`
- **Факт трудозатрат:** `project-effort-write`
- **Анализ трудозатрат:** `project-effort-analysis` (будущий)
- **Архитектура:** `fst-pmpractice/references/project-architecture.md` и `fst-pmpractice/references/project-finance-budget-entities.md` (карта финансовых сущностей Форсайт с обходом 403 — загружай когда задача про бюджет/трудозатраты в денежном выражении)

## Будущие расширения

- Массовое планирование (диапазон дат × список сотрудников)
- Шаблон «распределение по ролям» (назначить автоматически по `RoleId`)
- Импорт плана из Excel/CSV
- Сравнение plan vs fact в реальном времени
- Уведомления о превышении загрузки (>100%)
- **Helper-скрипт** `scripts/update_rpkp_hours.py` — обёртка над `delete_entity + save_entity(id="new"` для безопасного обновления `planning_hours`