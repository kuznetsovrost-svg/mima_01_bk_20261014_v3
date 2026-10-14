# Playbook по фильтрам MCP в скилле `fst-project-health`

**Версия:** 1.0.0 — 2026-09-06
**Назначение:** единый справочник по всем фильтрам, которые
`fst-project-health` передаёт в `get_view`-вызовы MCP. Для каждого:
назначение фильтра, какие параметры поддерживаются view, характерные
объёмы выдачи (по данным прогона `fst-mcp-tester` 2026-09-06 на проекте
504-595), и связанные Pitfall'ы.

---

## Часть 1. Обзор всех фильтров

### 1.1. Сводная таблица

| View | Фильтр | Тип значения | Пример | Где в коде | Объём (504-595) |
|---|---|---|---|---|---|
| `Project/MyProject` | `ProjectId` | int | `4595` | `mcp_config.py::PROJECT_HEALTH_COST_MY_FILTERS` (шапка) | 12 строк |
| `Project/MyProject` | (без фильтра) | — | `{}` | `project_indicators.py::check_*` для 6.8/6.9/6.15 | 1 строка |
| `Project/_get_entity_data_` | (без фильтра) | — | `{}` | `project_indicators.py` (карточка проекта для 6.1, 6.2, и т.д.) | 1 объект |
| `Point/AllMyPoint` | `ProjectId` | int | `4595` | `run_all.py::ALL_MY_POINT_FILTERS` + `project_indicators.py` | 20 строк |
| `Point/AllFinancePoint` | `ProjectId` | int | `4595` | `project_indicators.py::check_financial_deadlines` (6.8) | 6 строк |
| `Project/ProjectResourcePlan` | `ProjectId` | int | `4595` | `mcp_config.py::PROJECT_RESOURCE_PLAN_FILTERS` | 196 строк |
| `Project/ProjectResourcePlan` | `accountid` + `startdate`/`enddate` | int + date | — | `project_indicators.py::check_cross_activity_overload` (6.7) | варьируется |
| `Project/ProjectResourcePlan` | `ProjectId` + `startdate`/`enddate` | int + date | — | `project_indicators.py::check_plan_effort` (6.4) | ≤ 2000 |
| `Project/ProjectBudgetCompleteBusiness` | `ProjectId` | int | `4595` | `mcp_config.py::PROJECT_BUDGET_FILTERS` (шапка) | 14 строк |
| `Project/ProjectBudgetCompleteBusiness` | `ProjectId` | int | `4595` | `project_indicators.py` (6.10, 6.11, 6.12, 6.13, 6.14, 6.16) | 14 строк |
| `InContract/InContractBudgetBusiness` | `ProjectId` | int | `4595` | `mcp_config.py::IN_CONTRACT_MY_PROJECT_FILTERS` (шапка) | 6 строк |
| `Project/ApprovedBudget` | `ActivityId` + `Year` | int + int | `4595`, `2026` | `project_indicators.py::check_approved_budget` (6.13, 6.15) | 1 строка |
| `Project/ProjectHealthCostMy` | `ProjectId` | int | `4595` | `mcp_config.py::PROJECT_HEALTH_COST_MY_FILTERS` | 1 строка |
| `Project/_get_entity_data_` (как `get_entity_data`) | `data_id` | int/str | `4595` | `mcp_config.py::get_project_property` (шапка, 6.1, 6.2, и т.д.) | 1 объект |

### 1.2. Уникальные параметры фильтров

Всего **8 уникальных имён параметров**:

1. `ProjectId` — самый частый. Числовой ID проекта.
2. `ActivityId` — числовой ID активности (= ID проекта в PMForesight).
3. `accountid` — числовой ID счёта/сотрудника (для 6.7 «перегрузка
   исполнителя» — ищем все проекты одного исполнителя).
4. `startdate` — ISO-дата начала периода (`YYYY-MM-DD`).
5. `enddate` — ISO-дата конца периода.
6. `Year` — год (int), для `ApprovedBudget`.
7. `data_id` — для `get_entity_data` (НЕ `get_view`).
8. `entityName` + `viewName` — обязательные, не «фильтр», а
   идентификаторы view (Pitfall: фильтр НЕ включает `entityName`,
   он передаётся отдельным полем в JSON-RPC).

---

## Часть 2. По view

### 2.1. `Project/MyProject` (расширенная карточка проекта)

**Что возвращает:** расширенные атрибуты проекта: `ProjectTypeName`,
`IsPresale`, `OwnerId`, `LeaderId`, `LifeCycleStage`, и т.п. — больше,
чем в `_get_entity_data_`.

**Фильтр:** `{"ProjectId": <int>}` — в шапке (`run_all.py`).
Используется **без фильтра** (`filters={}`) в `project_indicators.py`
для 6.8, 6.9, 6.15 — тогда view возвращает ВСЕ проекты организации
(нужно фильтровать в Python).

**Объём (504-595):** 12 строк (вероятно, родитель + дочерние проекты
или история переименований).

**Покрытие в скилле:** раздел 1 (шапка), 6.8, 6.9, 6.15.

---

### 2.2. `Project/_get_entity_data_` (псевдоним для `get_entity_data`)

**Что возвращает:** полные свойства одной сущности. Используется
как «карточка проекта» с фильтром `{}` — потому что `data_id` мы
передаём отдельно (через `project_id=...` в `fetch_with_cache`,
что внутри подставляется в `data_id`).

**Фильтр:** всегда `{}` (фильтрация через `data_id`).

**Объём:** 1 объект.

**Покрытие:** 6.1 (юрлицо), 6.2 (ЖЦ), 6.5, 6.7, 6.15, 6.16
(метаданные для расчёта).

**Pitfall #211:** исторически в `build_section_7()` пытались брать
`project["name"]` как ФИО пользователя → баг «N/A». Правильный путь —
JWT-парсинг (`get_current_user_from_token`).

---

### 2.3. `Point/AllMyPoint` (КТ уровня проекта)

**Что возвращает:** все КТ с `ParentEntityName="Project"` для
указанного проекта.

**Фильтр:** `{"ProjectId": <int>}` — обязательно.
Без фильтра view вернёт тысячи КТ по всем проектам организации.

**Объём (504-595):** 20 строк.

**Покрытие:** разделы 3, 5, 6.2, 6.3, 6.4, 6.5, 6.7, 6.13, 6.14,
6.15, 6.16.

**Pitfall #217:** НЕ путать с `AllFinancePoint` (там
`ParentEntityName="InContract"`, для 6.8).

---

### 2.4. `Point/AllFinancePoint` (финансовые КТ)

**Что возвращает:** финансовые КТ с `ParentEntityName="InContract"`
(привязаны к контрактам, не к проекту напрямую).

**Фильтр:** `{"ProjectId": <int>}` — обязательно.

**Объём (504-595):** 6 строк (финансовые КТ 504-595).

**Покрытие:** 6.8 «Соблюдение сроков финансовых КТ».

**Pitfall #214:** до v1.0.11 использовали `InContractBudgetBusiness`
(там были «Акт-4724», «Оплата-4724» — это ID финансовых сущностей, не КТ).
С v1.0.11 — только `Point/AllFinancePoint`.

---

### 2.5. `Project/ProjectResourcePlan` (ресурсный план)

**Что возвращает:** план/прогноз трудозатрат по исполнителям и
периодам (месяцам). Самая «тяжёлая» view.

**Поддерживает 3 комбинации фильтров:**

| Фильтр | Когда | Где |
|---|---|---|
| `{"ProjectId": <int>}` | общий случай | `mcp_config.py::PROJECT_RESOURCE_PLAN_FILTERS`, индикаторы 6.5, 6.6, 6.13, 6.14 |
| `{"ProjectId": <int>, "startdate": <iso>, "enddate": <iso>}` | когда нужны только плановые/факт в окне дат | `project_indicators.py::check_plan_effort` (6.4) |
| `{"accountid": <int>, "startdate": <iso>, "enddate": <iso>}` | для 6.7 «перегрузка исполнителя» — все проекты одного человека | `project_indicators.py::check_cross_activity_overload` |

**Объём (504-595):** 196 строк (без фильтра по датам).

**Покрытие:** разделы 1 (шапка), 6.3, 6.4, 6.5, 6.6, 6.7, 6.13, 6.14.

**Pitfall #196:** поле `projectid` в `ProjectResourcePlan` —
**lowercase**, без подчёркивания. НЕ `project_id`, НЕ `ProjectId`!

---

### 2.6. `Project/ProjectBudgetCompleteBusiness` (бюджет проекта)

**Что возвращает:** статьи бюджета с `budgettype`, `financeSourceId`,
суммами plan/fact/forecast.

**Фильтр:** `{"ProjectId": <int>}` — обязательно.

**Объём (504-595):** 14 строк.

**Покрытие:** разделы 1 (шапка), 6.10, 6.11, 6.12, 6.13, 6.14, 6.16.

**Особенности для 6.12:** берём строки с `budgettype="Доходный контракт"`
для amount и `budgettype="Расход ручной ввод"` + `fs=128` для НДС
(статья 611-13). Это **не баг системы** — НДС-строка логически
связана с доходным контрактом, но учтена как расход.

---

### 2.7. `InContract/InContractBudgetBusiness` (финансовый поток)

**Что возвращает:** статьи финансового потока по контрактам проекта
(`ActForecastSum`, `PayForecastSum`).

**Фильтр:** `{"ProjectId": <int>}` — обязательно.

**Объём (504-595):** 6 строк (вероятно, контракты 504-595).

**Покрытие:** 6.9 «Суммы актов и оплат».

**Pitfall:** `startdate`/`enddate` для этой view **НЕ задокументированы**
в `list_views`, но в коде скилла они не передаются (только `ProjectId`).

---

### 2.8. `Project/ApprovedBudget` (утверждённый бюджет по годам)

**Что возвращает:** утверждённые суммы по `Year` для указанной
активности.

**Фильтр:** `{"ActivityId": <int>, "Year": <int>}` — ОБА обязательны.

**Объём (504-595):** 1 строка (один год — текущий).

**Покрытие:** 6.13, 6.15.

**Особенность:** в `check_approved_budget` фильтр `Year=current_year`,
но в `check_kp_labels` (6.16) — только `ActivityId` (без `Year`),
тогда view возвращает все годы.

---

### 2.9. `Project/ProjectHealthCostMy` (финансовое здоровье)

**Что возвращает:** агрегаты `forecast`, `devcost`, `outallforecast`,
`plan`, `fact`, и др. — для старого раздела 6 (до v1.0.0).

**Фильтр:** `{"ProjectId": <int>}`.

**Объём (504-595):** 1 строка.

**Покрытие:** раздел 6 «Финансовый статус» (до v1.0.0, 3 показателя).
В v1.0.0+ — не основной, но используется как fallback.

---

## Часть 3. По параметру фильтра

### 3.1. `ProjectId` (int)

**Самый частый параметр.** Используется в 7 view: `MyProject`,
`AllMyPoint`, `AllFinancePoint`, `ProjectResourcePlan`,
`ProjectBudgetCompleteBusiness`, `InContractBudgetBusiness`,
`ProjectHealthCostMy`.

**Тип:** int (числовой ID проекта в PMForesight).

**Откуда брать:**
- Из `find_project_by_code.py` (поиск по коду → `project_id`).
- Из UI PMForesight (URL содержит `projectId=...`).
- Из переменной окружения `MCP_TEST_PROJECT_ID` для тестов.

**Pitfall #159:** `project_id` ≠ `accountid` — разные сущности.
`accountid` — это ID счёта/контракта, не проекта.

---

### 3.2. `ActivityId` (int)

Используется в `ApprovedBudget`. По смыслу = `ProjectId` (в PMForesight
«активность» = проект). Тип: int.

**Где:** `project_indicators.py::check_approved_budget`, `check_kp_labels`.

---

### 3.3. `accountid` (int)

Используется в `ProjectResourcePlan` для **6.7 «перегрузка исполнителя»**
— нужно достать все проекты одного человека.

**Тип:** int (ID сотрудника/счёта).

**Где:** `project_indicators.py::check_cross_activity_overload`.

**Пример:**
```python
fetch_with_cache(
    sid, "Project", "ProjectResourcePlan",
    filters={
        "accountid": accountid,
        "startdate": effective_start.isoformat(),
        "enddate": end_date.isoformat(),
    },
    project_id=project_id, limit=2000,
)
```

---

### 3.4. `startdate` / `enddate` (ISO date)

Используются в `ProjectResourcePlan` для ограничения окна дат.

**Формат:** `YYYY-MM-DD` (ISO 8601).

**Применение:**
- 6.4 «Плановые трудозатраты» — `startdate=today`, `enddate=today+1year`.
- 6.7 «Перегрузка исполнителя» — `startdate` от текущей даты,
  `enddate` до конца проекта.

**Пример:**
```python
filters={
    "ProjectId": project_id,
    "startdate": today_str,
    "enddate": one_year_later,
}
```

**Pitfall:** для `AllMyPoint`, `AllFinancePoint`, `InContractBudgetBusiness`
эти фильтры **НЕ передаются**, хотя могли бы (Pitfall: задокументированы,
но не используются). См. комментарий в `project_indicators.py`:
> «filter startdate/enddate НЕ задокументирован в list_views для
> AllMyPoint (хотя работает через live-call). Не добавляем».

---

### 3.5. `Year` (int)

Используется в `ApprovedBudget` (только там).

**Тип:** int (4 цифры, например `2026`).

**Где:** `project_indicators.py::check_approved_budget`.

**Пример:**
```python
filters={"ActivityId": project_id, "Year": dt.date.today().year}
```

---

### 3.6. `data_id` (int/str)

Используется в `get_entity_data` (НЕ в `get_view`).

**Тип:** int или str (числовой ID сущности).

**Pitfall #159:** для проекта это `project_id` (НЕ `accountid`).

---

## Часть 4. Характерные объёмы выдачи (504-595)

По данным прогона `fst-mcp-tester` 2026-09-06 (12 тестов, все ok):

| View | Объём | Размер payload (≈) | Время | Примечание |
|---|---|---|---|---|
| `MyProject` | 12 строк | небольшой | ~2 с | расширенная карточка |
| `_get_entity_data_` (Project) | 1 объект | средний | ~2 с | карточка со всеми полями |
| `AllMyPoint` | 20 строк | средний | ~700 мс | КТ проекта |
| `AllFinancePoint` | 6 строк | маленький | ~1 с | финансовые КТ |
| `ProjectResourcePlan` | **196 строк** | **большой** | ~1.4 с | самая тяжёлая view |
| `ProjectBudgetCompleteBusiness` | 14 строк | **большой** | **~3.5 с** | медленная (фильтр на стороне сервера?) |
| `InContractBudgetBusiness` | 6 строк | маленький | ~700 мс | финансовый поток |
| `ApprovedBudget` | 1 строка | маленький | ~500 мс | утверждённый бюджет |
| `ProjectHealthCostMy` | 1 строка | маленький | ~1.3 с | финансовое здоровье |
| `find_entity` (`name="MetaModel"`) | ≤ 5 items | маленький | ~500 мс | поиск |
| `find_entity` (`name="Title"`) | ≤ 5 items | маленький | ~500 мс | поиск |
| `initialize` | — | маленький | ~400 мс | handshake |

**Самые тяжёлые:**
- `ProjectResourcePlan` — 196 строк, может превышать `limit=1000`
  на крупных проектах.
- `ProjectBudgetCompleteBusiness` — мало строк (14), но **самый
  медленный** (~3.5 с) — видимо, тяжёлый JOIN на стороне сервера.

---

## Часть 5. Конвенции и стили

### 5.1. Именование лямбд-фильтров

В `mcp_config.py` определены 5 лямбд:

```python
PROJECT_HEALTH_COST_MY_FILTERS = lambda project_id: {"ProjectId": project_id}
PROJECT_RESOURCE_PLAN_FILTERS   = lambda project_id: {"ProjectId": project_id}
ALL_MY_POINT_FILTERS            = lambda project_id: {"ProjectId": project_id}
PROJECT_BUDGET_FILTERS          = lambda project_id: {"ProjectId": project_id}
IN_CONTRACT_MY_PROJECT_FILTERS  = lambda project_id: {"ProjectId": project_id}
```

Использовать вместо inline-фильтров для **консистентности**.

### 5.2. Inline-фильтры

В `project_indicators.py` (для `fetch_with_cache`) часто
используются inline-фильтры с дополнительными полями
(`startdate`/`enddate`, `Year`, `accountid`). Это нормально —
лямбды покрывают только базовый случай `ProjectId`.

### 5.3. Старый формат (DEPRECATED)

```python
# DEPRECATED (удалено 2026-09-01): формат ?<Field>=<id> в URL.
# Если найдёте — замените на *_FILTERS(pid).
```

Сейчас фильтры передаются как **поля верхнего уровня** в JSON-RPC
аргументах, а не как параметры URL. Старый формат больше не работает.

### 5.4. Обязательность фильтров

| View | Фильтр обязателен? | Что будет без фильтра |
|---|---|---|
| `Project/MyProject` | да (в шапке) / нет (в `project_indicators`) | вернёт все проекты организации (Pitfall из `mcp-filters-format.md`) |
| `Point/AllMyPoint` | да | вернёт тысячи КТ по всем проектам |
| `Point/AllFinancePoint` | да | аналогично |
| `Project/ProjectResourcePlan` | да | аналогично |
| `Project/ProjectBudgetCompleteBusiness` | да | аналогично |
| `InContract/InContractBudgetBusiness` | да | аналогично |
| `Project/ApprovedBudget` | да (`ActivityId`) | вернёт все активности |
| `Project/ProjectHealthCostMy` | да | вернёт все проекты |
| `Project/_get_entity_data_` | — (фильтрация через `data_id`) | — |

**Правило:** всегда фильтровать по `ProjectId`/`ActivityId`,
если view это поддерживает. Иначе — десятки тысяч строк.

---

## Часть 6. Pitfall'ы (по фильтрам)

1. **Pitfall #159** (`accountid` vs `projectid`): для `get_entity_data`
   это `data_id` = `project_id`. Никогда не путать с `accountid`.

2. **Pitfall #193** (фильтрация по `ProjectId`): для всех view,
   которые поддерживают фильтр, **всегда** передавать `ProjectId`.

3. **Pitfall #196** (`projectid` lowercase в `ProjectResourcePlan`):
   поле для фильтрации — `projectid` (lowercase), НЕ `project_id`,
   НЕ `ProjectId`. Сравнение: `str(row_projectid) == str(project_id)`.

4. **Pitfall #214**: для 6.8 — `Point/AllFinancePoint`, не
   `InContractBudgetBusiness`. `AllFinancePoint` фильтруется по
   `ProjectId` (Pitfall #216 — `ParentEntityName=InContract`).

5. **Pitfall #217**: `AllMyPoint` (parent=Project) ≠ `AllFinancePoint`
   (parent=InContract). Для 6.8 — только `AllFinancePoint`.

6. **DEPRECATED формат `?<Field>=<id>` в URL** — больше не
   поддерживается. Если найдёте в коде — заменить на inline-фильтр.

7. **Сравнение строкового и числового `ProjectId`** — сервер может
   вернуть `ProjectId` как `str` или `int`. Сравнивать через
   `str(row["ProjectId"]) == str(project_id)`.

---

## Часть 7. Сводка: какой индикатор использует какие фильтры

| Индикатор / раздел | View | Фильтр | Limit |
|---|---|---|---|
| Шапка (раздел 1) | `MyProject` | `{"ProjectId": project_id}` | 1000 |
| Шапка | `ProjectResourcePlan` | `{"ProjectId": project_id}` | 1000 |
| Шапка | `ProjectBudgetCompleteBusiness` | `{"ProjectId": project_id}` | 1000 |
| Шапка | `_get_entity_data_` (Project) | (data_id) | — |
| Раздел 3 | `AllMyPoint` | `{"ProjectId": project_id}` | 1000 |
| Раздел 4 | `ProjectHealthCostMy` + `MyProject` | `{"ProjectId": project_id}` | 100 |
| Раздел 5 | `AllMyPoint` | `{"ProjectId": project_id}` | (кеш из 3) |
| Раздел 6.1 | `_get_entity_data_` (Project) | (data_id) | — |
| Раздел 6.2 | `_get_entity_data_` + `AllMyPoint` | mixed | — |
| Раздел 6.3, 6.4 | `ProjectResourcePlan` | `{"ProjectId": project_id, "startdate": ..., "enddate": ...}` | 2000 |
| Раздел 6.5 | `ProjectResourcePlan` | `{"ProjectId": project_id}` | 2000 |
| Раздел 6.6 | `ProjectResourcePlan` | `{"ProjectId": project_id}` | 2000 |
| Раздел 6.7 | `ProjectResourcePlan` × N (по исполнителям) | `{"accountid": ..., "startdate": ..., "enddate": ...}` | 2000 |
| Раздел 6.8 | `AllFinancePoint` + `MyProject` | `{"ProjectId": project_id}` | 200 / 200 |
| Раздел 6.9 | `InContractBudgetBusiness` + `MyProject` | `{"ProjectId": project_id}` | 500 |
| Раздел 6.10, 6.11, 6.12 | `ProjectBudgetCompleteBusiness` | `{"ProjectId": project_id}` | 500 |
| Раздел 6.13, 6.14 | `ProjectBudgetCompleteBusiness` + `ProjectResourcePlan` | `{"ProjectId": project_id}` | 500 / 2000 |
| Раздел 6.15 | `ApprovedBudget` + `MyProject` | `{"ActivityId": project_id, "Year": current_year}` | 200 |
| Раздел 6.16 | `AllMyPoint` + `ProjectBudgetCompleteBusiness` | `{"ProjectId": project_id}` | 500 |
| Раздел 7 | `find_entity` (MetaModel, Title, Version) | — | 5 |

---

## Часть 8. Чек-лист перед добавлением нового фильтра

- [ ] Фильтр поддерживается view (проверить через `list_views`)?
- [ ] Тип значения совпадает (int vs str)?
- [ ] Сервер не возвращает 500/400 на пустой фильтр?
- [ ] Фильтр не ломает существующие тесты (Pitfall #193)?
- [ ] Если новый параметр (`startdate`/`enddate`/`Year`/...) — добавить
      в `mcp_config.py` лямбду (по конвенции)?
- [ ] Покрыть юнит-тестом (mock view)?

---

*Сгенерировано для скилла `fst-project-health`. Реальные объёмы — из
прогона `fst-mcp-tester` 2026-09-06 на проекте 504-595 (id=4595).*