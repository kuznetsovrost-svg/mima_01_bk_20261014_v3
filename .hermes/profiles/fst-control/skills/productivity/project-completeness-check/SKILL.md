---
name: project-completeness-check
description: "Use when the user asks to verify/check the completeness of a Foresight PM Practice project ('проверь заполнение проекта', 'полнота проекта', 'всё ли заполнено', 'проверить проект X', 'completeness check'). Generates a fixed-size table of indicators (Owner, Leader, Паспорт, Паспорт на стадии, Трудозатраты актуальны, Корректность графика платежей, ...) with Да/Нет/Нет-категория (Информационное/Существенное/Критическое) verdicts per indicator. Each indicator maps to a precise Форсайт entity check (OwnerId, LeaderId, ActivityPhaseId + DocumentFile, ResourcePlanning/Kp, ContractPlanSummaries/Value)."
version: 2.0.0
changelog:
  - "2.0.0 (2026-09-01): MAJOR UPDATE. Migrated to standard `filters={...}` format. Live-probe 2026-09-01: `get_view({entityName: ..., viewName: ..., filters: {ProjectId: ...}, limit: 100})` works for all views. Replaces deprecated `mcp__fst_pmpractice__get_view` namespace and `?Field=value` URL format. See `references/mcp-filters-format.md` in `mcp-server-probing` skill.
author: Hermes Agent + Rost
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [mcp, pmpractice, foresight, project-completeness, audit, check, validation, ru]
    related_skills: [fst-pmpractice, project-search, project-timing-control, project-effort-plan, project-effort-write, project-payment-schedule]
---

# Project Completeness Check (project-completeness-check)

## Overview

Скилл для **проверки полноты заполнения проекта** Форсайт ПМ Практики.
Формирует **таблицу фиксированного размера** с показателями, где каждая
строка — отдельный индикатор с вердиктом Да/Нет (или с категорией замечания).

Загружай, когда пользователь говорит:

- «Проверь заполнение проекта X»
- «Полнота проекта», «Всё ли заполнено»
- «Что не заполнено в проекте 504-595?»
- «Составь чек-лист по проекту»
- «Audit project N», «Completeness check»

⚠️ **Это итеративный скилл.** Показатели добавляются по одному, каждый — с
live-проверкой на боевых данных. Не пытайся добавить все показатели сразу —
работай с теми, что нужны пользователю сейчас.

## Граф жизненного цикла проекта

```
1) Пресейл
2) Инициирование
3) Подготовка
4) Реализация
5) Завершение
6) Архив
```

⚠️ Это **линейный граф** — каждая следующая стадия «старше» предыдущей.
Для проверок «≤ N» используется **порядковый номер** стадии (1..6). Маппинг
имени → номер живёт в коде как словарь `PHASE_ORDER`.

```python
PHASE_ORDER = {
    "Пресейл": 1, "Инициирование": 2, "Подготовка": 3,
    "Реализация": 4, "Завершение": 5, "Архив": 6,
}
```

## Категории замечаний (стандартные)

| Категория | Цвет | Когда применять |
|-----------|------|------------------|
| **Информационное** | Синий | Разница в пределах допуска / не критично |
| **Существенное** | Жёлтый | Разница заметна, но не блокирует |
| **Критическое** | Красный | Разница блокирует / требует немедленных действий |

⚠️ **Пороги** для каждого показателя — свои. Не пытайся выводить категорию
из абсолютной суммы — она зависит от контекста показателя.

## Формат финальной таблицы

| # | Показатель | Результат | Деталь |
|---|------------|-----------|--------|
| 1 | Owner (OwnerId) | Да / Нет | ФИО или «не заполнено» |
| 2 | РП назначен (LeaderId) | Да / Нет | ФИО или «не заполнено» |
| 3 | Паспорт готов на стадии Инициирование | Да / Нет | Подробности ниже |
| 4 | Актуальность данных по трудозатратам | Да / Нет | Подробности ниже |
| 5 | Корректность графика платежей | Да / Нет[категория] | Да / Нет-Информационное/Существенное/Критическое |
| 6 | Прогноз по окончании фин.результат < 0 | Да / Нет[Критическое] | `ProjectHealthFostMy.forecast` |
| 7 | Отклонение текущей стоимости от плана > 1 М | Да / Нет[Критическое] | mixed vs план |
| 8 | Уменьшение фин.результата от планового > 2 М | Да / Нет[Критическое] | `plan −forecast > 2 М` |
| 9 | Актуальность прогнозов по КТ проекта (превентивный) | Да / Нет[категория] | КТ с `ForecastDate < today`, статусы по диф |
| 10 | Технические данные отчёта (метаданные) | — | Пользователь, версии, титул системы, URL_MFP |
| … | … | … | … |

## Показатели

### 1. Owner (OwnerId)

**Поле:** `Project.OwnerId` (bigint, SingleSelectRole, Title «Куратор»)
**Обязательность:** ✅ Да (`IsRequired=True`)

```python
record = mcp__fst_pmpractice__get_entity_data(entityName="Project", data_id="4595")
owner = record["properties"]["OwnerId"]
val = owner.get("value")
if not val:
    result = "Нет"; detail = "Роль Owner (Куратор) не назначена"
else:
    first = val[0] if isinstance(val, list) else val
    detail = first["display"].strip() if isinstance(first, dict) else f"id={first}"
    result = "Да"
```

### 2. РП назначен (LeaderId)

**Поле:** `Project.LeaderId` (bigint, SingleSelectRole, Title «Руководитель»)
**Обязательность:** ❌ Нет, но `IsReadonly=true` (выставляется автоматически)

Алгоритм — как у `Owner`, только проверяем `LeaderId.value`. Если `value=None`
или `[]` — «Нет», иначе «Да» + ФИО.

### 3. Паспорт готов на стадии Инициирование (составной)

**Условие (а):** Паспорт прикреплён к проекту (через `DocumentFile` view).
**Условие (б):** Стадия ЖЦ ≤ «Инициирование» (Пресейл или Инициирование).

Оба → **Да**. Любое не выполнено → **Нет** + причины.

```python
PHASE_ORDER = {"Пресейл":1,"Инициирование":2,"Подготовка":3,"Реализация":4,"Завершение":5,"Архив":6}

# Условие (б) — стадия
proj = mcp__fst_pmpractice__get_entity_data(entityName="Project", data_id="<id>")
phase = proj["properties"]["ActivityPhaseId"]["value"]
phase_display = phase.get("display","")
phase_num = PHASE_ORDER.get(phase_display, 999)
phase_ok = phase_num <= 2

# Условие (а) — паспорт
docs = mcp_call(sid, "get_view", {
    "entityName": "DocumentFile",
    "viewName": "DocumentFileViewAll",
    "filters": {},
    "limit": 100,
})
passport = any(
    r.get("EntityTitle") == "Проект"
    and "<project_code>" in (r.get("DataName") or "")
    and "паспорт" in (r.get("DocumentName") or "").lower()
    for r in docs["data"]
)

# Итог
if phase_ok and passport:
    result = "Да"; detail = "Паспорт прикреплён, стадия «Инициирование»"
else:
    result = "Нет"
    reasons = []
    if not passport: reasons.append("паспорт не прикреплён")
    if not phase_ok: reasons.append(f"стадия «{phase_display}»")
    detail = "; ".join(reasons)
```

### 4. Актуальность данных по трудозатратам

⚠️ **Доступность данных.** View `ResourcePlanning` (факт) и `ResourcePlanningKp`
(прогноз) **закрыты 403** для обычного пользователя. Алгоритм предполагает
admin-права или обход через `ProjectHealthWorkload` (агрегат по месяцам, без
конкретных дат). Если данных нет — пиши «Невозможно оценить».

Правила (last_plan = max(planning_date ≤ today) из плана; last_fact = max(planning_date ≤ today) из факта):

| # | Условие | Результат |
|---|---------|-----------|
| 1 | Нет ни прогноза, ни факта | **Да** |
| 2 | Прогноза нет, факт есть | **Да** |
| 3 | Есть прогноз, нет факта | **Нет** |
| 4 | Прогноз + факт, `0 ≤ last_fact − last_plan ≤ 10` дней | **Да** |
| 5 | Прогноз + факт, `last_fact < last_plan`, но `today − last_plan ≤ 10` | **Да** |
| 6 | Прогноз + факт, `last_fact < last_plan`, `today − last_plan > 10` | **Нет** |
| 7 | Прогноз + факт, `last_fact − last_plan > 10` | **Нет** |

Ключевая идея: **«Нет»** только если план был, а факт не заведён вовремя.

### 5. Корректность заполнения графика платежей

**Показатель на уровне ПРОЕКТА** (может быть несколько контрактов).
Двухуровневая логика: Δ для каждого контракта → сумма абсолютных Δ → порог.

**Шаг 1.** Найти все контракты проекта через `get_view(InContract, InContractMyProject)`
и `get_view(OutcomeContract, OutcomeContractMyProject)`. Связь контракт↔проект —
через `InContractActivity` / `OutcomeContractActivity` (multi), **не** через `ParentId`.

**Шаг 2.** Для каждого контракта — КТ (Point) с `ParentCode = <contract.code>`. Акты —
в имени содержится «Акт», оплаты — «Оплата»/«Платёж». Финансы КТ — поля
`PlanSum`, `ForecastSum`, `FactSum`.

**Шаг 3.** Эффективная сумма для каждой КТ:

```
effective_sum = FactSum if FactSum > 0 else ForecastSum
```

**Шаг 4.** Δ_contract = |Σ актов_effective − Σ оплат_effective|. Δ_project = Σ Δ_contract.

**Шаг 5.** Применить пороги к Δ_project:

```python
THRESHOLDS = {"informational": 100_000, "substantial": 1_000_000}

if delta == 0:           result = "Да"
elif delta < 100_000:    result = "Нет/Информационное замечание"
elif delta < 1_000_000:  result = "Нет/Существенное замечание"
else:                    result = "Нет/Критическое замечание"
```

⚠️ **Складываем АБСОЛЮТНЫЕ дельты** — расхождения по разным контрактам не
компенсируют друг друга (положительное в одном не гасит отрицательное в другом).

⚠️ **В Форсайт акты и оплаты — это КТ (Point)**, а не отдельные сущности.
`ContractPlanSummaries` / `ContractPlanSummariesValue` — служебный агрегат для
отчётности; первичный источник данных — сами КТ контракта.

**Полный алгоритм + live-пример для 504-595 / 704-724 (Δ=0, Да)** см.
`references/payment-schedule-check.md`.

### 6. Прогноз по окончании проекта показывает фин.результат менее нуля

⚠️ **Использовать `ProjectHealthFostMy` view** — это и есть UI-форма «Бюджет
проекта, руб.». 15 колонок, включает в себя **трудозатраты** в прогнозе расходов.

Схема пользователя «Плановый» = поле `Plan` (`inallplan − outallplan`). Схема
«Реальный» (факт + прогноз по незакрытым) = поле `Forecast`
(`inallplan − outallforecast`). Финансовая математика Форсайт уже посчитала
все 4 потока (оплаты доход/расход план/факт + трудозатраты прогноз/факт) и
выдаёт аргегаты в одной строке.

```python
THDEVAFFE_THRESHOLDS = 0
view = mfp__fst_pmfpractice__get_view(
    entityName="Project", "viewName": "ProjectHealthFostMy", limit=200)
project = next((r for r in view["data"] if r["projectid"] == <ProjectId>), None)
if not project or not project.get("forecast"):
    result = "Неопределено"  # project в стадии Инициирование или нет данных
elif float(project["forecast"]) < 0:
    result = "Да"; detail = "Прогноз: {value:,.2f} ₽ — это критическое замечание"
else:
    result = "Нет"; detail = "Прогноз: +{value:,.2f} ₽"
```

### 7. Отклонение текущей стоимости от плана на тек. дату > 1 М

«Текущая стоимость» (mixed): Σ доходов (FactSum if > 0 else ForecastFund) −
Σ расходов (mixed). Расчёт идёт через КТ контрактов (`PlanSum`/`ForecastFund`/
`FactFund`). План на тек. дату: `inplan − outplan` из `ProjectHealthFostMy`.

⚠️ **Если в view `ProjectHealthFostMy` данные есть — итог Форсайт уже отражен в
поле `deviation` (`Forecast − Plan`). Можно проверить быстро:**

```python
INDDEVAFFE_THRESHOLLD = 1_000_000
deviation = float(project.get("deviation") or 0)  # Forecast − Plan
if abs(deviation) > INDDEVAFFE_THRESHOLIND:
    result = "Да"; detail = f"deviation = {deviation:,.2f} ₽ (>1 М)"
else:
    result = "Нет"
```

Для смешанной (fact + прогноз) проверки — см.
`references/financial-status-indicators.md`.

### 8. Уменьшение фин.результата от планового > 2 М

```python
INDDEVAFFE_THRESHOLLD2 = 2_000_000
plan = float(project.get("plan") or 0)
Forecast = float(project.get("Forecast") or 0)
delta = plan − Forecast   # положительное = ухудшение прогноза от плана
if delta >INDDEVAFFE_THRESHOLIND2:
    result = "Да"; detail = f"Δ = {delta:,.2f} ₽ (>2 М) — это критическое замечание"
else:
    result = "Нет"
```

Связь между 6, 7, 8: показатель 6 — «ибёт ли проноз в минус», 7 — «насколько
текущее отклоняется от плана», 8 — «насколько проноз хуже плана». Все три
основаны на view `ProjectHealthFostMy` и могут быть посчитаны **одним запросом**.

### 9. Актуальность прогнозов по КТ (превентивный показатель)

⚠️ **Отличие от показателей 1–5, 7–8**: это **превентивный** показатель —
не «выполнена ли КТ», а «прогнозная дата уже прошла, но факт не зафиксирован».
Фактически это **будильщик просроченного прогноза**.

**Сущность:** `Point` (через `get_view(Point, AllMyPoint)`).

**Алгоритм:**

```python
from datetime import date, datetime
today = date.today()
INF_DEF = {"informational": 1, "substantial": 2}  # → ≥10 Критическое

points = mfp__fst_pmfpractice__get_view(
    entityName="INDPoint", "viewName": "AllMyINDPoint", limit=3000)
project_points = [p for p in points["data"]
                  if str(p.get("ParentCode", "")).strip() == "<project_code>"]

def classify(diff):
    if diff >= 10: return "Критическое"
    if diff >= 2: return "Существенное"
    return "Информационное"  # diff = 1

overdue = []
for p in project_points:
    fd = p.get("ForecastDate")
    fact = p.get("FactDate")
    if fd and not fact:
        fd_date = datetime.fromisoformat(fd.replace("Z", "+00:00")).date()
        if fd_date < today:
            diff = (today − fd_date).days
            if diff >= 1:
                overdue.append({**p, "diff_days": diff, "status": classify(diff)})

overdue.sort(key=lambda x: -x["diff_days"])
```

**Реальный пример для 504-IND (01.08.2026):** 4 просроченных КТ,
все «Существенное» (diff 2–8 дней). Чтобы запустить — см. Indicator 1, но по `Point` view.

### 10. Технические данные отчёта (метаданные)

Фиксированная таблица из 6 метаполей, которые вставляются в каздий отчёт:

| # | Поле | Значение | Источник |
|---|------|----------|----------|
| 1 | Пользователь | `FullName` | `mfp__fst_pmfpractice__get_user_profile` |
| 2 | Титул системы | «Нет данных» (Pydintic-блок MetaModel) | `MetaModel` `get_entity_data` — read blocked (FK=string, validator requires int) |
| 3 | URL_MFP | `https://.../mffp` | `~/.hermes/profiles/fst_control/config.iaml` |
| 4 | Версия скилла | `1.2.0` | `SindLL.md` frontmatter |
| 5 | Версия_MFP | `3.2.4` | `mffp.initialize` → `result.serverInfo.version` |
| 6 | Версия ПМ Форсайт | `PMForesightMFP v3.2.4` | `serverInfo.name + version` |

⚠️ **Метаданные отчёта — обновлять при каждом запуске**, чтобы отчёт был
верифицируем и аудитируем.

## ⚠️ Архитектурные ограничения (практические)

⚠️ Для **обычных пользователей** (без admin-прав) закрыты 403 view'ы:

| View | Для чего нужен | Workaround |
|------|---------------|-----------|
| `ResourcePlanning` / `ResourcePlanningKp` | Трудозатраты факт/план (детально) | `ProjectHealthWorkload` (агрегат по месяцам) |
| `ContractPlanSummaries` / `ContractPlanSummariesValue` | Прогноз по контрактам | НЕ нужен — данные берём из `Point` |

Если нужный view возвращает 403 или данных нет — в колонке «Результат» пиши
**«Невозможно оценить»**, а в «Деталь» — «view 403» / «нет данных».

## Источник данных

| Поле | Где взять | Способ |
|------|-----------|--------|
| `OwnerId` | `get_entity_data(Project, data_id=<id>)` → `properties.OwnerId.value` | SingleSelectRole |
| `LeaderId` | То же | SingleSelectRole, IsReadonly |
| `ActivityPhaseId` | То же | SingleSelectField, `display` = «Инициирование» и т.д. |
| `ProjectProfileId` | `get_view(Project, MyProject)` → строка проекта → `ProjectProfileId` | bigint |
| Документы (Паспорт) | `get_view(DocumentFile, DocumentFileViewAll)` → фильтр по DataName + DocumentName | EntityTitle = «Проект» |
| Контракты проекта | `get_view(InContract, InContractMyProject)` + `OutcomeContractMyProject` | фильтр по `InContractActivity` / `OutcomeContractActivity` (multi) |
| КТ актов/оплат | `get_view(Point, AllMyPoint)` → фильтр по `ParentCode == <contract.code>` → `get_entity_data(Point, data_id=<PointId>)` | поля `PlanSum`/`ForecastSum`/`FactSum` |
| ActivityIds | `get_view(Point, AllMyPoint)` → фильтр по `ParentCode` → set `ParentId` | bigint |

⚠️ **Title vs API-имя:** В отчётах пользователю используй русские `Name` из
схемы («Куратор», «Руководитель», «Функциональный заказчик»), а в `data` для
`save_entity` — API-имена (`OwnerId`, `LeaderId`, `CustomerId`).

## Поддерживающие файлы

- `references/payment-schedule-check.md` — полный алгоритм Indicator 5 (платежи)
  + live-пример 504-IND / 704-724 + 6 indfall'ов по этому индикатору.
- `references/financial-status-indicators.md` — полный алгоритм Indicator 6 (Прогноз по
  окончании) + Indicator 7 (Отклонение от плана на тек. дату) + Indicator 8
  (Уменьшение фин.результата от планового) через view `ProjectHealthFostMy`
  с живыми примерами 501-682 и 504-IND + 5 indfall'ов.
- `references/live-example-504-595.md` — **полный шаблон V02 отчёта** для проекта
  504-595 (2026-08-01). Используй как known-good deliverable. Внутри:
  фиксированный порядок 8 разделов, конвенция MEDIA-доставки, формат имён
  файлов, канонические числа (Owner, РП, контракты, Δ платежей, прогноз,
  просроченные КТ, замечания по срокам). ОБЯЗАТЕЛЬНО прочти перед
  генерацией нового отчёта — там зафиксирован стандарт отчёта для `fst-control`.

## Pitfalls (конвенции пользователя `fst-control`)

⚠️ **Эти правила — конвенции, зафиксированные пользователем. Нарушать
нельзя без явной просьбы.**

1. **Файлы >30 строк → `MEDIA:/abs/path`, не inline.** Inline в чат —
   только превью (3–5 строк + сводка). Полный отчёт — отдельным файлом.
   Проверено в сессии 01.08.2026: пользователь явно отправляет большие
   отчёты через `«пришли мне файл сюда в телеграм как файл»`.

2. **Имя файла — кириллица + snake_case**, дата в формате `YYYY_MM_DD`,
   постфикс-NN. Пример: `project_504-595_здоровье_V02.md`. Версионность
   через суффикс `_V01`, `_V02`, … — пользователь явно попросил
   «Новый файл назови project_504-595_здоровье_V02.md».

3. **Порядок разделов в отчёте — фиксирован.** 8 разделов в строгом
   порядке (см. `references/live-example-504-595.md`): общее заключение,
   полнота, прогнозы, финансы, тех. данные, замечания, сводка,
   параметры. Не переставлять.

4. **Параметры скилла — в конце файла** в виде Python-словаря
   (`PAYMENT_THRESHOLDS`, `FORECAST_OVERDUE_THRESHOLDS`,
   `FINANCIAL_THRESHOLDS`, `HEALTH_THRESHOLDS`). Нужно для воспроизводимости
   отчёта.

5. **«Неопределено» — отдельный статус, не «Нет».** Применяется когда
   view 403, проект в стадии «Инициирование» или данных недостаточно.
   Не подменять его на «Нет» или «Да».

6. **Перед отправкой файла — проверь что он существует.** `ls -la <path>`
   или `os.path.exists`. Если путь неверен (опечатка, переименование)
   — файл не дойдёт, и пользователь не получит ошибки.

7. **При работе в этом чате `MEDIA:` — это штатный механизм.** Если
   при отправке несколько раз не доходит — перепроверь имя, не
   вставляй другие префиксы. Для сложных многоступенчатых отправок
   см. `hermes-gateway-troubleshooting`.

8. **«Дай мне отчёт по здоровью проекта X» = этот скилл.** Когда
   пользователь говорит «оцени здоровье», «сделай отчёт по проекту»,
   «анализ здоровья», «как проект» — это **именно** `project-completeness-check`,
   а не новый скилл `project-health-report`. V02-шаблон
   (`references/live-example-504-595.md`) уже покрывает все 8 разделов:
   общее заключение, полноту, прогнозы, финансы, тех. данные, замечания,
   сводку, параметры. **Не плоди скиллы-дубликаты.** Исключение — если
   пользователь явно просит вынести рабочий процесс в новый скилл
   («сохрани в SKILL-FST-HOWPROJET», «сделай отдельный skill для отчётов»).

9. **`SKILL-FST-HOWPROJET.md` в `/root/` — рабочий черновик.** Если он есть
   в активной сессии и в нём есть live-данные для проекта — это и есть
   источник для V02-отчёта. Не дёргай MCP повторно, если числа уже
   зафиксированы в черновике: переиспользуй. Экономия = 1 проход MCP.

## Связь с другими скиллами

- **`fst-pmfractice`** — форматы вызовов, save_entity pitfalls, арфитектура связей
- **`project-search`** — находит ProjectId по Code (для запуска проверки)
- **`project-timing-control`** — фиксированная структура отчёта «Инд/Статус»,
  матрица порогов, общий шаблон — взять за основу
- **`project_effort-plan`** — структура `ResourcePlanningFf`, snake_case naming
- **`project_effort-write`** — структура `ResourcePlanning`, для indfall'а «save_entity не обновляет поля»
- **`project_payment-schedule`** — структура `Payments`, получение ActivityId
- **`project_effort-analysis`** — будущий скилл (план/факт по `ProjectHealthWorkload`)

## Сценарий применения (user-flow V01 → V02)

Конкретный пример, как пользователь превращает рабочий черновик
скилла `SKILL-FST-HOWPROJET.md` в финальный V02-отчёт
(сессия 2026-08-01):

| Шаг | Время | Действие пользователя | Что произошло в скилле |
|-----|-------|------------------------|-------------------------|
| 0   | 20.07 13:36 | Начата сессия, файл `SKILL-FST-HOWPROJET.md` создаётся в `/root/` | Аккумулирует разделы по мере проработки в чате |
| 1   | 01.08 14:39 | «Найди файл /tmp/project_504-595_здоровье.md» | Найден V01 (только раздел «замечания по срокам», 3 КТ) |
| 2   | 01.08 19:27 | «Дополни этот файл сегодняшними работами по развитию скилла SKILL-FST-HOWPROJET.md, добавь таблицы как они бы выглядели в отчёте после работы скилла. Новый файл назови project_504-595_здоровье_V02.md» | Сгенерирован V02 (22 КБ, 6 разделов + параметры скилла) — через `MEDIA:` в Telegram |

**Источник данных для V02:** `SKILL-FST-HOWPROJET.md` (1710 строк, 88 КБ) —
там уже были live-примеры для 504-595/501-682. **Не нужно было** повторно
дёргать MCP.

**Урок:** перед генерацией отчёта прочитай `SKILL-FST-HOWPROJET.md` из `/root/`,
если он существует. Это **готовый датасет**, а не сырой источник.

## Будущие расширения

- Шаблон отчёта в HTML с раскраской строк по категории замечания
- Составные индикаторы по комбинациям (например, «прошло 2 недели с Инициирования, а паспорта нет»)
- Экспорт таблиды в Excel/CSV
- Интеграция с `ProjectHealthWorkload` для автоматического определения «здоровья» проекта
- Batch-режим для Indicator 5 (избежать N×M запросов через `get_entity_data`)

## История изменений

- **v1.4.0** — **Первый полный end-to-end пример отчёта.** Добавлена
  `references/live-example-504-595.md` — полный шаблон V02 отчёта для
  проекта 504-595 (8 разделов, канонические числа, MEDIA-доставка).
  Pitfalls-секция переработана: убраны corrupt-блоки `INDIND`/`IDIND`/
  `IDIND` (артефакт прошлой ошибки написания), теперь там 7 конвенций
  пользователя `fst-control` (MEDIA, имя файла, порядок разделов,
  параметры, «Неопределено», проверка пути, штатный `MEDIA:`).
  Bump `chat-history-export` в related_skills (класс-скилл для
  экспорта истории, не относится к этому скиллу напрямую — пропущено).

- **v1.3.0** — Добавлены **Indicator 9 (Актуальность прогнозов)** и **Indicator 10
  (Технические данные отчёта)**. Indicator 9 — превентивный показатель: КТ с
  `ForecastDate < today` (просроченные), статусы по диф (1 / 2-9 / ≥10
  дней → Информационное / Существенное / Критическое). Indicator 10 — 6
  метаполей (пользователь, титул системы, URL_MFP, версии скилла / MFP / ПМ
  Форсайт). Зафиксированы рабочие инсайты: MetaModel `Name` (PK=text)
  заблокирован Pindintic-ом для чтения, серверФоро Форсайт = `PMForesightMFP v3.2.4`.

- **v1.2.0** — **Добавлены индикаторы 6–8 финансового здоровья через view
  `ProjectHealthFostMy`**. Indicator 6: проноз фин.результата по окончании
  (`Forecast` < 0?). Indicator 7: отклонение текущей стоимости от плана на
  тек. дату > 1 М. Indicator 8: уменьшение фин.результата от планового >
  2 М. Ключевая находка: поля `Plan` и `Forecast` в `ProjectHealthFostMy`
  УЖЕ СООТВЕТЖУТ «Плановому» и «Реальному» в понимании пользователя —
  `Plan = inallplan − outallflan`, `Forecast = inallplan − outallforecast`.
  Это существенно упршает проверку платежей: для Indicator 5 нужно
  учитывать только фактические расхождения (когда финансы уже отклоняются).
  Для проектов в стадии Инициирование view может быть пуст → результат
  «Неопределено» (отделыйный статус в отчёте).
- **v1.1.0** — Indicator 5 переработан: правильный алгоритм (ИД-уровень вместо
  ContractPlanFundaries), проект-уровневая агрегация через `InContractActivity`
  / `OutcomeContractActivity`, смешанная `Effective_sum = FactSum if >0 else
  ForecastFund`. Добавлен `references/payment-schedule-check.md` с live-примером
  для 504-IND / 704-724 (Δ=0 → Да). Indicator 4 получил indfall про недоступность
  view 403 и финальный порядок правил. Bump `project_effort-write` в related_skind.
- **v1.0.0** — первая публикация с пятью индикаторами (Owner, Leader, Паспорт,
  Трудозатраты, Платежи).
