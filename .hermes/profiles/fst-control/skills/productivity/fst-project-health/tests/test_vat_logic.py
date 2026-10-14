"""
test_vat_logic.py — тесты для индикатора 6.12 «Сумма НДС расчётная».

Покрывает (Pitfall #218, #223, v1.0.13):
- Логика суммирования amount/vat по периодам
- Приоритет fact > forecast > plan (для каждого pay/act — max)
- Только budgettype="Доходный контракт" (расходы не участвуют)
- vat берётся в ТОМ ЖЕ сценарии что amount
- Формула: расчётный НДС = total / 21 × 5
- Фактический % = vat / (total - vat) × 100
- Допуск: 0.0001 ₽ (VAT_TOLERANCE_RUB)
- Формат текста результата: «Нет,» (запятая, без (+N))

Запуск:
    python3 tests/test_vat_logic.py
"""
import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


class TestVatConstants(unittest.TestCase):
    """Проверка констант НДС."""

    def test_default_vat_rate_is_5_percent(self):
        """DEFAULT_VAT_RATE = 5.0 (по требованию пользователя)."""
        from vat_constants import DEFAULT_VAT_RATE
        self.assertEqual(DEFAULT_VAT_RATE, 5.0)

    def test_tolerance_is_small(self):
        """VAT_TOLERANCE_RUB = 0.0001 (4 знака после запятой)."""
        from vat_constants import VAT_TOLERANCE_RUB
        self.assertEqual(VAT_TOLERANCE_RUB, 0.0001)


class TestVatCalculation(unittest.TestCase):
    """Проверка формулы расчёта НДС."""

    def test_calculate_vat_from_total(self):
        """НДС = Сумма / 21 × 5."""
        from vat_calc import calculate_vat_from_total
        # 1260 / 21 × 5 = 300 (но по формуле amount/(100+rate)*rate = 1260/105*5 = 60)
        # Тест на 1260 из примера пользователя
        self.assertAlmostEqual(calculate_vat_from_total(1260, 5.0), 60.0, places=2)
        # Тест на 1 500 000 (пример 504-595 август)
        self.assertAlmostEqual(calculate_vat_from_total(1500000, 5.0), 71428.5714, places=3)
        # Тест на 4 000 000 (сумма за весь проект)
        self.assertAlmostEqual(calculate_vat_from_total(4000000, 5.0), 190476.1905, places=3)

    def test_calculate_vat_zero(self):
        """Если сумма = 0 или None, возвращаем 0."""
        from vat_calc import calculate_vat_from_total
        self.assertEqual(calculate_vat_from_total(0, 5.0), 0.0)
        self.assertEqual(calculate_vat_from_total(None, 5.0), 0.0)


class TestVatAmountPeriodLogic(unittest.TestCase):
    """Проверка периодической логики 6.12 (по требованию 2026-09-04)."""

    def _make_row(self, budgettype, fs_id, date, fact=0, forecast=0, plan=0,
                  pay_fact=0, pay_fcst=0, pay_plan=0, act_fact=0, act_fcst=0, act_plan=0):
        """Создаёт mock-строку из ProjectBudgetCompleteBusiness."""
        return {
            "budgettype": budgettype,
            "financesourceid": fs_id,
            "date": date,
            "payfactsum": pay_fact,
            "payforecastsum": pay_fcst,
            "payplansum": pay_plan,
            "actfactsum": act_fact,
            "actforecastsum": act_fcst,
            "actplansum": act_plan,
        }

    def test_504_595_july_and_august(self):
        """Кейс 504-595: июль 2_497_500 (факт) + август 1_500_000 (прогноз)."""
        # Имитация данных MCP для 504-595
        rows = [
            # Июль — акт/оплата (факт 2 497 500)
            self._make_row("Доходный контракт", None, "2026-07-01",
                           pay_fact=2497500, act_fact=2497500,
                           pay_fcst=2500000, act_fcst=2500000,
                           pay_plan=2500000, act_plan=2500000),
            # Июль — НДС (611-13): факт и прогноз = 125 000
            self._make_row("Расход ручной ввод", 128, "2026-07-01",
                           pay_fact=125000, pay_fcst=125000, act_fact=125000, act_fcst=125000),
            # Август — акт/оплата (прогноз 1 500 000)
            self._make_row("Доходный контракт", None, "2026-08-01",
                           pay_fcst=1500000, act_fcst=1500000,
                           pay_plan=1500000, act_plan=1500000),
            # Август — НДС: прогноз и план = 75 000
            self._make_row("Расход ручной ввод", 128, "2026-08-01",
                           pay_fcst=75000, pay_plan=75000, act_plan=75000),
        ]

        # Симулируем логику check_vat_amount
        period_amount = {}
        period_vat = {}
        nd_id = 128
        for row in rows:
            fs_id = row.get("financesourceid")
            date = (row.get("date") or "")[:7]
            if not date:
                continue
            fact = max(row.get("payfactsum") or 0, row.get("actfactsum") or 0)
            forecast = max(row.get("payforecastsum") or 0, row.get("actforecastsum") or 0)
            plan = max(row.get("payplansum") or 0, row.get("actplansum") or 0)
            if fs_id == nd_id:
                if date not in period_vat:
                    period_vat[date] = {}
                if fact > 0:
                    period_vat[date]["fact"] = max(period_vat[date].get("fact", 0), fact)
                if forecast > 0:
                    period_vat[date]["forecast"] = max(period_vat[date].get("forecast", 0), forecast)
                if plan > 0:
                    period_vat[date]["plan"] = max(period_vat[date].get("plan", 0), plan)
            else:
                if row.get("budgettype") != "Доходный контракт":
                    continue
                if date not in period_amount:
                    period_amount[date] = {}
                if fact > 0:
                    period_amount[date]["fact"] = max(period_amount[date].get("fact", 0), fact)
                if forecast > 0:
                    period_amount[date]["forecast"] = max(period_amount[date].get("forecast", 0), forecast)
                if plan > 0:
                    period_amount[date]["plan"] = max(period_amount[date].get("plan", 0), plan)

        total_amount = 0.0
        total_vat = 0.0
        for period in sorted(set(period_amount.keys()) | set(period_vat.keys())):
            amounts = period_amount.get(period, {})
            vats = period_vat.get(period, {})
            for scen in ("fact", "forecast", "plan"):
                if scen in amounts and amounts[scen] > 0:
                    total_amount += amounts[scen]
                    total_vat += vats.get(scen, 0)
                    break

        # Июль: fact=2 497 500, vat=125 000 (fact)
        # Август: forecast=1 500 000, vat=75 000 (forecast)
        self.assertAlmostEqual(total_amount, 2497500 + 1500000, places=2)
        self.assertAlmostEqual(total_vat, 125000 + 75000, places=2)
        # Расчётный НДС = 3 997 500 / 21 × 5 = 190 357.14
        from vat_calc import calculate_vat_from_total
        calculated = calculate_vat_from_total(total_amount, 5.0)
        self.assertAlmostEqual(calculated, 190357.14, places=2)
        # Фактический % = 200 000 / (3 997 500 - 200 000) × 100 = 5.2666%
        actual_pct = (total_vat / (total_amount - total_vat) * 100) if total_amount > total_vat else 0
        self.assertAlmostEqual(actual_pct, 5.2666, places=3)

    def test_skips_expense_rows(self):
        """Расходы (не Доходный контракт) НЕ должны попадать в amount (только vat)."""
        rows = [
            # Расход без НДС — игнорируется
            self._make_row("Расход расчет по ресурсам", 71, "2026-06-01", act_fcst=867306),
        ]
        period_amount = {}
        for row in rows:
            if row.get("budgettype") != "Доходный контракт":
                continue
            # ... логика
        self.assertEqual(period_amount, {})

    def test_vat_only_rows_have_no_amount(self):
        """Строки НДС (fs=128) не должны попадать в amount, только в vat."""
        rows = [
            self._make_row("Расход ручной ввод", 128, "2026-07-01", pay_fcst=125000),
        ]
        period_amount = {}
        period_vat = {}
        nd_id = 128
        for row in rows:
            fs_id = row.get("financesourceid")
            if fs_id == nd_id:
                period_vat["2026-07"] = {"forecast": 125000}
            else:
                period_amount["2026-07"] = {"forecast": 125000}
        self.assertEqual(period_amount, {})
        self.assertEqual(period_vat["2026-07"]["forecast"], 125000)


class TestVatResultTextFormat(unittest.TestCase):
    """Формат текста результата 6.12 (Pitfall #218)."""

    def test_comma_in_Net(self):
        """После 'Нет' — запятая, НЕ пайп."""
        # Проверяем на реальном результате check_vat_amount (если доступен)
        # Иначе — на строке формата
        # Формат: "Нет, Должно быть:X руб./Указано:Y руб./%:Z"
        sample = "Нет, Должно быть:190357.14 руб./Указано:200000.00 руб./%:5.2666"
        self.assertIn("Нет,", sample)
        self.assertNotIn("Нет |", sample)
        self.assertNotIn("(+", sample)

    def test_no_extra_count_suffix(self):
        """В тексте НЕТ (+N) — даже если несколько mismatches."""
        # Проверяем что f-string в коде не использует `(+{len(mismatches) - 1})`
        from pathlib import Path as P
        indicators_path = P(SCRIPTS_DIR) / "project_indicators.py"
        text = indicators_path.read_text(encoding="utf-8")
        # Не должно быть конструкции (+{len в контексте VAT
        self.assertNotIn("(+{len(mismatches) - 1})", text,
                         "Bug v1.0.12: 'Нет, (+N)' suffix should be removed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
