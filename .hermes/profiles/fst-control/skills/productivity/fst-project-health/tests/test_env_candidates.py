"""
test_env_candidates.py — тесты для ENV_FILE_CANDIDATES (Pitfall #224, v1.0.14).

Покрывает:
- ENV_FILE_CANDIDATES — список путей в правильном порядке
- load_token_from_env_file перебирает все кандидаты
- Приоритет: каталог скилла → профиль Hermes
- Корректно игнорирует placeholder-токены (PASTE...)
- Возвращает None если ничего не найдено

Запуск:
    python3 tests/test_env_candidates.py
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


class TestEnvFileCandidates(unittest.TestCase):
    """Проверка ENV_FILE_CANDIDATES в mcp_config.py (Pitfall #224)."""

    def test_candidates_exist(self):
        """ENV_FILE_CANDIDATES — список из >= 2 путей."""
        from mcp_config import ENV_FILE_CANDIDATES
        self.assertIsInstance(ENV_FILE_CANDIDATES, list)
        self.assertGreaterEqual(len(ENV_FILE_CANDIDATES), 2,
                                "Должно быть минимум 2 кандидата (.env в скилле + .env в профиле)")

    def test_first_candidate_is_skill_dir(self):
        """Первый кандидат — каталог скилла (..parent от mcp_config.py)."""
        from mcp_config import ENV_FILE_CANDIDATES
        first = Path(ENV_FILE_CANDIDATES[0]).resolve()
        skill_dir = SKILL_DIR.resolve()
        self.assertEqual(first, skill_dir / ".env",
                         f"Первый кандидат должен быть каталог скилла + .env, получено: {first}")

    def test_second_candidate_is_hermes_profile(self):
        """Второй кандидат — профиль Hermes."""
        from mcp_config import ENV_FILE_CANDIDATES
        if len(ENV_FILE_CANDIDATES) >= 2:
            second = Path(ENV_FILE_CANDIDATES[1]).resolve()
            home = Path.home().resolve()
            expected = (home / ".hermes/profiles/fst-control/.env").resolve()
            self.assertEqual(second, expected,
                             f"Второй кандидат должен быть {expected}, получено: {second}")


class TestLoadTokenFromEnvFile(unittest.TestCase):
    """Проверка load_token_from_env_file (Pitfall #224)."""

    def setUp(self):
        """Создаём временные .env-файлы для теста."""
        self.tmpdir = tempfile.mkdtemp()
        self.env_path = Path(self.tmpdir) / ".env"
        self.env_path.write_text(
            "PMP_TOKEN=test_real_token_12345\n",
            encoding="utf-8"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_loads_token_from_explicit_path(self):
        """Загружает токен из явно указанного .env."""
        from mcp_config import load_token_from_env_file
        token = load_token_from_env_file(env_path=self.env_path)
        self.assertEqual(token, "test_real_token_12345")

    def test_loads_token_with_quotes(self):
        """Поддерживает PMP_TOKEN='value' (с одинарными кавычками)."""
        self.env_path.write_text("PMP_TOKEN='quoted_token_abc'\n", encoding="utf-8")
        from mcp_config import load_token_from_env_file
        token = load_token_from_env_file(env_path=self.env_path)
        self.assertEqual(token, "quoted_token_abc")

    def test_loads_token_with_double_quotes(self):
        """Поддерживает PMP_TOKEN=\"value\" (с двойными кавычками)."""
        self.env_path.write_text('PMP_TOKEN="double_quoted"\n', encoding="utf-8")
        from mcp_config import load_token_from_env_file
        token = load_token_from_env_file(env_path=self.env_path)
        self.assertEqual(token, "double_quoted")

    def test_skips_paste_placeholder(self):
        """Игнорирует placeholder-токены (PASTE...)."""
        self.env_path.write_text("PMP_TOKEN=PASTE_YOUR_TOKEN_HERE\n", encoding="utf-8")
        from mcp_config import load_token_from_env_file
        token = load_token_from_env_file(env_path=self.env_path)
        self.assertIsNone(token, "Placeholder-токен должен игнорироваться")

    def test_nonexistent_file_returns_none(self):
        """Несуществующий файл → None."""
        from mcp_config import load_token_from_env_file
        token = load_token_from_env_file(env_path=Path("/nonexistent/.env"))
        self.assertIsNone(token)

    def test_empty_env_var_returns_none(self):
        """PMP_TOKEN= (пусто) → None."""
        self.env_path.write_text("PMP_TOKEN=\n", encoding="utf-8")
        from mcp_config import load_token_from_env_file
        token = load_token_from_env_file(env_path=self.env_path)
        self.assertIsNone(token)

    def test_no_pmptoken_var_returns_none(self):
        """Файл без PMP_TOKEN → None."""
        self.env_path.write_text("OTHER_VAR=value\nPMP_URL=https://example.com\n",
                                 encoding="utf-8")
        from mcp_config import load_token_from_env_file
        token = load_token_from_env_file(env_path=self.env_path)
        self.assertIsNone(token)


class TestEnvFileExample(unittest.TestCase):
    """Проверка .env.example в каталоге скилла."""

    def test_env_example_exists(self):
        """Файл .env.example существует в каталоге скилла."""
        env_example = SKILL_DIR / ".env.example"
        self.assertTrue(env_example.exists(),
                        f".env.example не найден в {SKILL_DIR}")
        # Должен содержать PMP_TOKEN
        text = env_example.read_text(encoding="utf-8")
        self.assertIn("PMP_TOKEN", text,
                      ".env.example должен содержать переменную PMP_TOKEN")
        # Не должен содержать реальных секретов
        self.assertNotIn("eyJ", text,
                         ".env.example не должен содержать JWT (это шаблон!)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
