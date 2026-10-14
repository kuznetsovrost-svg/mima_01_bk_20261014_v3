__version__ = "1.0.19"
# Пример сводки по разделу 3 «Оценка здоровья проекта с точки зрения сроков».
# ⚠️ Числа порогов (10 / 2 для классификации КТ, 3 / 1 для здоровья проекта)
#    хранятся в:
#      scripts/point-timing-remark-thresholds.py  → REMARK_THRESHOLDS
#      scripts/point-timing-health-thresholds.py  → HEALTH_THRESHOLDS
#    Если правишь — поправь и здесь.

mcp__fst_pmpractice__get_view(entityName="Project", viewName="MyProject")
# → найти проект по Code или ProjectId

mcp__fst_pmpractice__get_view(entityName="Point", viewName="AllMyPoint")
# → фильтр по ParentCode

# Локальная обработка:
for point in project_points:
    if not (point.plan and point.forecast): continue
    if point.fact: continue
    if point.plan == point.forecast: continue
    diff = (point.forecast - point.plan).days
    abs_diff = abs(diff)
    if abs_diff > REMARK_THRESHOLDS["critical"]["min_diff_days"]:    # > 10
        color, status = "Красный", "Критическое"
    elif abs_diff > REMARK_THRESHOLDS["substantial"]["min_diff_days"]:  # > 2
        color, status = "Желтый", "Существенное"
    else:
        color, status = "Синий", "Информационное"

critical_count = sum(1 for r in remarks if r.color == "Красный")
if critical_count >= HEALTH_THRESHOLDS["sick"]["min_critical_count"]:      # ≥ 3
    health = "БОЛЕН"
elif critical_count >= HEALTH_THRESHOLDS["attention"]["min_critical_count"]:  # ≥ 1
    health = "ТРЕБУЕТ ВНИМАНИЯ"
else:
    health = "ЗДОРОВ"
