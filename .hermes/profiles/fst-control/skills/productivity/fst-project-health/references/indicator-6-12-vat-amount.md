# 6.12 Сумма НДС расчётная — справочные заметки

## Суть проверки

Проверить, что указанная в статье **«611-13 НДС»** сумма соответствует расчётной по формуле:

```
НДС = сумма_с_НДС × ставка / (100 + ставка)
```

Пример (ставка 5%):
- Сумма с НДС: 1 260 руб.
- Расчётная НДС: (1260 / (100 + 5)) × 5 = **60 руб.**

## Источник данных

View: `Project/ProjectBudgetCompleteBusiness` с фильтром `ProjectId=<id>`.

В каждой строке:
- `budgettype = "Доходный контракт"` или `"Расход ручной ввод"`
- `financesourceid` — ID финансовой статьи (128 = НДС, 71 = Ресурсы, 72 = Полиграфия и т.д.)
- `date` — период (каждая строка = 1 месяц)
- Поля сумм: `actplansum`, `actforecastsum`, `actfactsum`, `payplansum`, `payforecastsum`, `payfactsum`

## Логика по приоритету (Pitfall #121)

Для каждой строки выбирается ОДНА сумма по приоритету:
1. `payfactsum`
2. `payforecastsum`
3. `payplansum`
4. `actfactsum`
5. `actforecastsum`
6. `actplansum`

Если сумма `payfactsum > 0`, берётся она. Иначе `payforecastsum`. Иначе идём по списку.

## Сравнение

Расчётная НДС вычисляется через `vat_calc.calculate_vat_from_total()`.
Сравнение через `vat_calc.check_vat_amounts_match()` с допуском `VAT_TOLERANCE_RUB = 0.0001` руб.

```python
abs(calculated - vat) <= 0.0001
```

## Модули

| Файл | Что |
|------|-----|
| `scripts/vat_constants.py` | `DEFAULT_VAT_RATE = 5.0`, `VAT_TOLERANCE_RUB = 0.0001` |
| `scripts/vat_calc.py` | `calculate_vat_from_total`, `calculate_vat_rate`, `calculate_actual_vat_rate`, `pick_amount_by_priority`, `check_vat_amounts_match` |
| `scripts/project_indicators.py::check_vat_amount` | Главная функция |

## Pitfall #127: "Нет" vs "-" для tax-индикаторов

- `"Нет"` — посчитано, но не совпало (или суммы = 0 при наличии актов)
- `"-"` — не вычислялось (актов/оплат вообще нет)

User: «В налоговом законодательстве это разные вещи!»

## Live-probe 2026-09-03

**504-595:** `Нет | Должно быть:71428.57 руб./Указано:75000.00 руб./%:5.2632 (+2)`

**503-434, 503-152, 504-314:** `"-"` (акты/оплаты не заданы)

## Детализация при "Нет"

```
Должно быть:{N} руб./Указано:{M} руб./%:{Y}
```

Где:
- N — расчётная НДС (`сумма_с_НДС × ставка / (100 + ставка)`)
- M — указанная в статье НДС
- Y — фактическая ставка: `(M / (сумма_с_НДС - M)) × 100`

Если несколько несовпадений, показывается первое, после скобок `(+N)` с количеством дополнительных.

## Будущее расширение

Когда появится справочник ставок НДС по юрлицам — `vat_constants.py` нужно будет дополнить:

```python
VAT_RATES_BY_COMPANY = {
    "АТР": 5.0,
    "Проектная ПРАКТИКА": 5.0,
    # ...
}
DEFAULT_VAT_RATE = 5.0  # fallback

def get_vat_rate(company_name: str) -> float:
    return VAT_RATES_BY_COMPANY.get(company_name, DEFAULT_VAT_RATE)
```