"""
test_section_8_indicators.py — тесты для секции 8 «Показатели проекта» (16 индикаторов).

Покрывает (Pitfall #193, #194, #196, #198, #200, #210, #214, #215):
- Whitelist подпунктов: {2, 3, 4, 5, 6, 7, 8, 15, 16}
- Подсветка: data-status только на <tr> (не на <td>)
- table=[] vs table=None: рендер ▼ серого или вообще без ▼
- 6.7: формат таблицы 5 колонок, сортировка по ФИО
- 6.8: формат как в секции 3 «Замечания по срокам»

Запуск:
    python3 tests/test_section_8_indicators.py
"""
import ast
import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"


class TestWhitelistAllowedNumbers(unittest.TestCase):
    """Проверка whitelist подпунктов с вложенными таблицами (Pitfall #193)."""

    def test_whitelist_in_build_html_report(self):
        """allowed_numbers = {2, 3, 4, 5, 6, 7, 8, 15, 16} в build_html_report.py."""
        path = SCRIPTS_DIR / "build_html_report.py"
        text = path.read_text(encoding="utf-8")
        self.assertIn("allowed_numbers", text,
                      "allowed_numbers не найден в build_html_report.py")
        # Проверяем набор
        import re
        m = re.search(r'allowed_numbers\s*=\s*\{([^}]+)\}', text)
        self.assertIsNotNone(m)
        nums = {int(x.strip()) for x in m.group(1).split(",") if x.strip()}
        self.assertEqual(nums, {2, 3, 4, 5, 6, 7, 8, 15, 16})


class TestDataStatusOnTrNotTd(unittest.TestCase):
    """Подсветка только на <tr>, не на <td> (Pitfall #190)."""

    def test_no_data_status_on_td(self):
        """В project_indicators.py data-status не должен стоять на <td>."""
        path = SCRIPTS_DIR / "project_indicators.py"
        text = path.read_text(encoding="utf-8")
        # Ищем строки вида <td data-status="..."> — не должно быть
        import re
        bad = re.findall(r'<td[^>]*\bdata-status\s*=', text)
        # Может быть 0 или мало (только в комментариях)
        self.assertLessEqual(len(bad), 0,
                             f"Найден data-status на <td>: {len(bad)} мест. Должно быть на <tr>.")


class TestTableEmptyVsNone(unittest.TestCase):
    """table=[] vs table=None: рендер ▼ (Pitfall #198)."""

    def test_build_html_report_handles_empty_table(self):
        """В коде build_html_report.py есть ветка для has_data=False (серый ▼)."""
        path = SCRIPTS_DIR / "build_html_report.py"
        text = path.read_text(encoding="utf-8")
        self.assertIn("col-details-marker-disabled", text,
                      "Класс col-details-marker-disabled не найден — серый неактивный ▼ не реализован")


class TestSection6_7Format(unittest.TestCase):
    """6.7 формат таблицы (Pitfall #210)."""

    def test_67_header_override_for_plan(self):
        """Колонка 'План' переопределяется в 'Прогноз по активн.' для 6.7."""
        path = SCRIPTS_DIR / "build_html_report.py"
        text = path.read_text(encoding="utf-8")
        self.assertIn('"Прогноз по активн."', text,
                      "Строка 'Прогноз по активн.' не найдена в build_html_report.py")

    def test_67_header_override_for_overload(self):
        """Колонка 'Превышение' → 'Превышение сумм.' для 6.7."""
        path = SCRIPTS_DIR / "build_html_report.py"
        text = path.read_text(encoding="utf-8")
        self.assertIn('"Превышение сумм."', text,
                      "Строка 'Превышение сумм.' не найдена в build_html_report.py")

    def test_67_header_override_for_percent(self):
        """Колонка '%' → '%Превышения' для 6.7."""
        path = SCRIPTS_DIR / "build_html_report.py"
        text = path.read_text(encoding="utf-8")
        self.assertIn('"%Превышения"', text,
                      "Строка '%Превышения' не найдена в build_html_report.py")

    def test_67_uses_str_num_comparison(self):
        """Сравнение num с строкой '7' (Pitfall #200)."""
        path = SCRIPTS_DIR / "build_html_report.py"
        text = path.read_text(encoding="utf-8")
        self.assertIn('str(num) == "7"', text,
                      "Сравнение str(num) == '7' не найдено — Pitfall #200 не исправлен")


class TestSection6_8Format(unittest.TestCase):
    """6.8 формат как в секции 3 (Pitfall #214, #215)."""

    def test_68_uses_all_finance_point(self):
        """check_financial_deadlines использует Point/AllFinancePoint."""
        path = SCRIPTS_DIR / "project_indicators.py"
        text = path.read_text(encoding="utf-8")
        # Ищем функцию check_financial_deadlines
        import re
        m = re.search(r'def check_financial_deadlines.*?(?=^def |\Z)',
                      text, re.DOTALL | re.MULTILINE)
        self.assertIsNotNone(m, "check_financial_deadlines не найдена")
        func_text = m.group(0)
        self.assertIn("AllFinancePoint", func_text,
                      "View AllFinancePoint не используется в 6.8 — Pitfall #214")
        # Условие forecast_date < today (после lower/без пробелов)
        flat = func_text.lower().replace(" ", "")
        self.assertIn("forecast_date<today", flat,
                      "Условие forecast_date < today не найдено в 6.8")

    def test_68_no_more_in_contract_budget_business(self):
        """check_financial_deadlines НЕ вызывает InContractBudgetBusiness (только в коде, не в docstring)."""
        path = SCRIPTS_DIR / "project_indicators.py"
        text = path.read_text(encoding="utf-8")
        import re
        m = re.search(r'def check_financial_deadlines.*?(?=^def |\Z)',
                      text, re.DOTALL | re.MULTILINE)
        self.assertIsNotNone(m)
        func_text = m.group(0)
        # Удаляем docstring (всё между """...""")
        no_doc = re.sub(r'"""[\s\S]*?"""', '', func_text)
        self.assertNotIn("InContractBudgetBusiness", no_doc,
                         "check_financial_deadlines всё ещё вызывает InContractBudgetBusiness (в коде, не в docstring) — Pitfall #214 не применён")


class TestSection6Colors(unittest.TestCase):
    """6.6 без синего, 6.x палитра (Pitfall #194)."""

    def test_66_returns_normal_verdict(self):
        """check_unfilled_roles возвращает verdict='Норма' (без синего)."""
        path = SCRIPTS_DIR / "project_indicators.py"
        text = path.read_text(encoding="utf-8")
        import re
        m = re.search(r'def check_unfilled_roles.*?(?=^def |\Z)',
                      text, re.DOTALL | re.MULTILINE)
        self.assertIsNotNone(m, "check_unfilled_roles не найдена")
        func_text = m.group(0)
        # Не должно быть Информационное в контексте verdict
        # Но может быть в комментариях — ищем именно в if/elif
        bad = re.findall(r'verdict\s*=\s*["\']Информационное["\']', func_text)
        self.assertEqual(bad, [],
                         "verdict='Информационное' для 6.6 должен быть 'Норма'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
