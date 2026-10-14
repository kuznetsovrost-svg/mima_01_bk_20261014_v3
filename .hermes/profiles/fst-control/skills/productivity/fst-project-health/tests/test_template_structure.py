"""
test_template_structure.py — тесты для templates/report.html.

Покрывает (Pitfall #202, #203):
- Правильный порядок секций (по эталону 26, 2026-08-07):
  3 → 4 → 5 → Показатели (16 индикаторов) → 6 (финансы) → 7 (тех. данные)
- Отсутствие дублей открывашек
- Заголовки по эталону:
  - «Полнота заполнения проекта»
  - «Актуальность прогнозов»
  - «Показатели проекта»
  - «Финансовый статус проекта»
  - «Технические данные отчёта»

Запуск:
    python3 tests/test_template_structure.py
"""
import re
import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "templates" / "report.html"


class TestTemplateExists(unittest.TestCase):
    """Базовые проверки."""

    def test_template_exists(self):
        """templates/report.html существует."""
        self.assertTrue(TEMPLATE.exists(),
                        f"Шаблон не найден: {TEMPLATE}")


class TestSectionOrder(unittest.TestCase):
    """Порядок секций в шаблоне (Pitfall #203)."""

    def setUp(self):
        self.text = TEMPLATE.read_text(encoding="utf-8")

    def _extract_tbl_names(self):
        """Извлекает список названий таблиц в порядке их появления."""
        return re.findall(r'<span class="tbl-name">([^<]+)</span>', self.text)

    def test_correct_order(self):
        """Порядок: Замечания → Полнота → Прогнозы → Показатели → Финансы → Тех.данные."""
        names = self._extract_tbl_names()
        # Убираем двоеточия
        names = [n.rstrip(":").strip() for n in names]
        expected = [
            "Замечания по срокам",
            "Полнота заполнения проекта",
            "Актуальность прогнозов",
            "Показатели проекта",
            "Финансовый статус проекта",
            "Технические данные отчёта",
        ]
        # В шаблоне могут быть только первые N названий, проверим что они идут в правильном порядке
        for exp in expected:
            self.assertIn(exp, names,
                          f"Секция '{exp}' не найдена в шаблоне")
        # Проверим что порядок — в шаблоне должны быть все 6 названий и идти в правильном порядке
        indices = [names.index(n) for n in expected]
        self.assertEqual(indices, sorted(indices),
                         f"Секции идут НЕ в правильном порядке: {names}")


class TestNoDuplicates(unittest.TestCase):
    """Отсутствие дублей открывашек (Pitfall #202)."""

    def setUp(self):
        self.text = TEMPLATE.read_text(encoding="utf-8")

    def test_each_section_appears_once(self):
        """Каждая секция (по названию) встречается ровно 1 раз."""
        names = re.findall(r'<span class="tbl-name">([^<]+)</span>', self.text)
        names = [n.rstrip(":").strip() for n in names]
        from collections import Counter
        counts = Counter(names)
        duplicates = {name: count for name, count in counts.items() if count > 1}
        self.assertEqual(duplicates, {},
                         f"Найдены дубли секций: {duplicates}")


class TestSectionHeaders(unittest.TestCase):
    """Заголовки по эталону (Pitfall #203)."""

    def setUp(self):
        self.text = TEMPLATE.read_text(encoding="utf-8")

    def test_fullness_header(self):
        """Секция 4 — 'Полнота заполнения проекта' (НЕ 'Полнота заполнения КТ')."""
        self.assertIn("Полнота заполнения проекта", self.text)
        self.assertNotIn("Полнота заполнения КТ", self.text,
                         "Устаревший заголовок 'Полнота заполнения КТ' не должен быть в шаблоне")

    def test_finance_header(self):
        """Секция 6 (финансы) — 'Финансовый статус проекта' (НЕ 'Финансы')."""
        self.assertIn("Финансовый статус проекта", self.text)
        self.assertNotIn('>Финансы:', self.text,
                         "Устаревший заголовок 'Финансы:' не должен быть в шаблоне")

    def test_indicators_header(self):
        """Секция 'Показатели проекта' присутствует."""
        self.assertIn("Показатели проекта", self.text)

    def test_tech_data_header(self):
        """Секция 7 — 'Технические данные отчёта'."""
        self.assertIn("Технические данные отчёта", self.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
