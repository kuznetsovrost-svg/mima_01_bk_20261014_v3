# Recipe: как получить трудозатраты для раздела 4 показатель 4

> **ОБНОВЛЕНО 2026-08-07:** найден рабочий путь через `?ProjectId=<id>` (pitfall #50).
> `ProjectResourcePlan` теперь фильтруется на стороне сервера. Никаких scan-offset
> больше не нужно. Решает проблемы 1.2 и 16.2 из «Вопросы по MCP 2026_08_07.md».

## TL;DR — проблема 1.2 РЕШЕНА (server-side фильтр)

Live-probe 2026-08-07 нашёл два уровня решений:

1. **`ProjectResourcePlan`** (open view, `AccessForAll=true`) — заменяет `ResourcePlanning*` (403).
2. **`?ProjectId=<id>` в имени view** (pitfall #50) — **server-side фильтр** на уровне MCP. Возвращает ТОЛЬКО нужный проект. Для 504-595: 149 строк сразу, без scan-offset.

```bash
# CLI — рабочий пример
python3 scripts/get_effort.py --project 504-595 --project-id 4595
python3 scripts/get_effort.py --project 503-152 --project-id 3152 --by-user --by-spec
```

```python
# Программно — server-side фильтр
from mcp_config import PROJECT_RESOURCE_PLAN_VIEW_FOR, mcp_init, mcp_call

sid, _ = mcp_init()
data = mcp_call(
    sid, "get_view",
    {
        "entityName": "Project",
        "viewName": PROJECT_RESOURCE_PLAN_VIEW_FOR(4595),  # = "ProjectResourcePlan?ProjectId=4595"
        "limit": 500,
    },
)
```

## Было (DEPRECATED)

`ResourcePlanning` / `ResourcePlanningKp` views → 403 Forbidden для обычных пользователей.
Старый подход с scan-offset до 600000 — медленный (6 HTTP-запросов) и ненадёжный.

## Стало (live-probe 2026-08-07) — server-side фильтр

`ProjectResourcePlan` через `?ProjectId=<id>` — **ОТКРЫТЫЙ** view с **server-side** фильтром:

| Поле | Тип | Описание |
|------|-----|----------|
| `activityid` | int | ProjectId (= тот же id что и в `Project`) |
| `activity_name` | text | «<code> <name>», формат «504-595 Космодром Жуковский…» |
| `username` | text | ФИО пользователя |
| `specialization` | text | Специализация (Архитектор, Аналитик, РП, …) |
| `planning_date` | date | Дата планирования |
| `plan_hours` | decimal | Плановые часы |
| `forecast_hours` | decimal | Прогнозные часы |
| `fact_hours` | decimal | Фактические часы |

⚠️ **Известные ограничения:**

1. Сервер может не поддерживать `?ProjectId=<id>` для **всех** view (например, для тех, где `ProjectId` не имеет смысла). Подтверждено для `ProjectResourcePlan` и `ProjectBudgetCompleteBusiness` (2026-08-07).
2. **504-595** имеет 149 строк в view (Носов А.Н. — 71 row, Кузнецов Р.В. — 78 rows), `plan/forecast/fact_hours` заполнены.
3. **503-152 (Пресейл)** имеет 1100+ строк с реальными данными (`forecast=255.46ч`, `fact=402.64ч`).

## Сценарии и что они означают

| Сценарий | Условие | result для отчёта |
|----------|---------|-------------------|
| **1. Записей нет вообще** | `rows=[]` | **«Неопределено»** — трудозатраты не введены в Форсайт |
| **2. Записи есть, но все часы = 0/None** | `has_any_hour=False` | **«Неопределено»** — записи-шаблоны, надо заполнить |
| **3. Только прогноз** | `forecast > 0`, `plan=0`, `fact=0` | **«Нет»** — план и факт не заведены |
| **4. Есть план, факт не заведён** | `plan_dates` OK, `fact_dates=[]` | **«Нет»** — факт не заведён |
| **5. План + факт, разрыв ≤ 10 дней** | `0 ≤ gap ≤ EFFORT_GAP_THRESHOLD_DAYS` | **«Да»** — данные актуальны |
| **6. План + факт, разрыв > 10 дней** | `gap > EFFORT_GAP_THRESHOLD_DAYS` | **«Нет»** — данные устарели |

## Логика `_evaluate_effort` (из `Effort-check.py`)

```python
def _evaluate_effort(rows, today=None, gap_threshold_days=10):
    """Возвращает (result, detail, has_data) для раздела 4 показатель 4."""
    if today is None:
        today = date.today()

    # 1. Записей нет
    if not rows:
        return ("Неопределено",
                "Нет данных в ProjectResourcePlan — трудозатраты не введены в Форсайт",
                False)

    # 2. Записи есть, но ВСЕ часы = 0 или None
    has_any_hour = any(
        (r.get("plan_hours") or 0) > 0
        or (r.get("forecast_hours") or 0) > 0
        or (r.get("fact_hours") or 0) > 0
        for r in rows
    )
    if not has_any_hour:
        users = {r.get("username") for r in rows if r.get("username")}
        specs = {r.get("specialization") for r in rows if r.get("specialization")}
        return ("Неопределено",
                f"Записи шаблонов без часов: {len(rows)} строк, "
                f"{len(users)} пользователей, "
                f"{len(specs)} специализаций. "
                f"Все plan/forecast/fact = 0 или null. "
                f"Заполните данные в Форсайт для расчёта разрыва.",
                True)

    # 3. Только прогноз
    plan_dates, fact_dates = [], []
    forecast_total = 0.0
    for r in rows:
        date_str = r.get("planning_date")
        if not date_str:
            continue
        plan = r.get("plan_hours") or 0
        forecast = r.get("forecast_hours") or 0
        fact = r.get("fact_hours") or 0
        forecast_total += forecast
        if plan > 0: plan_dates.append(date_str)
        if fact > 0: fact_dates.append(date_str)

    if not plan_dates and not fact_dates and forecast_total > 0:
        return ("Нет", f"Только прогноз ({forecast_total:.2f}ч), план и факт не заведены", True)

    # 4-5. Считаем разрыв
    last_plan = max(plan_dates) if plan_dates else None
    last_fact = max(fact_dates) if fact_dates else None

    if not last_plan:
        return ("Нет", "Прогноз отсутствует", True)
    if not last_fact:
        return ("Нет", f"Прогноз на {last_plan}, факт не заведён", True)

    plan_date = date.fromisoformat(last_plan[:10])
    fact_date = date.fromisoformat(last_fact[:10])
    gap = (fact_date - plan_date).days

    if 0 <= gap <= gap_threshold_days:
        return ("Да", f"Прогноз {last_plan}, факт {last_fact} (разрыв {gap}д)", True)
    if gap < 0 and (today - plan_date).days <= gap_threshold_days:
        return ("Да", f"Факт {last_fact} раньше плана {last_plan}, но не устарел", True)
    return ("Нет", f"Прогноз {last_plan}, факт {last_fact} (разрыв {gap}д)", True)
```

## Интеграция в run-скрипт

```python
import sys
import importlib.util
from pathlib import Path
from datetime import date

SKILL_DIR = Path("/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health")
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from get_effort import get_project_effort

# Effort-check — файл с дефисом, через importlib
spec = importlib.util.spec_from_file_location("Effort-check", str(SKILL_DIR / "scripts" / "Effort-check.py"))
effort_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(effort_check)

# Получаем данные и оцениваем (server-side фильтр через project_id)
summary = get_project_effort(
    project_code="504-595",
    project_id=4595,  # ← сервер фильтрует на стороне MCP
)
result, detail, has_data = effort_check._evaluate_effort(
    summary.rows, today=date.today()
)

md = f"""
## 4. Полнота заполнения проекта

| 4 | Актуальность трудозатрат | {result} — {detail} |
"""
```

## Live-пример (504-595, 2026-08-07)

С `?ProjectId=4595`:

```text
=== get_effort.py --project 504-595 --project-id 4595 ===
   ProjectId:      4595
   ProjectName:    504-595 Космодром Жуковский внедрение ИСУП
   Rows:           149
   Period:         2026-06-05 → 2026-08-20
   PlanHours:            143.90 ч
   ForecastHours:        610.40 ч
   FactHours:            550.00 ч
   Δ plan-forecast:      -466.50 ч
   Δ forecast-fact:       -60.40 ч

👥 По пользователям:
   Носов Антон Николаевич         | plan=    0.00ч forecast=  321.60ч fact=  324.00ч (71 rows)
   Кузнецов Ростислав Владимирович | plan=  143.90ч forecast=  288.80ч fact=  226.00ч (78 rows)
```

`_evaluate_effort` → result="Да", detail="Прогноз 2026-07-31, факт 2026-07-31 (разрыв 0д)".

## Резервный fallback (если `?ProjectId=<id>` не работает)

Клиентский фильтр через `activity_name.startswith(code + " ")` (pitfall #49) — **fallback**, не основной путь. Используй только если `?ProjectId=<id>` не возвращает данные (например, для какого-то view сервер не реализовал этот фильтр).

```python
# Fallback (DEPRECATED, scan-offset не нужен если работает ?ProjectId=...)
rows = [
    r for r in all_rows
    if str(r.get("activity_name", "")).startswith(code + " ")
    or str(r.get("activity_name", "")).startswith(code + ".")
    or str(r.get("activity_name", "")).startswith(code + "~")
]
```

## Что осталось

- `ProjectHealthWorkload` — агрегат по профилю (Базовый, Базовый2, …), не по проекту. Полезен как **дополнительный fallback** для отчёта — показывает суммы по всем проектам профиля. Но **не помогает** разделить данные по конкретному проекту.
- `ResourcePlanning` / `ResourcePlanningKp` — **403** для обычных пользователей. Нужны admin-права. Не у всех.

`/tmp/run_<code>_section_4.py` — пример скрипта-сборщика для раздела 4.

## Связанные

- `references/forsight-mcp-quirks.md` pitfall #50 — `?ProjectId=<id>` server-side фильтр
- `references/forsight-mcp-quirks.md` pitfall #48 — `ProjectResourcePlan` подробности
- `references/forsight-mcp-quirks.md` pitfall #49 — формат `activity_name` (БЕЗ точки)
- `SKILL.md` pitfall #6 — обновлён 2026-08-07