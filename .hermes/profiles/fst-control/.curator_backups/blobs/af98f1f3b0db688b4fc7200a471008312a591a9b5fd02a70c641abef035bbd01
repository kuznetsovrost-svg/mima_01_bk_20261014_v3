# Архитектура связей в Форсайт ПМ Практике

> Подробная схема того, как сущности Форсайт связаны между собой, и почему
> большинство дочерних сущностей не имеет прямого FK на Project.

## Главный вывод

```
⚠️ В Форсайт ПМ Практике 1.0 (PMForesight MCP v3.2.4):

Большинство «дочерних» сущностей (Point, Payments, Risk, DocumentFile)
имеют FK НЕ на Project, а на Activity.

Исключение: ProjectId в схеме Point — это FK на ACTIVITY, не на Project.

Стандартный путь к данным проекта:
    Project → Activity → [Point / Payments / Risk / DocumentFile / ...]

Поэтому в каждом скилле, который анализирует дочерние сущности,
нужен шаг «получить список ActivityId проекта».
```

---

## Диаграмма архитектуры

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                         PROJECT                              │    │
│  │  ┌────────────────────────────────────────────────────────┐  │    │
│  │  │  ProjectId (bigint PK)                                  │  │    │
│  │  │  Code      (string, "504-595")                          │  │    │
│  │  │  Name      (string)                                     │  │    │
│  │  │  Description, Contractor, Owner, Leader, Administrator  │  │    │
│  │  │  ActivityPhaseId → ActivityPhase (FK, не Activity!)     │  │    │
│  │  │  StartPlan, FinishPlan, PlanSum, ForecastSum, FactSum  │  │    │
│  │  │  PortfolioId, ProgramId, CalendarPeriodId, ProfileId   │  │    │
│  │  └────────────────────────────────────────────────────────┘  │    │
│  │                            │                                  │    │
│  │                            │ «исторически Project ≈ Activity» │    │
│  │                            ▼                                  │    │
│  │  ┌────────────────────────────────────────────────────────┐  │    │
│  │  │                         ACTIVITY                         │  │    │
│  │  │  ┌──────────────────────────────────────────────────┐  │  │    │
│  │  │  │  ActivityId (bigint PK)                            │  │  │    │
│  │  │  │  Code     (string, "504-595")                      │  │  │    │
│  │  │  │  Name     (string)                                 │  │  │    │
│  │  │  │  ParentId → Activity (родитель)                   │  │  │    │
│  │  │  │  Owner, Leader, Responsible, Customer             │  │  │    │
│  │  │  │  ContractorId → Contractor (FK)                   │  │  │    │
│  │  │  │  CalendarPeriod, Profile                          │  │  │    │
│  │  │  └──────────────────────────────────────────────────┘  │  │    │
│  │  │             │       │        │            │              │  │    │
│  │  │             │       │        │            │              │  │    │
│  │  │   ┌─────────┘       │        │            │              │  │    │
│  │  │   │                 │        │            │              │  │    │
│  │  │   ▼                 ▼        ▼            ▼              │  │    │
│  │  │                                                       │  │    │
│  │  │  ┌────────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐  │  │    │
│  │  │  │   POINT     │ │ PAYMENTS │ │   RISK   │ │DOCUMENT │  │  │    │
│  │  │  │            │ │          │ │          │ │  FILE   │  │  │    │
│  │  │  │ PointId    │ │PaymentsId│ │  RiskId  │ │ FileId  │  │  │    │
│  │  │  │ Code       │ │ Date     │ │ Name     │ │ Name    │  │  │    │
│  │  │  │ Name       │ │ SumRub   │ │ Severity │ │ Url     │  │  │    │
│  │  │  │ PlanDate   │ │ Name     │ │ Status   │ │Document │  │  │    │
│  │  │  │ Forecast   │ │InvNumDate│ │ Desc     │ │  Id     │  │  │    │
│  │  │  │ FactDate   │ │Contractor│ │          │ │ DataId  │  │  │    │
│  │  │  │ ProjectId ⚠│ │ Activity │ │ProjectId⚠│ │Activity │  │  │    │
│  │  │  │ (→Activity)│ │   Id     │ │(→Activity)│ │   Id   │  │  │    │
│  │  │  │ ParentId   │ │CompanyId │ │ActivityId│ │AuthorId │  │  │    │
│  │  │  │   (→Act)   │ │FinanceId │ │ (→Act)   │ │PhaseId  │  │  │    │
│  │  │  └────────────┘ └──────────┘ └──────────┘ └─────────┘  │  │    │
│  │  │                                                       │  │    │
│  │  └────────────────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

⚠️ = FK на **Activity**, не на Project

---

## Сущности: какие имеют прямой FK на Project, какие — нет

### ✅ С прямым FK на Project (через `ProjectId` → Project)

| Сущность | Поле FK | Связь реально на |
|----------|---------|------------------|
| (нет таких) | — | — |

Прямого FK на Project в публичной схеме Форсайт **нет ни у одной сущности**.
Все связи идут через Activity.

### ⚠️ Без прямого FK на Project (только через `ActivityId` / `ParentId` / `ProjectId`→Activity)

| Сущность | Поле в схеме | Реально указывает на | Как фильтровать по проекту |
|----------|--------------|---------------------|------------------------------|
| `Point` | `ProjectId` | **Activity** (историч.) | `ParentId`/`ParentCode` в строке view |
| `Point` | `ParentId` | Activity | напрямую через `ParentId` |
| `Point` | `ActivityId` | Activity | напрямую через `ActivityId` |
| `Payments` | `ActivityId` | Activity | через `ActivityId` |
| `Risk` | `ProjectId` | **Activity** (предпол.) | аналогично Point |
| `DocumentFile` | `DataId` | Карточка (любая) | через `DataName`/`EntityTitle` |
| `Activity` | `ParentId` | Activity (родительская) | иерархия |

### 🤔 Особые сущности

| Сущность | Связь с Project | Примечание |
|----------|----------------|------------|
| `Project` | (корневая) | Сам является корнем |
| `Activity` | Через `Code` (формат `"<project>-<num>"`) | У одной Activity Code часто совпадает с Code родительского Project |
| `ProjectProfile` | Через `ProjectProfileAttribute` (M:N) | Связь многие-ко-многим |
| `Portfolio` | Через `Project.PortfolioId` | Не содержит FK на Project, а Project ссылается на Portfolio |
| `Program` | Через `Project.ProgramId` | Аналогично |
| `Document` | Через `DocumentActivityPhase`, `ProjectProfileDocument` | Справочник категорий документов |
| `MetaModel` | — | Служебная (настройки системы), не привязана к проектам |

---

## Как получить список `ActivityId` проекта

### В публичном API нет прямого «список Activity проекта».

Обходной путь — через `Point` view, где есть `ParentId` (FK на Activity) и
`ParentCode` (FK на Project через Code):

```python
point_view = mcp__fst_pmpractice__get_view(
    entityName="Point", viewName="AllMyPoint"
)

# Способ A: через ParentCode (надёжно, используется в скиллах)
activity_ids = set()
for r in point_view["data"]:
    if str(r.get("ParentCode", "")).strip() == "<project_code>":
        activity_ids.add(r.get("ParentId"))

# Способ B: через ProjectId в схеме (но он == ActivityId, см. парадокс)
# ActivityId = r["ProjectId"] в строке Point
```

### Альтернативы (если есть права админа)

- Прямой `get_view(Activity, <view>)` с фильтром по `ProjectId` в схеме Activity
- Прямой SQL-запрос к БД (вне MCP)

---

## Подводные камни (Pitfalls)

### 1. Парадокс имён `ProjectId`

⚠️ В схеме `Point` есть поле `ProjectId` (bigint). Но **это FK на Activity**, не на Project.

```sql
-- ❌ Неправильно: путаем ProjectId с ActivityId
SELECT * FROM Point WHERE ProjectId = 4595  -- это ActivityId, а не ProjectId!
-- Случайно может вернуть данные другого проекта, если у них совпадает ActivityId.

-- ✅ Правильно: фильтруем по человекочитаемому ParentCode
SELECT * FROM Point pt
JOIN Activity a ON pt.ParentId = a.ActivityId
WHERE a.Code = '504-595'
```

**Защита:** всегда используй `ParentCode` (человекочитаемый) вместо `ProjectId` в схеме
Point. Для других сущностей (`Payments`, `Risk`) — используй полученный `ActivityId`.

### 2. Несколько Activity на один Project

В норме у Project одна основная Activity с тем же Code. Но бывают случаи:

- Project содержит несколько дочерних Activity (иерархия)
- Activity переименована или перекодирована (Code старый ≠ Code новый)
- Project в архиве, но Activity активна (или наоборот)

**Защита:** при сборе `activity_ids` не останавливайся на первом — собирай **set()** всех
ParentId, удовлетворяющих фильтру по `ParentCode`.

### 3. View может быть пустым из-за прав

`get_view(Point, AllMyPoint)` возвращает только точки, на которые у тебя есть
права. Если проект чужой и тебе не назначены роли — view будет пустым.

**Защита:** если `activity_ids` пустой после фильтра по `ParentCode`, попроси
пользователя либо подтвердить ProjectId, либо дать хотя бы один `ActivityId` явно.

### 4. Code vs Id — не путать!

- `Code` — человекочитаемый артикул (`"504-595"`)
- `ProjectId` — числовой PK в таблице `Project`
- `ActivityId` — числовой PK в таблице `Activity`
- `PointId` — числовой PK в таблице `Point`
- Все `*Id` — **bigint**, передаются в API **строкой цифр**
- `Code` — **строка** с дефисом, **не передаётся в get_entity_data/save_entity**

---

## Шаблон для скиллов, работающих с дочерними сущностями

```python
def get_project_children(entity_name: str, project_code: str) -> list[dict]:
    """Получить дочерние сущности проекта (Point / Payment / Risk / и т.д.).

    Args:
        entity_name: имя сущности ("Point", "Payments", "Risk", ...)
        project_code: код проекта ("504-595")

    Returns:
        Список записей, принадлежащих проекту
    """
    # Шаг 1: получить ActivityIds проекта через Point view
    point_view = mcp__fst_pmpractice__get_view(
        entityName="Point", viewName="AllMyPoint"
    )
    activity_ids = {
        r["ParentId"]
        for r in point_view["data"]
        if str(r.get("ParentCode", "")).strip() == project_code
    }

    if not activity_ids:
        return []  # нет КТ — возможно, нет и других дочерних сущностей

    # Шаг 2: получить все записи дочерней сущности
    entity_view = mcp__fst_pmpractice__get_view(
        entityName=entity_name, viewName=f"All{entity_name}"
    )

    # Шаг 3: отфильтровать по ActivityId
    return [
        r for r in entity_view["data"]
        if r.get("ActivityId") in activity_ids
    ]
```

---

## Сущности трудозатрат: ResourcePlanning и связанные

### Иерархия сущностей трудозатрат

```
ResourcePlanning (Ресурсное планирование)
  ├─ детальная сущность: одна запись = один сотрудник + один день + один Point/Activity
  ├─ содержит planning_hours, planning_hours_kp
  └─ привязка через ActivityId (FK на Activity, НЕ на Project)

ResourcePlanningKp (Прогнозные трудозатраты)
  ├─ прогнозный аналог ResourcePlanning
  ├─ привязка через PointId (FK на Point)
  ├─ содержит planning_hours, participation (% привлечения)
  └─ используется для plan-vs-fact анализа

resourceplanningfact_userview (Фактические затраты)
  └─ фактические трудозатраты (заполняется по результатам работы)

ProjectHealthWorkload (агрегат)
  └─ помесячный план/факт/прогноз по проекту
  └─ НЕ детализирован по сотрудникам
  └─ view доступен через get_view(Project, ProjectHealthWorkload)

Load (Загрузки)
  ├─ источник данных о трудозатратах
  ├─ содержит SourceDate, SourceUrl, Success, IsUndone
  └─ служебная сущность для импорта данных
```

### Схема `ResourcePlanning` (10 полей)

| Поле | Назначение | Связь |
|------|-----------|-------|
| `ResourcePlanningId` | PK | — |
| `ActivityId` | Сущность | FK на **Activity** ⚠️ не на Project |
| `SpecializationId` | Специализация | FK на Specialization |
| `AccountId` | Сотрудник / Ресурс | FK на Account |
| `planning_date` | День планирования | date |
| `planning_hours` | Запланированные часы | numeric |
| `planning_hours_kp` | Запланированные часы КП | numeric |
| `batchid` | Идентификатор изменения | uuid |
| `ChangeDate` | Дата изменения | timestamp |
| `ChangeAuthorId` | Автор изменения | FK на Account |

### Схема `ResourcePlanningKp` (13 полей)

| Поле | Назначение |
|------|-----------|
| `ResourcePlanningKpId` | PK |
| `AccountId` | Назначение (FK) |
| `RoleId` | Роль (FK на Role) |
| `SpecializationId` | Специализация |
| `planning_hours` | Часы, план |
| `participation` | % привлечения, план |
| `manual` | Ручное планирование (boolean) |
| `planning_date` | Дата |
| **`PointId`** | Этап / работа (FK на **Point**) |
| `CreationDate` / `ChangeDate` | timestamps |
| `CreationAuthorId` / `ChangeAuthorId` | FK на Account |

### ⚠️ Та же архитектурная проблема: FK не на Project

`ResourcePlanning` и `ResourcePlanningKp` **не имеют прямого FK на Project** —
только на `Activity` / `Point`. Поэтому стандартный путь тот же:

```
Project
  └─ Activity
       ├─ ResourcePlanning (ActivityId)
       └─ ResourcePlanningKp (через PointId → Activity)

⚠️ Парадокс имён — поле ProjectId в Point в схеме означает ActivityId.
Поэтому цепочка для трудозатрат проекта:
  Project → Activity → Point → ResourcePlanningKp
                      └─→ ResourcePlanning
```

### Агрегатные views для трудозатрат

| View | Что содержит | Доступ |
|------|-------------|--------|
| `ProjectHealthWorkload` | Помесячный план/факт/прогноз по проекту (часы) | ✅ открыт |
| `ResourcePlanning` (view) | Все ResourcePlanning-записи | ⚠️ 403 для обычных пользователей |
| `ResourcePlanningKp` (view) | Все прогнозные трудозатраты | ⚠️ 403 для обычных пользователей |
| `PointToMeToDo`, `AllMyPoint` | КТ с распределением ролей | ✅ открыт |

### Алгоритм получения трудозатрат по ProjectId

```python
def get_project_effort(project_code: str) -> dict:
    """Получить трудозатраты проекта."""
    # Шаг 1: получить ActivityIds проекта через Point view
    point_view = mcp__fst_pmpractice__get_view(
        entityName="Point", viewName="AllMyPoint"
    )
    activity_ids = {
        r["ParentId"]
        for r in point_view["data"]
        if r.get("ParentCode") == project_code
    }
    point_ids = {
        r["PointId"]
        for r in point_view["data"]
        if r.get("ParentCode") == project_code
    }

    # Шаг 2A: агрегат через ProjectHealthWorkload (доступен всем)
    workload = mcp__fst_pmpractice__get_view(
        entityName="Project", viewName="ProjectHealthWorkload"
    )
    project = mcp__fst_pmpractice__get_view(
        entityName="Project", viewName="MyProject"
    )
    project_data = next(
        p for p in project["data"] if p["Code"] == project_code
    )
    # В workload строки привязаны к projectprofileid, не к ProjectId напрямую
    project_hours = [
        r for r in workload["data"]
        if r.get("projectprofileid") == project_data.get("ProjectProfileId")
    ]

    # Шаг 2Б: детальные через ResourcePlanning (требует admin прав)
    # ⚠️ View запрещён для обычных пользователей (403)
    # Только для администраторов Форсайт

    # Шаг 2В: детальные через ResourcePlanningKp (привязка к Point)
    # ⚠️ Тоже запрещён для обычных пользователей
    return {
        "activity_ids": list(activity_ids),
        "point_ids": list(point_ids),
        "monthly_aggregate": project_hours,  # всегда доступно
        # "detailed_hours": [...]  # только для админов
    }
```

### Доступные vs закрытые данные

| Уровень детализации | Источник | Доступ |
|--------------------|----------|--------|
| **Помесячный план/факт/прогноз по проекту** | `ProjectHealthWorkload` view | ✅ всем |
| **Детальные КТ → сотрудник → часы** | `ResourcePlanningKp` view | ⚠️ админам |
| **Детальные сотрудник → день → часы** | `ResourcePlanning` view | ⚠️ админам |
| **Фактические трудозатраты** | `resourceplanningfact_userview` | ⚠️ админам |

Для обычного пользователя **единственный способ** увидеть трудозатраты — это
view `ProjectHealthWorkload` (агрегат по месяцам, без разбивки по людям).

---

## Что в других reference-файлах

| Файл | Содержание |
|------|------------|
| `mcp-api-quirks.md` | Pydantic-ошибки, формат дат, save_entity, MetaModel |
| `tool-catalog.md` | Полная таблица 9 tools с описанием каждого |
| `documents-and-files.md` | Как искать Паспорт / Отчёт / Протокол через DocumentFile |
| `project-search-workflow.md` | Подробный procedure «найти проект по подстроке имени» |
| `points-by-project-recipe.md` | Готовая функция list_points_of_project() + шаблон отчёта |
| **`project-architecture.md`** | ← этот файл |

## Связь со скиллами

| Скилл | Использует эту архитектуру |
|-------|-----------------------------|
| `fst-pmpractice` | Содержит секцию «Архитектура связей» в SKILL.md |
| `project-search` | Находит ProjectId, далее см. выше |
| `project-timing-control` | Фильтрует Point по `ParentCode` (обходит проблему) |
| `project-payment-schedule` | Получает `ActivityId` через Point view, фильтрует Payments |
| будущие скиллы | Следовать шаблону выше |
