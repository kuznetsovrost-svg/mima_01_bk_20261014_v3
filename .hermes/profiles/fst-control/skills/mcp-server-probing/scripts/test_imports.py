#!/usr/bin/env python3
"""
test_imports.py — проверяет, что все скрипты в scripts/ импортируются
через importlib.util без ошибок.

ВАЖНО: для корректной работы @dataclass модуль **должен** быть в
sys.modules[name] = m ДО exec_module (иначе NameError на __module__).

Pitfall: #14 в SKILL.md (meta-skill testing convention).

Запуск:
    python3 tests/test_imports.py
"""
import sys
import unittest
import importlib.util
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent


# Скрипты, которые нужно проверить
SCRIPTS = sorted([
    p.name for p in SCRIPTS_DIR.glob("*.py")
    if not p.name.startswith("test_") and p.name != "__init__.py"
])


class TestScriptImports(unittest.TestCase):
    """Проверка, что все скрипты в scripts/ импортируются без ошибок."""

    def setUp(self):
        self.failures = []

    def _try_import(self, name: str):
        """Импорт модуля с правильной регистрацией в sys.modules."""
        try:
            spec = importlib.util.spec_from_file_location(
                name, str(SCRIPTS_DIR / name)
            )
            m = importlib.util.module_from_spec(spec)
            # ВАЖНО: sys.modules[name] = m ДО exec_module (для @dataclass)
            sys.modules[name] = m
            spec.loader.exec_module(m)
            return True
        except SystemExit:
            # argparse вызывает sys.exit(2) при --help без args
            return True
        except Exception as e:
            self.failures.append((name, str(e)))
            return False

    def test_all_scripts_importable(self):
        """Каждый .py файл в scripts/ импортируется без ошибок."""
        for script in SCRIPTS:
            self.assertTrue(
                self._try_import(script),
                f"Не удалось импортировать {script}"
            )

    def test_no_failures_recorded(self):
        """Ни одного скрипта не упало при импорте."""
        if self.failures:
            msgs = "\n".join(f"  {n}: {e[:100]}" for n, e in self.failures)
            self.fail(f"Failed to import:\n{msgs}")


def main():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestScriptImports)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
