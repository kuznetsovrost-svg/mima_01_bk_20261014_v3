__version__ = "1.0.19"
"""
plan_effort_thresholds.py — пороги для интерпретации индикатора 6.4
«Плановые трудозатраты заданы».

Аналог effort_forecast_thresholds.py, но для ПЛАНОВЫХ трудозатрат (plan_hours)
вместо прогнозных (forecast_hours).

Используется в project_indicators.py::check_plan_effort().

Логика (по уточнениям пользователя, 2026-09-02):
- Если плановых трудозатрат нет вообще (Σ=0) → вердикт "Нет" (критическое)
- Если планы за каждый месяц + РП учтён → вердикт "Да, NN ч" (норма)
- Если планы частично или РП не учтён → вердикт "Вопросы, NN ч" (существенное)

Специализация РП — точное название в MCP: "Руководитель проекта".
"""
from typing import Callable, Any, Dict


# ============================================================================
# Пороги для 6.4 — Плановые трудозатраты заданы
# ============================================================================

INDICATOR_THRESHOLDS = {
    "6.4_plan_effort": {
        # Критическое: плановых трудозатрат нет вообще
        "critical_when": lambda r: r.get("total_plan", 0) == 0,

        # Существенное: планы есть, но не за каждый месяц или РП не учтён
        "substantial_when": lambda r: (
            r.get("total_plan", 0) > 0 and (
                r.get("missing_months_count", 0) > 0 or
                r.get("missing_pm_months_count", 0) > 0
            )
        ),

        # Информационное: нет месяцев с полным покрытием
        "informational_when": lambda r: False,

        # По умолчанию — норма
        "default_verdict": "Норма",

        # Дополнительные параметры
        "pm_specialization": "Руководитель проекта",
        "include_partial_months": True,
    },
}


def interpret_indicator(indicator_key: str, result_value: str, detail: str = "") -> str:
    """Вычислить вердикт индикатора."""
    cfg = INDICATOR_THRESHOLDS.get(indicator_key, {})
    default = cfg.get("default_verdict", "Норма")

    crit_when = cfg.get("critical_when")
    if crit_when:
        try:
            if crit_when({"result": result_value, "detail": detail}):
                return "Критическое"
        except Exception:
            pass

    subst_when = cfg.get("substantial_when")
    if subst_when:
        try:
            if subst_when({"result": result_value, "detail": detail}):
                return "Существенное"
        except Exception:
            pass

    return default
