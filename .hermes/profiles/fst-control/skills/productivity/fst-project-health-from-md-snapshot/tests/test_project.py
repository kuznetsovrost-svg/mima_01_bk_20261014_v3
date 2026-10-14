"""
test_project.py — указатель на тестовый проект для MCP-тестов.

Что это:
    Этот файл содержит КОД ПРОЕКТА, который тесты используют
    для upload/list/read MD-снимков. По умолчанию это «504-595
    Космодром Жуковский» — наш рабочий проект, в карточку которого
    можно писать со спецсимволами в имени файла.

Как переносить на другой стенд:
    При переносе скилла на другой стенд — измените TEST_PROJECT_CODE
    на код вашего проекта (например, "502-999" или "100-001").
    Если у вас нет прав на чтение/запись в карточку проекта
    в PMForesight MCP — оставьте None, и группа MCP-тестов
    будет пропущена.

Поведение:
    1) TEST_PROJECT_CODE is None  → MCP-тесты пропускаются (нет проекта).
    2) TEST_PROJECT_CODE имеет неверный формат (не "NNN-NNN")
       → MCP-тесты пропускаются (синтаксическая ошибка).
    3) TEST_PROJECT_CODE указан, но нет доступа к карточке
       → MCP-тесты пропускаются (permission denied / not_found).

Во всех трёх случаях пользователь видит в логе «SKIP: ...» и
ненулевой exit code от run_all_tests.py.

См. также:
    playbook.md (раздел «Тестовый проект»), SKILL.md.
"""

# ----- НАСТРОЙКИ ПОЛЬЗОВАТЕЛЯ ---------------------------------------------
# Измените на свой код проекта при переносе на другой стенд.
# None = MCP-тесты полностью отключены.
TEST_PROJECT_CODE = "504-595"

# Допустимые форматы кода. По умолчанию "NNN-NNN" (3 цифры, тире, 3 цифры).
import re
CODE_PATTERN = re.compile(r"^\d{3}-\d{3}$")


def get_test_project_code() -> str | None:
    """Возвращает код проекта или None, если он не настроен.

    Используется тестами:
        from test_project import get_test_project_code
        code = get_test_project_code()
        if code is None:
            pytest.skip("TEST_PROJECT_CODE не указан")
    """
    code = TEST_PROJECT_CODE
    if code is None:
        return None
    code = str(code).strip()
    if not code:
        return None
    if not CODE_PATTERN.match(code):
        return None
    return code


def is_valid_format(code: str) -> bool:
    """Проверка формата (без обращения к MCP)."""
    if not code:
        return False
    return bool(CODE_PATTERN.match(code.strip()))
