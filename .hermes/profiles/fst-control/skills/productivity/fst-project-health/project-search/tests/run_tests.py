"""run_tests.py — запуск тестов для project-search."""
import sys
import unittest
from pathlib import Path

if __name__ == "__main__":
    test_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(test_dir))
    loader = unittest.TestLoader()
    suite = loader.discover(str(test_dir), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
