# Project/ProjectParameter — reference card

**Дата:** 2026-09-02
**Источник:** live-probe при разработке indicator 6.1 «Юрлицо» в `fst-project-health`.

`Project/ProjectParameter` — «недокументированный» view с domain-specific данными проекта, **отсутствующими** в `MyProject` / `AllProject`. Не поддерживает server-side `ProjectId` фильтр — возвращает все проекты (~22), фильтровать клиентом через `code`.

## Поля (live-probe 2026-09-02, 504-595)

| Поле | Тип | Пример | Назначение |
|------|-----|--------|-----------|
| `code` | str | `'504-595'` | Код проекта (lowercase!) |
| `name` | str | `'Космодром Жуковский внедрение ИСУП'` | Название |
| `activityphase` | str | `'Инициирование'` | Стадия ЖЦ (lowercase!) |
| `activityphaseid` | int | `40032` | ID стадии |
| `leader` | str | ФИО | Руководитель (lowercase!) |
| `owner` | str | ФИО | Владелец (lowercase!) |
| `administrator` | str | ФИО | Администратор (lowercase!) |
| `creationauthor`, `changeauthor` | str | ФИО | Авторы (lowercase!) |
| `creationdate`, `changedate` | date | `2026-07-27T...` | Даты создания/изменения |
| **`ProjectCompanyNames`** | str | `'Проектная ПРАКТИКА'` | **Юрлицо проекта** ⭐ |
| **`ProjectBudgetGrade`** | float | `54_000_000.0` | **Грейд бюджета проекта** (₽) ⭐ |
| **`DirectProjectCostsGrade`** | float | `32_000_000.0` | **Грейд прямых затрат** (₽) ⭐ |
| **`ContractorName`** | str | `'АО ЦентрКосмодромСтрой'` | **Контрагент/подрядчик** ⭐ |
| **`PresaleStateName`** | str | `'Активен'` / `'Заморожен'` | Состояние пресейла |
| `PresaleClosedDate`, `PresaleRegisterDate` | date | | Даты пресейла |
| `ProbabilitySaleName` | str | `'10% - Заказчик одобрил...'` | Вероятность продажи |
| `ReportClosingDate` | date | `2026-05-31T...` | Дата закрытия отчёта |
| `RequestSourceName` | str | `'Повторная продажа'` | Источник запроса |
| `controlsubject` | str | `'Амурская область'` | Контролирующий субъект |
| `controlsubjectid` | int | `295` | ID субъекта |
| `portfolioid`, `portfolioname` | int, str | `4594`, `'904-594. Портфель...'` | Портфель |
| `projecttype`, `projecttypeid` | str, int | `'Коммерческий '`, `15` | Тип проекта |
| `priority`, `priorityid` | str, int | `'Обычный'`, `2` | Приоритет |
| `strategicdirection`, `strategicdirectionid` | str, int | | Стратегическое направление |
| `IndicatorColor`, `IndicatorId`, `IndicatorTitle` | | `#ff5940`, `3`, `'Просрочено'` | Индикатор |
| `PhaseFinish_*`, `ProjectStart_*` | date, str | | Доп. индикаторы по фазам |
| `projectclose_plandate`, `projectstart_plandate` | date | | Плановые даты |
| `phasefinish_*` | date | | Факт/план/прогноз окончания фазы |

## Доступ

```python
r = mcp_call(sid, "get_view", {
    "entityName": "Project",
    "viewName": "ProjectParameter",
    "filters": {},  # НЕ фильтруем через сервер!
    "limit": 200,
})
# Client-side фильтр:
target = next(
    (p for p in r.get("data", [])
     if str(p.get("code", "")).strip() == project_code),
    None
)
```

## Отличие от `MyProject` / `AllProject`

| Поле | MyProject | ProjectParameter |
|------|:---:|:---:|
| `Code`, `Name`, `ActivityPhaseName` | ✅ | ✅ (но lowercase: `code`, `name`, `activityphase`) |
| `ProjectId`, `MyRole`, `PortfolioId` | ✅ | ❌ |
| **`ProjectCompanyNames`** | ❌ | ✅ |
| **`ProjectBudgetGrade`** | ❌ | ✅ |
| **`DirectProjectCostsGrade`** | ❌ | ✅ |
| **`ContractorName`** | ❌ | ✅ |
| Фильтр `ProjectId` | ✅ | ❌ |

**Рекомендация:** использовать `MyProject` / `AllProject` для общих данных (ProjectId, роли, портфели), а `ProjectParameter` — для domain-specific полей (юрлицо, грейд, контрактор).

## Сценарии использования (в разработке)

| Сценарий | Какое поле | Возможный потребитель |
|----------|-----------|------------------------|
| Indicator 6.1 «Юрлицо проекта указано» | `ProjectCompanyNames` | `fst-project-health` ✅ |
| Indicator 6.13 «Бюджет проект/пресейл» | `ProjectBudgetGrade`, `DirectProjectCostsGrade` | `fst-project-health` (planned) |
| Проверка контрагента для проекта | `ContractorName` | `project-payment-schedule` (planned) |
| Отображение стадии ЖЦ | `activityphase`, `activityphaseid` | `fst-project-health` indicator 6.2 ✅ |

## Чего НЕТ в ProjectParameter

- `MyRole` (роль текущего пользователя в проекте) → только в `MyProject`
- `ProjectId` напрямую (есть `id` — но это sequence, НЕ ProjectId!) → используй `code` для поиска
- Фильтр `ProjectId` → фильтруй клиентом
