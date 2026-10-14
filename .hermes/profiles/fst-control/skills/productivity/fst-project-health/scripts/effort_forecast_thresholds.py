__version__ = "1.0.19"
"""
effort_forecast_thresholds.py — пороги для интерпретации индикатора 6.3
«Прогнозы по ресурсам заданы».

Используется в project_indicators.py::check_effort_forecast().

Логика (по уточнениям пользователя, 2026-09-02):
- Если прогнозных трудозатрат нет вообще (Σ=0) → вердикт "Нет" (критическое)
- Если прогнозы за каждый месяц + РП учтён → вердикт "Да, NN ч" (норма)
- Если прогнозы частично или РП не учтён → вердикт "Вопросы, NN ч" (существенное)

Специализация РП — точное название в MCP: "Руководитель проекта".
"""
from typing import Callable, Any, Dict


# ============================================================================
# Пороги для 6.3 — Прогнозы по ресурсам заданы
# ============================================================================

INDICATOR_THRESHOLDS = {
    "6.3_effort_forecast": {
        # Критическое: прогнозов нет вообще
        "critical_when": lambda r: r.get("total_forecast", 0) == 0,

        # Существенное: прогнозы есть, но не за каждый месяц или РП не учтён
        "substantial_when": lambda r: (
            r.get("total_forecast", 0) > 0 and (
                r.get("missing_months_count", 0) > 0 or
                r.get("missing_pm_months_count", 0) > 0
            )
        ),

        # Информационное: нет месяцев с полным покрытием
        "informational_when": lambda r: False,  # не используется для 6.3

        # По умолчанию — норма
        "default_verdict": "Норма",

        # Дополнительные параметры
        "pm_specialization": "Руководитель проекта",
        "include_partial_months": True,  # даже 1 день прогноза = месяц закрыт
    },
}


# ============================================================================
# Утилиты
# ============================================================================

def interpret_indicator(indicator_key: str, result_value: str, detail: str = "") -> str:
    """Вычислить вердикт индикатора по его ключу и результату.

    Args:
        indicator_key: ключ вида "6.3_effort_forecast"
        result_value: результат проверки ("Да, 168 ч" / "Нет" / "Вопросы, 80 ч")
        detail: детализация (опционально)

    Returns:
        Вердикт: "Норма" / "Информационное" / "Существенное" / "Критическое"
    """
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
