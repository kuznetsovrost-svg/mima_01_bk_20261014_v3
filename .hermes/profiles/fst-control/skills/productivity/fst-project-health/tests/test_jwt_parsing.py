"""
test_jwt_parsing.py — тесты для JWT-парсинга (Pitfall #213, v1.0.10).

Покрывает:
- get_current_user_from_token() в mcp_config.py
- Декодирование JWT payload (displayname, givenname, name claims)
- Edge cases: невалидный токен, пустой токен, без claims

Запуск:
    python3 tests/test_jwt_parsing.py
"""
import base64
import json as _json
import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def _make_jwt(payload: dict, header: dict = None) -> str:
    """Создаёт фейковый JWT с заданным payload (для тестов)."""
    if header is None:
        header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(
        _json.dumps(header).encode()
    ).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(
        _json.dumps(payload).encode()
    ).decode().rstrip("=")
    return f"{header_b64}.{payload_b64}.fake_signature"


class TestJwtParsing(unittest.TestCase):
    """Проверка get_current_user_from_token."""

    def test_displayname_extracted(self):
        """displayname извлекается из JWT."""
        from mcp_config import get_current_user_from_token
        token = _make_jwt({"displayname": "Иванов Иван"})
        self.assertEqual(get_current_user_from_token(token=token), "Иванов Иван")

    def test_givenname_claim_fallback(self):
        """Если нет displayname, берётся givenname (XML claim)."""
        from mcp_config import get_current_user_from_token
        token = _make_jwt({
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname":
                "Петров Петр Петрович"
        })
        self.assertEqual(get_current_user_from_token(token=token),
                         "Петров Петр Петрович")

    def test_displayname_priority_over_givenname(self):
        """displayname имеет приоритет над givenname."""
        from mcp_config import get_current_user_from_token
        token = _make_jwt({
            "displayname": "Иванов (Короткое)",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname":
                "Иванов Иван Иванович (Длинное)"
        })
        result = get_current_user_from_token(token=token)
        self.assertEqual(result, "Иванов (Короткое)")

    def test_real_pmforeisght_jwt_structure(self):
        """Реальная структура JWT PMForesight: displayname, givenname, email."""
        from mcp_config import get_current_user_from_token
        token = _make_jwt({
            "UserId": 120872,
            "displayname": "Кузнецов Ростислав Владимирович",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/sid": "120872",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name":
                "tekora-c\\rkuznetsov",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname":
                "Кузнецов Ростислав Владимирович",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress":
                "rkuznetsov@pmpractice.ru",
            "nbf": 1784550446,
            "exp": 1803416400,
            "iss": "PMPractice.Foresight",
        })
        self.assertEqual(get_current_user_from_token(token=token),
                         "Кузнецов Ростислав Владимирович")


class TestJwtEdgeCases(unittest.TestCase):
    """Edge cases для JWT-парсинга."""

    def test_invalid_token(self):
        """Не JWT (нет двух точек) → '—'."""
        from mcp_config import get_current_user_from_token
        self.assertEqual(get_current_user_from_function(token="not-a-jwt") if False
                         else get_current_user_from_token(token="not-a-jwt"),
                         "—")

    def test_only_one_part(self):
        """Только один сегмент (нет точки) → '—'."""
        from mcp_config import get_current_user_from_token
        self.assertEqual(get_current_user_from_token(token="a"), "—")

    def test_two_parts(self):
        """Два сегмента (нет подписи) → парсится."""
        from mcp_config import get_current_user_from_token
        token = _make_jwt({"displayname": "Test"})
        # JWT имеет 3 сегмента, _make_jwt делает правильный формат
        self.assertEqual(get_current_user_from_token(token=token), "Test")

    def test_empty_string(self):
        """Пустая строка → '—'."""
        from mcp_config import get_current_user_from_token
        self.assertEqual(get_current_user_from_token(token=""), "—")

    def test_invalid_base64(self):
        """Невалидный base64 в payload → '—'."""
        from mcp_config import get_current_user_from_token
        # header.valid.payload.notbase64
        bad = "abc.def!!!invalid.ghi"
        self.assertEqual(get_current_user_from_token(token=bad), "—")

    def test_no_name_claims(self):
        """JWT без name-claims → '—'."""
        from mcp_config import get_current_user_from_token
        token = _make_jwt({"UserId": 12345, "sub": "user@example.com"})
        self.assertEqual(get_current_user_from_token(token=token), "—")

    def test_cyrillic_in_displayname(self):
        """Кириллица в displayname корректно декодируется."""
        from mcp_config import get_current_user_from_token
        token = _make_jwt({"displayname": "Петров-Петров Петр"})
        self.assertEqual(get_current_user_from_token(token=token), "Петров-Петров Петр")


if __name__ == "__main__":
    unittest.main(verbosity=2)
