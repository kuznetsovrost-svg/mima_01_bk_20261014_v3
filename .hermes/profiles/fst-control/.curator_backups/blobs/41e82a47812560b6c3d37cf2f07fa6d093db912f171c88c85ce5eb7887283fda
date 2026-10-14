"""
test_imports.py — проверка, что все модули скилла импортируются без ошибок.

Запуск:
    python3 tests/test_imports.py
"""
import sys
import unittest
import importlib.util
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


# Все production скрипты
PRODUCTION_SCRIPTS = [
    "mcp_config.py",
    "build_report_header.py",
    "build_html_report.py",
    "build_word_report.py",
    "rebuild_report.py",
    "find_project_by_code.py",
    "run_all.py",
    "get_effort.py",
    "get_project_budget.py",
    "get_metamodel.py",
]


class TestImports(unittest.TestCase):
    """Проверка импорта всех production модулей."""

    def setUp(self):
        self.failures = []

    def _try_import(self, name: str):
        """Пытается импортировать модуль через importlib.util."""
        try:
            spec = importlib.util.spec_from_file_location(
                name, str(SCRIPTS_DIR / name)
            )
            m = importlib.util.module_from_spec(spec)
            # ВАЖНО: регистрируем модуль в sys.modules ДО exec_module
            # чтобы @dataclass работал (иначе NameError на __module__)
            sys.modules[name] = m
            spec.loader.exec_module(m)
            return True
        except Exception as e:
            self.failures.append((name, str(e)))
            return False

    def test_all_scripts_importable(self):
        for script in PRODUCTION_SCRIPTS:
            self.assertTrue(
                self._try_import(script),
                f"Не удалось импортировать {script}"
            )

    def test_run_all_main_exists(self):
        """run_all.py имеет функцию main() для CLI."""
        spec = importlib.util.spec_from_file_location(
            "run_all", str(SCRIPTS_DIR / "run_all.py")
        )
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        self.assertTrue(hasattr(m, "main"))
        self.assertTrue(callable(m.main))

    def test_build_html_main_exists(self):
        spec = importlib.util.spec_from_file_location(
            "build_html_report", str(SCRIPTS_DIR / "build_html_report.py")
        )
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        self.assertTrue(hasattr(m, "main"))

    def test_build_word_main_exists(self):
        spec = importlib.util.spec_from_file_location(
            "build_word_report", str(SCRIPTS_DIR / "build_word_report.py")
        )
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        self.assertTrue(hasattr(m, "main"))


def main():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestImports)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
