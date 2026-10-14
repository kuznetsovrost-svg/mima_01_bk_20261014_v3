__version__ = "1.0.19"
PAYMENT_DEVIATION_THRESHOLDS = {
    "informational": 100_000,    # 0 < Δ < 100 тыс. → Информационное замечание
    "substantial":   1_000_000,  # 100 тыс. ≤ Δ < 1 млн → Существенное замечание
    # Δ ≥ 1 млн = critical (Критическое замечание)
}
