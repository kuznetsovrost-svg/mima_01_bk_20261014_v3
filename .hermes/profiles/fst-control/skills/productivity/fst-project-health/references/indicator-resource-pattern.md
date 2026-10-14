# Resource-related indicators (6.3, 6.4, 6.5, 6.6, 6.7) — implementation pattern

Documented 2026-09-02 after implementing 6.3, 6.4, 6.5, 6.6 from user's эскизы.

## Common data source

All resource indicators pull from **`Project/ProjectResourcePlan`** (NOT from `Point/AllMyPoint` or any other view). Filter is `filters={"ProjectId": <id>}`.

**Key fields:**

| Field | Type | Used for |
|-------|------|----------|
| `activityid` | int | ProjectId (sanity check) |
| `accountid` | int | UserId (always set, even for roles — see Pitfall #104) |
| `username` | str | User name OR role name (e.g., "Аналитик") |
| `specialization` | str | Role/specialization name |
| `planning_date` | str (ISO) | Date of effort entry (YYYY-MM-DD or full ISO) |
| `plan_hours` | float | Committed/approved effort hours |
| `forecast_hours` | float | Predicted effort hours (often much larger) |
| `fact_hours` | float | Already-spent effort hours |

## The 3 different "effort" indicators

| # | Indicator | Field | Live-probe (504-595) |
|---|-----------|-------|----------------------|
| 6.3 | Прогнозы по ресурсам | `forecast_hours` | 610 ч |
| 6.4 | Плановые ТРЗ | `plan_hours` | 144 ч |
| 6.5 | Перегрузка >100% | `forecast_hours` (per user explicit correction) | — |
| 6.6 | Нереализованные роли | `forecast_hours` for `username == specialization` | 87.1 ч |
| 6.7 | План по всем активностям >100% | `plan_hours` for **all projects** | — |

**Pitfall:** User explicitly corrected when I was implementing 6.5 to use `plan_hours`: «ТОлько не плановая дата, а прогнозная!» — when the эскиз says "прогноз", use `forecast_hours`, not `plan_hours`. The user distinguishes them clearly.

## Common helper functions

```python
def _parse_iso_date(s):
    """ISO date string → date object, or None on error."""
    if not s: return None
    try: return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except: return None

def _format_month_year(d):
    """date → 'Месяц-Год' (e.g. 'Сентябрь-2026')."""
    months_ru = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                 "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
    return f"{months_ru[d.month]}-{d.year}"
```

## Project period detection (shared by 6.3, 6.4, 6.5)

```python
def get_project_period(project_id, sid, project_code):
    """Returns (start_date, end_date) for the project.

    Priority order:
      - Start: ProjectParameter.projectstart_plandate
      - End: phasefinish_forecastdate → phasefinish_plandate (forecast > plan)
      - Fallback to КТ dates (min PlanDate, max ForecastDate)
    """
    param = next((r for r in param_rows
                  if str(r.get("code", "")).strip() == project_code), None)
    start = _parse_iso_date(param.get("projectstart_plandate"))
    end = (_parse_iso_date(param.get("phasefinish_forecastdate"))
           or _parse_iso_date(param.get("phasefinish_plandate")))
    if not start or not end:
        # fallback to КТ
        ...
```

## Workday calculation for 6.5 / 6.7

Per user requirement: норма = 8ч × рабочие дни (Пн-Пт), для **неполных** месяцев тоже.

```python
def _count_workdays(start_date, end_date) -> int:
    """Count weekdays (Mon-Fri) in period."""
    if not start_date or not end_date or end_date < start_date:
        return 0
    workdays = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:  # Mon=0, Sun=6
            workdays += 1
        current += timedelta(days=1)
    return workdays

# Норма за месяц = workdays × 8ч
# Процент = (forecast_за_месяц / норма) × 100%
```

## Severity bands (for 6.5/6.7)

| Процент | Severity | Цвет |
|--------:|:--------:|:----:|
| ≤100% | (норма, не выводится) | — |
| >100% до 110% | informational | нейтральный |
| >110% до 150% | substantial | 🟡 жёлтый |
| >150% | critical | 🔴 красный |

Note: 6.7 эскиз НЕ описывает severity выше 150% — пока используем `substantial` для всех нарушений.

## Threshold module pattern

Each resource indicator has its own threshold module in `scripts/<name>_thresholds.py`:

- `scripts/effort_forecast_thresholds.py` (6.3)
- `scripts/plan_effort_thresholds.py` (6.4)
- `scripts/overload_thresholds.py` (6.5)
- `scripts/unfilled_roles_thresholds.py` (6.6)

Each exposes:
```python
INDICATOR_THRESHOLDS = {
    "6.X_<name>": {
        "critical_when": lambda r: ...,
        "substantial_when": lambda r: ...,
        "informational_when": lambda r: ...,
        "default_verdict": "Норма",
    }
}
def interpret_indicator(key, result_value, detail) -> str: ...
# Optional: domain-specific helpers (e.g. classify_overload_percent, is_role_resource)
```

This keeps `project_indicators.py` focused on data fetching + formatting, separate from policy.

## Result column format (user-confirmed)

```python
f"Да, {N} ч"        # comma between prefix and number
f"Нет"               # no comma (no number follows)
f"Вопросы, {N} ч"   # comma
```

For merging multiple issues in one row:
```python
", ".join(parts)  # NO quotes around parts
# "Трудозатраты не заданы, Не учлен труда РП"
```

## Row color priority (6.3, 6.5)

When one row has multiple conditions:
- 🔴 red > 🟡 yellow (red wins)
- "только РП" → 🟡 yellow
- "только прогнозов нет" → 🔴 red
- "оба" → 🔴 red (но примечание содержит оба сообщения)

## Кеширование

Все `fetch_with_cache()` для `ProjectResourcePlan` используют TTL=5 мин через `scripts/project_indicators.py::fetch_with_cache`. Не вызывать MCP напрямую из индикаторов.

## Live-probe coverage (2026-09-02)

| Индикатор | 504-595 | 503-434 | 503-152 | 504-314 |
|-----------|---------|---------|---------|---------|
| 6.3 Прогнозы | ✅ Да, 610 ч | 🟡 Вопросы, 1025 ч (5 замечаний) | ✅ Да, 1021 ч | 🟡 Вопросы, 553 ч (1 замечание) |
| 6.4 Плановые | ✅ Да, 144 ч | 🟡 Вопросы, 608 ч (7 замечаний) | 🔴 Нет (8 замечаний) | 🔴 Нет (1 замечание) |
| 6.5 Перегрузка | ✅ Да | ✅ Да | ✅ Да | ✅ Да |
| 6.6 Роли в прошлом | ✅ Да (нет в прошлом) | ✅ Да | ✅ Да | ✅ Да |

После того как пользователь добавил тестовую строку (Аналитик, 45 строк за Июнь-Июль 2026) в 504-595 — 6.6 правильно сработал:
- Результат: `Нет`
- Verdict: Информационное
- Замечание: `Аналитик: 87.1 ч` (Σ forecast в прошлом)

## Antipatterns to avoid

1. ❌ Use `mcp__fst_pmpractice__get_view` namespace — DEPRECATED (Pitfall #22 in mcp-server-probing)
2. ❌ Hardcode `/root/...` paths — use `Path(__file__).resolve().parent.parent`
3. ❌ Hardcode `known = {'504-595': 4595}` — use `find_project_by_code(sid, code)`
4. ❌ Filter on `?ProjectId=N` in URL — use `filters={"ProjectId": N}` (Pitfall #18 in mcp-server-probing)
5. ❌ Use `PointTemplateActivityPhase` for КТ state — use `Point.ActivityPhaseId` (Pitfall #85)
6. ❌ Detect role by `accountid` being null — use `username == specialization` (Pitfall #104)
7. ❌ "Forecast = plan" assumption — they're DIFFERENT fields; respect user's choice

## Step-by-step implementation procedure (added 2026-09-02 from 6.5/6.7)

When implementing a new resource indicator (e.g. 6.5, 6.7), follow these **10 steps** in order:

### Step 1. Получить список исполнителей текущего проекта

```python
current_rows = fetch_with_cache(
    sid, "Project", "ProjectResourcePlan",
    filters={"ProjectId": project_id},
    project_id=project_id, limit=2000,
)
current_users = set((r.get("username") or "").strip() for r in current_rows if r.get("username"))
```

For **6.7** (по всем активностям), additionally получить все строки:
```python
all_rows = fetch_with_cache(
    sid, "Project", "ProjectResourcePlan",
    filters={},  # БЕЗ фильтра по проекту
    project_id=project_id, limit=10000,
)
```

### Step 2. Получить период проекта

Использовать `ProjectParameter` (`projectstart_plandate`, `phasefinish_forecastdate`, `phasefinish_plandate`), fallback на `AllMyPoint.PlanDate/ForecastDate`. См. функцию выше.

### Step 3. Отсечь прошлое (только для 6.5, 6.7)

```python
today = date.today()
effective_start = max(today, start_date)
if effective_start > end_date:
    return IndicatorResult(...verdict="Норма")  # проект завершён
```

**Pitfall #113:** не путать просрочку (смотрим прошлое) с перегрузкой (смотрим будущее). Разные метрики.

### Step 4. Группировка по месяцам

```python
from collections import defaultdict
data = defaultdict(float)  # (user, (year, month)) или (year, month)
for row in rows:
    d = _parse_iso_date(row.get("planning_date"))
    if not d or d < effective_start or d > end_date:
        continue
    data[(d.year, d.month)] += row.get("forecast_hours") or 0
```

### Step 5. Подсчёт рабочих дней (Россия, пн-пт)

```python
from datetime import timedelta

def _count_workdays(start_date, end_date) -> int:
    if not start_date or not end_date or end_date < start_date:
        return 0
    workdays = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:  # Mon=0, Sun=6
            workdays += 1
        current += timedelta(days=1)
    return workdays

# Норма = workdays × 8ч
```

**Без учёта российских праздников** (Pitfall #105).

### Step 6. Пропуск пустых месяцев и расчёт

**Pitfall #114:** если `value <= 0` — пропускаем (месяц без прогноза → не в таблице).

```python
for (y, m) in data:
    value = data[(y, m)]
    if value <= 0:
        continue  # нет загрузки в этом месяце

    month_start = date(y, m, 1)
    month_end = date(y, m + 1, 1) - timedelta(days=1) if m < 12 else date(y, 12, 31)
    period_start = max(effective_start, month_start)
    period_end = min(month_end, end_date)

    workdays = _count_workdays(period_start, period_end)
    norm = workdays * 8
    if norm <= 0:
        continue

    diff = value - norm
    percent = (value / norm) * 100
    if diff <= 0:
        continue  # нет проблемы
```

### Step 7. Severity через helper

```python
from <name>_thresholds import classify_overload_percent, INDICATOR_THRESHOLDS
cfg = INDICATOR_THRESHOLDS["6.X_<name>"]
severity = classify_overload_percent(percent, cfg)
```

Шкала: >150% → critical, >110% → substantial, >100% → informational, ≤100% → normal.

### Step 8. Формат результата

```python
# С запятой перед числом:
f"Да, {N} ч"            # норма
f"Вопросы, {N} ч"       # частично
# Без запятой:
f"Нет"                   # Σ==0
f"Да" / f"Нет"          # без числа
```

**Pitfall #106, #99:** запятая + пробел, не ":" и не просто пробел.

### Step 9. Объединение строк

Если для месяца справедливо несколько условий, объединяем:

```python
parts = []
if condition_a: parts.append("Сообщение A")
if condition_b: parts.append("Сообщение B")
remark = ", ".join(parts)
```

**Pitfall #110:** без кавычек, через запятую + пробел.

### Step 10. Сортировка строк таблицы

```python
severity_order = {"critical": 0, "substantial": 1, "informational": 2}
rows.sort(key=lambda r: (severity_order.get(r["severity"], 9), -r["percent"]))
```

Critical первыми, потом substantial, потом informational. Внутри severity — по проценту убыванию.

## Edge cases — что делать

| Edge case | Поведение | Питфол |
|-----------|-----------|-------|
| Все месяцы с прогнозами в прошлом | workdays=0 → пропускаем, Норма | #113 |
| Исполнитель с ролью в 6.7 | Пропускаем (`username == specialization`) | #108 |
| Нет данных в ProjectResourcePlan | Возвращаем Норма | — |
| Нет дат в ProjectParameter | Fallback на КТ (PlanDate/ForecastDate) | #100 |
| `period_end < period_start` | workdays=0 → пропускаем | — |
| `ProjectTypeName = "Коммерческий "` (с пробелом) | `.strip()` перед сравнением | #109 |

## Чек-лист перед завершением

- [ ] `_parse_iso_date()` обрабатывает ISO-даты с timezone (`+03:00`, `Z`)
- [ ] `effective_start = max(today, start_date)` для 6.5/6.7
- [ ] `workdays` использует `.weekday() < 5` (без праздников)
- [ ] Месяцы с Σ==0 пропускаются (Pitfall #114)
- [ ] Severity из `classify_overload_percent()` (в отдельном `*-thresholds.py`)
- [ ] "Результат" форматируется через запятую + пробел ("Да, N ч")
- [ ] Объединение строк через `", ".join(parts)` без кавычек
- [ ] Тесты: live-probe на 4 проектах (504-595, 503-434, 503-152, 504-314)
- [ ] `tests/run_all_tests.py` → 6/6 PASS