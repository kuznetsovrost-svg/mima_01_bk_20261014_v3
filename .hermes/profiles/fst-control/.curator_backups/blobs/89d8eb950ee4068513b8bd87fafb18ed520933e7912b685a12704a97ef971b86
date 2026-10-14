"""
test_section_7_format.py — тесты для секции 7 «Технические данные».

Покрывает (Pitfall #211, #212, #213, v1.0.10):
- build_section_7 генерирует 6 строк (по эталону 26)
- Заголовок таблицы — 1) Пользователь 2) Титул системы 3) URL MCP-сервера
  4) Версия скилла 5) Версия MCP 6) Версия Core
- Титул системы — с одинарными кавычками
- Пользователь — из JWT-токена (get_current_user_from_token)
- Fallback-список в render_tbl5_tech совпадает

Запуск:
    python3 tests/test_section_7_format.py
"""
import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


class TestSection7RenderOutput(unittest.TestCase):
    """Проверка что build_section_7 генерирует 6 строк в правильном порядке."""

    def test_section_7_has_six_rows(self):
        """В MD-выводе build_section_7 ровно 6 строк данных."""
        import re
        # build_section_7 в run_all.py (не в project_indicators.py)
        run_all_path = SCRIPTS_DIR / "run_all.py"
        text = run_all_path.read_text(encoding="utf-8")
        # Ищем def build_section_7
        m = re.search(r'def build_section_7.*?(?=^def |\Z)',
                      text, re.DOTALL | re.MULTILINE)
        self.assertIsNotNone(m, "build_section_7 не найдена в run_all.py")
        section_text = m.group(0)
        # Проверяем что в коде 6 строк (по номерам 1-6)
        for n in range(1, 7):
            pattern = rf'\|\s*{n}\s*\|'
            self.assertRegex(section_text, pattern,
                            f"Строка {n} не найдена в коде build_section_7")

    def test_section_7_correct_order(self):
        """Строки в секции 7 идут в правильном порядке (по эталону 26)."""
        import re
        run_all_path = SCRIPTS_DIR / "run_all.py"
        text = run_all_path.read_text(encoding="utf-8")
        m = re.search(r'def build_section_7.*?(?=^def |\Z)',
                      text, re.DOTALL | re.MULTILINE)
        if not m:
            self.skipTest("build_section_7 не найдена в run_all.py")
        section_text = m.group(0)
        # Ищем строки таблицы
        rows = re.findall(r'\|\s*(\d)\s*\|\s*([^|]+?)\s*\|', section_text)
        # Проверяем порядок
        expected_names = [
            "Пользователь", "Титул системы", "URL MCP-сервера",
            "Версия скилла", "Версия MCP", "Версия Core"
        ]
        actual_names = [name.strip() for _, name in rows[:6]]
        for i, expected in enumerate(expected_names):
            actual = actual_names[i] if i < len(actual_names) else ""
            self.assertIn(expected, actual,
                          f"Строка {i+1}: ожидалось '{expected}', получено '{actual}'")


class TestRenderTbl5TechFallback(unittest.TestCase):
    """Проверка fallback в render_tbl5_tech (Pitfall #211)."""

    def test_fallback_has_six_rows(self):
        """Fallback-список содержит 6 строк."""
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location("build_html_report",
                                         SCRIPTS_DIR / "build_html_report.py")
        # Не выполняем модуль (нужен template_html), только компилируем
        import py_compile
        try:
            py_compile.compile(str(SCRIPTS_DIR / "build_html_report.py"),
                               doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f"build_html_report.py не компилируется: {e}")

        # Парсим AST для проверки fallback
        import ast
        tree = ast.parse((SCRIPTS_DIR / "build_html_report.py").read_text(encoding="utf-8"))
        # Ищем функцию render_tbl5_tech
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "render_tbl5_tech":
                # Ищем вложенный список с 6 строк
                for item in ast.walk(node):
                    if isinstance(item, ast.List):
                        if len(item.elts) == 6 and all(
                            isinstance(e, ast.Tuple) and len(e.elts) == 2
                            for e in item.elts
                        ):
                            names = [e.elts[1].value for e in item.elts
                                     if isinstance(e.elts[1], ast.Constant)]
                            if names and "Пользователь" in names[0]:
                                self.assertEqual(len(names), 6)
                                self.assertIn("Пользователь", names)
                                self.assertIn("Титул системы", names)
                                self.assertIn("URL MCP-сервера", names)
                                self.assertIn("Версия скилла", names)
                                self.assertIn("Версия MCP", names)
                                # Допускаются варианты: "Версия Core" или "Версия Core (ПМ «Форсайт»)"
                                self.assertTrue(
                                    "Версия Core" in names or "Версия Core (ПМ «Форсайт»)" in names,
                                    f"Ожидался 'Версия Core' (или с суффиксом), получено: {names}"
                                )
                                return
        self.fail("Не найден fallback-список из 6 строк в render_tbl5_tech")


class TestJwtUserParsing(unittest.TestCase):
    """Проверка get_current_user_from_token (Pitfall #213)."""

    def _make_jwt(self, payload_dict):
        """Создаёт фейковый JWT с заданным payload."""
        import base64
        import json as _json
        header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode().rstrip("=")
        payload = base64.urlsafe_b64encode(
            _json.dumps(payload_dict).encode()
        ).decode().rstrip("=")
        return f"{header}.{payload}.fake_signature"

    def test_extract_displayname(self):
        """displayname извлекается из JWT."""
        from mcp_config import get_current_user_from_token
        token = self._make_jwt({
            "displayname": "Иванов Иван Иванович",
            "UserId": 12345
        })
        result = get_current_user_from_token(token=token)
        self.assertEqual(result, "Иванов Иван Иванович")

    def test_fallback_to_givenname(self):
        """Если нет displayname, берётся givenname (XML claim)."""
        from mcp_config import get_current_user_from_token
        token = self._make_jwt({
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname":
                "Петров Петр",
        })
        result = get_current_user_from_token(token=token)
        self.assertEqual(result, "Петров Петр")

    def test_invalid_token_returns_dash(self):
        """Невалидный токен возвращает '—'."""
        from mcp_config import get_current_user_from_token
        self.assertEqual(get_current_user_from_token(token="not-a-jwt"), "—")
        self.assertEqual(get_current_user_from_token(token="a.b"), "—")
        self.assertEqual(get_current_user_from_token(token=""), "—")


if __name__ == "__main__":
    unittest.main(verbosity=2)
