__version__ = "1.0.19"
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
