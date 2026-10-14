"""Запуск всех тестов скилла idef0-excalidraw без внешних зависимостей."""
import sys
import unittest
from pathlib import Path

# Добавляем tests/ в sys.path для импорта conftest
TESTS_DIR = Path(__file__).parent
sys.path.insert(0, str(TESTS_DIR))


def run_all():
    """Найти и запустить все test_*.py файлы."""
    loader = unittest.TestLoader()

    # Импортируем все модули тестов
    test_modules = [
        "test_excalidraw_parser",
        "test_block_extractor",
        "test_arrow_extractor",
        "test_side_detector",
        "test_tunnel_detector",
        "test_icom_checker",
        "test_catalogue_generator",
        "test_description_generator",
        "test_validator",
    ]

    suite = unittest.TestSuite()
    for mod_name in test_modules:
        try:
            module = __import__(mod_name)
            suite.addTests(loader.loadTestsFromModule(module))
        except ImportError as e:
            print(f"FAILED to import {mod_name}: {e}", file=sys.stderr)
            return 1

    runner = unittest.TextTestRunner(
        verbosity=2,
        buffer=True,
    )
    result = runner.run(suite)

    print()
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors:   {len(result.errors)}")
    print(f"Skipped:  {len(result.skipped)}")
    print("=" * 60)

    if result.failures:
        print("\nFAILURES:")
        for test, trace in result.failures:
            print(f"  - {test}: {trace.split(chr(10))[-2]}")

    if result.errors:
        print("\nERRORS:")
        for test, trace in result.errors:
            print(f"  - {test}: {trace.split(chr(10))[-2]}")

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_all())
