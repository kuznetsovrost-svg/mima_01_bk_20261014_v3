__version__ = "1.0.19"
"""
vat_calc.py — расчёт фактической ставки НДС по полученным суммам.

Используется в project_indicators.py::check_vat_amount() (6.12).

Формулы (по уточнению пользователя, 2026-09-02):

1) Расчёт суммы НДС (если известна "сумма с НДС"):
   N = ({сумма с НДС} / (100 + {ставка НДС})) * {ставка НДС}
   Пример: (1260 / (100 + 5)) * 5 = 60

2) Расчёт ставки НДС (если известны "сумма с НДС" и "сумма без НДС"):
   Ставка НДС = ({сумма с НДС} / {сумма без НДС}) * 100 - 100

3) Обратная проверка — получение Y (ставки по указанным суммам):
   Y = (Сумма НДС из статьи 611-13 / (сумма акта/оплаты - Сумма НДС из статьи 611-13)) * 100
   Y должна равняться справочной ставке НДС
"""
from typing import Optional, Tuple
from vat_constants import DEFAULT_VAT_RATE, VAT_TOLERANCE_RUB


def calculate_vat_from_total(total_with_vat: float, vat_rate: float = DEFAULT_VAT_RATE) -> float:
    """Расчётная сумма НДС из суммы с НДС.

    Args:
        total_with_vat: сумма акта/оплаты с НДС
        vat_rate: ставка НДС (по умолчанию из DEFAULT_VAT_RATE)

    Returns:
        расчётная сумма НДС

    Пример:
        (1260 / (100 + 5)) * 5 = 60.0
    """
    if total_with_vat is None:
        return 0.0
    return (total_with_vat / (100 + vat_rate)) * vat_rate


def calculate_vat_rate(total_with_vat: float, total_without_vat: float) -> Optional[float]:
    """Обратный расчёт ставки НДС по суммам с НДС и без НДС.

    Args:
        total_with_vat: сумма с НДС
        total_without_vat: сумма без НДС

    Returns:
        ставка НДС в % или None (если деление на 0)

    Пример:
        (1260 / 1200) * 100 - 100 = 5.0
    """
    if not total_with_vat or not total_without_vat:
        return None
    if total_without_vat == 0:
        return None
    return (total_with_vat / total_without_vat) * 100 - 100


def calculate_actual_vat_rate(amount_with_vat: float, vat_amount: float) -> Optional[float]:
    """Расчёт фактической ставки НДС (Y) по суммам.

    Y = (Сумма НДС из статьи 611-13 / (сумма акта/оплаты - Сумма НДС из статьи 611-13)) * 100

    Args:
        amount_with_vat: сумма акта/оплаты (с НДС)
        vat_amount: указанная сумма НДС в статье 611-13

    Returns:
        ставка Y в % или None (если деление на 0)

    Пример:
        vat=60, amount=1260:
        (60 / (1260 - 60)) * 100 = 5.0
    """
    if amount_with_vat is None or vat_amount is None:
        return None
    base = amount_with_vat - vat_amount
    if base == 0:
        return None
    return (vat_amount / base) * 100


def pick_amount_by_priority(row: dict) -> float:
    """Выбирает сумму акта/оплаты по приоритету (как в 6.10).

    Приоритет: payfactsum > payforecastsum > payplansum >
               actfactsum > actforecastsum > actplansum

    Args:
        row: словарь с полями payfactsum, payforecastsum, и т.д.

    Returns:
        выбранная сумма (0 если ничего нет)
    """
    if (row.get("payfactsum") or 0) > 0:
        return row["payfactsum"]
    if (row.get("payforecastsum") or 0) > 0:
        return row["payforecastsum"]
    if (row.get("payplansum") or 0) > 0:
        return row["payplansum"]
    if (row.get("actfactsum") or 0) > 0:
        return row["actfactsum"]
    if (row.get("actforecastsum") or 0) > 0:
        return row["actforecastsum"]
    if (row.get("actplansum") or 0) > 0:
        return row["actplansum"]
    return 0


def check_vat_amounts_match(amount_with_vat: float, vat_amount: float,
                            vat_rate: float = DEFAULT_VAT_RATE,
                            tolerance: float = VAT_TOLERANCE_RUB) -> bool:
    """Проверяет что указанная сумма НДС соответствует расчётной.

    Args:
        amount_with_vat: сумма акта/оплаты с НДС
        vat_amount: указанная сумма НДС в статье 611-13
        vat_rate: справочная ставка НДС
        tolerance: допуск в рублях

    Returns:
        True если суммы совпадают (в пределах допуска)
    """
    calculated = calculate_vat_from_total(amount_with_vat, vat_rate)
    return abs(calculated - vat_amount) <= tolerance