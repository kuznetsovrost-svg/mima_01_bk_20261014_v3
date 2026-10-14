__version__ = "1.0.19"
from datetime import date, datetime

# �️ Пороги 1 / 2 / 10 дней хранятся в scripts/point-overdue-thresholds.py
#    как OVERDUE_THRESHOLDS. Ниже пример использует это имя (импорт опущен —
#    скрипт является самодостаточной выдержкой кода для SKILL.md, а не
#    исполняемым модулем).

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

# 3. Фильтр просроченных (ForecastDate < today, без факта)
overdue = []
for p in project_points:
    forecast = parse_date(p.get("ForecastDate"))
    fact = parse_date(p.get("FactDate"))
    if forecast and forecast < today and not fact:
        diff = (today - forecast).days
        if diff >= 1:  # только реально просроченные (не сегодня и не в будущем)
            overdue.append({**p, "diff_days": diff})

# 4. Сортировка по убыванию просрочки
overdue.sort(key=lambda x: -x["diff_days"])

# 5. Классификация по порогам из OVERDUE_THRESHOLDS
def classify(diff):
    if diff >= OVERDUE_THRESHOLDS["critical"]["min_days"]:        # ≥ 10
        return "Критическое"
    if diff >= OVERDUE_THRESHOLDS["substantial"]["min_days"]:     # ≥ 2
        return "Существенное"
    return "Информационное"  # diff ∈ [1, 1]

# 6. Вывод
for o in overdue:
    status = classify(o["diff_days"])
    print(f"{o['Code']} | {o['Name']} | план={parse_date(o['PlanDate'])} | "
          f"прогноз={parse_date(o['ForecastDate'])} | "
          f"+{o['diff_days']}д | {status} | {o['Responsible']}")
