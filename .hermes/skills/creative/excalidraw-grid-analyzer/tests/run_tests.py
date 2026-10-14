"""Простой runner для всех тестов."""
import sys
import subprocess
from pathlib import Path

TESTS_DIR = Path(__file__).parent
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"


def run_all():
    """Запустить pytest на всех test_*.py."""
    # Пробуем pytest
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(TESTS_DIR), "-v",
             "--tb=short", "-x"],
            env={"PYTHONPATH": str(SCRIPTS_DIR), "PATH": "/usr/bin:/usr/local/bin"},
            capture_output=True, text=True,
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr, file=sys.stderr)
        return result.returncode
    except FileNotFoundError:
        print("pytest не установлен, используем прямой запуск")
        return run_manual()


def run_manual():
    """Запустить каждый test_*.py напрямую (если нет pytest)."""
    test_files = sorted(TESTS_DIR.glob("test_*.py"))
    failed = []
    for test_file in test_files:
        print(f"\n{'='*60}")
        print(f"Running: {test_file.name}")
        print('='*60)
        result = subprocess.run(
            [sys.executable, str(test_file)],
            env={"PYTHONPATH": str(SCRIPTS_DIR)},
            capture_output=True, text=True,
        )
        print(result.stdout)
        if result.returncode != 0:
            print("STDERR:", result.stderr, file=sys.stderr)
            failed.append(test_file.name)

    print(f"\n{'='*60}")
    if failed:
        print(f"❌ Failed: {len(failed)}")
        for f in failed:
            print(f"  - {f}")
        return 1
    print(f"✅ All passed ({len(test_files)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(run_all())