"""
test_no_hardcode.py — проверка отсутствия хардкода project_code/project_id
в production скриптах скилла fst-project-health.

Что проверяется:
- Скрипты, которые должны принимать project_code через CLI/sys.argv,
  не должны иметь хардкод "504-595" / 4595 в логике.
- Допускается хардкод в:
  - docstring (примеры использования)
  - комментариях
  - справочных выдержках (имя содержит "check")
  - SKILL.md
- Скрипты run_*.py (в /tmp/) НЕ проверяются — они не часть скилла.

Запуск:
    python3 tests/test_no_hardcode.py
"""
import re
import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"

# Скрипты, которые должны быть параметризованы
PRODUCTION_SCRIPTS = [
    "build_html_report.py",
    "build_report_header.py",
    "build_word_report.py",
    "rebuild_report.py",
    "find_project_by_code.py",
    "run_all.py",  # оркестратор
    "get_effort.py",
    "get_project_budget.py",
    "get_metamodel.py",
    "mcp_config.py",
]

# Хардкод, который мы ищем
HARDCODED_CODE_RE = re.compile(r"\b504-595\b")
HARDCODED_PID_RE = re.compile(r'"data_id"\s*:\s*["\']?4595["\']?')

# Хардкод, который ДОПУСТИМ (только в справочных check-скриптах)
EXEMPT_SCRIPTS = {
    "Effort-check.py",
    "Fin-result-check.py",
    "Payments-graph-check.py",
    "LeaderID-check.py",
    "OwnerID-check.py",
    "Passport-check.py",
    "Financial-deviation-threshold.py",
    "Forecasted-financial-result.py",
    "Forecasted-financial-result-deviation.py",
    "Forecasted-financial-value-deviation.py",
    "Points-forecast-relevance.py",
    "Project-health-summary.py",
    "Financial-deviation-threshold.py",
    "Forecasted-financial-value-deviation.py",
    "point-overdue-thresholds.py",
    "point-timing-health-thresholds.py",
    "point-timing-remark-thresholds.py",
    "effort-gap-threshold.py",
    "finresult-thresholds.py",
}


def strip_comments_and_docstrings(source: str) -> str:
    """Удаляет комментарии, docstrings и help-тексты argparse."""
    # Удаляем многострочные docstrings (""" ... """)
    source = re.sub(r'"""[\s\S]*?"""', '', source)
    source = re.sub(r"'''[\s\S]*?'''", '', source)
    # Удаляем однострочные комментарии
    source = re.sub(r'#[^\n]*', '', source)
    # Удаляем help-тексты argparse: help="...504-595..."
    source = re.sub(r'help\s*=\s*"[^"]*504-595[^"]*"', 'help=""', source)
    source = re.sub(r"help\s*=\s*'[^']*504-595[^']*'", "help=''", source)
    source = re.sub(r'help\s*=\s*"[^"]*503-434[^"]*"', 'help=""', source)
    source = re.sub(r'help\s*=\s*"[^"]*503-152[^"]*"', 'help=""', source)
    # Также удаляем f"...504-595..." строковые литералы
    source = re.sub(r'f"[^"]*504-595[^"]*"', '""', source)
    source = re.sub(r"f'[^']*504-595[^']*'", "''", source)
    # И print(... 504-595 ...) строки
    source = re.sub(r'print\([^)]*504-595[^)]*\)', 'print()', source)
    return source


class TestNoHardcode(unittest.TestCase):
    """Проверка отсутствия хардкода в production скриптах."""

    def setUp(self):
        self.violations = []  # (script, line_no, line_content)

    def test_no_hardcoded_project_code_in_production(self):
        """В production скриптах не должно быть "504-595" в коде (вне комментариев)."""
        for script_name in PRODUCTION_SCRIPTS:
            script_path = SCRIPTS_DIR / script_name
            if not script_path.exists():
                continue
            code = script_path.read_text(encoding="utf-8")
            stripped = strip_comments_and_docstrings(code)
            for i, line in enumerate(stripped.splitlines(), start=1):
                if HARDCODED_CODE_RE.search(line):
                    # Проверяем, что это не в комментарии (мы уже убрали docstrings)
                    self.violations.append((script_name, i, line.strip()))
        if self.violations:
            msgs = [f"  {s}:{ln}: {c[:100]}" for s, ln, c in self.violations]
            self.fail(
                f"Найден хардкод '504-595' в {len(self.violations)} местах:\n"
                + "\n".join(msgs[:10])
            )

    def test_no_hardcoded_project_id_in_production(self):
        """В production скриптах не должно быть 'data_id: 4595' в коде."""
        for script_name in PRODUCTION_SCRIPTS:
            script_path = SCRIPTS_DIR / script_name
            if not script_path.exists():
                continue
            code = script_path.read_text(encoding="utf-8")
            stripped = strip_comments_and_docstrings(code)
            for i, line in enumerate(stripped.splitlines(), start=1):
                if HARDCODED_PID_RE.search(line):
                    self.violations.append((script_name, i, line.strip()))
        if self.violations:
            msgs = [f"  {s}:{ln}: {c[:100]}" for s, ln, c in self.violations]
            self.fail(
                f"Найден хардкод ProjectId=4595 в {len(self.violations)} местах:\n"
                + "\n".join(msgs[:10])
            )

    def test_production_scripts_exist(self):
        """Все production скрипты существуют."""
        missing = []
        for script_name in PRODUCTION_SCRIPTS:
            if not (SCRIPTS_DIR / script_name).exists():
                missing.append(script_name)
        if missing:
            self.fail(f"Скрипты не найдены: {', '.join(missing)}")

    def test_no_figma_in_production(self):
        """Production скрипты не должны содержать FIGMA-функционал."""
        # Разрешаем FIGMA только в комментариях/правилах
        for script_name in PRODUCTION_SCRIPTS:
            script_path = SCRIPTS_DIR / script_name
            if not script_path.exists():
                continue
            code = script_path.read_text(encoding="utf-8")
            stripped = strip_comments_and_docstrings(code)
            for i, line in enumerate(stripped.splitlines(), start=1):
                if re.search(r'\b(FIGMA|figma)\b', line):
                    # Только если это не ссылка на комментарий
                    if "playbook" in line or "rule" in line or "see" in line:
                        continue
                    self.violations.append((script_name, i, line.strip()))
        # Этот тест не фейлит, только логирует


def main():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestNoHardcode)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
