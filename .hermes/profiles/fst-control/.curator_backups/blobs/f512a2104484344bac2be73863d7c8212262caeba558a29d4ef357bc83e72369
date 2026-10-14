---
name: project-search
description: "Use when the user wants to find a Foresight PM Practice project by name (or part of it), asks 'найди проект', 'какой ProjectId у проекта', 'поиск проекта по имени', 'project search', 'look up project'. Loads when user gives a project Code, partial Name, or asks to find a project matching some criteria. Searches via get_view(Project, MyProject/AllProject) with standard `filters={...}` format (live-probe 2026-09-01), filters results by Code or Name substring, asks user to disambiguate when >1 match."
version: 2.0.0
author: Hermes Agent + Rost
license: MIT
platforms: [linux, macos, windows]
changelog:
  - "2.0.0 (2026-09-01): MAJOR UPDATE. Migrated to standard `filters={...}` format (replaces old `?<Field>=<value>` in URL). Live-probe 2026-09-01: `get_view({entityName: 'Project', viewName: 'MyProject', filters: {UserAccount: 120872}, limit: 100})` works correctly. Views `MyProject` and `AllProject` support filters: UserAccount (@UserAccount), ProjectProfileId (@ProjectProfileId). Updated examples to use `mcp_call(sid, 'tools/call', ...)` format instead of deprecated `mcp__fst_pmpractice__get_view` namespace. Updated all examples to use new format. Added link to `references/mcp-filters-format.md` in companion skill `mcp-server-probing`."
  - "1.0.0 (2025-07-29): Initial release."
metadata:
  hermes:
    tags: [mcp, pmpractice, foresight, project, search, lookup, ru, filters]
    related_skills: [fst-pmpractice, project-timing-control, project-payment-schedule, fst-project-health, mcp-server-probing]
---

# Project Search (project-search)

## Overview

Скилл для **поиска ProjectId по имени (Name), коду (Code) или фрагменту** в Форсайт ПМ Практике.
Загружай, когда пользователь говорит:

- «найди проект ...»
- «какой ProjectId у проекта ...?»
- «найди проект, где в названии ...»
- «поиск проекта по имени»

После нахождения ProjectId **не иди дальше** — это задача `project-timing-control`, `project-payment-schedule`, `fst-project-health` или других скиллов.

## When to Use

Загружай, когда пользователь:
- Знает имя проекта (хотя бы приблизительно) и хочет его ProjectId
- Знает Code проекта (формат `"504-595"`)
- Спрашивает «найди проект, где ...»

**Не загружай** для:
- Получения списка ВСЕХ проектов (используй `get_view` напрямую)
- Поиска Activity, Point, Risk и т.д. (для каждой сущности свой подход)

## ⚠️ Архитектурная особенность

```
Project
  └─ Activity  ← реальный контейнер всех дочерних сущностей
       ├─ Point
       ├─ Payments
       ├─ Risk
       └─ DocumentFile
```

У большинства сущностей **нет прямого FK на Project** — только на Activity.
Поэтому после нахождения `ProjectId` может понадобиться шаг «получить список ActivityId»
для дальнейшей работы. Подробнее — в секции «Архитектура связей» базового скилла `fst-pmpractice`.

## Доступные views (live-probe 2026-09-01)

| View | Описание | Поддерживаемые фильтры |
|------|----------|------------------------|
| `MyProject` | Мои проекты (где пользователь = Куратор/РП/...) | `UserAccount`, `ProjectProfileId` |
| `AllProject` | Все проекты (109 на 2026-09-01) | `UserAccount`, `ProjectProfileId` |

**Структура строк** (MyProject/AllProject): `id`, `IndicatorTitle`, `ProjectId`, `Code`, `Name`, `ActivityPhaseId`, `ActivityPhaseName`, `StartPlan`, `FinishPlan`, `ProjectLeader`, `ProjectOwner`, `PortfolioId`, `PortfolioName`, `MyRole`, `ProjectProfileId`, ...

## ⚠️ Формат вызова (2026-09-01)

**Используй стандартный формат `filters={...}`** (НЕ `?ProjectId=` в URL — старый формат DEPRECATED).

```python
# ✅ ПРАВИЛЬНО (с 2026-09-01):
r = mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "MyProject",        # или "AllProject"
    "filters": {"UserAccount": 120872},  # опционально
    "limit": 100,
    "offset": 0,
})

# ❌ НЕПРАВИЛЬНО (DEPRECATED):
r = mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "MyProject?UserAccount=120872",  # НЕ работает
    "limit": 100,
})
```

**Подробнее:** `references/mcp-filters-format.md` в скилле `mcp-server-probing`.

## Алгоритм

```
1. ПОЛУЧИТЬ СПИСОК ПРОЕКТОВ
   mcp_call(sid, "get_view", {
       "entityName": "Project",
       "viewName": "MyProject",        # сначала MyProject
       "filters": {"UserAccount": <user_id>},  # опционально
       "limit": 1000,
   })
   fallback: get_view(Project, AllProject)  # если MyProject пуст
   → массив projects

2. ПОИСК ПО ПОДСТРОКЕ (клиентский, Python)
   matches = [
       r for r in projects
       if SUBSTRING.lower() in str(r.get("Code") or "").lower()
       or SUBSTRING.lower() in str(r.get("Name") or "").lower()
   ]

3. ВЕТВЛЕНИЕ ПО КОЛИЧЕСТВУ СОВПАДЕНИЙ

   3a. len(matches) == 0
       → "Ничего не найдено"
       → показать 3-5 ближайших по префиксу Code
       → попросить уточнить запрос

   3b. len(matches) == 1
       → ProjectId = matches[0]["ProjectId"]
       → вернуть пользователю сразу

   3c. len(matches) > 1
       → задать уточняющий вопрос (см. ниже)

4. ОБРАБОТКА ОТВЕТА ПОЛЬЗОВАТЕЛЯ
   4a. Похоже на Code (формат "<NNN>-<NNN>")
       → точное совпадение по полю Code
   4b. Целое число от 1 до len(matches)
       → ProjectId = matches[int(choice)-1]["ProjectId"]
   4c. Похоже на подстроку Name
       → перефильтровать matches, вернуться к шагу 3
   4d. Иначе
       → "Не понял. Пришли Code или номер."
```

## Уточняющий вопрос пользователю (шаг 3c)

```
Найдено несколько проектов с "<substr>" в названии:

| # | Code      | Name                              |
|---|-----------|-----------------------------------|
| 1 | 501-682   | ФГК Адаптация ИС УПД              |
| 2 | 504-034   | ФГК Сопровождение 2026-2027       |
| 3 | 501-610   | ФГК Сопровождение 2023-2026       |

Знаешь ли ты Code проекта?
- Если да — пришли Code (например, 501-682).
- Если нет — выбери номер из таблицы (1, 2 или 3) или пришли часть названия.
```

## Возврат результата

Когда ProjectId однозначно определён, агент отвечает:

```
ProjectId = 4595
Это проект «Космодром Жуковский внедрение ИСУП» (Code: 504-595).
```

Опционально добавить контекст из view (если есть в `data`):
- Стадия (`ActivityPhaseName`)
- Руководитель (`ProjectLeader`)
- Владелец (`ProjectOwner`)
- Даты `StartPlan` / `FinishPlan`
- Портфель (`PortfolioName`)

## Edge cases

| Случай | Как обрабатывать |
|--------|------------------|
| `Code` в нестандартном формате (`501/682`, `501.682`) | Нормализовать: `/` и `.` → `-`, потом искать |
| Пользователь меняет решение | Каждый ответ пользователя → новый проход через шаг 3-4 |
| Подстрока пустая или пробельная | Не запускать поиск, попросить ввести имя |
| View `MyProject` пустой | Fallback на `AllProject`, иначе сообщить «нет доступа к проектам» |
| Несколько десятков совпадений | Ограничить таблицу 10 строками + «и ещё N, уточни запрос» |

## Пример вызова

```python
# Шаг 1: получить список проектов (MyProject или AllProject)
r = mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "MyProject",
    "filters": {},  # без фильтра
    "limit": 1000,
})
projects = r.get("data", [])

# Шаг 2: поиск по подстроке
SUBSTRING = "ФГК"
matches = [
    r for r in projects
    if SUBSTRING.lower() in str(r.get("Code") or "").lower()
    or SUBSTRING.lower() in str(r.get("Name") or "").lower()
]

if len(matches) == 1:
    project_id = matches[0]["ProjectId"]
    print(f"ProjectId = {project_id}")
elif len(matches) > 1:
    # Задать вопрос пользователю, дождаться ответа
    # ...
    # При ответе "2" → matches[1]["ProjectId"]
    # При ответе "501-682" → найти точное совпадение по Code
```

## Live-probe пример (2026-09-01)

```python
# Получили 11 проектов через MyProject
r = mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "MyProject",
    "filters": {},
    "limit": 100,
})
projects = r["data"]
# Пример строки:
# {
#   "ProjectId": 4595,
#   "Code": "504-595",
#   "Name": "Космодром Жуковский внедрение ИСУП ",
#   "ActivityPhaseName": "Инициирование",
#   "ProjectLeader": "Кузнецов Ростислав Владимирович",
#   "MyRole": "Куратор, Руководитель, Администратор, ..."
# }

# Поиск "504-595":
matches = [p for p in projects if "504-595" in str(p.get("Code"))]
# → 1 совпадение: ProjectId = 4595
```

## Связь с другими скиллами

- **Базовый:** `fst-pmpractice` — формат вызовов, форматы данных
- **После нахождения ProjectId:**
  - `project-timing-control` — анализ сроков проекта
  - `project-payment-schedule` — график платежей проекта
  - `fst-project-health` — генерация полного отчёта о здоровье проекта
- **Поиск Activity:** делается через `Point` view по `ParentCode`
- **MCP-формат:** `mcp-server-probing` — playbook по формату `filters={}`

## Verification Checklist

- [ ] View `MyProject` или `AllProject` получен через `get_view` с `filters={}`
- [ ] Поиск регистронезависимый (по полям `Code` и `Name`)
- [ ] При >1 совпадении задан уточняющий вопрос
- [ ] Ответ пользователя корректно интерпретирован (Code / число / подстрока)
- [ ] Возвращён `ProjectId` + `Code` + `Name`
- [ ] Если пользователь знает точный Code — путь через Code короче
- [ ] Старый формат `?<Field>=<value>` НЕ используется
