__version__ = "1.0.19"
# ⚠️ Порог 1 млн хранится в scripts/finresult-thresholds.py как
#    FINRESULT_THRESHOLDS["current_cost_deviation"]["max_value"].
#    Ниже пример использует это имя (импорт опущен — скрипт является
#    самодостаточной выдержкой кода для SKILL.md, а не исполняемым модулем).

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

if delta > FINRESULT_THRESHOLDS["current_cost_deviation"]["max_value"]:
    result = "Да"
    detail = f"Δ = {delta:,.2f} ₽ (> 1 млн) — это критическое замечание"
else:
    result = "Нет"
    detail = f"Δ = {delta:,.2f} ₽ (≤ 1 млн)"
