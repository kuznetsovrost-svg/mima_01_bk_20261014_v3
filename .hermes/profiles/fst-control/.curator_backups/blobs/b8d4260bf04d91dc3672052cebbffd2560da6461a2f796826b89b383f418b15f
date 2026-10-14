"""
test_project_search.py — проверка структуры SKILL.md project-search.

Что проверяется:
- Наличие frontmatter с name, version, description
- Отсутствие DEPRECATED форматов (?ProjectId=, mcp__fst_pmpractice__)
- Упоминание filters={} как стандартного формата
- Наличие раздела "Доступные views"
- Наличие примера вызова с filters={}

Запуск:
    python3 tests/run_tests.py
"""
import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent  # tests/.. = skill root
SKILL_FILE = SKILL_DIR / "SKILL.md"


class TestProjectSearchSkill(unittest.TestCase):

    def setUp(self):
        self.content = SKILL_FILE.read_text(encoding="utf-8")

    def test_skill_md_exists(self):
        """SKILL.md существует."""
        self.assertTrue(SKILL_FILE.exists(), f"SKILL.md не найден: {SKILL_FILE}")

    def test_frontmatter_valid(self):
        """Frontmatter содержит обязательные поля."""
        # Начинается с ---
        self.assertTrue(self.content.startswith("---\n"), "Должен начинаться с ---")
        # Заканчивается \n---\n (где-то в первых 2000 символов)
        end = self.content.index("\n---\n", 4)
        # Проверяем что end < разумного предела (2000 байт)
        self.assertLess(end, 2000, f"Frontmatter заканчивается слишком далеко: {end}")
        # Извлекаем frontmatter
        front = self.content[4:end]
        # Проверяем поля
        self.assertIn("name: project-search", front)
        self.assertIn("version:", front)
        self.assertIn("description:", front)

    def test_name_correct(self):
        """name = project-search."""
        end = self.content.index("\n---\n", 4)
        front = self.content[4:end]
        self.assertIn("name: project-search", front)

    def test_version_2_or_higher(self):
        """Версия >= 2.0.0 (новый формат filters)."""
        import re
        end = self.content.index("\n---\n", 4)
        front = self.content[4:end]
        m = re.search(r"version:\s*(\d+)\.(\d+)", front)
        self.assertIsNotNone(m)
        major, minor = int(m.group(1)), int(m.group(2))
        self.assertGreaterEqual(
            (major, minor), (2, 0),
            f"Версия {major}.{minor} < 2.0.0 — старый формат"
        )

    def test_no_deprecated_url_format(self):
        """Нет примеров с ?ProjectId=, ?UserAccount= в URL (DEPRECATED)."""
        lines = self.content.split("\n")
        offenders = []
        for i, line in enumerate(lines, 1):
            if "?ProjectId=" in line or "?UserAccount=" in line or "?ActivityId=" in line:
                # Игнорируем строки про DEPRECATED
                if "DEPRECATED" in line or "НЕ работает" in line or "❌" in line:
                    continue
                if "v1.0.0" in line or "changelog" in line.lower():
                    continue
                offenders.append(f"  строка {i}: {line.strip()}")
        self.assertEqual(
            offenders, [],
            "Найдены использования старого формата ?Field=value в URL:\n" + "\n".join(offenders)
        )

    def test_no_mcp_namespace_prefix(self):
        """Нет устаревшего префикса mcp__fst_pmpractice__."""
        # В changelog может быть упоминание о миграции — это ок
        # В production-примерах не должно быть
        import re
        # Ищем все вхождения
        for match in re.finditer(r"mcp__fst_pmpractice__\w+", self.content):
            start = max(0, match.start() - 200)
            end = min(len(self.content), match.end() + 50)
            context = self.content[start:end]
            # Допустимо только в контексте "deprecated" или "replaces"
            if "deprecated" in context.lower() or "replaces" in context.lower():
                continue
            self.fail(f"Найден устаревший префикс: {match.group()}\nКонтекст: ...{context}...")

    def test_uses_filters_format(self):
        """Примеры используют filters={}."""
        self.assertIn('"filters":', self.content)

    def test_documents_views(self):
        """Описаны views MyProject/AllProject с фильтрами."""
        self.assertIn("MyProject", self.content)
        self.assertIn("AllProject", self.content)
        self.assertIn("UserAccount", self.content)
        self.assertIn("ProjectProfileId", self.content)

    def test_has_live_probe_section(self):
        """Есть раздел с live-probe данными."""
        self.assertIn("Live-probe", self.content)

    def test_references_filters_format_doc(self):
        """Есть ссылка на docs о filters= (mcp-server-probing)."""
        self.assertIn("mcp-server-probing", self.content)

    def test_verification_checklist_present(self):
        """Есть Verification Checklist."""
        self.assertIn("Verification Checklist", self.content)

    def test_related_skills_present(self):
        """Related skills включают нужные."""
        self.assertIn("related_skills:", self.content)
        self.assertIn("fst-project-health", self.content)
        self.assertIn("mcp-server-probing", self.content)


if __name__ == "__main__":
    unittest.main()
