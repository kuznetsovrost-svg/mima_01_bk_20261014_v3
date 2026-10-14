__version__ = "1.0.19"
"""
act_pay_amounts_thresholds.py — пороги для интерпретации индикатора 6.9
«Суммы актов и оплат».

Используется в project_indicators.py::check_act_pay_amounts().

Логика (по уточнениям пользователя, 2026-09-02):
- Проверка только для коммерческих проектов.
- Σ актов ( ActForecastSum) и Σ оплат (PayForecastSum).
- Δ = акты - оплаты.
- Δ ≤ 0 — норма (нет замечания).
- Δ > 0 — замечание по severity.

Пороги:
- 0 < Δ ≤ 100 000 — Информационное
- 100 000 < Δ ≤ 1 000 000 — Существенное
- Δ > 1 000 000 — Критическое

Пороги вынесены в отдельный скрипт.
"""
from typing import Callable, Any, Dict


# ============================================================================
# Пороги для 6.9 — Суммы актов и оплат
# ============================================================================

INDICATOR_THRESHOLDS = {
    "6.9_act_pay_amounts": {
        "critical_when": lambda r: r.get("has_critical", False),
        "substantial_when": lambda r: (
            not r.get("has_critical", False)
            and r.get("has_substantial", False)
        ),
        "informational_when": lambda r: (
            not r.get("has_critical", False)
            and not r.get("has_substantial", False)
            and r.get("has_informational", False)
        ),
        "default_verdict": "Норма",

        # Пороги
        "informational_max": 100_000,      # до 100 тыс
        "substantial_max": 1_000_000,      # до 1 млн

        # Тип проекта
        "commercial_type_name": "Коммерческий",
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


def classify_amount_delta(delta: float, cfg: dict) -> str:
    """Классифицирует Δ по severity.

    Args:
        delta: разница (акты - оплаты) в рублях
        cfg: конфиг порогов

    Returns:
        "informational" / "substantial" / "critical" / "normal"
    """
    if delta <= 0:
        return "normal"
    if delta > cfg["substantial_max"]:
        return "critical"
    if delta > cfg["informational_max"]:
        return "substantial"
    return "informational"


def format_amount_short(value: float) -> str:
    """Форматирует сумму в рублях в короткий формат.

    Примеры:
        0 → "0 млн. руб."
        333 → "333 руб." (если млн округляется до 0)
        999 → "0,001 млн. руб."
        2_000_000 → "2 млн. руб."
        3_500_000 → "3,5 млн. руб."
        4_752_000 → "4,752 млн. руб."

    Args:
        value: сумма в рублях

    Returns:
        отформатированная строка
    """
    if value == 0:
        return "0 млн. руб."

    # Переводим в млн
    mln = value / 1_000_000

    # Если округление до 3 знаков = 0, выводим сумму в рублях
    if abs(mln) < 0.0005:
        # Целое число рублей
        if value == int(value):
            return f"{int(value)} руб."
        return f"{value:.3f}".rstrip("0").rstrip(".").replace(".", ",") + " руб."

    # Если целое число млн (2.000) — выводим без знаков
    if abs(mln - round(mln)) < 0.0005:
        return f"{int(round(mln))} млн. руб."

    # Иначе 3 знака после запятой
    formatted = f"{mln:.3f}".rstrip("0").rstrip(".")
    formatted = formatted.replace(".", ",")
    return f"{formatted} млн. руб."