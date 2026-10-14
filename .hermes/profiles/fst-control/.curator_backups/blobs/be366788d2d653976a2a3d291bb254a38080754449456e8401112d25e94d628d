__version__ = "1.0.19"
"""
Effort-check.py — проверка актуальности трудозатрат (Раздел 4 показатель 4).

🔥 ОБНОВЛЕНО 2026-08-07: вместо закрытых 403-views `ResourcePlanning`/
`ResourcePlanningKp` теперь используется **открытый** `ProjectResourcePlan`
(AccessForAll=true). Решает проблему 1.2 из «Вопросы по MCP 2026_08_07.md».

Это **справочная выдержка** для SKILL.md — агент читает её при написании
реальных скриптов. Сам файл не импортируется (имя с дефисом → pitfall #5).

⚠️ IMPORTANT: Это НЕ исполняемый модуль. Можно либо:
  (1) Скопировать логику в /tmp/run_section_4.py — реальный скрипт для проекта
  (2) Использовать scripts/get_effort.py — готовый CLI/mодуль

═══════════════════════════════════════════════════════════════════════════════
АЛГОРИТМ (соответствует Размерелки разделу 4 показатель 4)
═══════════════════════════════════════════════════════════════════════════════

Три возвращаемых значения:
    (result, detail, has_data)
    result:    «Да» | «Нет» | «Неопределено»
    detail:    объяснение для отчёта
    has_data:  bool — есть ли ВООБЩЕ записи в view (т.е. трудо­затраты введены)

Сценарии (отсортированы по приоритету — первый подходящий выигрывает):

1. Записей в view нет вообще (проект не в ProjectResourcePlan)
   → «Неопределено», «Нет данных в ProjectResourcePlan — трудозатраты
     не введены в Форсайт», has_data=False

2. Записи есть, но ВСЕ часы = None или 0
   → «Неопределено», «Записи шаблонов без часов:
     {N} строк, {users} пользователей, но plan/forecast/fact = 0/None»,
     has_data=True (записи есть, но пустые)

3. Записи есть, но только прогноз (forecast > 0, plan=0, fact=0)
   → «Нет», «Только прогноз ({forecast_hours}ч), факт не заведён»,
     has_data=True

4. Записи есть, есть план и факт, разрыв ≤ 10 дней
   → «Да», «Прогноз {last_plan}, факт {last_fact} (разрыв {gap}д)», has_data=True

5. Записи есть, разрыв > 10 дней
   → «Нет», «Прогноз {last_plan}, факт {last_fact} (разрыв {gap}д)», has_data=True

6. Прочие случаи (план есть, факт отсутствует)
   → «Нет», «Прогноз на {last_plan}, факт не заведён», has_data=True

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР (504-595, июнь-август 2026, live-probe 2026-08-07)
═══════════════════════════════════════════════════════════════════════════════

504-595 в view: 10 строк (Носов А.Н. — 7 раз, Кузнецов Р.В. — 3 раза)
Но ВСЕ plan_hours=None, forecast_hours=0.0, fact_hours=None.

→ Сценарий 2.
→ result = «Неопределено»
→ detail = «Записи шаблонов без часов: 10 строк, 2 пользователя
  (Носов А.Н. — Архитектор, Кузнецов Р.В. — Руководитель проекта),
  но plan/forecast/fact = 0/None»
→ has_data = True

Это НЕ «Нет» — записи введены, просто пустые.
Это НЕ «Да» — данные не готовы.
Это «Неопределено» — для принятия решения по разделу 4 нужно
заполнить записи.

═══════════════════════════════════════════════════════════════════════════════
"""

from datetime import date

# ⚠️ Значение 10 (дней) — порог. По умолчанию 10, см.
# scripts/effort-gap-threshold.py (EFFORT_GAP_THRESHOLD_DAYS).
EFFORT_GAP_THRESHOLD_DAYS = 10


def _patch(item: dict, *keys, default=None):
    """Безопасное извлечение вложенных ключей из dict.

    Пример: _patch(row, 'planning_date', 'plan_hours') → row['planning_date']['plan_hours']
    """
    for key in keys:
        if not isinstance(item, dict):
            return default
        item = item.get(key)
    return item if item is not None else default


def _filter_by_project(rows: list[dict], project_code: str) -> list[dict]:
    """Фильтрует строки view по `activity_name` содержащему `code` как слово.

    В Форсайт формат именования — «<code> …» (без точки) или «<code>. …».
    """
    if not project_code:
        return rows
    return [
        r for r in rows
        if str(r.get("activity_name", "")).startswith(project_code + " ")
        or str(r.get("activity_name", "")).startswith(project_code + ".")
        or str(r.get("activity_name", "")).startswith(project_code + "~")
    ]


def is_effort_data_current(
    project_code: str,
    *,
    today: date = None,
    gap_threshold_days: int = EFFORT_GAP_THRESHOLD_DAYS,
) -> tuple[str, str, bool]:
    """Проверяет актуальность трудозатрат через ProjectResourcePlan.

    Args:
        project_code: Код проекта (например, "504-595").
        today: Дата для сравнения (по умолчанию date.today()).
        gap_threshold_days: Порог разрыва план-факт в днях.

    Returns:
        (result, detail, has_data):
            - result: «Да» / «Нет» / «Неопределено»
            - detail: подробное объяснение для отчёта
            - has_data: True если записи в view есть (даже пустые)

    ⚠️ Реальный вызов должен использовать скрипт scripts/get_effort.py
    или повторять нумерацию строк через mcp_config.PROJECT_RESOURCE_PLAN_VIEW.

    Пример бы impl:
        from get_effort import get_project_effort
        summary = get_project_effort(project_code="504-595")
        result, detail, has_data = is_effort_data_current(
            "504-595", today=date.today()
        )
    """
    if today is None:
        today = date.today()

    # ──────────────────────────────────────────────────────────────────
    # 0. Получить данные (вызывающий код использует get_effort.py)
    # ──────────────────────────────────────────────────────────────────
    # В реальном run-скрипте:
    #   from get_effort import get_project_effort
    #   summary = get_project_effort(project_code=project_code)
    #   rows = summary.rows
    #
    # Здесь — справочная сигнатура с тем, что агент читает rows
    # из переменной. Если «всё None» — выставляем return прямо.

    # Для этого reference-скрипта rows не передаётся — показываем
    # интерфейс через list[dict]
    # В реале: импортируй get_effort и передавай rows.

    # Сигнатура расширена: реальная функция ниже (см. live runs)
    raise NotImplementedError(
        "Это справочная выдержка. В реальном коде: "
        "from scripts.get_effort import get_project_effort; "
        "summary = get_project_effort(project_code); "
        "rows = summary.rows; "
        "→ затем вызвать _evaluate_effort(rows, today, gap_threshold_days)."
    )


def _evaluate_effort(
    rows: list[dict],
    today: date = None,
    gap_threshold_days: int = EFFORT_GAP_THRESHOLD_DAYS,
) -> tuple[str, str, bool]:
    """Реальная логика оценки. Принимает rows из ProjectResourcePlan.

    Args:
        rows: список строк view (уже отфильтрованных по project_code).
        today: дата для сравнения.
        gap_threshold_days: порог разрыва план-факт.

    Returns:
        (result, detail, has_data)
    """
    if today is None:
        today = date.today()

    # ── Сценарий 1: записей вообще нет ──────────────────────────────
    if not rows:
        return (
            "Неопределено",
            "Нет данных в ProjectResourcePlan — трудозатраты "
            "не введены в Форсайт для этого проекта",
            False,
        )

    # ── Сценарий 2: записи есть, но ВСЕ часы = None или 0 ───────────
    #
    # В 504-595 в июне-августе 2026: 10 строк, все plan/forecast/fact = 0/None.
    # Такие «пустые шаблоны» не означают «нет трудозатрат» — они означают
    # «строки созданы, но не заполнены». Возвращаем «Неопределено» с
    # описанием, чтобы пользователь увидел и пошёл до­полнять.
    has_any_hour = any(
        (r.get("plan_hours") or 0) > 0
        or (r.get("forecast_hours") or 0) > 0
        or (r.get("fact_hours") or 0) > 0
        for r in rows
    )
    if not has_any_hour:
        users = set()
        specs = set()
        for r in rows:
            u = r.get("username")
            s = r.get("specialization")
            if u: users.add(u)
            if s: specs.add(s)
        detail = (
            f"Записи шаблонов без часов: {len(rows)} строк, "
            f"{len(users)} пользователей, "
            f"{len(specs)} специализаций. "
            f"Все plan/forecast/fact = 0 или null. "
            f"Заполните данные в Форсайт для расчёта разрыва."
        )
        return ("Неопределено", detail, True)

    # ── Разбираем даты ─────────────────────────────────────────────────
    plan_dates = []
    fact_dates = []
    forecast_hours_total = 0.0
    for r in rows:
        date_str = r.get("planning_date")
        if not date_str:
            continue
        plan = r.get("plan_hours") or 0
        forecast = r.get("forecast_hours") or 0
        fact = r.get("fact_hours") or 0
        forecast_hours_total += forecast
        if plan > 0:
            plan_dates.append(date_str)
        if fact > 0:
            fact_dates.append(date_str)

    # ── Сценарий 3: только прогноз, без плана и факта ─────────────────
    if not plan_dates and not fact_dates and forecast_hours_total > 0:
        return (
            "Нет",
            f"Только прогноз ({forecast_hours_total:.2f}ч), "
            f"план и факт не заведены",
            True,
        )

    # ── Сценарий 4-5: есть план и/или факт, считаем разрыв ───────────
    last_plan = max(plan_dates) if plan_dates else None
    last_fact = max(fact_dates) if fact_dates else None

    if not last_plan:
        return ("Нет", "Прогноз отсутствует", True)

    if not last_fact:
        return (
            "Нет",
            f"Прогноз на {last_plan}, факт не заведён",
            True,
        )

    # Оба есть — считаем разрыв
    plan_date = date.fromisoformat(last_plan[:10])
    fact_date = date.fromisoformat(last_fact[:10])
    gap = (fact_date - plan_date).days

    if 0 <= gap <= gap_threshold_days:
        return (
            "Да",
            f"Прогноз {last_plan}, факт {last_fact} (разрыв {gap}д)",
            True,
        )
    if gap < 0 and (today - plan_date).days <= gap_threshold_days:
        return (
            "Да",
            f"Факт {last_fact} раньше плана {last_plan}, но не устарел",
            True,
        )

    return (
        "Нет",
        f"Прогноз {last_plan}, факт {last_fact} (разрыв {gap}д)",
        True,
    )


# ════════════════════════════════════════════════════════════════════════
# ИНТЕГРАЦИЯ В РЕАЛЬНЫЙ RUN-СКРИПТ
# ════════════════════════════════════════════════════════════════════════
#
# Пример для /tmp/run_<code>_section_4.py (раздел 4 показатель 4):
#
#   import sys
#   from pathlib import Path
#   from datetime import date
#
#   SKILL_DIR = Path("/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health")
#   sys.path.insert(0, str(SKILL_DIR / "scripts"))
#
#   from get_effort import get_project_effort
#   from Effort-check import _evaluate_effort
#
#   summary = get_project_effort(project_code="504-595")
#   result, detail, has_data = _evaluate_effort(
#       summary.rows, today=date.today()
#   )
#
#   md = f"""
# ## 4. Полнота заполнения проекта
#
# **Статус раздела:** (определяется на уровне раздела)
# **Цвет заголовка:** (определяется на уровне раздела)
# **Итог по замечаниям:** (определяется на уровне раздела)
#
# | 4 | Актуальность данных проекта по трудозатратам | {result} — {detail} |
# """
#
#   Path("/tmp/section_4_result.md").write_text(md, encoding="utf-8")
