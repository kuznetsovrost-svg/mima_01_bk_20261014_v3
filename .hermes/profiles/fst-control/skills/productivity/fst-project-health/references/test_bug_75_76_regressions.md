# Регрессионные тесты для Bug #75, #76, #78

**Дата:** 2026-08-22
**Источник:** live-probe после введения `run_all.py`

## Назначение

Этот reference содержит копию тестов `test_bug_75_76_regressions.py` (расположен в `tests/`) — для тех, кто хочет прочитать тесты до их запуска.

## Запуск

```bash
cd /root/.hermes/profiles/fst-control/skills/productivity/fst-project-health/tests
python3 -m unittest test_bug_75_76_regressions -v
```

Или автоматически через общий orchestrator:

```bash
python3 run_all_tests.py --report
```

## Что покрывают

| Bug | Severity | Тест | Что проверяет |
|-----|----------|------|--------------|
| #75 | High (классификация) | `TestBuildSection5OverdueVsDiff` | forecast vs plan, фильтр future forecasts, overdue_days приоритет |
| #75 | High (классификация) | `TestBuildSection3OverdueVsDiff` | overdue_days приоритет в build_section_3 |
| #76 | Low (визуал) | `TestCssTblFinanceHeight` | tbl-finance td height <= 50px |
| #78 | High (ширины) | `TestCssTblKtColumnWidths` | tbl-kt widths для 5 колонок, >=110px для дат, >=400px для названий |
| Hard rule | Universal | `TestCssUniversalTablePattern` | word-wrap для kt и overdue |

## Код теста

```python
"""Регрессионные тесты для Bug #75 (overdue vs diff_days) и #76 (tbl-finance height)."""
import sys
import unittest
import importlib.util
import re
from pathlib import Path

SKILL_DIR = Path("/root/.hermes/profiles/fst-control/skills/productivity/fst-project-health")
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def _load_module(name: str, fname: str):
    spec = importlib.util.spec_from_file_location(name, str(SCRIPTS_DIR / fname))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


class TestBuildSection5OverdueVsDiff(unittest.TestCase):
    """Bug #75: build_section_5 должна использовать overdue_days, не diff_days."""

    def test_classify_relevance_uses_overdue_only(self):
        """classify_relevance должен использовать ТОЛЬКО overdue_days."""
        run_all = _load_module("run_all", "run_all.py")
        import inspect
        src = inspect.getsource(run_all.build_section_5)
        self.assertIn("overdue_days >= 30", src)
        self.assertIn("overdue_days >= 14", src)

    def test_section_5_excludes_future_forecasts(self):
        """Bug #75 (canonical): КТ с forecast в будущем НЕ должны быть в разделе 5."""
        run_all = _load_module("run_all", "run_all.py")
        import inspect
        src = inspect.getsource(run_all.build_section_5)
        self.assertIn("if fd >= today: continue", src)
        self.assertIn("overdue_days = (today - fd).days", src)


class TestBuildSection3OverdueVsDiff(unittest.TestCase):
    def test_section_3_uses_overdue_days(self):
        """build_section_3 должна использовать overdue_days для классификации."""
        run_all = _load_module("run_all", "run_all.py")
        import inspect
        src = inspect.getsource(run_all.build_section_3)
        self.assertIn("overdue_days >= 30", src)
        self.assertIn("overdue_days >= 14", src)


class TestCssTblFinanceHeight(unittest.TestCase):
    def test_tbl_finance_height_is_reasonable(self):
        """tbl-finance td height должна быть 30-50px (не 70+)."""
        css_path = SKILL_DIR / "templates" / "report.css"
        if not css_path.exists():
            self.skipTest("report.css не найден")
        css = css_path.read_text(encoding="utf-8")
        m = re.search(
            r"table\.tbl-finance td\s*\{[^}]*?height:\s*(\d+)px",
            css, re.DOTALL
        )
        if not m:
            self.skipTest("tbl-finance td height не найден в CSS")
        height = int(m.group(1))
        self.assertLessEqual(height, 50,
                            f"tbl-finance td height={height}px — слишком много, должно быть <= 50px")


class TestCssTblKtColumnWidths(unittest.TestCase):
    def test_tbl_kt_has_width_for_nth_child(self):
        """tbl-kt должен иметь width для nth-child(1)-(5)."""
        css_path = SKILL_DIR / "templates" / "report.css"
        if not css_path.exists():
            self.skipTest("report.css не найден")
        css = css_path.read_text(encoding="utf-8")
        for n in (1, 2, 3, 4, 5):
            self.assertIn(
                f"table.tbl-kt th:nth-child({n}), table.tbl-kt td:nth-child({n})",
                css
            )

    def test_tbl_kt_date_columns_wide_enough(self):
        """План/Прогноз >= 110px (для дат YYYY-MM-DD)."""
        css_path = SKILL_DIR / "templates" / "report.css"
        css = css_path.read_text(encoding="utf-8")
        for n in (4, 5):
            m = re.search(
                rf"table\.tbl-kt th:nth-child\({n}\), table\.tbl-kt td:nth-child\({n}\)\s*\{{\s*width:\s*(\d+)px",
                css
            )
            self.assertIsNotNone(m)
            self.assertGreaterEqual(int(m.group(1)), 110)

    def test_tbl_kt_name_column_wide(self):
        """Наименование >= 400px (для длинных КТ-названий)."""
        css_path = SKILL_DIR / "templates" / "report.css"
        css = css_path.read_text(encoding="utf-8")
        m = re.search(
            r"table\.tbl-kt th:nth-child\(3\), table\.tbl-kt td:nth-child\(3\)\s*\{\s*width:\s*(\d+)px",
            css
        )
        self.assertIsNotNone(m)
        self.assertGreaterEqual(int(m.group(1)), 400)


class TestCssUniversalTablePattern(unittest.TestCase):
    def test_all_tables_have_word_wrap(self):
        """Все основные таблицы должны иметь word-wrap."""
        css_path = SKILL_DIR / "templates" / "report.css"
        css = css_path.read_text(encoding="utf-8")
        for tbl in ["tbl-kt", "tbl-overdue"]:
            block = re.search(
                rf"table\.{tbl} td\s*\{{[^}}]*word-wrap:\s*break-word",
                css, re.DOTALL
            )
            self.assertIsNotNone(block, f"{tbl}: нет word-wrap: break-word")
```

## Связь с SKILL.md

См. основной skill `fst-project-health` → раздел "Workflow rule — fix the GENERATOR, not just one report" + "Live-bugs исправленные в `run_all.py`".

## Когда добавлять

- Каждый раз когда **новый bug** в `run_all.py` / `build_html_report.py` / `templates/report.css` исправлен — добавлять **регрессионный тест** сюда или в `tests/`.
- При добавлении **новой таблицы** в HTML-отчёт — добавить проверку ширин + word-wrap для неё.
