"""Тесты validator CLI."""
import unittest
import sys
from pathlib import Path

from conftest import (
    make_simple_diagram, make_diagram_with_tunnels,
    make_inconsistent_diagram, write_excalidraw_file
)


class TestValidatorCLI(unittest.TestCase):
    """Тесты CLI через subprocess."""

    def setUp(self):
        # Добавляем scripts/ в sys.path чтобы validator.py работал
        self.scripts_dir = Path(__file__).parent.parent / "scripts"
        self.saved_path = sys.path.copy()
        sys.path.insert(0, str(self.scripts_dir))

        # Подготовить файлы
        self.tmp_ok = write_excalidraw_file(make_simple_diagram())
        self.tmp_tunnels = write_excalidraw_file(
            make_diagram_with_tunnels()
        )
        self.tmp_bad = write_excalidraw_file(make_inconsistent_diagram())
        self.tmp_invalid = Path("/tmp/invalid.excalidraw")
        self.tmp_invalid.write_text("{not json", encoding="utf-8")

    def tearDown(self):
        sys.path = self.saved_path
        for f in [self.tmp_ok, self.tmp_tunnels, self.tmp_bad,
                  self.tmp_invalid]:
            Path(f).unlink(missing_ok=True)

    def _run_cli(self, *args):
        """Запустить CLI команды через main()."""
        import validator
        from unittest.mock import patch

        captured = []
        with patch('sys.stdout') as mock_stdout:
            # Перехватить print
            def fake_print(*a, **kw):
                captured.append(' '.join(str(x) for x in a))
            mock_stdout.write = lambda s: captured.append(s)
            mock_stdout.flush = lambda: None

            # Подменить sys.argv
            backup = sys.argv
            sys.argv = ["validator.py"] + list(args)
            try:
                exit_code = validator.main()
            except SystemExit as e:
                exit_code = e.code
            finally:
                sys.argv = backup
        return exit_code, '\n'.join(captured)

    def test_summary_ok(self):
        code, out = self._run_cli("--file", str(self.tmp_ok), "summary")
        self.assertEqual(code, 0)
        self.assertIn("rectangles", out)

    def test_validate_ok(self):
        code, out = self._run_cli("--file", str(self.tmp_ok), "validate")
        # Может вернуть 0 или 1 в зависимости от warnings
        self.assertIn(code, [0, 1])
        self.assertIn("Blocks", out)
        self.assertIn("Arrows", out)

    def test_validate_invalid_file(self):
        code, out = self._run_cli("--file",
                    str(self.tmp_invalid), "validate")
        # Exit 1 при ошибке загрузки
        self.assertNotEqual(code, 0)

    def test_generate_description_ok(self):
        code, out = self._run_cli(
            "--file", str(self.tmp_ok), "generate-description"
        )
        self.assertEqual(code, 0)
        self.assertIn("Блок", out)

    def test_generate_catalogue_ok(self):
        code, out = self._run_cli(
            "--file", str(self.tmp_ok), "generate-catalogue"
        )
        self.assertEqual(code, 0)
        self.assertIn("Имя стрелки", out)

    def test_generate_catalogue_with_frame(self):
        code, out = self._run_cli(
            "--file", str(self.tmp_ok), "generate-catalogue",
            "--frame", "A0"
        )
        self.assertEqual(code, 0)

    def test_generate_catalogue_unknown_frame(self):
        code, out = self._run_cli(
            "--file", str(self.tmp_ok), "generate-catalogue",
            "--frame", "NONEXISTENT"
        )
        # Exit 1 при ненайденном frame
        self.assertEqual(code, 1)

    def test_check_icom_required_parent(self):
        # Без --parent — argparse должен ругаться
        code, out = self._run_cli(
            "--file", str(self.tmp_bad), "check-icom"
        )
        self.assertEqual(code, 2)  # argparse error

    def test_check_icom_with_parent(self):
        code, out = self._run_cli(
            "--file", str(self.tmp_bad), "check-icom",
            "--parent", "rect-group-parent"
        )
        # Есть inconsistencies — должен быть 1
        self.assertIn(code, [0, 1])

    def test_validate_with_parent(self):
        code, out = self._run_cli(
            "--file", str(self.tmp_bad), "validate",
            "--parent", "rect-group-parent"
        )
        self.assertIn(code, [0, 1])
        # ICOM consistency issues
        self.assertIn("ICOM", out)

    def test_summary_with_tunnels(self):
        code, out = self._run_cli(
            "--file", str(self.tmp_tunnels), "summary"
        )
        self.assertEqual(code, 0)
        # 3 туннеля
        self.assertIn("Tunnels: 3", out)


class TestValidatorCLIWithoutFile(unittest.TestCase):
    """Тесты без указания --file."""

    def setUp(self):
        self.scripts_dir = Path(__file__).parent.parent / "scripts"
        self.saved_path = sys.path.copy()
        sys.path.insert(0, str(self.scripts_dir))

    def tearDown(self):
        sys.path = self.saved_path

    def test_no_file_arg(self):
        import validator
        backup = sys.argv
        sys.argv = ["validator.py", "summary"]
        try:
            with self.assertRaises(SystemExit) as cm:
                validator.main()
            # argparse exit code 2
            self.assertEqual(cm.exception.code, 2)
        finally:
            sys.argv = backup

    def test_no_command_arg(self):
        import validator
        backup = sys.argv
        sys.argv = ["validator.py", "--file", "/tmp/x"]
        try:
            with self.assertRaises(SystemExit) as cm:
                validator.main()
            self.assertEqual(cm.exception.code, 2)
        finally:
            sys.argv = backup


if __name__ == '__main__':
    unittest.main()
