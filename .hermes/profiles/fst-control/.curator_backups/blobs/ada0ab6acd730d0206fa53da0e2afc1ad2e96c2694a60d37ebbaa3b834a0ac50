# Cookbook: разведка MCP-эндпоинтов через live-probe

> «Не останавливайся на первом «нет» view — пробуй систематически.»

Этот reference — **рецепт разведки**, не каталог view. Каждый раз, когда ты
слышишь «view X возвращает 403 / 500 / 404 / SQL error / не те поля» —
**не пиши сразу «нет данных»**. Потрать 5-10 минут на `mcp_probe.py` по списку
кандидатов из таблицы ниже. Реальные данные часто лежат рядом.

## WorkFlow

1. **Не доверяй первому «N/A»**. Если view закрыт (403) — значит альтернативы
   может быть 2-3 штуки в том же namespace. Проверяй по `AccessForAll=true`:
   - `view_definition.AccessForAll` (логическое: «доступно всем»)
   - `view_definition.CanAdd / CanRemove` (косвенное: «не только админ-операции»)

2. **Один раз `mcp_probe.py --tool get_view --args '{"entityName":"<entity>","viewName":"<view>","limit":3}'`** на 5-10 candidate views каждый раз.

3. **Смотри:**
   - `CanAdd: true` или `AccessForAll: true` → **хороший кандидат**
   - `AccessForAll: false` И `CanAdd: false` → скорее всего **под admin**, не наш
   - `Error: 404 / 500 / SQL` → **не работает**, но попробуй другой view
   - `Error: 403 Forbidden` → **под admin**, есть смысл искать альтернативу

4. **Сравни реальные данные с тем, что ты хочешь получить.** Если view
   содержит нужные колонки, но формат не тот — это **лучше чем ничего**,
   и это +10 к вариантам отображения в JSON.

## Открытые view для Форсайт (live-probe 2026-08-07)

| View | Entity | Строк для 504-595 | Колонок | Решает |
|------|--------|-------------------|----------|--------|
| `ProjectHealthCostMy` | `Project` | 1 | 16 | Агрегат фин. данных, **но** `as_of_date` неясен |
| `ProjectHealthWorkload` | `Project` | 78 (месяцев) | 12 | Агрегат трудозатрат по профилю, не по проекту |
| `ProjectBudgetCompleteBusiness` | `Project` | 12 | **31** | **Полные фин. данные per КТ/контракт/дата** |
| `ProjectResourcePlan` | `Project` | 10 (в хвосте, за 600k строк) | 11 | **per-user per-date трудозатраты** |
| `MyProject` | `Project` | 1 | много | Базовые поля проекта |
| `AllProject` | `Project` | 100+ | много | Все проекты (включая admin-роли) |
| `MyPoint` | `Point` | 67 | много | КТ текущего пользователя |
| `AllPoint` | `Point` | 3000+ | много | Все КТ |
| `InContractMyProject` | `InContract` | 1 | много | Контракты в проекте (НЕТ `InContractActivity`) |
| `InContractAll` | `InContract` | 100+ | много | Все контракты |
| `AllMyPoint` | `Point` | 67 | много | Альтернатива `MyPoint` |
| `AllPayments` | `Payments` | 100+ | 7 | Все платежи (но `ProjectId` нет — текстовое `ActivityName`) |

## Закрытые view для Форсайт (live-probe 2026-08-07)

| View | Статус | Альтернатива |
|------|--------|--------------|
| `ResourcePlanning` | 403 Forbidden | `ProjectResourcePlan` (открыт) |
| `ResourcePlanningKp` | 403 Forbidden | `ProjectResourcePlan` (открыт) |
| `StatusReportBudget` | 403 Forbidden | `ProjectBudgetCompleteBusiness` (открыт) |
| `ApprovedBudget` | 403 Forbidden | `Project.ProjectBudgetGrade` (поле) |
| `ContractPlanSummaries` | 403 Forbidden | `ProjectBudgetCompleteBusiness` (открыт) |
| `ContractPlanSummariesValue` | 403 Forbidden | `ProjectBudgetCompleteBusiness` (открыт) |
| `ActivityFinanceLimit` | 403 Forbidden | (нет равноценной) |
| `ConsolidatedBudget` | 403 Forbidden | `ProjectBudgetCompleteBusiness` (открыт) |
| `StatusReportBudget` | 403 Forbidden | `ProjectBudgetCompleteBusiness` (открыт) |

## Probe-рецепт: «разведка view по категории»

Когда нужен определённый тип данных (финансы, трудозатраты, время и т.п.):

```bash
# 1. Сначала — список views для entity (через tools/list или describe_entity)
python3 scripts/mcp_probe.py --tool describe_entity \
  --args '{"entityName":"Project"}' | python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
sc = json.loads(d['result']['content'][0]['text'])
# print только views с AccessForAll=true
for v in sc.get('views', []):
    if v.get('AccessForAll'):
        print(v['ViewName'])
"

# 2. Проверить каждый candidate view
for v in ProjectResourcePlan ProjectBudgetCompleteBusiness ProjectHealthWorkload ProjectHealthCostMy; do
  python3 scripts/mcp_probe.py --tool get_view \
    --args "{\"entityName\":\"Project\",\"viewName\":\"$v\",\"limit\":3}" 2>&1 | head -5
done

# 3. Если view НЕ отдаёт нужные поля — проверить schema одной строки
python3 scripts/mcp_probe.py --tool get_view \
  --args '{"entityName":"Project","viewName":"ProjectResourcePlan","limit":1}' 2>&1 | \
  python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
sc = json.loads(d['result']['content'][0]['text'])
# list всех колонок
for col in sc.get('columns', []):
    print(col['field'], col['name'])
"
```

## Когда данных всё равно нет — 3 уровня fallback

| Уровень | Что пробовать | Пример |
|---------|---------------|--------|
| 1. **Open views** | `AccessForAll=true` views для нужной сущности | `ProjectResourcePlan`, `ProjectBudgetCompleteBusiness` |
| 2. **Агрегаты** | Views с месячной/проектной агрегацией | `ProjectHealthWorkload` (только по профилю), `ProjectHealthCostMy` (по проекту, но без даты) |
| 3. **Entity-level** | `get_entity_data(Project, data_id=<id>)` для конкретного проекта | Поля `ProjectBudgetGrade`, `DirectProjectCostsGrade`, `PresaleLimit` |

Если все три уровня ничего не дали — пиши «Нет данных» в отчёте.

## Pitfall #48 в figures

535 строк в `ProjectResourcePlan` для 503-152? **Не 535 потоков и N+1**. Один
HTTP-запрос с `limit=30000` → один фильтр в Python → сводка. **Это и есть
преимущество** открытых view с per-user per-date данными.

## Workflow «Probe → Extract → Render»

```
1. PROBE: enumerate 5-10 candidate views через mcp_probe.py
2. EXTRACT: найти тот, который открыт и содержит нужные колонки
3. RENDER: использовать его как источник для показателя отчёта
```

## Зафиксированные открытия 2026-08-07

Документ — история live-probe сессии. Фиксирует **что нашли и когда**:

| View | Проблема | Решение | Когда |
|------|----------|---------|-------|
| `MetaModel` / `Title` | `find_entity` возвращает 0, `get_entity_data(MetaModel, "1")` — SQL error | `get_entity_data("metamodel", data_id="Title")` после фикса 2026-08-07 | Утро 2026-08-07 |
| `ProjectResourcePlan` | `ResourcePlanning` view 403 | `ProjectResourcePlan` — открыт, per-user per-date | Утро 2026-08-07 |
| `ProjectBudgetCompleteBusiness` | `StatusReportBudget`/`ApprovedBudget` 403 | `ProjectBudgetCompleteBusiness` — открыт, 31 столбец | Утро 2026-08-07 |
| `ProjectHealthWorkload` | Не разделяет по проектам | Использовать как есть; ограниченно полезный | Утро 2026-08-07 |
| `ProjectHealthCostMy` | `as_of_date` отсутствует | Использовать `plan/forecast/deviation` как есть | До 2026-08-07 |

## Чек-лист для будущих сессий

Когда ты слышишь «view X возвращает 403 / 500 / 404 / SQL error»:

- [ ] **Не пиши сразу «нет данных»**. Проверь 5-10 candidate views.
- [ ] Ищи `AccessForAll=true` или `CanAdd=true` — это открытые view.
- [ ] Проверь `tools/list` ещё раз — может, после фикса появились новые view.
- [ ] Если не нашёл — fallback на `get_entity_data(Project, data_id=<id>)`.
- [ ] Если и там ничего — fallback на `ProjectHealthCostMy` (агрегат).
- [ ] Если все три уровня пусты — только тогда «Нет данных».

## Связанные references

- `references/forsight-mcp-quirks.md` — pitfall #47 (`ProjectBudgetCompleteBusiness`) и #48 (`ProjectResourcePlan`)
- `references/effort-data-403-recipe.md` — **ОБНОВЛЕН 2026-08-07** основной путь через `ProjectResourcePlan`
- `references/project-finance-budget-entities.md` — карта финансовых сущностей Форсайт
- `references/meta-model-pitfalls.md` — `MetaModel` через `get_entity_data("metamodel", data_id=...)`
