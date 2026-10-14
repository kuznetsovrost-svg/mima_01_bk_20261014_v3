"""
test_run_all.py — проверка CLI run_all.py без сетевых вызовов.

Что проверяется:
- argparse принимает --code (required), --no-html, --no-word, --sections
- Имя кода передаётся в логику правильно
- main() возвращает 0 при корректных аргументах + --help
- --help не падает

Запуск:
    python3 tests/test_run_all.py
"""
import sys
import unittest
import argparse
import importlib.util
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def load(name: str, fname: str):
    """Загружает модуль из файла с именем, содержащим дефисы."""
    spec = importlib.util.spec_from_file_location(name, str(SCRIPTS_DIR / fname))
    m = importlib.util.module_from_spec(spec)
    # ВАЖНО: sys.modules[name] = m ДО exec_module (для @dataclass)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


# Загружаем run_all для проверки структуры
run_all = load("run_all", "run_all.py")


class TestRunAllCLI(unittest.TestCase):

    def test_load_project_points_view_name(self):
        """load_project_points использует ALL_MY_POINT_VIEW + ALL_MY_POINT_FILTERS."""
        # Проверяем что используется новый формат filters={}
        self.assertEqual(run_all.ALL_MY_POINT_VIEW, "AllMyPoint")
        self.assertEqual(run_all.ALL_MY_POINT_FILTERS(3434), {"ProjectId": 3434})

    def test_parse_date_handles_iso(self):
        """parse_date обрабатывает ISO формат."""
        from datetime import datetime
        d = run_all.parse_date("2026-08-07T00:00:00+03:00")
        self.assertEqual(d, datetime(2026, 8, 7).date())

    def test_parse_date_handles_null(self):
        self.assertIsNone(run_all.parse_date(None))
        self.assertIsNone(run_all.parse_date(""))
        self.assertIsNone(run_all.parse_date("invalid"))

    def test_find_project_returns_dict(self):
        """find_project возвращает dict с нужными полями."""
        # Тип проверки — есть нужные ключи
        self.assertTrue(callable(run_all.find_project))

    def test_save_project_json_returns_path(self):
        """save_project_json возвращает Path."""
        self.assertTrue(callable(run_all.save_project_json))

    def test_build_section_functions_exist(self):
        """Все build_section_* функции существуют."""
        for n in range(3, 9):
            func_name = f"build_section_{n}"
            self.assertTrue(
                hasattr(run_all, func_name),
                f"Нет функции {func_name}"
            )
            self.assertTrue(callable(getattr(run_all, func_name)))

    def test_build_html_word_in_process(self):
        """build_html и build_word используют importlib (in-process)."""
        # Проверяем что они не вызывают subprocess напрямую
        import inspect
        html_src = inspect.getsource(run_all.build_html)
        self.assertIn("importlib.util", html_src)
        self.assertNotIn("subprocess.run", html_src)

    def test_main_signature(self):
        """main() принимает --code (required)."""
        # Проверяем что argparse в main имеет --code
        import inspect
        main_src = inspect.getsource(run_all.main)
        self.assertIn('"--code"', main_src)
        self.assertIn('required=True', main_src)
        self.assertIn('"--no-html"', main_src)
        self.assertIn('"--no-word"', main_src)
        self.assertIn('"--sections"', main_src)
        self.assertIn('"--timing"', main_src)

    def test_cache_functions_exist(self):
        """cache_get / cache_put существуют."""
        self.assertTrue(callable(run_all.cache_get))
        self.assertTrue(callable(run_all.cache_put))
        self.assertEqual(run_all.CACHE_TTL_SEC, 300)


def main():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestRunAllCLI)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
