"""
test_pipeline_integration.py — проверка оркестрации run_all.py
БЕЗ реальных вызовов MCP. Использует argparse и проверяет структуру.

Запуск:
    python3 tests/test_pipeline_integration.py
"""
import sys
import unittest
import subprocess
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"


class TestPipelineIntegration(unittest.TestCase):

    def test_run_all_help(self):
        """python3 scripts/run_all.py --help работает."""
        result = subprocess.run(
            ["python3", str(SCRIPTS_DIR / "run_all.py"), "--help"],
            capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--code", result.stdout)
        self.assertIn("--no-html", result.stdout)
        self.assertIn("--no-word", result.stdout)
        self.assertIn("--sections", result.stdout)
        self.assertIn("--timing", result.stdout)

    def test_run_all_requires_code(self):
        """python3 scripts/run_all.py без --code падает с ошибкой."""
        result = subprocess.run(
            ["python3", str(SCRIPTS_DIR / "run_all.py")],
            capture_output=True, text=True, timeout=10
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--code", result.stderr)

    def test_build_html_help(self):
        """python3 scripts/build_html_report.py --help работает."""
        result = subprocess.run(
            ["python3", str(SCRIPTS_DIR / "build_html_report.py"), "--help"],
            capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--code", result.stdout)

    def test_build_html_ls(self):
        """python3 scripts/build_html_report.py --ls работает."""
        result = subprocess.run(
            ["python3", str(SCRIPTS_DIR / "build_html_report.py"), "--ls"],
            capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0)

    def test_build_word_help(self):
        """python3 scripts/build_word_report.py --help работает."""
        result = subprocess.run(
            ["python3", str(SCRIPTS_DIR / "build_word_report.py"), "--help"],
            capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--code", result.stdout)

    def test_rebuild_report_help(self):
        """python3 scripts/rebuild_report.py без аргументов показывает usage."""
        result = subprocess.run(
            ["python3", str(SCRIPTS_DIR / "rebuild_report.py")],
            capture_output=True, text=True, timeout=10
        )
        # Должен падать с usage
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Usage", result.stderr + result.stdout)


def main():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPipelineIntegration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
