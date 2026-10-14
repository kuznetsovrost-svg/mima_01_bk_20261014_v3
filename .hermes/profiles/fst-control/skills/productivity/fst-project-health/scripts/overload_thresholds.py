__version__ = "1.0.19"
"""
overload_thresholds.py — пороги для интерпретации индикатора 6.5
«Прогнозы ресурсов на исполнителя в проекте не превышают 100%».

Используется в project_indicators.py::check_resource_overload().

Логика (по уточнениям пользователя, 2026-09-02):
- Норма = 8 часов × количество рабочих дней в месяце (по производственному календарю РФ).
- Для каждого исполнителя считаем Σ прогноз с текущей даты в каждом месяце.
- Сравниваем с доступным временем за этот же период.
- Процент = (прогноз / доступное_время) × 100%.

Severity (по проценту превышения):
- >100% но ≤110% → informational (нейтральный)
- >110% но ≤150% → substantial (жёлтый)
- >150% → critical (красный)

Общий verdict:
- Хотя бы 1 critical → "Критическое"
- Иначе хотя бы 1 substantial → "Существенное"
- Иначе хотя бы 1 informational → "Информационное"
- Иначе → "Норма"
"""
from typing import Callable, Any, Dict


# ============================================================================
# Пороги для 6.5 — Перегрузка исполнителей
# ============================================================================

INDICATOR_THRESHOLDS = {
    "6.5_overload": {
        # Critical: перегрузка > 50% (> 150%)
        "critical_when": lambda r: r.get("has_critical", False),

        # Substantial: перегрузка 10-50% (110-150%)
        "substantial_when": lambda r: (
            not r.get("has_critical", False)
            and r.get("has_substantial", False)
        ),

        # Informational: перегрузка 0-10% (100-110%)
        "informational_when": lambda r: (
            not r.get("has_critical", False)
            and not r.get("has_substantial", False)
            and r.get("has_informational", False)
        ),

        # По умолчанию — норма
        "default_verdict": "Норма",

        # Дополнительные параметры
        "hours_per_day": 8,  # норма часов в рабочем дне
        # Шкалы severity (процент превышения = (прогноз / норма) * 100)
        "informational_max": 110,  # до 110% включительно — informational
        "substantial_max": 150,    # до 150% включительно — substantial
        # > 150% — critical
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

    info_when = cfg.get("informational_when")
    if info_when:
        try:
            if info_when({"result": result_value, "detail": detail}):
                return "Информационное"
        except Exception:
            pass

    return default


def classify_overload_percent(percent: float, cfg: dict) -> str:
    """Классифицирует процент превышения по severity.

    Args:
        percent: процент (прогноз / доступное_время) * 100
        cfg: конфиг порогов

    Returns:
        "informational" / "substantial" / "critical"
    """
    if percent > cfg["substantial_max"]:
        return "critical"
    if percent > cfg["informational_max"]:
        return "substantial"
    if percent > 100:
        return "informational"
    return "normal"
