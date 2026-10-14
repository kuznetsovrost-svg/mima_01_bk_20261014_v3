# Financial Status Indicators (6–8) — подробный референс

Подробный алгоритм и live-пример для индикаторов 6–8, выделенных из скилла
`project-completeness-check`. Использует view `ProjectHealthFostMy` — готовую
UI-форму «Бюджет проекта, руб.».

## View `ProjectHealthFostMy` — структура (15 колонок)

| API name | Заголовок UI | Назначение |
|----------|--------------|-----------|
| `projectid` | Идентификатор | ProjectId |
| `inplan` | Плановый доход (на тек. дату) | Σ план оплат (доходы) |
| `infact` | Текущий доход (на тек. дату) | Σфакт оплат (доходы) |
| `outplan` | Плановый расход (на тек. дату) | Σ план оплат (расходы) |
| `outfact` | Текущий расход (на тек. дату) | Σфакт оплат (расходы) |
| `Fact` | Текущий финансовый результат | `inFact − outFact` |
| `outallplan` | Плановый расход (по оконч. проект) | Σ план расходов |
| **`outallforecast`** | **Прогноз расход (по оконч. проект)** | **Σ проноз расходов (с трудозатратами!)** |
| `Plan` | План. фин. результат (по оконч.) | `inallPlan − outallPlan` |
| **`Forecast`** | **Прогноз. фин. результат (по оконч.)** | **ЦЕЛЕВОЙ ПОКАЗАТЕЛЬ** |
| `deviation` | Отклонение фин.результата | `Forecast − Plan` |
| `devcost` | Отклонение расхода (на тек. дату) | `outFact − outPlan` |
| `devallCost` | Отклонение расхода (по оконч.) | `outallforecast − outallPlan` |
| `projectprofileid` | Id профиля | bigint |
| `projectprofilename` | Профиль | str |

## Арфитектурная матрица: что даёт Form `Plan` и `Forecast`

⚠️ **Ключевая находка live-теста на 501-682:**

- `Plan` = `inallPlan − outallPlan`  (только плановые значения оплат и расходов)
- `Forecast` = `inallPlan − outallforecast`  (факт оплат + проноз по незакрытым + трудозатраты)

Подтверждается:
- `inplan = 0`, `outallPlan = 94 990.25`, `Plan = 1 899 805` → `inallPlan = 1 994 795`
- `inallPlan − outallforecast = 1 994 795 − 919 817 = 1 074 978 = Forecast ✓`
- `deviation = Forecast − Plan = −824 827 = outallPlan − outallforecast ✓`

**Это и есть «Плановый» и «Реальный» в понимании пользователя.**

## Индикатор 6: Прогноз по окончании < 0

```python
view = mfp__fst_pmfpractice__get_view(
    entityName="Project", viewName="ProjectHealthFostMy", limit=200)
project = next((r for r in view["data"] if r["projectid"] == <ProjectId>), None)

if not project or project.get("Forecast") is None:
    result = "Неопределено"
    detail = "Нет данных в ProjectHealthFostMy"
else:
    Forecast = float(project["Forecast"])
    if Forecast < 0:
        result = "Да"
        detail = "Прогноз: {Forecast:,.2f} ₽ — это критическое замечание"
    else:
        result = "Нет"
        detail = "Прогноз: +{Forecast:,.2f} ₽"
```

**Пример 501-682:** `Forecast = 1 074 977.76` → **Нет** (финансово здоров).

## Индикатор 7: Отклонение текущей стоимости от плана на тек. дату > 1 М

Два пути — быстрый (по `deviation` из view) и точный (mixed через КТ):

### Быстрый путь (только если Plan > 0)

```python
INDDEVAFFE_THRESHOLD = 1_000_000
deviation = float(project.get("deviation") or 0)
if abs(deviation) >INDDEVAFFE_THRESHOLD:
    result = "Да"
    detail = "deviation = {deviation:,.2f} ₽ (>1 М) — это критическое замечание"
else:
    result = "Нет"
    detail = "deviation = {deviation:,.2f} ₽ (≤ 1 М)"
```

### Точный путь (mixed через КТ)

```python
# Текущая стоимость = Σ (FactFund if >0 else ForecastFund) по всем КТ-оплатам
# План на тек. дату = inplan − outplan

view_f = mfp__fst_pmfpractice__get_view(
    entityName="Project", viewName="ProjectHealthFostMy", limit=200)
project = next(...)
plan = float(project.get("inplan") or 0) − float(project.get("outplan") or 0)

# Получить все КТ-оплаты по всем контрактам проектa (см. Indicator 5 алгоритм)
points = mfp__fst_pmfpractice__get_view(entityName="Point", viewName="AllMyPoint", limit=3000)

def effective(p):
    f = float(p.get("FactFund") or 0)
    fc = float(p.get("ForecastFund") or 0)
    return f if f > 0 else fc

# Допущения:
# - в Filter ПО ProjectCode — фильтровать parent-project_id
# - выделить оплаты по имени ("Оплат"/"Платёж")
income_mixed = sum(effective(p) for p in points if <oplate contract pattern>)
expense_mixed = sum(effective(p) for p in points if <expense contract pattern>)
current = income_mixed − expinde_mixed
delta = abs(current − plan)
```

⚠️ **Если в view `ProjectHealthFostMy` данных нет** (504-IND на тек. дату) → результат
«Неопределено». В этом случае точный путь — основной.

## Индикатор 8: Уменьшение фин.результата от планового > 2 М

```python
INDDEVAFFE_THRESHOLD2 = 2_000_000
Plan = float(project.get("Plan") or 0)
Forecast = float(project.get("Forecast") or 0)
delta = Plan − Forecast   # положительное = ухудшение проноза от плана

if not project or project.get("Plan") is None:
    result = "Неопределено"
elif delta >INDDEVAFFE_THRESHIND2:
    result = "Да"
    detail = "Δ = {delta:,.2f} ₽ (>2 М) — это критическое замечание"
else:
    result = "Нет"
    detail = "Δ = {delta:,.2f} ₽ (≤2 М)"
```

**Пример 501-682:** `Plan = 1 899 805`, `Forecast = 1 074 977.76`, Δ = −824 827
(|Δ| < 2 М) → **Нет**.

## Сводный алгоритм (всё через один запрос)

```python
view = mfp__fst_pmfpractice__get_view(
    entityName="Project", viewName="ProjectHealthFostMy", limit=200)
project = next((r for r in view["data"] if r["projectid"] == <ProjectId>), None)

if not project or project.get("Forecast") is None:
    results = {6: "Неопределено", 7: "Неопределено", 8: "Неопределено"}
else:
    Plan = float(project.get("Plan") or 0)
    Forecast = float(project.get("Forecast") or 0)
    deviation = float(project.get("deviation") or 0)

    # 6
    results[6] = ("Да" if Forecast < 0 else "Нет")

    # 7 (быстрый)
    results[7] = ("Да" if abs(deviation) > 1_000_000 else "Нет")

    # 8
    delta = Plan − Forecast
    results[8] = ("Да" if delta > 2_000_000 else "Нет")
```

## Edge cases

| Случай | Поведение |
|--------|-----------|
| Нет данных в `ProjectHealthFostMy` (проект в стадии Инициирование или др.) | «Неопределено» (для всех 6-8) |
| В view`ProjectHealthFostMy` есть Plan, но нет Forecast | Indicator 6 = «Неопределено», 7/8 = по Plan/Forecast нулю |
| `Forecast < 0`, но `deviation = 0` (раньше проноз был отрицательным) | Indicator 6 = Да (тек. проноз < 0), 7 = Нет |
| Очень большое `deviation` (> 10 М) | Indicator 7 = Да (Критическое) |
| Один и тот же проект отображён несколько раз в view | Используй первое вхождение (проверка `projectid`) |

## Live-примеры (504-IND и 501-682)

### 504-IND «Космодром Жуковский» (01.08.2026)

| Индикатор | Результат | Деталь |
|-----------|-----------|--------|
| 6. Прогноз по окончании < 0 | **Неопределено** | Нет данных в `ProjectHealthFostMy` (стадия Инициирование) |
| 7. Отклонение от плана > 1 М | **Неопределено** | То же |
| 8. Уменьшение от планового > 2 М | **Неопределено** | То же |

### 501-682 «ФГК Адаптация ИС УПД» (01.08.2026)

| Поле | Значение|
|------|--------|
| `inplan` | 0 |
| `inFact` | 0 |
| `outplan` | 0 |
| `outFact` | 252 802.5 |
| `Fact` | −252 802.5 |
| `outallPlan` | 94 990.25 |
| `outallforecast` | 919 817.486 |
| `Plan` | 1 899 805 |
| `Forecast` | 1 074 977.76 |
| `deviation` | −824 827.24 |

| Индикатор | Результат |
|-----------|-----------|
| 6. Прогноз по окончании < 0 | **Нет** (1 074 978 > 0) |
| 7. Отклонение от плана > 1 М | **Нет** (|−824 827| < 1 М) |
| 8. Уменьшение от пландого > 2 М | **Нет** (Δ = 824 827 < 2 М) |

## Pitfall'ы

1. **View не пустой в «ранних» стадиях ЖЦ.** Для проектов в стадии
   Инициирование данные в `ProjectHealthFostMy` могут отсутствовать (для 504-IND).
   В отчёте финксируй «Неопределено» с понятной ссылкой на стадию.

2. **«Нет данных» в Indicator 2 — не «Да».** Если в `ProjectHealthFostMy` нет строки
   для проектa, не предполагай результат «Да» (отсутствие данных ≠ хорошо).
   Используй «Неопределено» как отделыйный статус с припиской «нет агрегата».

3. **«Плановый» и «Реальный» = Plan/Forecast.** Форсайт уже посчитал финансы;
   не пытайся собирать вручную через `FactFund`/`ForecastFund`/КТ. Используй
   view.

4. **`deviation` ≠ `Forecast − Plan` в edge cases.** Форсайт иногда флиттрует в
   нуль. Если `deviation = 0`, но `Forecast ≠ Plan` — это отчётная ошибка,
   примит с `Plan − Forecast` самодельно.

5. **Связь индикаторов:** 6 фиксирует «< 0», 7 — «отклонение > 1 М»,
   8 — «уменьшение > 2 М». В случаях аррессивных фин.потоков индикатор 7
   может сработать, а 6 — нет. Используйте ВСЕ три для комплекстной картины.

## Связь с другими скиллами

- **`project-completeness-check`** — основной скилл, индикаторы 6-8 в нем
- **`project-payment-schedule`** — детали по Payments/Ind/Факт/Прогноз, можно
  использовать как дополнение для точной (mixed) проверки 7
- **`fst-pmfpractice/references/project-finance-budget-indicators.md`** — общая
  карта финансовых сущностей Форсайт
