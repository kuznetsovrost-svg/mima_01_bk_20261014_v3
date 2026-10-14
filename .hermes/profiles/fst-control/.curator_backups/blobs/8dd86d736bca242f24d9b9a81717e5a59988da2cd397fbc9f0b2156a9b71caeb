__version__ = "1.0.19"
# ⚠️ Порог 2 млн хранится в scripts/finresult-thresholds.py как
#    FINRESULT_THRESHOLDS["end_finresult_decrease"]["max_value"].
#    Ниже пример использует это имя (импорт опущен — скрипт является
#    самодостаточной выдержкой кода для SKILL.md, а не исполняемым модулем).
#
# ⚠️ Логика: показатель срабатывает ТОЛЬКО на УХУДШЕНИЕ (forecast < plan),
#    не на любое отклонение. Улучшение — это «Нет», даже если |Δ| > 2 млн.

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
    delta = forecast - plan  # отрицательное = ухудшение, положительное = улучшение

    threshold = FINRESULT_THRESHOLDS["end_finresult_decrease"]["max_value"]
    if delta >= -threshold:
        result = "Нет"
        detail = f"Δ = {delta:,.2f} ₽ (уклонение ≤ 2 млн)"
    else:
        result = "Да"
        detail = f"Δ = {delta:,.2f} ₽ (уклонение > 2 млн) — это критическое замечание"
