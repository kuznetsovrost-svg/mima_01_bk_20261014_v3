# SKILL: FST-HOWPROJET (рабочий черновик)

> Проектный скилл по работе с проектами Форсайт ПМ Практики.
> В этом файле фиксируются разделы по мере их проработки в чате.

## Структура файла

1. [Проверка полноты заполнения проекта](#1-проверка-полноты-заполнения-проекта)
2. [Актуальность прогнозов по проекту](#2-актуальность-прогнозов-по-проекту)
3. [Финансовый статус проекта](#3-финансовый-статус-проекта)
4. [Технические данные отчёта](#4-технические-данные-отчёта)
5. *(будут добавляться)*

---

## 1. Проверка полноты заполнения проекта

### Назначение

При анализе проекта сформировать **таблицу фиксированного размера** с показателями
полноты заполнения ключевых полей. Каждая строка — отдельный показатель
(Да/Нет + краткая деталь).

### Граф жизненного цикла проекта

```
1) Пресейл
2) Инициирование
3) Подготовка
4) Реализация
5) Завершение
6) Архив
```

⚠️ Это **линейный граф** — каждая следующая стадия «старше» предыдущей.
Для проверок «≤ N» используется **порядковый номер** стадии (1..6).

### Формат таблицы

| # | Показатель | Результат | Деталь |
|---|------------|-----------|--------|
| 1 | Owner (OwnerId) | Да / Нет | ФИО владельца или «не заполнено» |
| 2 | РП назначен (LeaderId) | Да / Нет | ФИО руководителя проекта или «не заполнено» |
| 3 | Паспорт готов на стадии Инициирование | Да / Нет | Подробности ниже |
| 4 | Актуальность данных проекта по трудозатратам | Да / Нет | Подробности ниже |
| 5 | Корректность заполнения графика платежей проекта | Да / Нет[статус] | Да / Нет/(Информационное/Существенное/Критическое) замечание |

---

## 2. Актуальность прогнозов по проекту

### Назначение

Найти все КТ проекта, **прогнозная дата которых превысила текущую дату** (т.е. `ForecastDate < today`),
но **факт ещё не зафиксирован** (`FactDate` пустое). Для каждой такой КТ
определить статус отклонения.

### Состав колонок

Таблица **аналогична таблице с контрольными точками** (в перспективе), но
вместо факта выполнения КТ показывается **превентивный показатель** — насколько
прогнозная дата отстаёт от текущей.

| # | Код КТ | Название | План | Прогноз | Факт | Дней просрочки | Статус | Исполнитель |
|---|--------|----------|------|---------|------|----------------|--------|-------------|
| … | … | … | … | … | … | … | … | … |

### Алгоритм

```
1. Получить все КТ проекта:
   points = mcp__fst_pmpractice__get_view(
       entityName="Point", viewName="AllMyPoint", limit=3000
   )
   project_points = [p for p in points["data"]
                     if str(p.get("ParentCode", "")).strip() == "<project_code>"]

2. Определить today = date.today()

3. Отфильтровать КТ с просроченным прогнозом:
   overdue = []
   for p in project_points:
       forecast = parse_date(p.ForecastDate)
       fact = parse_date(p.FactDate)
       if forecast and forecast < today and not fact:
           diff = (today - forecast).days
           overdue.append({...p, "diff_days": diff})

4. Отсортировать по diff (наибольшее отклонение — вверху):
   overdue.sort(key=lambda x: -x["diff_days"])

5. Классифицировать по diff (отклонение от текущей даты):
   if diff_days >= 10:
       status = "Критическое"
   elif diff_days >= 2:
       status = "Существенное"
   elif diff_days >= 1:
       status = "Информационное"
   # diff = 0 не попадает (ForecastDate = today, не превышена)
   # diff < 0 не попадает (прогноз в будущем)

6. Вывести таблицу
```

### Правила статусов

| # | Дней просрочки (diff) | Статус | Цвет |
|---|----------------------|--------|------|
| 1 | ≥ 10 | **Критическое** | Красный |
| 2 | 2 – 9 | **Существенное** | Жёлтый |
| 3 | 1 | **Информационное** | Синий |
| 4 | ≤ 0 (прогноз в будущем или сегодня) | Не попадает в таблицу | — |

⚠️ **Не путать с таблицей «Проверка полноты заполнения»** — там отклонение
считалось как |ForecastDate − PlanDate|, здесь — `(today − ForecastDate).days`.

### Пример вызова

```python
from datetime import date, datetime

THRESHOLDS = {
    "informational": 1,   # 1 день
    "substantial": 2,     # 2..9 дней
    # >= 10 = critical
}

def parse_date(s):
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00")).date()

# 1. КТ проекта
points = mcp__fst_pmpractice__get_view(
    entityName="Point", viewName="AllMyPoint", limit=3000
)
project_points = [p for p in points["data"]
                  if str(p.get("ParentCode", "")).strip() == "504-595"]

# 2. Сегодня
today = date.today()

# 3. Фильтр просроченных
overdue = []
for p in project_points:
    forecast = parse_date(p.get("ForecastDate"))
    fact = parse_date(p.get("FactDate"))
    if forecast and forecast < today and not fact:
        diff = (today - forecast).days
        if diff >= 1:  # только просроченные
            overdue.append({**p, "diff_days": diff})

# 4. Сортировка
overdue.sort(key=lambda x: -x["diff_days"])

# 5. Классификация
def classify(diff):
    if diff >= 10:
        return "Критическое"
    if diff >= 2:
        return "Существенное"
    return "Информационное"  # diff = 1

# 6. Вывод
for o in overdue:
    status = classify(o["diff_days"])
    print(f"{o['Code']} | {o['Name']} | план={parse_date(o['PlanDate'])} | "
          f"прогноз={parse_date(o['ForecastDate'])} | "
          f"+{o['diff_days']}д | {status} | {o['Responsible']}")
```

### Реальный пример для проекта 504-595 (на 01.08.2026)

**Просрочено КТ: 4** (все со статусом «Существенное»)

| # | Код КТ | Название | План | Прогноз | Факт | Дней просрочки | Статус | Исполнитель |
|---|--------|----------|------|---------|------|----------------|--------|-------------|
| 1 | 104-723 | Подписан акт по 1-му блоку раб | 2026-07-24 | 2026-07-24 | — | +8 | **Существенное** | Кузнецов Р.В. |
| 2 | 104-721 | ЧТЗ согласовано | 2026-07-15 | 2026-07-27 | — | +5 | **Существенное** | Кузнецов Р.В. |
| 3 | 104-722 | Подписан протокол согласования | 2026-07-24 | 2026-07-27 | — | +5 | **Существенное** | Кузнецов Р.В. |
| 4 | 104-727 | Плановые трудозатраты по 1-му | 2026-07-30 | 2026-07-30 | — | +2 | **Существенное** | Кузнецов Р.В. |

**Сводка:**

| Статус | Кол-во |
|--------|--------|
| 🔴 Критическое (≥10 дн) | 0 |
| 🟡 Существенное (2–9 дн) | **4** |
| 🔵 Информационное (1 дн) | 0 |

### Источник

- Поле: `Point.ForecastDate` (datetime, ISO 8601)
- Поле: `Point.FactDate` (datetime, ISO 8601) — должно быть пустое
- Поле: `Point.PlanDate` (datetime, ISO 8601) — для отображения
- View: `AllMyPoint` (или `PointToMeToDo`)

---

## 3. Финансовый статус проекта

### Назначение

Таблица из **3 строк**, отражающая финансовое состояние проекта по завершении.
Первая строка — **«Прогноз по окончании проекта показывает финансовый результат менее нуля»** —
содержание этой секции. Остальные строки добавляются позже.

### Формат таблицы

| # | Показатель | Результат | Деталь |
|---|------------|-----------|--------|
| 1 | Прогноз по окончании проекта показывает финансовый результат менее нуля | Нет / Да ["Это критическое замечание"] | Расчёт: Σ доходы − Σ расходы (включая трудозатраты) |
| 2 | Отклонение текущей стоимости от плана на текущую дату более 1 млн. руб. | Нет / Да ["Критическое замечание"] | Текущая стоимость (mixed) vs план на тек. дату |
| 3 | Прогноз по окончанию показывает уменьшение финансового результата от планового более чем на 2 млн. руб. | Нет / Да ["Критическое замечание"] | "Реальный" (forecast) vs "Плановый" (plan) |

### ⚠️ Главная находка: view `ProjectHealthCost` (Здоровье по стоимости)

В UI Форсайт форма «**Бюджет проекта, руб.**» — это view **`ProjectHealthCost`**
(или `ProjectHealthCostMy` для всех доступных проектов). Это **готовый агрегат**,
который Форсайт считает на лету из 4 потоков:

1. **Оплаты (доходы)** — план и факт
2. **Оплаты (расходы)** — план и факт
3. **Трудозатраты (прогноз)** — часы × ставка × грейд сотрудника
4. **Трудозатраты (факт)** — часы × ставка × грейд сотрудника

#### Схема view `ProjectHealthCost` (15 колонок)

| API name | Заголовок | Что это |
|----------|-----------|---------|
| `projectid` | Идентификатор | ProjectId |
| `inplan` | Плановый доход (на текущую дату) | Σ план оплат (доходы) |
| `infact` | Текущий доход (на текущую дату) | Σ факт оплат (доходы) |
| `outplan` | Плановый расход (на текущую дату) | Σ план оплат (расходы) |
| `outfact` | Текущий расход (на текущую дату) | Σ факт оплат (расходы) |
| `fact` | Текущий финансовый результат | `infact − outfact` |
| `outallplan` | Плановый расход (по окончании проекта) | Σ план расходов (с трудозатратами) |
| **`outallforecast`** | **Прогноз расход (по окончании проекта)** | Σ прогноз расходов (включает трудозатраты) |
| `plan` | План. фин. результат (по окончании проекта) | `inplan − outallplan` |
| **`forecast`** | **Прогноз. фин.результат (по окончании проекта)** | **ЦЕЛЕВОЙ ПОКАЗАТЕЛЬ** |
| `deviation` | Отклонение фин.результата | `forecast − plan` |
| `devcost` | Отклонение расхода (на текущую дату) | `outfact − outplan` |
| `devallcost` | Отклонение расхода (по окончании проекта) | `outallforecast − outallplan` |
| `projectprofileid` | Id профиля проекта | (как в `ProjectHealthWorkload`) |
| `projectprofilename` | Профиль | (как в `ProjectHealthWorkload`) |

#### Алгоритм

```
1. Получить данные через get_view(Project, ProjectHealthCostMy):
   rows = mcp__fst_pmpractice__get_view(
       entityName="Project", viewName="ProjectHealthCostMy", limit=200
   )

2. Найти наш проект:
   project = next((r for r in rows.data if r.projectid == <ProjectId>), None)

3. Проверить наличие данных:
   if not project or "forecast" not in project:
       result = "Неопределено"
       detail = "Нет агрегированных данных в ProjectHealthCost (возможно, проект в стадии Инициирование или ещё не сформирован план)"

4. Извлечь прогноз:
   forecast = float(project["forecast"])  # в рублях

5. Применить правило:
   if forecast < 0:
       result = "Да"
       detail = f"Прогноз фин.результата: {forecast:,.2f} ₽ — это критическое замечание"
   else:
       result = "Нет"
       detail = f"Прогноз фин.результата: {forecast:,.2f} ₽"

6. Добавить строку в таблицу:
   | 1 | Прогноз по окончании проекта показывает финансовый результат менее нуля | <result> | <detail> |
```

#### Пример вызова

```python
# 1. Получить данные
view = mcp__fst_pmpractice__get_view(
    entityName="Project",
    viewName="ProjectHealthCostMy",
    limit=200
)

# 2. Найти проект
project_id = 4595  # 504-595
project = next((r for r in view["data"] if r.get("projectid") == project_id), None)

# 3. Проверить наличие данных
if not project or not project.get("forecast"):
    result = "Неопределено"
    detail = "Нет данных в ProjectHealthCost"
else:
    forecast = float(project["forecast"])
    if forecast < 0:
        result = "Да"
        detail = f"Прогноз: {forecast:,.2f} ₽ — это критическое замечание"
    else:
        result = "Нет"
        detail = f"Прогноз: {forecast:,.2f} ₽"
```

#### Реальный пример для проекта 501-682 (другой проект, на 01.08.2026)

⚠️ У проекта 504-595 (Космодром Жуковский) **данных в `ProjectHealthCostMy` пока нет** —
проект в стадии «Инициирование», агрегат не сформирован. Для демонстрации алгоритма
привожу данные по **501-682 «ФГК Адаптация ИС УПД»** (тоже наш проект):

| Поле API | Значение (₽) | Расшифровка |
|----------|--------------|-------------|
| `inplan` | 54 000 000 | Плановый доход |
| `infact` | 54 000 000 | Факт дохода (оплата поступила) |
| `outplan` | — | Плановый расход на тек. дату (нет) |
| `outfact` | 300 440 | Факт расхода (уже потрачено) |
| `fact` | **53 699 560** | Текущий фин. результат (положительный) |
| `outallplan` | — | Плановый расход по оконч. (нет) |
| `outallforecast` | 563 880 | Прогноз расхода по оконч. (включает трудозатраты) |
| `plan` | 54 000 000 | Плановый фин. результат |
| **`forecast`** | **53 436 120** | **Прогноз фин.результата по окончании** |
| `deviation` | -563 880 | Отклонение от плана (расходы выше) |

**Вердикт по 501-682:** forecast = 53 436 120 > 0 → **Нет** (финансово здоров).

#### Реальный пример для проекта 504-595 (на 01.08.2026)

⚠️ **Данных в `ProjectHealthCostMy` пока нет** для проекта 504-595 — проект в стадии
«Инициирование», агрегат финансов ещё не сформирован Форсайтом.

| # | Показатель | Результат | Деталь |
|---|------------|-----------|--------|
| 1 | Прогноз по окончании проекта показывает финансовый результат менее нуля | **Неопределено** | Нет данных в ProjectHealthCost (стадия «Инициирование») |
| 2 | *(следующий показатель)* | … | … |
| 3 | *(следующий показатель)* | … | … |

### Алгоритм для показателя «Отклонение текущей стоимости от плана на текущую дату более 1 млн. руб.»

#### Семантика

| Понятие | Что это | Где |
|---------|---------|-----|
| **Текущая стоимость** (mixed) | Σ доходов (FactSum если > 0, иначе ForecastSum) − Σ расходов (FactSum если > 0, иначе ForecastSum) | Расчёт через КТ контрактов |
| **План на текущую дату** | Сумма оплат/расходов, запланированных к сегодняшнему дню | `inplan − outplan` из `ProjectHealthCostMy` |
| **Δ** | `|текущая стоимость − план|` | — |

⚠️ **Важная особенность:** в `ProjectHealthCostMy` колонка `fact` (Текущий фин. результат)
— это **`infact − outfact`**, то есть **только факт**. По правилу пользователя нужна **mixed** (факт
там, где он есть, + прогноз по незакрытым). Эта mixed-сумма **не хранится** в view напрямую —
её нужно считать через КТ контрактов.

#### Правила

| # | Условие | Результат |
|---|---------|-----------|
| 1 | Нет данных по контрактам проекта | **Нет** (нечего оценивать) |
| 2 | Δ ≤ 1 000 000 ₽ | **Нет** (отклонение в пределах нормы) |
| 3 | Δ > 1 000 000 ₽ | **Да [Критическое замечание]** (с указанием суммы) |

#### Алгоритм

```
1. Получить план на текущую дату из ProjectHealthCostMy:
   view = mcp__fst_pmpractice__get_view(
       entityName="Project", viewName="ProjectHealthCostMy", limit=200
   )
   project = next(r for r in view.data if r.projectid == <ProjectId>)
   plan = float(project.get("inplan") or 0) - float(project.get("outplan") or 0)

2. Получить доходные и расходные контракты проекта:
   in_contracts = [...]  # см. показатель №1
   out_contracts = [...]  # см. показатель №1

3. Получить все КТ проекта (и контрактов):
   points = get_view(Point, AllMyPoint, limit=3000)

4. Суммировать mixed-суммы (только КТ-оплаты):
   def effective(p):
       f = float(p.FactSum or 0)
       fc = float(p.ForecastSum or 0)
       return f if f > 0 else fc

   # Доходы: КТ-оплаты доходных контрактов
   income_mixed = sum(
       effective(p) for p in project_points
       if p.ParentCode in {c.Code for c in in_contracts}
       and "Оплат" in p.Name
   )
   # Расходы: КТ-оплаты расходных контрактов
   expense_mixed = sum(
       effective(p) for p in project_points
       if p.ParentCode in {c.Code for c in out_contracts}
       and "Оплат" in p.Name
   )

5. Текущая стоимость (mixed):
   current = income_mixed - expense_mixed

6. Δ = |current − plan|
   if Δ > 1_000_000:
       result = "Да"
       detail = f"Δ = {Δ:,.2f} ₽ (текущая {current:,.2f} − план {plan:,.2f}) — это критическое замечание"
   else:
       result = "Нет"
       detail = f"Δ = {Δ:,.2f} ₽ (текущая {current:,.2f} − план {plan:,.2f})"

7. Добавить строку:
   | 2 | Отклонение текущей стоимости от плана на текущую дату более 1 млн. руб. | <result> | <detail> |
```

#### Пример вызова

```python
THRESHOLD = 1_000_000  # 1 млн

# 1. План на тек. дату
view = mcp__fst_pmpractice__get_view(
    entityName="Project", viewName="ProjectHealthCostMy", limit=200
)
project = next(r for r in view["data"] if r["projectid"] == 4595)
plan = float(project.get("inplan") or 0) - float(project.get("outplan") or 0)

# 2-3. Контракты и КТ (см. показатель №1)
# ... (опущено)

# 4. Mixed-суммы
def effective(p):
    f = float(p.FactSum or 0)
    fc = float(p.ForecastSum or 0)
    return f if f > 0 else fc

income_mixed = sum(...)
expense_mixed = sum(...)

# 5-6. Δ
current = income_mixed - expense_mixed
delta = abs(current - plan)

if delta > THRESHOLD:
    result = "Да"
    detail = f"Δ = {delta:,.2f} ₽ (> 1 млн) — это критическое замечание"
else:
    result = "Нет"
    detail = f"Δ = {delta:,.2f} ₽ (≤ 1 млн)"
```

#### Реальный пример для проекта 501-682 (на 01.08.2026)

⚠️ У 504-595 (Космодром Жуковский) **нет данных** в `ProjectHealthCostMy` (стадия
«Инициирование»). Привожу расчёт для **501-682 (ФГК Адаптация ИС УПД)** — у которого
есть полные данные.

| Показатель | Значение |
|------------|----------|
| План на тек. дату (`inplan − outplan`) | 0 − 0 = 0 ₽ |
| Текущая стоимость (mixed) | infact − outfact = 0 − 252 802.50 = **−252 802.50 ₽** |
| Δ | **252 802.50 ₽** |
| **Вердикт** | Δ = 252 802.50 ≤ 1 млн → **Нет** |

> ⚠️ **Замечание:** для точного расчёта mixed нужно знать `FactSum`/`ForecastSum`
> всех КТ-оплат по всем контрактам проекта. Для 504-595 (стадия «Инициирование»)
> в текущий момент данных недостаточно — отметка «Неопределено».

#### Ограничения

⚠️ **Mixed-логика требует данных по КТ-оплатам** всех контрактов проекта. Если у проекта:
- Нет контрактов → «Нет» (нечего оценивать)
- Есть контракты, но нет финансовых КТ в видимой части view → «Неопределено»

### Алгоритм для показателя «Прогноз по окончанию показывает уменьшение финансового результата от планового более чем на 2 млн. руб.»

#### Семантика

| Схема | Что это | Формула через поля `ProjectHealthCostMy` |
|-------|---------|------------------------------------------|
| **«Плановый»** фин. результат | Только плановые значения оплат и затрат | `plan` (= `inallplan − outallplan`) |
| **«Реальный»** фин. результат | Факт оплат + прогноз по незакрытым оплатам и расходам (включая трудозатраты) | `forecast` (= `inallplan − outallforecast`) |

⚠️ **Важная архитектурная находка:** В `ProjectHealthCostMy` поля `plan` и `forecast`
**уже соответствуют** схемам пользователя:
- `plan` = план. фин. результат (только плановые значения) — это **«Плановый»**
- `forecast` = прогноз. фин. результат (факт + прогноз по незакрытым) — это **«Реальный»**

Это подтверждается на 501-682:
- `inplan` = 0, `outallplan` = 94 990.25, `plan` = 1 899 805 → `inallplan = 1 994 795`
- `inallplan − outallplan` = 1 899 805 = `plan` ✓
- `inallplan − outallforecast` = 1 074 978 = `forecast` ✓
- `deviation = forecast − plan` = −824 827 = `outallplan − outallforecast` ✓

#### Правила

| # | Условие | Результат |
|---|---------|-----------|
| 1 | В `ProjectHealthCostMy` нет строки для проекта | **Неопределено** (стадия «Инициирование» или др.) |
| 2 | Нет данных по `plan` или `forecast` | **Неопределено** |
| 3 | forecast − plan ≥ −2 000 000 ₽ (уклонение ≤ 2 млн) | **Нет** |
| 4 | forecast − plan < −2 000 000 ₽ (уклонение > 2 млн) | **Да [Критическое замечание]** |

#### Алгоритм

```
1. Получить данные через ProjectHealthCostMy:
   view = mcp__fst_pmpractice__get_view(
       entityName="Project", viewName="ProjectHealthCostMy", limit=200
   )

2. Найти проект:
   project = next(r for r in view.data if r.projectid == <ProjectId>)

3. Проверить наличие:
   if not project or "plan" not in project or "forecast" not in project:
       result = "Неопределено"
       detail = "Нет данных в ProjectHealthCostMy"
   else:
       plan = float(project["plan"])
       forecast = float(project["forecast"])
       delta = forecast - plan  # отрицательное = ухудшение

       if abs(delta) <= 2_000_000:
           result = "Нет"
           detail = f"Δ = {delta:,.2f} ₽ (уклонение < 2 млн)"
       else:
           result = "Да"
           detail = f"Δ = {delta:,.2f} ₽ (уклонение > 2 млн) — это критическое замечание"

4. Добавить строку:
   | 3 | Прогноз по окончанию показывает уменьшение фин.результата от планового > 2 млн. | <result> | <detail> |
```

#### Пример вызова

```python
THRESHOLD = 2_000_000  # 2 млн

view = mcp__fst_pmpractice__get_view(
    entityName="Project", viewName="ProjectHealthCostMy", limit=200
)
project = next(r for r in view["data"] if r["projectid"] == 4595)

if not project or not project.get("plan") or not project.get("forecast"):
    result = "Неопределено"
    detail = "Нет данных"
else:
    plan = float(project["plan"])
    forecast = float(project["forecast"])
    delta = forecast - plan

    if abs(delta) <= THRESHOLD:
        result = "Нет"
        detail = f"Δ = {delta:,.2f} ₽ (уклонение ≤ 2 млн)"
    else:
        result = "Да"
        detail = f"Δ = {delta:,.2f} ₽ (уклонение > 2 млн) — это критическое замечание"
```

#### Реальный пример для проекта 501-682 (на 01.08.2026)

⚠️ У 504-595 (Космодром Жуковский) **нет данных** в `ProjectHealthCostMy` (стадия
«Инициирование»). Привожу расчёт для **501-682 (ФГК Адаптация ИС УПД)** — у которого
есть полные данные.

| Поле | Значение (₽) | Расшифровка |
|------|--------------|-------------|
| `plan` (Плановый) | **1 899 805.00** | `inallplan − outallplan` |
| `forecast` (Реальный) | **1 074 977.76** | `inallplan − outallforecast` (факт + прогноз) |
| **Δ (forecast − plan)** | **−824 827.24** | `outallplan − outallforecast` |
| **\|Δ\|** | 824 827.24 | — |

**Вердикт по 501-682:** \|Δ\| = 824 827.24 < 2 000 000 → **Нет** (уклонение в пределах нормы).

#### Реальный пример для проекта 504-595 (на 01.08.2026)

⚠️ **Данных нет** в `ProjectHealthCostMy` — проект в стадии «Инициирование».

| # | Показатель | Результат | Деталь |
|---|------------|-----------|--------|
| 3 | Прогноз по окончанию показывает уменьшение фин.результата от планового > 2 млн. | **Неопределено** | Нет данных в ProjectHealthCostMy |

#### Связь между показателями 1 и 3

| Показатель | Используемое поле | Логика |
|------------|---------------------|--------|
| **1. Прогноз по окончании** | `forecast` | Проверяем: forecast < 0? |
| **3. Уменьшение от плана > 2 млн** | `plan` и `forecast` | Проверяем: plan − forecast > 2 млн? |

Показатель 3 — это **обогащение** показателя 1: не просто «убыточен ли прогноз»,
а «насколько хуже плана».

### Связь с другими views
### Связь с другими views
### Связь с другими views

| View | Отношение |
|------|-----------|
| `ProjectHealthCost` | То же, что `ProjectHealthCostMy`, но без фильтра по правам (доступен админам) |
| `ProjectHealthCostMy` | **Основной view для обычного пользователя** |
| `ProjectHealthWorkload` | Здоровье по трудозатратам (без цен) — для показателя №4 «Актуальность данных» |
| `ProjectBudgetStandart` | Бюджет по проекту (агрегат по финансовым источникам, 16 колонок) |
| `ProjectHealthCost` (без суффикса) | **0 строк** для нашего пользователя (нет прав) — поэтому используем `My` |

### ⚠️ Замечания

1. **Привязка по `projectid`**: в `ProjectHealthCostMy` поле `projectid` — это **bigint ProjectId**, не Code. Сопоставление через `get_view(Project, MyProject)` → `ProjectId` по `Code`.
2. **Данных может не быть** для проектов в ранних стадиях ЖЦ (Пресейл, Инициирование) — в этом случае ответ «Неопределено», а не «Нет».
3. **`outallforecast` уже включает трудозатраты** — это ключевое отличие от показателя №5 (который смотрит только на оплаты).
4. **Сопоставление view по `projectprofileid`**: в `ProjectHealthCost` привязка строк идёт через `projectprofileid`, а не `projectid` напрямую (типичная архитектура Форсайт). Нужно фильтровать по `projectid`.

---
---

## 4. Технические данные отчёта

### Назначение

Таблица с **метаданными отчёта** — кто его сформировал, на какой версии системы, через какой MCP.
Заполняется автоматически при каждом запуске скилла, чтобы отчёт можно было
верифицировать и аудировать.

### Формат таблицы

| # | Поле | Значение | Источник |
|---|------|----------|----------|
| 1 | Пользователь | Кузнецов Ростислав Владимирович | `mcp__fst_pmpractice__get_user_profile` → `FullName` |
| 2 | Титул системы | Нет данных | Сущность `MetaModel` (Настройки системы) — чтение заблокировано (валидатор требует int, PK = string) |
| 3 | URL MCP | `https://ppreplica.hera.pmpractice.ru/mcp` | Из `~/.hermes/profiles/fst-control/config.yaml` → `mcp_servers.fst_pmpractice.url` |
| 4 | Версия скилла | 1.3 | Из `SKILL.md` → frontmatter `version` |
| 5 | Версия MCP | 3.2.4 | Из `mcp.initialize` → `result.serverInfo.version` |
| 6 | Версия ПМ Форсайт | PMForesight MCP v3.2.4 (= версия MCP-сервера) | Из `mcp.initialize` → `result.serverInfo.name + version` |

### Алгоритм заполнения

```
1. Пользователь:
   user = mcp__fst_pmpractice__get_user_profile()
   value = user["FullName"]

2. Титул системы:
   try:
       record = mcp__fst_pmpractice__get_entity_data(
           entityName="MetaModel", data_id="<ключ_записи>"
       )
       value = record["properties"]["Value"]["value"]
   except Exception:
       value = "Нет данных"  # Pydantic-ошибка: data_id должен быть int, а PK = string

3. URL MCP:
   value = "https://ppreplica.hera.pmpractice.ru/mcp"  # из config.yaml

4. Версия скилла:
   value = "1.3"  # из SKILL.md frontmatter

5. Версия_MCP:
   init = POST /mcp {"method":"initialize", ...}
   value = init["result"]["serverInfo"]["version"]

6. Версия ПМ Форсайт:
   value = f"{init['result']['serverInfo']['name']} v{init['result']['serverInfo']['version']}"
   # или просто "Нет данных", если поле пустое
```

### Реальный пример для отчёта 01.08.2026 (504-595)

| # | Поле | Значение |
|---|------|----------|
| 1 | Пользователь | Кузнецов Ростислав Владимирович |
| 2 | Титул системы | Нет данных |
| 3 | URL_MCP | https://ppreplica.hera.pmpractice.ru/mcp |
| 4 | Версия скилла | 1.3 |
| 5 | Версия_MCP | 3.2.4 |
| 6 | Версия ПМ Форсайт | PMForesight MCP v3.2.4 |

### Особенности и ограничения

⚠️ **Титул системы (поле 2):**
- Сущность `MetaModel` («Настройки системы») содержит 2 поля: `Name` (Ключ) и `Value` (Наименование)
- `IdFieldName = Name` — PK строковый
- НО: Pydantic-валидатор в `get_entity_data` требует `int` для `data_id`
- Результат: ошибка «Input should be a valid integer» — запись прочитать нельзя
- Workaround: запросить у администратора Форсайт нужные ключи (например, `SystemName`) и попробовать через `list_entities` или `find_entity`
- **В текущий момент: «Нет данных»**

⚠️ **Версия ПМ Форсайт (поле 6):**
- В MCP-протоколе версия Форсайт = версия MCP-сервера
- `serverInfo.name` = «PMForesight MCP» (название MCP-сервера)
- `serverInfo.version` = «3.2.4» (версия)
- Отдельной «версии ПМ Форсайт» (без MCP) в ответе initialize нет
- Workaround: парсить `X-PM-Version` или другие кастомные HTTP-заголовки (если есть)

### Связь с другими сущностями

| Что | Откуда |
|-----|--------|
| Имя Форсайт как продукта | «Сервер предоставляет доступ к инструментам и данным **ИСУП «Форсайт»**» (из `serverInfo.instructions`) |
| Версия MCP | `serverInfo.version` = «3.2.4» |
| Версия протокола MCP | `protocolVersion` = «2024-11-05» (это **НЕ** версия Форсайт) |

---

## История изменений
---

## История изменений

### Алгоритм для показателя «Owner (OwnerId)»

```
1. Получить данные проекта через get_entity_data(Project, data_id=<projectId>)
   └─ В ответе properties.OwnerId.value

2. Проверить:
   if properties.OwnerId.value == [] или None:
       результат = "Нет"
       деталь = "Роль Owner (Куратор) не назначена"
   elif value is list with items:
       результат = "Да"
       деталь = "<display первого элемента>"
   else:
       результат = "Нет"
       деталь = "Непредвиденный формат значения: <value>"

3. Добавить строку в таблицу:
   | 1 | Owner (OwnerId) | <результат> | <деталь> |
```

### Пример вызова

```python
record = mcp__fst_pmpractice__get_entity_data(
    entityName="Project",
    data_id="4595"  # ProjectId
)

owner = record["properties"]["OwnerId"]
val = owner.get("value")
if not val:  # None или []
    result = "Нет"
    detail = "Роль Owner (Куратор) не назначена"
else:
    first = val[0] if isinstance(val, list) else val
    if isinstance(first, dict) and first.get("display"):
        result = "Да"
        detail = first["display"].strip()
    else:
        result = "Да"
        detail = f"id={first}"
```

### Реальный пример для проекта 504-595 (Космодром Жуковский внедрение ИСУП)

#### OwnerId («Куратор»)

```json
{
  "Name": "Куратор",
  "kind": "SingleSelectRole",
  "type": "bigint",
  "IsRequired": true,
  "IsVisible": true,
  "value": [
    {"value": 120872, "display": "Кузнецов Ростислав Владимирович"}
  ]
}
```

**Результат проверки:** `Owner (OwnerId) | Да | Кузнецов Ростислав Владимирович`

#### LeaderId («Руководитель»)

```json
{
  "Name": "Руководитель",
  "kind": "SingleSelectRole",
  "type": "bigint",
  "IsRequired": false,
  "IsVisible": true,
  "IsReadonly": true,
  "IsEditable": false,
  "value": [
    {"value": 120872, "display": "Кузнецов Ростислав Владимирович"}
  ]
}
```

**Результат проверки:** `РП назначен (LeaderId) | Да | Кузнецов Ростислав Владимирович`

⚠️ **Особенности LeaderId:** `IsRequired=false` (необязательное), `IsReadonly=true`,
`IsEditable=false` — то есть система выставляет его автоматически, но значение
отображается и попадает в отчёт.

### Алгоритм для показателя «РП назначен (LeaderId)»

```
1. Получить данные проекта через get_entity_data(Project, data_id=<projectId>)
   └─ В ответе properties.LeaderId.value

2. Проверить:
   if properties.LeaderId.value == [] или None:
       результат = "Нет"
       деталь = "Руководитель проекта (LeaderId) не назначен"
   elif value is list with items:
       результат = "Да"
       деталь = "<display первого элемента>"
   else:
       результат = "Нет"
       деталь = "Непредвиденный формат значения: <value>"

3. Добавить строку в таблицу:
   | 2 | РП назначен (LeaderId) | <результат> | <деталь> |
```

### Пример вызова (для LeaderId)

```python
record = mcp__fst_pmpractice__get_entity_data(
    entityName="Project",
    data_id="4595"
)

leader = record["properties"]["LeaderId"]
val = leader.get("value")
if not val:
    result = "Нет"
    detail = "Руководитель проекта (LeaderId) не назначен"
else:
    first = val[0] if isinstance(val, list) else val
    if isinstance(first, dict) and first.get("display"):
        result = "Да"
        detail = first["display"].strip()
    else:
        result = "Да"
        detail = f"id={first}"
```

### Алгоритм для показателя «Паспорт готов на стадии Инициирование»

Этот показатель **составной** — требует выполнения **двух** условий:
- (а) Паспорт прикреплён к проекту
- (б) Стадия ЖЦ проекта ≤ «Инициирование» (т.е. Пресейл или Инициирование)

Если хотя бы одно не выполнено → «Нет». Если оба выполнены → «Да».

```
1. Получить данные проекта через get_entity_data(Project, data_id=<projectId>)
   └─ properties.ActivityPhaseId.value.display  → название стадии
   └─ properties.ActivityPhaseId.value.value    → ID стадии (для сравнения)

2. Определить порядковый номер стадии через словарь:
   PHASE_ORDER = {
       "Пресейл": 1,
       "Инициирование": 2,
       "Подготовка": 3,
       "Реализация": 4,
       "Завершение": 5,
       "Архив": 6,
   }
   current_phase = PHASE_ORDER.get(display, 999)  # 999 = неизвестно

3. Проверить (б) условие:
   phase_ok = current_phase <= 2  # Пресейл или Инициирование

4. Проверить (а) условие — наличие паспорта:
   docs = mcp__fst_pmpractice__get_view(
       entityName="DocumentFile", viewName="DocumentFileViewAll"
   )
   passport_attached = False
   for r in docs["data"]:
       if (EntityTitle == "Проект"
           and "<project_code>" in (DataName или "")
           and "паспорт" in (DocumentName или "").lower()):
           passport_attached = True
           break

5. Итог:
   if phase_ok and passport_attached:
       result = "Да"
       detail = "Паспорт прикреплён, стадия «Инициирование» (или раньше)"
   else:
       result = "Нет"
       reasons = []
       if not passport_attached:
           reasons.append("паспорт не прикреплён")
       if not phase_ok:
           reasons.append(f"стадия «{display}» (>{'Инициирование'})")
       detail = "; ".join(reasons)

6. Добавить строку в таблицу:
   | 3 | Паспорт готов на стадии Инициирование | <result> | <detail> |
```

### Пример вызова (для «Паспорт готов на стадии Инициирование»)

```python
PHASE_ORDER = {
    "Пресейл": 1, "Инициирование": 2, "Подготовка": 3,
    "Реализация": 4, "Завершение": 5, "Архив": 6,
}

# 1. Данные проекта
proj = mcp__fst_pmpractice__get_entity_data(
    entityName="Project", data_id="4595"
)
phase = proj["properties"]["ActivityPhaseId"]["value"]
phase_display = phase.get("display", "")
phase_num = PHASE_ORDER.get(phase_display, 999)
phase_ok = phase_num <= 2

# 2. Документы
docs = mcp__fst_pmpractice__get_view(
    entityName="DocumentFile", viewName="DocumentFileViewAll"
)
passport = False
for r in docs["data"]:
    if (r.get("EntityTitle") == "Проект"
        and "504-595" in (r.get("DataName") or "")
        and "паспорт" in (r.get("DocumentName") or "").lower()):
        passport = True
        break

# 3. Итог
if phase_ok and passport:
    result = "Да"
    detail = f"Паспорт прикреплён, стадия «{phase_display}»"
else:
    result = "Нет"
    reasons = []
    if not passport:
        reasons.append("паспорт не прикреплён")
    if not phase_ok:
        reasons.append(f"стадия «{phase_display}» (>{'Инициирование'})")
    detail = "; ".join(reasons)
```

### Реальный пример для проекта 504-595 (Космодром Жуковский внедрение ИСУП)

#### Условия

| Условие | Результат | Деталь |
|---------|-----------|--------|
| (а) Паспорт прикреплён | ✅ Да | Файл «Оценка проектов ОПРОС 01.docx», категория «Паспорт» |
| (б) Стадия ≤ Инициирование | ✅ Да | Текущая стадия = «Инициирование» (№2 в графе) |

#### Результат проверки

`Паспорт готов на стадии Инициирование | Да | Паспорт прикреплён, стадия «Инициирование»`

### Алгоритм для показателя «Актуальность данных проекта по трудозатратам»

#### Семантика

- **Прогноз** — записи `ResourcePlanningKp` (`planning_date <= today`)
- **Факт** — записи `ResourcePlanning` (`planning_date <= today`)
- **today** — текущая дата (08.08.2026 в момент разработки)

#### Правила

| # | Условие | Результат |
|---|---------|-----------|
| 1 | Нет ни прогноза, ни факта | **Да** |
| 2 | Прогноза нет, факт есть | **Да** (факт не требовалось заводить) |
| 3 | Есть прогноз (`last_plan_date`), нет факта | **Нет** |
| 4 | Прогноз + факт, `last_fact_date ≥ last_plan_date`, `last_fact_date − last_plan_date ≤ 10` | **Да** |
| 5 | Прогноз + факт, `last_fact_date < last_plan_date`, `today − last_plan_date ≤ 10` | **Да** |
| 6 | Прогноз + факт, `last_fact_date < last_plan_date`, `today − last_plan_date > 10` | **Нет** |
| 7 | Прогноз + факт, `last_fact_date ≥ last_plan_date`, `last_fact_date − last_plan_date > 10` | **Нет** |

Ключевая идея: **«Нет»** возвращается только если **план был, но факт не заведен вовремя**.

#### Алгоритм

```
1. Получить прогнозы:
   kp_view = get_view(ResourcePlanningKp, ...)
   └─ Если view недоступен (403), fallback: get_entity_data по известным id
   plan_dates = [r.planning_date for r in kp if r.planning_date <= today]
   if not plan_dates:
       plan_present = False
   else:
       plan_present = True
       last_plan_date = max(plan_dates)

2. Получить факт:
   rp_view = get_view(ResourcePlanning, ...)
   └─ ВНИМАНИЕ: ResourcePlanning привязан через ActivityId, не через ProjectId!
   fact_dates = [r.planning_date for r in rp
                 if r.planning_date <= today
                 and r.ActivityId in <project activity ids>]
   if not fact_dates:
       fact_present = False
   else:
       fact_present = True
       last_fact_date = max(fact_dates)

3. Применить правила:
   if not plan_present:
       result = "Да"  # нет плана — нечего было заводить
   elif not fact_present:
       result = "Нет"  # план был, факт не заведён
   else:
       gap = (last_fact_date - last_plan_date).days
       if gap >= 0 and gap <= 10:
           result = "Да"  # факт сразу за планом
       elif gap < 0 and (today - last_plan_date).days <= 10:
           result = "Да"  # факт раньше плана, но недавно
       else:
           result = "Нет"  # слишком большой разрыв
```

#### Пример вызова

```python
from datetime import date, timedelta

TODAY = date.today()

def is_effort_data_current(project_id: int) -> tuple[str, str]:
    """Возвращает (result, detail). result = 'Да' или 'Нет'."""
    
    # 1. Прогнозы
    plan_present, last_plan = False, None
    try:
        kp = mcp__fst_pmpractice__get_view(
            entityName="ResourcePlanningKp", viewName="ResourcePlanningKp"
        )
        plan_dates = [<r.planning_date for ...>]
        if plan_dates:
            plan_present = True
            last_plan = max(plan_dates)
    except Exception:
        pass  # 403 или другая ошибка — считаем план отсутствующим
    
    # 2. Факт
    fact_present, last_fact = False, None
    try:
        rp = mcp__fst_pmpractice__get_view(
            entityName="ResourcePlanning", viewName="ResourcePlanning"
        )
        fact_dates = [<r.planning_date for ...>]
        if fact_dates:
            fact_present = True
            last_fact = max(fact_dates)
    except Exception:
        pass
    
    # 3. Правила
    if not plan_present:
        return "Да", "Прогнозов нет — факт не требовался"
    if not fact_present:
        return "Нет", f"Прогноз на {last_plan}, факт не заведён"
    
    gap = (last_fact - last_plan).days
    if 0 <= gap <= 10:
        return "Да", f"Прогноз {last_plan}, факт {last_fact} (разрыв {gap}д)"
    if gap < 0 and (TODAY - last_plan).days <= 10:
        return "Да", f"Факт {last_fact} раньше плана {last_plan}, но не устарел"
    return "Нет", f"Прогноз {last_plan}, факт {last_fact} (разрыв {gap}д)"
```

#### Реальный пример для проекта 504-595 (Космодром Жуковский внедрение ИСУП)

⚠️ **Доступные данные ограничены.** View `ResourcePlanningKp` и `ResourcePlanning`
закрыты для текущего пользователя (403). Единственная подтверждённая запись —
`ResourcePlanningKpId=1235030` (прогноз 2ч на 15.07.2026), созданная вручную
в этом чате. Других прогнозов и фактических данных получить не удалось.

| Условие | Результат |
|---------|-----------|
| Прогнозы | Известен 1 (наша запись 1235030 на 15.07.2026) |
| Факт | Недоступно (view 403) |
| **Итоговое заключение** | **Невозможно оценить** (недостаточно данных) |

> ⚠️ **Для production-использования** нужно либо admin-права на
> `ResourcePlanning`/`ResourcePlanningKp`, либо использовать обходной путь через
> `ProjectHealthWorkload` (агрегат по месяцам, без разбивки по сотрудникам).

#### Ограничения данных

⚠️ Оба view (`ResourcePlanning`, `ResourcePlanningKp`) **закрыты 403** для обычного
пользователя. `ProjectHealthWorkload` (агрегат помесячно) — открыт, но он
содержит `plan_m`/`fact_m` как **сумму часов за месяц**, а не отдельные даты.
Для строгой проверки алгоритма нужны детальные записи.

### Алгоритм для показателя «Корректность заполнения графика платежей проекта»

#### Семантика

⚠️ **Показатель на уровне ПРОЕКТА, а не контракта.** К проекту может быть
привязано **несколько контрактов** (через `InContract.InContractActivity` или
`OutcomeContract.OutcomeContractActivity`). Для каждого контракта считаем Δ
отдельно, затем **складываем Δ по всем контрактам** — и сравниваем уже
суммарную дельту с порогами.

⚠️ **В Форсайт акты и оплаты — это КТ (Point)**, а не отдельные сущности.
У них есть поля `PlanSum`, `ForecastSum`, `FactSum`. Контракт — это `InContract`
(доходный) или `OutcomeContract` (расходный), а его КТ привязаны через
`ParentId` = `ActivityId` контракта.

| Понятие | Что это | Где |
|---------|---------|-----|
| **Контракт** | Запись в `InContract` / `OutcomeContract` с `Code` (например `704-724`) и `RealSum` | `InContract.RealSum` |
| **Акт** | КТ (Point) с `ParentId=ActivityId контракта`, в имени содержит «Акт» | `Point.FactSum`/`ForecastSum` |
| **Оплата** | КТ (Point) с `ParentId=ActivityId контракта`, в имени «Оплата»/«Платёж» | `Point.FactSum`/`ForecastSum` |
| **Связь контракт↔проект** | `InContractActivity` (multi) или `OutcomeContractActivity` (multi) → массив ActivityId | В обоих случаях |

#### Логика проверки

**Двухуровневая логика:**

**Уровень 1: контракт.**
Для каждого контракта, привязанного к проекту, считаем:

```
effective_sum = FactSum if FactSum > 0 else ForecastSum
Δ_contract = |Σ актов_effective − Σ оплат_effective|
```

**Уровень 2: проект.**
Суммируем дельты по всем контрактам проекта:

```
Δ_project = Σ Δ_contract (по всем контрактам проекта)
```

⚠️ **Важно:** складываем **абсолютные** Δ, а не сначала суммы. Это значит,
что расхождения по разным контрактам **не компенсируют** друг друга
(положительное в одном не гасит отрицательное в другом).

⚠️ **Смешанная сумма** — `FactSum` имеет приоритет (если > 0), иначе `ForecastSum`.

#### Правила

| # | Условие | Результат |
|---|---------|-----------|
| 1 | Нет ни актов, ни оплат | **Да** (платежей нет — нечего проверять) |
| 2 | |Σ актов − Σ оплат| = 0 | **Да** |
| 3 | 0 < |Σ актов − Σ оплат| < 100 тыс. | **Нет/Информационное замечание** |
| 4 | 100 тыс. ≤ |Σ актов − Σ оплат| < 1 млн | **Нет/Существенное замечание** |
| 5 | |Σ актов − Σ оплат| ≥ 1 млн | **Нет/Критическое замечание** |

⚠️ **Пороговые значения** (записать как параметры в финальный скилл):

```python
THRESHOLDS = {
    "informational": 100_000,    # < 100 тыс.
    "substantial": 1_000_000,    # 100 тыс. ... 1 млн
    # > 1 млн = critical
}
```

#### Алгоритм

```
1. Найти все контракты, привязанные к проекту:
   projects = get_view(Project, MyProject)
   project = next(p for p in projects.data if p.Code == "<project_code>")
   project_activity_ids = {project.ActivityId}  # один ID для проекта

   # Контракты InContract (доходные) с привязкой к проекту:
   ic_view = get_view(InContract, InContractMyProject)
   in_contracts = [c for c in ic_view.data
                   if any(a.value in project_activity_ids
                          for a in (c.InContractActivity or []))]

   # Контракты OutcomeContract (расходные) с привязкой к проекту:
   oc_view = get_view(OutcomeContract, OutcomeContractMyProject)
   out_contracts = [c for c in oc_view.data
                    if any(a.value in project_activity_ids
                           for a in (c.OutcomeContractActivity or []))]

   all_contracts = in_contracts + out_contracts

2. Для каждого контракта посчитать Δ_contract:
   total_delta = 0
   contract_deltas = []  # для отчёта

   points = get_view(Point, AllMyPoint, limit=3000)

   for contract in all_contracts:
       contract_points = [p for p in points.data
                          if str(p.ParentCode or "").strip() == contract.Code]
       # Разделить на акты и оплаты
       acts  = [p for p in contract_points if "Акт"  in (p.pointname or "")]
       pays  = [p for p in contract_points if "Оплат" in (p.pointname or "")
                                          or "Платеж" in (p.pointname or "")]

       # Получить детальные суммы через get_entity_data
       act_sum = sum(effective_sum(get_point_detail(p.PointId)) for p in acts)
       pay_sum = sum(effective_sum(get_point_detail(p.PointId)) for p in pays)
       delta_c = abs(act_sum - pay_sum)
       total_delta += delta_c
       contract_deltas.append({
           "code": contract.Code,
           "name": contract.Name,
           "acts_sum": act_sum,
           "pays_sum": pay_sum,
           "delta": delta_c
       })

3. Применить правила к total_delta:
   if total_delta == 0:
       result = "Да"
   elif total_delta < 100_000:
       result = "Нет/Информационное замечание"
   elif total_delta < 1_000_000:
       result = "Нет/Существенное замечание"
   else:
       result = "Нет/Критическое замечание"

4. Добавить строку в таблицу:
   | 5 | Корректность заполнения графика платежей проекта | <result> | <detail> |
   где detail = "Δ_project = X ₽ (по N контрактам)"
```

#### Пример вызова

```python
THRESHOLDS = {
    "informational": 100_000,
    "substantial": 1_000_000,
}

def effective_sum(point_props):
    """Берём FactSum если > 0, иначе ForecastSum."""
    fact = float(point_props.get("FactSum", {}).get("value") or 0)
    forecast = float(point_props.get("ForecastSum", {}).get("value") or 0)
    if fact > 0:
        return fact
    if forecast > 0:
        return forecast
    return 0

# 1. Найти проект и его ActivityId
projects = mcp__fst_pmpractice__get_view(entityName="Project", viewName="MyProject")
project = next(p for p in projects["data"] if p["Code"] == "504-595")
project_activity_ids = {project["ActivityId"]}

# 2. Найти все контракты, привязанные к проекту
contracts = []

# 2a. InContract (доходные)
ic_view = mcp__fst_pmpractice__get_view(
    entityName="InContract", viewName="InContractMyProject"
)
for c in ic_view["data"]:
    ica = c.get("InContractActivity") or []
    if any(a.get("value") in project_activity_ids for a in ica):
        contracts.append({"type": "InContract", "id": c["id"], "code": c["Code"]})

# 2b. OutcomeContract (расходные)
oc_view = mcp__fst_pmpractice__get_view(
    entityName="OutcomeContract", viewName="OutcomeContractMyProject"
)
for c in oc_view["data"]:
    oca = c.get("OutcomeContractActivity") or []
    if any(a.get("value") in project_activity_ids for a in oca):
        contracts.append({"type": "OutcomeContract", "id": c["id"], "code": c["Code"]})

# 3. Загрузить все КТ
points_view = mcp__fst_pmpractice__get_view(
    entityName="Point", viewName="AllMyPoint", limit=3000
)

# 4. Посчитать Δ для каждого контракта, сложить
total_delta = 0
contract_results = []

for contract in contracts:
    code = contract["code"]
    contract_points = [
        p for p in points_view["data"]
        if str(p.get("ParentCode", "")).strip() == code
    ]

    # Получить детали каждой КТ (для имени и сумм)
    act_sum = 0
    pay_sum = 0
    for p in contract_points:
        detail = mcp__fst_pmpractice__get_entity_data(
            entityName="Point", data_id=str(p["PointId"])
        )
        name = (detail["properties"].get("Name", {}).get("value") or "").lower()
        es = effective_sum(detail["properties"])
        if "акт" in name:
            act_sum += es
        elif "оплат" in name or "платеж" in name or "платёж" in name:
            pay_sum += es

    delta_c = abs(act_sum - pay_sum)
    total_delta += delta_c
    contract_results.append({
        "code": code,
        "acts": act_sum,
        "pays": pay_sum,
        "delta": delta_c
    })

# 5. Вердикт
if total_delta == 0:
    result = "Да"
    detail = f"Δ = 0 ₽ по {len(contracts)} контрактам"
elif total_delta < THRESHOLDS["informational"]:
    result = "Нет/Информационное замечание"
    detail = f"Δ = {total_delta:,.2f} ₽ (< 100 тыс.)"
elif total_delta < THRESHOLDS["substantial"]:
    result = "Нет/Существенное замечание"
    detail = f"Δ = {total_delta:,.2f} ₽ (100 тыс.–1 млн)"
else:
    result = "Нет/Критическое замечание"
    detail = f"Δ = {total_delta:,.2f} ₽ (> 1 млн)"

# Подробный отчёт по контрактам (опционально)
for cr in contract_results:
    print(f"{cr['code']}: Σ актов = {cr['acts']:,.2f}, Σ оплат = {cr['pays']:,.2f}, Δ = {cr['delta']:,.2f}")
```

#### Источник данных (уточнение)

⚠️ На практике **акты и оплаты хранятся как КТ (Point)** с `ParentId` = ActivityId контракта,
а не как отдельные сущности. Их финансы — в полях КТ: `PlanSum`, `ForecastSum`, `FactSum`.

Алгоритм сравнения:

```
1. Для каждого акта/оплаты определить ЭФФЕКТИВНУЮ сумму:
   if FactSum is not None and FactSum > 0:
       effective = FactSum        # факт есть
   elif ForecastSum is not None and ForecastSum > 0:
       effective = ForecastSum   # факта нет, берём прогноз
   else:
       effective = 0             # ничего нет

2. Σ актов  = sum(effective для всех актов контракта)
3. Σ оплат  = sum(effective для всех оплат контракта)
4. Δ = |Σ актов − Σ оплат|
```

#### Реальный пример для проекта 504-595

**Шаг 1: Найти контракты проекта.**

`get_view(InContract, InContractMyProject)` (или `OutcomeContractMyProject`).
Сейчас у проекта 504-595 (ProjectId=4595, ActivityId=4595) **один доходный контракт**:
`704-724. Контракт на разработку ИСУП для ТЛК "Космодром Жуковский"` (InContract id=4724),
привязан через `InContractActivity=[{value: 4595}]`.

⚠️ Если у проекта будет ещё расходный контракт или несколько — алгоритм обработает
все. Каждый даст свою дельту.

**Шаг 2: Посчитать Δ_contract для 704-724.**

**Акты контракта (ParentCode=704-724):**

| Code | Name | PlanSum | ForecastSum | FactSum | Берём | Сумма |
|------|------|---------|-------------|---------|-------|-------|
| 104-725 | Акт по 1-му блоку работ | 2 500 000 | 2 499 990 | 2 500 | **Fact** | 2 500 |
| 104-731 | Акт по 1-му блоку (доплата) | 2 497 500 | 2 497 500 | 2 497 500 | **Fact** | 2 497 500 |
| 104-732 | Акт по 2-му блоку работ | 1 500 000 | 1 500 000 | 0 | **Forecast** | 1 500 000 |
| **Σ актов** | | | | | | **4 000 000** |

**Оплаты контракта (ParentCode=704-724):**

| Code | Name | PlanSum | ForecastSum | FactSum | Берём | Сумма |
|------|------|---------|-------------|---------|-------|-------|
| 104-726 | Оплата по 1-му блоку | 2 500 000 | 2 500 000 | 2 500 | **Fact** | 2 500 |
| 104-730 | Промежуточная оплата | 2 497 500 | 2 497 500 | 2 497 500 | **Fact** | 2 497 500 |
| 104-733 | Оплата по 2-му блоку | 1 500 000 | 1 500 000 | 0 | **Forecast** | 1 500 000 |
| **Σ оплат** | | | | | | **4 000 000** |

**Δ_contract(704-724) = |4 000 000 − 4 000 000| = 0 ₽**

**Шаг 3: Сложить дельты по проекту.**

У проекта 504-595 один контракт → Δ_project = 0 ₽ → **Да**.

#### Ограничения

⚠️ Подход через `find_entity` для контракта → `get_entity_data` для каждой КТ —
надёжный, но **медленный** (много запросов). Для больших проектов нужен
batch-режим, который пока не реализован в MCP.

View `ContractPlanSummaries` / `ContractPlanSummariesValue` остаются **закрыты 403**
для обычного пользователя, но алгоритм выше работает и без них.

### Источник

#### Owner (OwnerId)

- Поле: `Project.OwnerId` (bigint, SingleSelectRole)
- Заголовок поля (Title): **«Куратор»** — важно! не «Owner» и не «Владелец»
- Обязательность: ✅ Да (`IsRequired=True`)
- Видимость: ✅ Да (`IsVisible=True`)
- ItemType: `Role`
- Возможные значения: массив `[{value: <userId>, display: "<ФИО>"}]`, может быть пустым `[]`

#### Leader (LeaderId)

- Поле: `Project.LeaderId` (bigint, SingleSelectRole)
- Заголовок поля (Title): **«Руководитель»** — НЕ «РП»!
- Обязательность: ❌ Нет (`IsRequired=false`)
- Видимость: ✅ Да (`IsVisible=True`)
- Readonly: ✅ Да (`IsReadonly=true`) — заполняется автоматически
- ItemType: `Role`
- Возможные значения: массив `[{value: <userId>, display: "<ФИО>"}]`, может быть пустым `[]`

### ⚠️ Особенности

- `describe_entity(Project, data_id=<id>)` возвращает **только схему** без значений полей.
  Для значений используй `get_entity_data`.
- Имя поля `OwnerId` в API, но **Title = «Куратор»** — это важно для отчёта пользователю.
- SingleSelectRole может вернуть пустой массив `[]` — это означает «роль не назначена».
- `display` в значениях содержит ФИО с пробелом на конце (нормально для Форсайт).

---

## 3. Финансовый статус проекта

### Назначение

Таблица из **3 строк**, отражающая финансовое состояние проекта по завершении.
Первая строка — **«Прогноз по окончании проекта показывает финансовый результат менее нуля»** —
содержание этой секции. Остальные строки добавляются позже.

### Формат таблицы

| # | Показатель | Результат | Деталь |
|---|------------|-----------|--------|
| 1 | Прогноз по окончании проекта показывает финансовый результат менее нуля | Нет / Да ["Это критическое замечание"] | Расчёт: Σ доходы − Σ расходы |
| 2 | *(следующий показатель)* | … | … |
| 3 | *(следующий показатель)* | … | … |

### Алгоритм для показателя «Финансовый результат прогноза по окончании проекта»

#### Семантика

| Понятие | Что это | Где |
|---------|---------|-----|
| **Доходы (приходы)** | Суммы по оплатам **доходных контрактов** (InContract), привязанных к проекту | `InContract.RealSum`, КТ-оплаты с `ParentId=ActivityId контракта` |
| **Расходы** | Суммы по оплатам **расходных контрактов** (OutcomeContract), привязанных к проекту | `OutcomeContract.RealSum`, КТ-оплаты с `ParentId=ActivityId контракта` |
| **Финансовый результат** | Σ доходов (смешанная) − Σ расходов (смешанная) | Расчёт |

⚠️ **Смешанная сумма** — `FactSum` если > 0, иначе `ForecastSum` для каждой КТ-оплаты
(по аналогии с показателем №5 «Корректность графика платежей»).

⚠️ **Привязка контракта к проекту** идёт через `InContractActivity` / `OutcomeContractActivity`
(multi-поле). У одного контракта может быть несколько проектов, у проекта — несколько контрактов.

#### Правила

| # | Условие | Результат |
|---|---------|-----------|
| 1 | Нет ни доходных, ни расходных контрактов | **Нет** (нечего оценивать) |
| 2 | Результат (Σ доходов − Σ расходов) ≥ 0 | **Нет** (финансово здоров) |
| 3 | Результат < 0 | **Да ["Это критическое замечание"]** (с указанием суммы) |

#### Алгоритм

```
1. Получить все доходные контракты, привязанные к проекту:
   in_contracts = []
   for c in find_entity(<project_code>) or InContractAll:
       detail = get_entity_data(InContract, c.id)
       ica = detail.properties.InContractActivity.value or []
       if any(a.value == <project_activity_id> for a in ica):
           in_contracts.append(detail)

2. Получить все расходные контракты, привязанные к проекту:
   out_contracts = []
   for c in OutcomeContractAll or find_entity:
       detail = get_entity_data(OutcomeContract, c.id)
       oca = detail.properties.OutcomeContractActivity.value or []
       if any(a.value == <project_activity_id> for a in oca):
           out_contracts.append(detail)

3. Получить все КТ (точки) проекта:
   points = get_view(Point, AllMyPoint, limit=3000)
   project_points = [p for p in points.data
                     if p.ParentCode == <project_code>]
   # Разделить на доходы (родитель = доходный контракт) и расходы
   income_points  = [p for p in project_points
                     if p.ParentCode in {c.Code for c in in_contracts}]
   expense_points = [p for p in project_points
                     if p.ParentCode in {c.Code for c in out_contracts}]

4. Для каждой КТ определить эффективную сумму:
   def effective(p):
       f = float(p.FactSum or 0)
       fc = float(p.ForecastSum or 0)
       return f if f > 0 else fc

5. Суммы:
   total_income  = sum(effective(p) for p in income_points)
   total_expense = sum(effective(p) for p in expense_points)
   result = total_income - total_expense

6. Вердикт:
   if result >= 0:
       row_result = "Нет"
       detail = f"Прогноз: +{result:,.2f} ₽ (доходы {total_income:,.2f} − расходы {total_expense:,.2f})"
   else:
       row_result = "Да"
       detail = f"Прогноз: {result:,.2f} ₽ (доходы {total_income:,.2f} − расходы {total_expense:,.2f}) — это критическое замечание"

7. Добавить строку:
   | 1 | Прогноз по окончании проекта показывает финансовый результат менее нуля | <row_result> | <detail> |
```

#### Пример вызова

```python
PROJECT_ACTIVITY_ID = 4595  # ActivityId проекта 504-595
PROJECT_CODE = "504-595"
THRESHOLD_PROFITABILITY = 0  # результат < 0 = убыток

# 1. Доходные контракты
in_contracts = []
# Через InContractAll (с фильтром по InContractActivity)
ic_all = mcp__fst_pmpractice__get_view(
    entityName="InContract", viewName="InContractAll", limit=1000
)
for c in ic_all["data"]:
    if str(c.get("Code", "")).startswith("704-724"):  # целевой контракт
        detail = mcp__fst_pmpractice__get_entity_data(
            entityName="InContract", data_id=str(c["InContractId"])
        )
        in_contracts.append(detail)

# 2. Расходные контракты
out_contracts = []
# Аналогично через OutcomeContractAll
oc_all = mcp__fst_pmpractice__get_view(
    entityName="OutcomeContract", viewName="OutcomeContractAll", limit=1000
)
# (для нашего проекта пока 0)

# 3. КТ проекта
points = mcp__fst_pmpractice__get_view(
    entityName="Point", viewName="AllMyPoint", limit=3000
)
project_points = [p for p in points["data"]
                  if str(p.get("ParentCode", "")).strip() == PROJECT_CODE]

# 4. Эффективные суммы
def effective(point_props):
    f = float(point_props.get("FactSum", {}).get("value") or 0)
    fc = float(point_props.get("ForecastSum", {}).get("value") or 0)
    return f if f > 0 else fc

# 5. Суммы (берем КТ с именем "Оплата" — это финансовые проводки)
total_income = 0
total_expense = 0
income_contract_codes = {c["properties"]["Code"]["value"] for c in in_contracts}
expense_contract_codes = {c["properties"]["Code"]["value"] for c in out_contracts}

for p in project_points:
    parent = str(p.get("ParentCode", "")).strip()
    if parent in income_contract_codes:
        detail = mcp__fst_pmpractice__get_entity_data(
            entityName="Point", data_id=str(p["PointId"])
        )
        name = (detail["properties"].get("Name", {}).get("value") or "").lower()
        if "оплат" in name or "платеж" in name or "платёж" in name:
            total_income += effective(detail["properties"])
    elif parent in expense_contract_codes:
        # аналогично для расходов
        ...

result = total_income - total_expense

# 6. Вердикт
if result < THRESHOLD_PROFITABILITY:
    row_result = "Да"
    detail = f"Прогноз: {result:,.2f} ₽ — это критическое замечание"
else:
    row_result = "Нет"
    detail = f"Прогноз: +{result:,.2f} ₽"
```

#### Реальный пример для проекта 504-595 (на 01.08.2026)

| Показатель | Значение |
|------------|----------|
| Доходные контракты | 1 (704-724, `RealSum=5 400 000 ₽`) |
| Расходные контракты | 0 (по проекту 504-595 в `OutcomeContractMyProject` пусто) |
| Σ доходов (смешанная) | 5 400 000 ₽ |
| Σ расходов (смешанная) | 0 ₽ |
| **Результат** | **+5 400 000 ₽** (положительный) |

| # | Показатель | Результат | Деталь |
|---|------------|-----------|--------|
| 1 | Прогноз по окончании проекта показывает финансовый результат менее нуля | **Нет** | Прогноз: +5 400 000 ₽ (доходы 5 400 000 − расходы 0) |
| 2 | *(следующий показатель)* | … | … |
| 3 | *(следующий показатель)* | … | … |

### Ограничения

⚠️ **Для live-расчёта нужно учитывать:**
- `InContractActivity` / `OutcomeContractActivity` приходят только через `get_entity_data`,
  а **в view `InContractAll` поле пустое** (None) — приходится делать `get_entity_data`
  для каждого контракта.
- Если у проекта много контрактов, это **медленно** (1 запрос на контракт).
- Для доходов и расходов нужно фильтровать КТ по `ParentId = ActivityId контракта` (не проекта!),
  что в строке view Point поле `ParentId` уже есть — но фильтр по `ParentCode` работает только
  если view содержит `Code` родителя (а это уже `ParentCode` в view Point).

---

## 4. Технические данные отчёта

### Назначение

Таблица с **метаданными отчёта** — кто его сформировал, на какой версии системы, через какой MCP.
Заполняется автоматически при каждом запуске скилла, чтобы отчёт можно было
верифицировать и аудировать.

### Формат таблицы

| # | Поле | Значение | Источник |
|---|------|----------|----------|
| 1 | Пользователь | Кузнецов Ростислав Владимирович | `mcp__fst_pmpractice__get_user_profile` → `FullName` |
| 2 | Титул системы | Нет данных | Сущность `MetaModel` (Настройки системы) — чтение заблокировано (валидатор требует int, PK = string) |
| 3 | URL MCP | `https://ppreplica.hera.pmpractice.ru/mcp` | Из `~/.hermes/profiles/fst-control/config.yaml` → `mcp_servers.fst_pmpractice.url` |
| 4 | Версия скилла | 1.3 | Из `SKILL.md` → frontmatter `version` |
| 5 | Версия MCP | 3.2.4 | Из `mcp.initialize` → `result.serverInfo.version` |
| 6 | Версия ПМ Форсайт | PMForesight MCP v3.2.4 (= версия MCP-сервера) | Из `mcp.initialize` → `result.serverInfo.name + version` |

### Алгоритм заполнения

```
1. Пользователь:
   user = mcp__fst_pmpractice__get_user_profile()
   value = user["FullName"]

2. Титул системы:
   try:
       record = mcp__fst_pmpractice__get_entity_data(
           entityName="MetaModel", data_id="<ключ_записи>"
       )
       value = record["properties"]["Value"]["value"]
   except Exception:
       value = "Нет данных"  # Pydantic-ошибка: data_id должен быть int, а PK = string

3. URL MCP:
   value = "https://ppreplica.hera.pmpractice.ru/mcp"  # из config.yaml

4. Версия скилла:
   value = "1.3"  # из SKILL.md frontmatter

5. Версия_MCP:
   init = POST /mcp {"method":"initialize", ...}
   value = init["result"]["serverInfo"]["version"]

6. Версия ПМ Форсайт:
   value = f"{init['result']['serverInfo']['name']} v{init['result']['serverInfo']['version']}"
   # или просто "Нет данных", если поле пустое
```

### Реальный пример для отчёта 01.08.2026 (504-595)

| # | Поле | Значение |
|---|------|----------|
| 1 | Пользователь | Кузнецов Ростислав Владимирович |
| 2 | Титул системы | Нет данных |
| 3 | URL_MCP | https://ppreplica.hera.pmpractice.ru/mcp |
| 4 | Версия скилла | 1.3 |
| 5 | Версия_MCP | 3.2.4 |
| 6 | Версия ПМ Форсайт | PMForesight MCP v3.2.4 |

### Особенности и ограничения

⚠️ **Титул системы (поле 2):**
- Сущность `MetaModel` («Настройки системы») содержит 2 поля: `Name` (Ключ) и `Value` (Наименование)
- `IdFieldName = Name` — PK строковый
- НО: Pydantic-валидатор в `get_entity_data` требует `int` для `data_id`
- Результат: ошибка «Input should be a valid integer» — запись прочитать нельзя
- Workaround: запросить у администратора Форсайт нужные ключи (например, `SystemName`) и попробовать через `list_entities` или `find_entity`
- **В текущий момент: «Нет данных»**

⚠️ **Версия ПМ Форсайт (поле 6):**
- В MCP-протоколе версия Форсайт = версия MCP-сервера
- `serverInfo.name` = «PMForesight MCP» (название MCP-сервера)
- `serverInfo.version` = «3.2.4» (версия)
- Отдельной «версии ПМ Форсайт» (без MCP) в ответе initialize нет
- Workaround: парсить `X-PM-Version` или другие кастомные HTTP-заголовки (если есть)

### Связь с другими сущностями

| Что | Откуда |
|-----|--------|
| Имя Форсайт как продукта | «Сервер предоставляет доступ к инструментам и данным **ИСУП «Форсайт»**» (из `serverInfo.instructions`) |
| Версия MCP | `serverInfo.version` = «3.2.4» |
| Версия протокола MCP | `protocolVersion` = «2024-11-05» (это **НЕ** версия Форсайт) |

---

## История изменений
---

## История изменений

- **v1.3** — добавлен показатель «Прогноз по окончанию показывает уменьшение финансового результата от планового более чем на 2 млн. руб.» в таблицу «Финансовый статус» (строка 3). Ключевая находка: поля `plan` и `forecast` в `ProjectHealthCostMy` **уже соответствуют** двум схемам пользователя — «Плановый» = `plan`, «Реальный» = `forecast`. Расхождение между ними = `outallplan − outallforecast`. Порог 2 млн. Для 501-682: Δ = −824 827.24 ₽ → «Нет». Для 504-595 — «Неопределено».
- **v1.2** — добавлен показатель «Отклонение текущей стоимости от плана на текущую дату более 1 млн. руб.» в таблицу «Финансовый статус». Алгоритм: текущая стоимость (mixed: FactSum если > 0, иначе ForecastSum) vs план на тек. дату (inplan − outplan). Порог 1 млн. Для 504-595 — «Неопределено» (нет данных в ProjectHealthCostMy), для 501-682 — Δ = 252 802 ₽ → «Нет».
- **v1.1** — **алгоритм «Финансовый результат по окончании» переработан.** Вместо ручного расчёта через `InContract` + `OutcomeContract` + КТ, найден **готовый view `ProjectHealthCostMy`** — это и есть UI-форма «Бюджет проекта, руб.». 15 колонок: `inplan/infact` (доходы), `outplan/outfact/outallplan/outallforecast` (расходы), `fact/plan/forecast` (фин.результат). Целевой показатель — `forecast` (Прогноз. фин.результат по окончании). Для 504-595 данных нет (стадия «Инициирование»), для 501-682 — forecast=53 436 120 ₽ → «Нет».
- **v1.0** — добавлен раздел «Финансовый статус проекта» (раздел 3). Первая строка таблицы: «Прогноз по окончании проекта показывает финансовый результат менее нуля». Доходы = Σ оплат доходных контрактов, Расходы = Σ оплат расходных контрактов. Смешанная сумма: FactSum если > 0, иначе ForecastSum. Пример 504-595: +5 400 000 ₽ → «Нет». Таблица содержит 3 строки, остальные 2 будут добавлены позже.
- **v0.9** — добавлена новая таблица «Актуальность прогнозов по проекту» (раздел 2). Превентивный показатель: КТ с `ForecastDate < today` и пустым `FactDate`. Пороги 1 / 2 / 10 дней → Информационное / Существенное / Критическое. Реальный пример для 504-595: 4 просроченных КТ, все «Существенное» (2–8 дней).
- **v0.8** — **показатель переработан на уровень ПРОЕКТА, а не контракта.** Теперь считаем Δ_contract для каждого контракта, привязанного к проекту (через `InContractActivity` / `OutcomeContractActivity`), затем суммируем абсолютные дельты → Δ_project. Сравнение с порогами уже по Δ_project. Пример: 504-595 имеет 1 контракт (704-724) с Δ=0 → Δ_project=0 → **Да**.
- **v0.5** — добавлен показатель «Актуальность данных проекта по трудозатратам» с матрицей из 7 условий. Уточнено правило: «Нет» только если план был, а факт не заведён вовремя. Зафиксировано ограничение: view ResourcePlanning/Kp = 403 для обычных пользователей.
- **v0.4** — добавлен составной показатель «Паспорт готов на стадии Инициирование» (требует паспорт + стадия ≤ Инициирование). Зафиксирован граф ЖЦ из 6 стадий (Пресейл → Архив). Реальный пример для 504-595: «Да».
- **v0.3** — добавлен показатель «РП назначен (LeaderId)» — реальные данные для 504-595 (Кузнецов Р.В.), зафиксирована особенность LeaderId (IsReadonly=true, IsEditable=false)
- **v0.2** — уточнён алгоритм по результатам live-проверки: `OwnerId` → Title «Куратор», значения через `get_entity_data`, реальный пример для проекта 504-595
- **v0.1** — добавлен раздел «Проверка полноты заполнения проекта», показатель `Owner (OwnerId)`
