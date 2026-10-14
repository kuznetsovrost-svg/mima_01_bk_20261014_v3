---
name: project-effort-write
description: "Use when the user wants to log/report worked hours, time entries, or effort (трудозатраты) for a specific Foresight PM Practice project on a specific date. Loads when user says 'запиши трудозатраты', 'списать часы', 'worked on project X for Y hours', 'отчитаться о часах', 'зафиксировать часы за сегодня', or provides project code/ProjectId + hours + date. Reads ResourcePlanning entity, finds Activity by project, upserts effort record for current user (AccountId from get_user_profile)."
version: 2.0.0
changelog:
  - "2.0.0 (2026-09-01): MAJOR UPDATE. Migrated to standard `filters={...}` format. Live-probe 2026-09-01: `get_view({entityName: ..., viewName: ..., filters: {ProjectId: ...}, limit: 100})` works for all views. Replaces deprecated `mcp__fst_pmpractice__get_view` namespace and `?Field=value` URL format. See `references/mcp-filters-format.md` in `mcp-server-probing` skill.
author: Hermes Agent + Rost
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [mcp, pmpractice, foresight, effort, hours, time-tracking, resource-planning, ru]
    related_skills: [fst-pmpractice, project-search, project-effort-plan, project-effort-analysis, project-architecture]
---

# Project Effort Write (project-effort-write)

## Overview

Скилл для **записи фактических трудозатрат** сотрудника в систему Форсайт ПМ Практики.
Загружай, когда пользователь говорит:

- «Спиши N часов на проект X»
- «Я работал над проектом 504-595, 4 часа»
- «Запиши трудозатраты за сегодня — 6 часов на проект ABC»
- «Отчитаться о часах»
- «Занеси трудозатраты на дату 2026-07-25»

Записывает **одну запись** в сущность `ResourcePlanning` для текущего пользователя.

## ⚠️ Архитектурная особенность

```
ResourcePlanning — НЕ имеет прямого FK на Project.
Связь: Project → Activity → ResourcePlanning (ActivityId)

⚠️ Парадокс: у ResourcePlanning поле ProjectId отсутствует,
но у некоторых связанных сущностей (Point, Risk) поле ProjectId = FK на Activity.
Это историческое наследие Форсайт.
```

Полная диаграмма связей и pitfall-таблица — в `references/project-architecture.md` →
секция «Сущности трудозатрат».

## When to Use

Загружай, когда пользователь:

- Сообщает количество часов по конкретному проекту на конкретную дату
- Хочет списать трудозатраты на себя
- Даёт комбинацию: `ProjectId/Code + hours + date`

**Не загружай** для:
- Просмотра трудозатрат (→ `project-effort-analysis` / `ProjectHealthWorkload`)
- **Планирования** трудозатрат (`ResourcePlanningKp` — отдельная сущность для плана) → `project-effort-plan`
- Изменения других полей `ResourcePlanning` (например, `batchid`, `ChangeDate`)

## Parameters

Все параметры запрашиваются у пользователя перед записью:

| Параметр | Обязательный | Описание | Пример |
|----------|---------------|----------|--------|
| `project_code` или `project_id` | ✅ | Код (`"504-595"`) или `ProjectId` (`4595`) | `"504-595"` |
| `date` | ✅ | Дата в формате `dd.MM.yyyy` | `"25.07.2026"` |
| `hours` | ✅ | Количество часов (numeric) | `4` или `4.5` |
| `activity_id` | ❌ | Если не указано — найдём через Point view | `4595` |
| `specialization_id` | ❌ | Специализация (по умолчанию — без специализации) | uuid |
| `notes` | ❌ | Комментарий (в текущей версии схемы нет поля — игнорируется) | — |

### Автоматические параметры (запрашивать не нужно)

- `AccountId` — берётся из `get_user_profile` (текущий пользователь)
- `planning_date` — из параметра `date` ⚠️ **см. warning ниже про naming convention**
- `planning_hours` — из параметра `hours`

## ⚠️ Naming convention для полей `ResourcePlanning` (НЕ ПОДТВЕРЖДЕНО ЭМПИРИЧЕСКИ)

`ResourcePlanning` — **«сестринская» сущность** с `ResourcePlanningKp`. У `ResourcePlanningKp`
**эмпирически подтверждено**, что поля дат/часов/привлечения в API — **snake_case**
(`planning_date`, `planning_hours`, `participation`, `manual`).

⚠️ **Распространение правила:** с высокой вероятностью `ResourcePlanning` использует
**ту же** схему именования (snake_case), но я не запускал тестовую запись для проверки.
**Алгоритм ниже использует snake_case** — если сервер вернёт `409 — Не заполнены обязательные
поля`, попробуй CamelCase (`PlanningDate`, `PlanningHours`, `PlanningHoursKp`).

> Если ты запустишь этот скилл первым — ОБЯЗАТЕЛЬНО сделай тестовую запись через
> `describe_entity(ResourcePlanning, data_id="new")` и сверь фактические имена
> атрибутов. Потом обнови таблицу ниже.

## Алгоритм работы

```
1. ОПРЕДЕЛИТЬ ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ
   mcp__fst_pmpractice__get_user_profile()
   └─ Извлечь: AccountId (наш userId)
   Если не получилось — СТОП, попросить пользователя войти.

2. ОПРЕДЕЛИТЬ ПРОЕКТ
   ┌─────────────────────────────────────────────────────────┐
   │ A: пользователь дал ProjectId → использовать напрямую  │
   │ B: пользователь дал Code → найти через get_view(Project)│
   │ C: пользователь дал только Name → уточнить выбор        │
   │           (см. project-search)                           │
   └─────────────────────────────────────────────────────────┘
   Извлечь: ProjectId, Code, Name, ActivityId (FK на Project → обычно == ProjectId)

3. ОПРЕДЕЛИТЬ ActivityId ПРОЕКТА
   ⚠️ ActivityId проекта обычно СОВПАДАЕТ с ProjectId (историческое наследие
   Форсайт: project_id == activity_id для корневой Activity проекта).
   Проверка через get_entity_data(Project, data_id="<projectId>").
       └─ В ответе: properties.ActivityId.value

   Альтернатива — обходной путь через Point view:
   point_view = mcp_call(sid, "get_view", {
       "entityName": "Point",
       "viewName": "AllMyPoint",
       "filters": {},
       "limit": 100,
   })
   activity_ids = set()
   for r in point_view["data"]:
       if str(r.get("ParentCode", "")).strip() == "<project_code>":
           activity_ids.add(r.get("ParentId"))
   if not activity_ids:
       СТОП: «У проекта <X> нет ни одной КТ. Не могу определить ActivityId»

4. ПОДТВЕРДИТЬ С ПОЛЬЗОВАТЕЛЕМ
   Перед записью показать пользователю:
   - Что именно будет записано (проект, дата, часы)
   - Что AccountId = текущий пользователь
   - Что ActivityId = найденный

   Запросить «Подтвердить запись? (да/нет)».

5. ЗАПИСАТЬ ЧЕРЕЗ save_entity (⚠️ snake_case — см. warning выше)
   mcp__fst_pmpractice__save_entity(
       entityName="ResourcePlanning",
       id="new",
       data={
           "ActivityId": <activity_id>,
           "AccountId": <current_user_id>,
           "planning_date": "<dd.MM.yyyy>",      # ⚠️ snake_case (НЕ PlanningDate!)
           "planning_hours": <hours>,            # ⚠️ snake_case (НЕ PlanningHours!)
           # опционально:
           # "SpecializationId": "<uuid>",
           # "planning_hours_kp": <hours>,        # если хотим КП — тоже snake_case?
       }
   )

6. ВЕРИФИКАЦИЯ (ОБЯЗАТЕЛЬНО)
   Сервер вернёт ПОЛНУЮ запись с присвоенным ResourcePlanningId.
   Проверить через ответ + get_entity_data(ResourcePlanning, id):
   • planning_hours = запрошенное значение (не верь "успеху"!)
   • planning_date = запрошенная дата
   • ActivityId = найденный
   • AccountId = наш userId

7. ОТЧЁТ ПОЛЬЗОВАТЕЛЮ
   "Записано: <hours> ч на проект <Name> за <date>.
    ResourcePlanningId = <id>.
    ActivityId = <activity_id>, AccountId = <user_id>."
```

## Структура записи `ResourcePlanning` (snake_case, по аналогии с `ResourcePlanningKp`)

| Поле | Что заполняем | Пример |
|------|---------------|--------|
| `ActivityId` | FK на Activity (обычно == ProjectId) | `4595` |
| `AccountId` | Из `get_user_profile` | `120872` |
| `planning_date` | Из параметра `date` (формат `dd.MM.yyyy`) | `"25.07.2026"` |
| `planning_hours` | Из параметра `hours` | `4.5` |
| `SpecializationId` | Опционально | `"a24de56e-7120-499a-b4b1-c384bf04f88d"` |
| `planning_hours_kp` | Опционально (КП) | `4.5` |

⚠️ **Не заполняем** автоматически:
- `ResourcePlanningId` — присваивается сервером
- `batchid` — служебный
- `ChangeDate`, `ChangeAuthorId` — обновляются сервером

## Пример вызова

```python
# Шаг 1
profile = mcp__fst_pmpractice__get_user_profile()
account_id = profile["Id"]  # например 120872

# Шаг 2
projects = mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "MyProject",
    "filters": {},
    "limit": 100,
})
project = next(p for p in projects["data"] if p["Code"] == "504-595")
project_id = project["ProjectId"]  # например 4595

# Шаг 3: ActivityId для проекта
project_data = mcp__fst_pmpractice__get_entity_data(
    entityName="Project", data_id=str(project_id)
)
activity_id = project_data["properties"]["ActivityId"]["value"]  # обычно == project_id

# Шаг 5: запись (snake_case!)
result = mcp__fst_pmpractice__save_entity(
    entityName="ResourcePlanning",
    id="new",
    data={
        "ActivityId": activity_id,
        "AccountId": account_id,
        "planning_date": "25.07.2026",
        "planning_hours": 4.5
    }
)

# Шаг 6: верификация — ОБЯЗАТЕЛЬНО
written = mcp__fst_pmpractice__get_entity_data(
    entityName="ResourcePlanning", data_id=str(result["id"])
)
assert float(written["properties"]["planning_hours"]["value"]) == 4.5, "Часы не записались!"
```

## Edge cases

| Случай | Поведение |
|--------|-----------|
| Пользователь не залогинен | СТОП: «Нет данных пользователя, проверьте `PMP_TOKEN`» |
| Проект не найден в MyProject | Fallback на AllProject. Если и там нет — СТОП |
| У проекта нет ни одной КТ | СТОП: «У проекта нет ни одной КТ. Не могу определить ActivityId» |
| У проекта несколько Activity | Взять первый. Если критично — спросить пользователя |
| `hours <= 0` или `hours > 24` | Спросить подтверждение (явная ошибка или работа > суток) |
| `date` в будущем (> сегодня) | Предупредить пользователя, спросить подтверждение |
| `date` старше 30 дней | Предупредить (Форсайт может блокировать правки задним числом) |
| У пользователя нет прав на запись | Сервер вернёт 403/422 — сообщить, попросить проверить права |
| `save_entity` упал с ошибкой | Показать полный текст ошибки, НЕ повторять без изменения |
| 🔴 **`save_entity` с существующим `id` НЕ обновляет поля** | Наблюдалось на `ResourcePlanningKp` — почти наверняка воспроизводится и здесь. Сервер притворяется успешным (обновляет `ChangeDate`/`ChangeAuthorId`), но `planning_hours` остаётся прежним. **Workaround:** `delete_entity` + `save_entity(id="new")`. |
| 🔴 **CamelCase вместо snake_case** | Если сервер вернул `409 — Не заполнены обязательные поля [Дата]` — попробуй CamelCase (`PlanningDate`, `PlanningHours`). См. warning в начале и pitfall #14 в `fst-pmpractice`. |

## Формат отчёта пользователю

```
✅ Записано:

  Проект:        Космодром Жуковский внедрение ИСУП (504-595)
  Дата:          25.07.2026
  Часы:          4.5
  Исполнитель:   Кузнецов Ростислав Владимирович (id=120872)
  ActivityId:    4595
  ResourcePlanningId: 987654

Проверить запись: get_entity_data(ResourcePlanning, data_id="987654")
```

Если ошибка:

```
❌ Не удалось записать:

  Сервер вернул: «...текст ошибки...»
  Возможная причина: ...
  Рекомендация: ...
```

## Verification Checklist

- [ ] `get_user_profile` вернул `Id` (текущий пользователь)
- [ ] Проект найден (Code/ProjectId валиден)
- [ ] `ActivityId` получен (через `get_entity_data(Project, ...)` или Point view)
- [ ] Пользователь подтвердил запись
- [ ] **Используются snake_case имена полей** (`planning_date`, `planning_hours`)
- [ ] `save_entity` вернул запись с присвоенным `ResourcePlanningId`
- [ ] **В ответе `planning_hours` = запрошенное значение** (не верь «успеху» — проверь через `get_entity_data`!)
- [ ] В ответе `planning_date` = запрошенная дата
- [ ] Сообщили пользователю `ResourcePlanningId` для проверки

## Связь с другими скиллами

- **Базовый:** `fst-pmpractice` — формат `save_entity`, `get_user_profile`, формат дат, pitfall #14 (naming conventions)
- **Поиск проекта:** `project-search` — если пользователь дал только часть Name
- **Планирование трудозатрат:** `project-effort-plan` (запись в `ResourcePlanningKp`) — **эмпирически подтверждено snake_case**
- **Анализ трудозатрат:** `project-effort-analysis` (будущий) — посмотреть итоги
- **Архитектура:** `references/project-architecture.md` — подробная диаграмма связей

## Будущие расширения

- Запись **диапазона дат** (например, «4 часа в день с 20.07 по 24.07»)
- Подтверждение записи через push в Telegram
- Шаблон отчёта «трудозатраты за неделю»
- Bulk-импорт из тайм-трекера (Clockify, Toggl)
- **Helper-скрипт** `scripts/verify_rp_schema.py` — определяет эмпирически, какие имена полей (snake vs Camel) используются в `ResourcePlanning` для конкретного сервера
