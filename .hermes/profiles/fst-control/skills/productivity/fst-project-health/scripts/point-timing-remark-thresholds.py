__version__ = "1.0.19"
# Пороги классификации замечаний на основе расхождения PlanDate vs ForecastDate (в календарных днях)
REMARK_THRESHOLDS = {
    "critical": {
        "min_diff_days": 10,      # строго больше 10
        "color": "Красный",
        "status": "Критическое",
    },
    "substantial": {
        "min_diff_days": 2,       # строго больше 2, но ≤ 10
        "max_diff_days": 10,
        "color": "Желтый",
        "status": "Существенное",
    },
    "informational": {
        "max_diff_days": 2,       # 0 ≤ diff ≤ 2
        "color": "Синий",
        "status": "Информационное",
    },
}

