"""
get_project_budget.py — CLI-утилита для просмотра ProjectBudgetCompleteBusiness.

`ProjectBudgetCompleteBusiness` — открытый view на сущности `Project`, который
содержит **полную финансовую картину** по проекту:
бюджет, акты (план/факт/прогноз), оплаты (план/факт/прогноз),
на одну КТ, на одну дату, с привязкой к контракту и платежу.

Использование:
    python3 scripts/get_project_budget.py --project 504-595
    python3 scripts/get_project_budget.py --activity-id 4595
    python3 scripts/get_project_budget.py --limit 100
    python3 scripts/get_project_budget.py --json

Импортируется также как модуль:
    from get_project_budget import get_project_budget, ProjectBudgetSummary

КОНТЕКСТ (live-probe 2026-08-07):
- View ОТКРЫТ для обычного пользователя (AccessForAll=false, но view
  возвращает данные для Perm-enabled user без 403).
- API: `get_view(Project, ProjectBudgetCompleteBusiness, limit=...)`.
- 31 столбец, ключ = `ProjectId` (= `ActivityId` в данных).
- Решает проблемы 1.3, 1.4, 1.5, 1.6, 1.7 из "Вопросы по MCP 2026_08_07.md".
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Импорт из mcp_config (централизованные URL, токен, headers, парсер SSE)
from mcp_config import (
    PROJECT_BUDGET_VIEW,
    mcp_init,
    mcp_call,
)


# ============================================================================
# DATACLASS для удобного представления
# ============================================================================

@dataclass
class ProjectBudgetSummary:
    """Сводка по проекту из ProjectBudgetCompleteBusiness.

    Каждая запись view — одна строка бюджета (для КТ, контракта, даты).
    Этот dataclass агрегирует все записи.
    """
    project_id: int
    project_name: str
    rows: list[dict] = field(default_factory=list)

    # Суммы по типам (агрегаты)
    budgetsum: float = 0.0          # Бюджет базовый
    actplansum: float = 0.0        # Акт план
    actforecastsum: float = 0.0    # Акт прогноз
    actfactsum: float = 0.0        # Акт факт
    payplansum: float = 0.0        # Оплата план
    payforecastsum: float = 0.0    # Оплата прогноз
    payfactsum: float = 0.0        # Оплата факт

    # Контракты
    contract_ids: set[int] = field(default_factory=set)
    contract_names: set[str] = field(default_factory=set)

    # Кол-во строк по бюджетному типу
    rows_by_type: dict[str, int] = field(default_factory=dict)

    def delta_pay(self) -> float:
        """Δ оплат = факт - план (отрицательное = недоплата)."""
        return self.payfactsum - self.payplansum

    def delta_act(self) -> float:
        """Δ актов = факт - план."""
        return self.actfactsum - self.actplansum

    def balance(self) -> float:
        """Σ актов - Σ оплат (для проверки графика платежей)."""
        return self.actfactsum - self.payfactsum

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "rows_count": len(self.rows),
            "budgetsum": self.budgetsum,
            "actplansum": self.actplansum,
            "actforecastsum": self.actforecastsum,
            "actfactsum": self.actfactsum,
            "payplansum": self.payplansum,
            "payforecastsum": self.payforecastsum,
            "payfactsum": self.payfactsum,
            "delta_act": self.delta_act(),
            "delta_pay": self.delta_pay(),
            "balance": self.balance(),
            "contract_ids": sorted(self.contract_ids),
            "contract_count": len(self.contract_ids),
            "rows_by_type": self.rows_by_type,
        }


# ============================================================================
# Получение данных
# ============================================================================

def get_project_budget_rows(sid: Optional[str] = None, limit: int = 2000) -> list[dict]:
    """Достаёт все строки ProjectBudgetCompleteBusiness без фильтрации.

    Возвращает список строк view. По умолчанию limit=2000 — этого хватает
    на крупный проект с большим кол-вом КТ и платежей.

    Args:
        sid: (опц.) уже открытая MCP-сессия.
        limit: сколько строк запросить у сервера.

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
                "viewName": PROJECT_BUDGET_VIEW,
                "limit": limit,
            },
        )
        if isinstance(data, dict) and "data" in data:
            return data["data"]
        return []
    finally:
        if own_session:
            pass


def _filter_by_project_name(rows: list[dict], code: str) -> list[dict]:
    """Фильтрует строки view по началу `activityname` (формат «<code>. …»)."""
    if not code:
        return rows
    prefix = f"{code}."
    return [r for r in rows if str(r.get("activityname", "")).startswith(prefix)]


def _filter_by_activity_id(rows: list[dict], activity_id: int) -> list[dict]:
    """Фильтрует строки view по `ActivityId` (= ProjectId)."""
    return [r for r in rows if r.get("ActivityId") == activity_id]


def get_project_budget(
    project_code: Optional[str] = None,
    activity_id: Optional[int] = None,
    sid: Optional[str] = None,
    limit: int = 2000,
) -> ProjectBudgetSummary:
    """Собирает финансовую сводку по проекту.

    Args:
        project_code: Код проекта (например, "504-595"). Фильтр по `activityname`.
        activity_id: ProjectId (=ActivityId). Прямая фильтрация.
        sid: (опц.) уже открытая MCP-сессия.
        limit: сколько строк запросить у сервера.

    Returns:
        ProjectBudgetSummary с агрегатами по проекту.

    Raises:
        ValueError: если не указан ни project_code, ни activity_id.
    """
    if not project_code and not activity_id:
        raise ValueError("Нужен хотя бы один из project_code / activity_id")

    rows = get_project_budget_rows(sid=sid, limit=limit)

    if activity_id:
        rows = _filter_by_activity_id(rows, activity_id)
    elif project_code:
        rows = _filter_by_project_name(rows, project_code)

    if not rows:
        return ProjectBudgetSummary(
            project_id=activity_id or 0,
            project_name="(пусто)",
        )

    summary = ProjectBudgetSummary(
        project_id=rows[0].get("ActivityId", 0),
        project_name=rows[0].get("activityname", ""),
        rows=rows,
    )

    for r in rows:
        summary.budgetsum += float(r.get("budgetsum") or 0)
        summary.actplansum += float(r.get("actplansum") or 0)
        summary.actforecastsum += float(r.get("actforecastsum") or 0)
        summary.actfactsum += float(r.get("actfactsum") or 0)
        summary.payplansum += float(r.get("payplansum") or 0)
        summary.payforecastsum += float(r.get("payforecastsum") or 0)
        summary.payfactsum += float(r.get("payfactsum") or 0)

        cid = r.get("contractid")
        if cid:
            summary.contract_ids.add(int(cid))
        cname = r.get("contractname")
        if cname:
            summary.contract_names.add(str(cname))

        btype = r.get("budgettype", "(unknown)")
        summary.rows_by_type[btype] = summary.rows_by_type.get(btype, 0) + 1

    return summary


# ============================================================================
# CLI
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Получить финансовую сводку проекта через ProjectBudgetCompleteBusiness."
    )
    parser.add_argument("--project", type=str, help="Код проекта (например, 504-595)")
    parser.add_argument("--activity-id", type=int, help="ProjectId (=ActivityId)")
    parser.add_argument("--limit", type=int, default=2000, help="Сколько строк запросить у сервера")
    parser.add_argument("--json", action="store_true", help="Вывод в JSON формате")
    parser.add_argument("--rows", action="store_true", help="Показать все строки view, не только сводку")
    args = parser.parse_args()

    if not args.project and not args.activity_id:
        parser.print_help()
        return 1

    summary = get_project_budget(
        project_code=args.project,
        activity_id=args.activity_id,
        limit=args.limit,
    )

    if args.json:
        if args.rows:
            print(json.dumps(summary.rows, indent=2, ensure_ascii=False, default=str))
        else:
            print(json.dumps(summary.to_dict(), indent=2, ensure_ascii=False, default=str))
    else:
        print(f"📊 Сводка по проекту:")
        print(f"   ProjectId:     {summary.project_id}")
        print(f"   ProjectName:   {summary.project_name}")
        print(f"   Rows:          {len(summary.rows)}")
        print(f"   Contracts:     {len(summary.contract_ids)}")
        print(f"   ---")
        print(f"   BudgetSum:     {summary.budgetsum:>15,.2f} ₽")
        print(f"   ActPlan:       {summary.actplansum:>15,.2f} ₽")
        print(f"   ActForecast:   {summary.actforecastsum:>15,.2f} ₽")
        print(f"   ActFact:       {summary.actfactsum:>15,.2f} ₽")
        print(f"   PayPlan:       {summary.payplansum:>15,.2f} ₽")
        print(f"   PayForecast:   {summary.payforecastsum:>15,.2f} ₽")
        print(f"   PayFact:       {summary.payfactsum:>15,.2f} ₽")
        print(f"   ---")
        print(f"   Δ Act:         {summary.delta_act():>15,.2f} ₽")
        print(f"   Δ Pay:         {summary.delta_pay():>15,.2f} ₽")
        print(f"   Balance:       {summary.balance():>15,.2f} ₽")
        print(f"   ---")
        print(f"   By budgettype:")
        for btype, cnt in summary.rows_by_type.items():
            print(f"     {btype}: {cnt}")

        if args.rows:
            print(f"\n📋 Все строки:")
            for i, r in enumerate(summary.rows, 1):
                print(f"   [{i}] {r.get('date', '?')} | {r.get('budgettype', '?')} | "
                      f"КТ={r.get('pointname', '?')[:40]} | "
                      f"budget={r.get('budgetsum', 0)} | "
                      f"actFact={r.get('actfactsum', 0)} | "
                      f"payFact={r.get('payfactsum', 0)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
