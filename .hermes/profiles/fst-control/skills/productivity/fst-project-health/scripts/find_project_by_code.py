"""
find_project_by_code.py

Поиск проекта в Форсайт ПМ Практике по строковому коду (Code).

Типичные сценарии использования:
- Пользователь ввёл "504-595" — найти проект с этим Code.
- Передать дальше в project_payment_schedule, project_effort_plan, и т.д.

Возвращает:
    dict | None — словарь с полями проекта, либо None, если проект не найден
                  или недоступен пользователю по правам.

Исключения:
    ProjectNotFoundError   — Code не найден ни в одном доступном view
    ProjectAccessDenied    — нет ни одного view (403 на обоих)
    McpConnectionError     — проблемы с сетью / токеном / MCP-серверу
"""

from __future__ import annotations

__version__ = "1.0.19"
import json
import logging
import re
from typing import Optional

import requests

# Импорт из mcp_config — централизованные URL, токен, headers, парсер SSE.
# Имя файла без дефиса, импортируется напрямую (pitfall #5 не применим).
from mcp_config import (
    MCP_URL,
    require_token,
    headers_for_call,
    parse_sse_response,
    McpConnectionError,
    mcp_init,
    mcp_call,
)

# Регулярка для валидации формата кода "NNN-NNN"
# Разрешает 1+ цифр с каждой стороны; в Форсайт встречаются 3-значные сегменты.
CODE_PATTERN = re.compile(r"^\d+-\d+$")

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ИСКЛЮЧЕНИЯ
# ═══════════════════════════════════════════════════════════════════════════════

class ProjectNotFoundError(Exception):
    """Проект с указанным Code не найден или недоступен пользователю."""
    pass


class ProjectAccessDenied(Exception):
    """Ни один view проектов не доступен (403 на MyProject и AllProject)."""
    pass


# McpConnectionError импортирован из mcp_config.


# ═══════════════════════════════════════════════════════════════════════════════
# НИЗКОУРОВНЕВЫЙ ДОСТУП К MCP — обёртки над mcp_config.mcp_init/mcp_call
# ═══════════════════════════════════════════════════════════════════════════════

def _mcp_init() -> str:
    """Инициализирует MCP-сессию, возвращает session-id."""
    sid, _ = mcp_init(client_name="find_project_by_code")
    return sid


def _mcp_call(sid: str, method: str, params: dict, *, timeout: int = 60) -> dict:
    """Вызов MCP-метода через tools/call (обёртка над mcp_config.mcp_call)."""
    if method != "tools/call":
        raise ValueError(
            f"_mcp_call поддерживает только tools/call, получили {method!r}"
        )
    tool_name = params["name"]
    arguments = params["arguments"]
    return mcp_call(sid, tool_name, arguments, timeout=timeout)


# ═══════════════════════════════════════════════════════════════════════════════
# ПОЛУЧЕНИЕ СПИСКА ПРОЕКТОВ
# ═══════════════════════════════════════════════════════════════════════════════

def _fetch_projects(sid: str) -> list[dict]:
    """Получает список проектов из всех доступных view.

    Стратегия:
    1. Пробуем MyProject — это «мои» проекты (где пользователь — участник).
    2. Если MyProject пуст или вернул isError — пробуем AllProject.
    3. **Собираем проекты из всех успешных view** (не возвращаем первый попавшийся,
       потому что проект может быть в AllProject, но не в MyProject — например,
       роль «Администратор» не попадает в MyProject).

    ⚠️ ВАЖНО: раннее поведение возвращало `data` первого успешного view
    без fallback. Это давало ложный ProjectNotFoundError, если проект был
    в AllProject но не в MyProject. Найдено при отладке проекта 503-152
    (Пресейл, 2026-08-06).
    """
    collected: list[dict] = []
    seen_project_ids: set = set()
    errors: list[str] = []

    for view_name in ("MyProject", "AllProject"):
        logger.debug("пробуем view %s", view_name)
        try:
            result = _mcp_call(
                sid,
                "tools/call",
                {"name": "get_view",
                 "arguments": {"entityName": "Project", "viewName": view_name}},
            )
        except McpConnectionError as e:
            logger.warning("view %s: %s", view_name, e)
            errors.append(f"{view_name}: {e}")
            continue

        # mcp_config.mcp_call возвращает {"_error": "..."} при isError=True.
        if isinstance(result, dict) and "_error" in result:
            logger.info("view %s вернул isError: %s",
                        view_name, result["_error"][:200])
            errors.append(f"{view_name}: {result['_error'][:100]}")
            continue

        # result — это уже распарсенный payload из content[0].text.
        try:
            data = result.get("data", []) if isinstance(result, dict) else None
            if data is None:
                raise KeyError("нет 'data' в payload")
            # Дедупликация по ProjectId — один проект может быть в обоих view
            added = 0
            for p in data:
                pid = p.get("ProjectId")
                if pid is not None and pid not in seen_project_ids:
                    seen_project_ids.add(pid)
                    collected.append(p)
                    added += 1
            logger.debug("view %s: добавлено %d уникальных проектов", view_name, added)
        except (KeyError, IndexError, TypeError) as e:
            logger.warning("view %s вернул неожиданный формат: %s", view_name, e)
            errors.append(f"{view_name}: {e}")
            continue

    if not collected:
        raise ProjectAccessDenied(
            "ни MyProject, ни AllProject не вернули проектов. "
            f"Ошибки: {'; '.join(errors) or 'нет данных'}. "
            "Проверьте права в ИСУП «Форсайт»."
        )

    logger.info("всего собрано %d уникальных проектов из view", len(collected))
    return collected


# ═══════════════════════════════════════════════════════════════════════════════
# ВАЛИДАЦИЯ ВВОДА
# ═══════════════════════════════════════════════════════════════════════════════

def _validate_code(code: str) -> str:
    """Валидирует формат кода проекта."""
    if not isinstance(code, str):
        raise ValueError(f"code должен быть строкой, получен {type(code).__name__}")
    normalized = code.strip()
    if not CODE_PATTERN.match(normalized):
        raise ValueError(
            f"код проекта '{code}' имеет неверный формат. "
            f"Ожидается 'NNN-NNN' (например, '504-595')."
        )
    return normalized


# ═══════════════════════════════════════════════════════════════════════════════
# ОСНОВНАЯ ФУНКЦИЯ ПОИСКА
# ═══════════════════════════════════════════════════════════════════════════════

def find_project_by_code(code: str, *, sid: Optional[str] = None) -> dict:
    """Ищет проект по строковому коду (Code)."""
    code = _validate_code(code)

    own_session = sid is None
    if own_session:
        sid = _mcp_init()

    try:
        projects = _fetch_projects(sid)

        matches = [
            p for p in projects
            if str(p.get("Code") or "").strip() == code
        ]

        if not matches:
            raise ProjectNotFoundError(
                f"такой код проекта '{code}' не существует либо не доступен"
            )

        if len(matches) > 1:
            logger.warning(
                "найдено %d проектов с Code=%s; берём первый (ProjectId=%s)",
                len(matches), code, matches[0].get("ProjectId"),
            )

        return matches[0]
    finally:
        if own_session:
            pass


def find_project_by_code_safe(code: str) -> Optional[dict]:
    """Безопасная обёртка: вместо исключений возвращает None или dict."""
    try:
        return find_project_by_code(code)
    except ProjectNotFoundError as e:
        logger.info("ProjectNotFoundError: %s", e)
        return None
    except ProjectAccessDenied as e:
        logger.error("ProjectAccessDenied: %s", e)
        return None
    except McpConnectionError as e:
        logger.error("McpConnectionError: %s", e)
        return None
    except ValueError as e:
        logger.warning("ValueError (неверный формат): %s", e)
        return None


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if len(sys.argv) != 2:
        print("Использование: python find_project_by_code.py <code>")
        print("Пример:        python find_project_by_code.py 504-595")
        sys.exit(1)

    user_code = sys.argv[1]
    print(f"\nИщем проект с Code='{user_code}'…\n")

    try:
        project = find_project_by_code(user_code)
        print("✅ Проект найден:")
        print(f"   Code:      {project.get('Code')}")
        print(f"   Name:      {project.get('Name')}")
        print(f"   ProjectId: {project.get('ProjectId')}")
        print(f"   Status:    {project.get('IndicatorTitle', '—')}")
    except ValueError as e:
        print(f"❌ Ошибка формата: {e}")
        sys.exit(2)
    except ProjectNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(3)
    except ProjectAccessDenied as e:
        print(f"🔒 {e}")
        sys.exit(4)
    except McpConnectionError as e:
        print(f"🔌 {e}")
        sys.exit(5)
