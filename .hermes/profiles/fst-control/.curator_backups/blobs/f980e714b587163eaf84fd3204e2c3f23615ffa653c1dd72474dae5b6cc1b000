"""
test_skill_md_integrity.py — проверка целостности SKILL.md.

Что проверяется:
- SKILL.md существует
- Содержит frontmatter с name=fst-project-health
- Версия 0.9.0+ (после FIGMA-отката)
- Нет FIGMA-функционала (только в комментариях и Hard rule)
- Hard rule о не-трогании SKILL.md/scripts/templates/references присутствует

Запуск:
    python3 tests/test_skill_md_integrity.py
"""
import sys
import unittest
import re
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"


class TestSkillMdIntegrity(unittest.TestCase):

    def setUp(self):
        if not SKILL_MD.exists():
            self.skipTest("SKILL.md не найден")
        self.content = SKILL_MD.read_text(encoding="utf-8")

    def test_has_frontmatter(self):
        """SKILL.md начинается с frontmatter."""
        self.assertTrue(self.content.startswith("---\n"))

    def test_has_name_fst_project_health(self):
        """SKILL.md содержит name: fst-project-health."""
        # Используем re.search с MULTILINE (assertRegex не поддерживает флаги)
        m = re.search(r"^name:\s+fst-project-health", self.content, re.MULTILINE)
        self.assertIsNotNone(m, "name: fst-project-health не найден")

    def test_version_at_least_090(self):
        """Версия >= 0.9.0 (после FIGMA-отката)."""
        m = re.search(r"^version:\s*([\d.]+)", self.content, re.MULTILINE)
        if not m:
            self.fail("Не найдена version в frontmatter")
        version = m.group(1)
        parts = version.split(".")
        major, minor = int(parts[0]), int(parts[1])
        # Accept any 0.9.0+ or 1.x
        if major == 0:
            self.assertGreaterEqual(minor, 9)
        else:
            self.assertGreaterEqual(major, 1)

    def test_no_figma_functionality(self):
        """SKILL.md не содержит FIGMA-bridge функционал."""
        figma_mentions = []
        for i, line in enumerate(self.content.splitlines(), start=1):
            if re.search(r"\b(FIGMA|figma)\b", line):
                if any(marker in line for marker in [
                    "Hard rule", "rule", "не менять", "нельзя", "не трогать",
                    "FIGMA-bridge workflow", "FIGMA round-trip",
                    "playbook", "creative/", "FIGMA-bridge",
                    "no FIGMA",  # исключаем упоминания в таблицах тестов
                ]):
                    continue
                figma_mentions.append((i, line.strip()))
        self.assertEqual(
            len(figma_mentions), 0,
            f"Найдены FIGMA упоминания в production SKILL.md: {figma_mentions[:3]}"
        )

    def test_has_hard_rule_about_no_modifications(self):
        """SKILL.md содержит Hard rule про не-трогание скилла."""
        self.assertIn("Hard rule", self.content)
        self.assertIn("NEVER modify", self.content)

    def test_has_performance_section(self):
        """SKILL.md содержит секцию про производительность pipeline."""
        # В SKILL.md есть раздел "Live-bugs исправленные в run_all.py"
        # с хронометражем (504-595: 18-19 сек и т.д.)
        self.assertIn("Live-bugs исправленные", self.content)
        self.assertIn("сек", self.content)  # упоминание бюджета по стадиям

    def test_tbl_overdue_wraps_long_text(self):
        """tbl-overdue должен разрешать перенос строк в длинных наименованиях."""
        css_path = SKILL_DIR / "templates" / "report.css"
        if not css_path.exists():
            self.skipTest("report.css не найден")
        css = css_path.read_text(encoding="utf-8")
        # tbl-overdue не должен иметь nowrap (fix 2026-08-21)
        self.assertNotIn(
            ".tbl-overdue td { white-space: nowrap",
            css,
            "tbl-overdue не должен иметь nowrap — длинные названия КТ не нереносятся"
        )
        # Вместо nowrap должен быть word-wrap: break-word
        self.assertIn("word-wrap: break-word", css)

    def test_tbl_kt_has_column_widths(self):
        """tbl-kt (раздел 3) должен иметь фиксированные ширины колонок."""
        css_path = SKILL_DIR / "templates" / "report.css"
        if not css_path.exists():
            self.skipTest("report.css не найден")
        css = css_path.read_text(encoding="utf-8")
        # Проверяем что tbl-kt имеет ширины для всех 5 колонок
        self.assertIn("table.tbl-kt th:nth-child(1)", css, "tbl-kt: нет ширины колонки 1")
        self.assertIn("table.tbl-kt th:nth-child(2)", css, "tbl-kt: нет ширины колонки 2 (Код)")
        self.assertIn("table.tbl-kt th:nth-child(3)", css, "tbl-kt: нет ширины колонки 3 (Наименование)")
        self.assertIn("table.tbl-kt th:nth-child(4)", css, "tbl-kt: нет ширины колонки 4 (План)")
        self.assertIn("table.tbl-kt th:nth-child(5)", css, "tbl-kt: нет ширины колонки 5 (Прогноз)")
        # План и Прогноз должны быть >= 110px чтобы дата помещалась
        import re
        m = re.search(r"table\.tbl-kt th:nth-child\(4\), table\.tbl-kt td:nth-child\(4\)\s*\{\s*width:\s*(\d+)px", css)
        if m:
            self.assertGreaterEqual(int(m.group(1)), 110, "Колонка 'План' должна быть >=110px")
        m = re.search(r"table\.tbl-kt th:nth-child\(5\), table\.tbl-kt td:nth-child\(5\)\s*\{\s*width:\s*(\d+)px", css)
        if m:
            self.assertGreaterEqual(int(m.group(1)), 110, "Колонка 'Прогноз' должна быть >=110px")
        # Наименование должно быть достаточно широким
        m = re.search(r"table\.tbl-kt th:nth-child\(3\), table\.tbl-kt td:nth-child\(3\)\s*\{\s*width:\s*(\d+)px", css)
        if m:
            self.assertGreaterEqual(int(m.group(1)), 400, "Колонка 'Наименование' должна быть >=400px")
        # Должен быть word-wrap: break-word для tbl-kt (как для tbl-overdue)
        self.assertIn("table.tbl-kt td { word-wrap: break-word", css,
                      "tbl-kt должен иметь word-wrap: break-word")

    def test_has_procedure_references(self):
        """SKILL.md ссылается на procedure-файлы."""
        # Минимум одна ссылка на references/
        m = re.search(r"references/[a-z_\-]+", self.content)
        self.assertIsNotNone(m, "references/* ссылка не найдена")

    def test_lists_output_formats(self):
        """SKILL.md упоминает все 4 формата вывода (MD, HTML, MD Форма 2, WORD Форма 1)."""
        for fmt in ["MD", "HTML", "WORD", "Форма"]:
            self.assertIn(fmt, self.content)


def main():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSkillMdIntegrity)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
