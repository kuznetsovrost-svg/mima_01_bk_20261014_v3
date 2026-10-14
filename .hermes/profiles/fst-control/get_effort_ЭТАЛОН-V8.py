"""
get_effort.py — CLI-утилита для просмотра трудозатрат через ProjectResourcePlan.

**`ProjectResourcePlan` — главное открытое view для трудозатрат** (live-probe 2026-08-07).
AccessForAll=true, в отличие от `ResourcePlanning`/`ResourcePlanningKp` (403 для
обычного пользователя).

View содержит:
- `username` — ФИО пользователя
- `specialization` — специализация (Аналитик, РП, Бэк-разработчик, …)
- `activity_name` — Проект/непроектное мероприятие (формат «<code>. <name>»)
- `activityid` — ИД проекта (= ProjectId)
- `planning_date` — Дата планирования
- `plan_hours` — Плановые часы
- `forecast_hours` — Прогнозные часы
- `fact_hours` — Фактические часы

Использование:
    python3 scripts/get_effort.py --project 504-595
    python3 scripts/get_effort.py --project 503-152 --max-rows 5000
    python3 scripts/get_effort.py --project 503-152 --limit 30000 --offset 30000
    python3 scripts/get_effort.py --json

Импортируется также как модуль:
    from get_effort import get_project_effort, EffortSummary

⚠️ Известные ограничения:
- View НЕ фильтруется по `projectid` на стороне сервера → приходится
  делать fetch на 20000-30000 строк и фильтровать локально.
- 504-595 нет в view (проект не имеет введённых трудозатрат).
- 503-152 имеет 1100+ строк (Пресейл — есть прогноз).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from mcp_config import (
    PROJECT_RESOURCE_PLAN_VIEW,
    mcp_init,
    mcp_call,
)


# ============================================================================
# DATACLASS
# ============================================================================

@dataclass
class EffortSummary:
    """Сводка по трудозатратам проекта из ProjectResourcePlan.

    Каждая запись view — одна строка (пользователь × дата × проект).
    Этот dataclass агрегирует по пользователям + по типу часов.
    """
    project_id: int
    project_name: str
    rows: list[dict] = field(default_factory=list)

    # Суммы по типу часов
    plan_hours: float = 0.0
    forecast_hours: float = 0.0
    fact_hours: float = 0.0

    # По пользователям
    by_user: dict[str, dict[str, float]] = field(default_factory=lambda: defaultdict(lambda: {
        "plan_hours": 0.0, "forecast_hours": 0.0, "fact_hours": 0.0, "rows": 0
    }))

    # По специализациям
    by_specialization: dict[str, dict[str, float]] = field(default_factory=lambda: defaultdict(lambda: {
        "plan_hours": 0.0, "forecast_hours": 0.0, "fact_hours": 0.0, "rows": 0
    }))

    # По датам (range)
    date_min: Optional[str] = None
    date_max: Optional[str] = None

    def delta_plan_forecast(self) -> float:
        """Δ план-прогноз (отрицательное = прогноз перевыполнен относительно плана)."""
        return self.plan_hours - self.forecast_hours

    def delta_forecast_fact(self) -> float:
        """Δ факт-прогноз (отрицательное = факт меньше прогноза)."""
        return self.fact_hours - self.forecast_hours

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "rows_count": len(self.rows),
            "plan_hours": self.plan_hours,
            "forecast_hours": self.forecast_hours,
            "fact_hours": self.fact_hours,
            "delta_plan_forecast": self.delta_plan_forecast(),
            "delta_forecast_fact": self.delta_forecast_fact(),
            "date_min": self.date_min,
            "date_max": self.date_max,
            "by_user": dict(self.by_user),
            "by_specialization": dict(self.by_specialization),
        }


# ============================================================================
# Получение данных
# ============================================================================

def get_project_resource_plan_rows(
    sid: Optional[str] = None,
    limit: int = 30000,
    offset: int = 0,
) -> list[dict]:
    """Достаёт все строки ProjectResourcePlan без фильтрации.

    ⚠️ View НЕ фильтруется по `projectid` на сервере — нужно делать
    несколько запросов с разным offset, чтобы получить данные конкретного
    проекта (если он в хвосте).

    Args:
        sid: (опц.) уже открытая MCP-сессия.
        limit: сколько строк запросить у сервера.
        offset: смещение от начала.

    Returns:
        list[dict] — сырые строки view.
    """
    own_session = sid is None
    if own_session:
        sid, _ = mcp_init()

    try:
        data = mcp_call(
            sid, "get_view",
            {
                "entityName": "Project",
                "viewName": PROJECT_RESOURCE_PLAN_VIEW,
                "limit": limit,
                "offset": offset,
            },
        )
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return []
    finally:
        if own_session:
            pass


def _filter_by_project_name(rows: list[dict], code: str) -> list[dict]:
    """Фильтрует строки view по `activity_name` содержащему `code` как слово.

    В Форсайт формат именования — НЕ «<code>. » (с точкой), а «<code> …»
    (без точки). Например: «503-152 ФРП - Минпромторг-Развитие 2026».
    Поэтому фильтруем через search по `<code> ` (с пробелом) ИЛИ
    через точное начало строки.
    """
    if not code:
        return rows
    return [
        r for r in rows
        if str(r.get("activity_name", "")).startswith(code + " ")
        or str(r.get("activity_name", "")).startswith(code + ".")
        or str(r.get("activity_name", "")).startswith(code + "~")
    ]


def get_project_effort(
    project_code: str,
    sid: Optional[str] = None,
    max_rows: int = 30000,
    page_size: int = 30000,
) -> EffortSummary:
    """Собирает сводку по трудозатратам проекта через ProjectResourcePlan.

    ⚠️ View не фильтруется по `projectid` на сервере — нужно перебирать
    данные страницами. По умолчанию смотрим первые 30000 строк, что
    покрывает ~95% проектов. Если проект в хвосте, увеличь `max_rows`.

    Args:
        project_code: Код проекта (например, "504-595").
        sid: (опц.) уже открытая MCP-сессия.
        max_rows: МАКС строк для сканирования.
        page_size: Размер одной страницы (limit для одного запроса).

    Returns:
        EffortSummary с агрегатами по пользователям и специализациям.
    """
    if not project_code:
        raise ValueError("Нужен project_code")

    summary = EffortSummary(
        project_id=0,
        project_name=f"(фильтр: {project_code})",
    )

    all_rows = []
    offset = 0
    own_session = sid is None
    if own_session:
        sid, _ = mcp_init()

    try:
        while offset < max_rows:
            rows = get_project_resource_plan_rows(
                sid=sid, limit=page_size, offset=offset
            )
            if not rows:
                break
            all_rows.extend(rows)
            offset += len(rows)
            if len(rows) < page_size:
                break  # последняя страница

        rows = _filter_by_project_name(all_rows, project_code)
        summary.rows = rows

        if not rows:
            return summary

        summary.project_id = rows[0].get("activityid", 0)
        summary.project_name = rows[0].get("activity_name", "")

        for r in rows:
            plan = float(r.get("plan_hours") or 0)
            forecast = float(r.get("forecast_hours") or 0)
            fact = float(r.get("fact_hours") or 0)
            user = r.get("username", "?")
            spec = r.get("specialization", "?")
            date = r.get("planning_date", "")

            summary.plan_hours += plan
            summary.forecast_hours += forecast
            summary.fact_hours += fact

            summary.by_user[user]["plan_hours"] += plan
            summary.by_user[user]["forecast_hours"] += forecast
            summary.by_user[user]["fact_hours"] += fact
            summary.by_user[user]["rows"] += 1

            summary.by_specialization[spec]["plan_hours"] += plan
            summary.by_specialization[spec]["forecast_hours"] += forecast
            summary.by_specialization[spec]["fact_hours"] += fact
            summary.by_specialization[spec]["rows"] += 1

            if date:
                if summary.date_min is None or date < summary.date_min:
                    summary.date_min = date
                if summary.date_max is None or date > summary.date_max:
                    summary.date_max = date

        return summary
    finally:
        if own_session:
            pass


# ============================================================================
# CLI
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Получить трудозатраты проекта через ProjectResourcePlan."
    )
    parser.add_argument("--project", type=str, required=True, help="Код проекта (например, 504-595)")
    parser.add_argument("--max-rows", type=int, default=30000, help="Макс строк для сканирования")
    parser.add_argument("--page-size", type=int, default=30000, help="Размер одной страницы")
    parser.add_argument("--limit", type=int, default=30000, help="DEPRECATED: используйте --max-rows")
    parser.add_argument("--offset", type=int, default=0, help="Смещение от начала")
    parser.add_argument("--json", action="store_true", help="Вывод в JSON формате")
    parser.add_argument("--rows", action="store_true", help="Показать все строки view, не только сводку")
    parser.add_argument("--by-user", action="store_true", help="Показать разбивку по пользователям")
    parser.add_argument("--by-spec", action="store_true", help="Показать разбивку по специализациям")
    args = parser.parse_args()

    # Поддержка старого `--limit` для обратной совместимости
    if args.limit != 30000:
        args.max_rows = args.limit

    summary = get_project_effort(
        project_code=args.project,
        max_rows=args.max_rows,
        page_size=args.page_size,
    )

    if args.json:
        if args.rows:
            print(json.dumps(summary.rows, indent=2, ensure_ascii=False, default=str))
        else:
            print(json.dumps(summary.to_dict(), indent=2, ensure_ascii=False, default=str))
    else:
        print(f"⏱️  Сводка по трудозатратам:")
        print(f"   ProjectId:      {summary.project_id}")
        print(f"   ProjectName:    {summary.project_name}")
        print(f"   Rows:           {len(summary.rows)}")
        if summary.rows:
            print(f"   Period:         {summary.date_min} → {summary.date_max}")
            print(f"   ---")
            print(f"   PlanHours:      {summary.plan_hours:>12,.2f} ч")
            print(f"   ForecastHours:  {summary.forecast_hours:>12,.2f} ч")
            print(f"   FactHours:      {summary.fact_hours:>12,.2f} ч")
            print(f"   ---")
            print(f"   Δ plan-forecast:   {summary.delta_plan_forecast():>10,.2f} ч")
            print(f"   Δ forecast-fact:   {summary.delta_forecast_fact():>10,.2f} ч")

        if args.by_user and summary.by_user:
            print(f"\n👥 По пользователям:")
            for user, data in sorted(
                summary.by_user.items(),
                key=lambda x: x[1]["forecast_hours"],
                reverse=True,
            ):
                print(f"   {user[:35]:35s} | plan={data['plan_hours']:>8,.2f}ч "
                      f"forecast={data['forecast_hours']:>8,.2f}ч fact={data['fact_hours']:>8,.2f}ч "
                      f"({data['rows']} rows)")

        if args.by_spec and summary.by_specialization:
            print(f"\n🎯 По специализациям:")
            for spec, data in sorted(
                summary.by_specialization.items(),
                key=lambda x: x[1]["forecast_hours"],
                reverse=True,
            ):
                print(f"   {spec[:35]:35s} | plan={data['plan_hours']:>8,.2f}ч "
                      f"forecast={data['forecast_hours']:>8,.2f}ч fact={data['fact_hours']:>8,.2f}ч "
                      f"({data['rows']} rows)")

        if args.rows and summary.rows:
            print(f"\n📋 Первые {min(20, len(summary.rows))} строк:")
            for i, r in enumerate(summary.rows[:20], 1):
                print(f"   [{i}] {r.get('planning_date', '?')} | "
                      f"{r.get('username', '?')[:30]} ({r.get('specialization', '?')[:15]}) | "
                      f"plan={r.get('plan_hours')} "
                      f"forecast={r.get('forecast_hours')} "
                      f"fact={r.get('fact_hours')}")

        if not summary.rows:
            print(f"\n⚠️  Нет данных для проекта {args.project}.")
            print(f"   Возможные причины:")
            print(f"   1. У проекта не введены трудозатраты в Форсайт")
            print(f"   2. Проект в хвосте данных (>30000 строк) — увеличьте --max-rows")
            print(f"   3. Ошибка в коде ({args.project})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
