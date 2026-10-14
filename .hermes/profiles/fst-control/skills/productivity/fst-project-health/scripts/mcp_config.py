"""
mcp_config.py — централизованные настройки и утилиты для подключения к MCP
серверу Форсайт (PMForesight).

Используется всеми скриптами скилла fst-project-health, которые ходят в
MCP напрямую через requests/urllib (мимо Hermes-обёртки):

- find_project_by_code.py
- build_report_header.py
- mcp_probe.py

Импортируется как обычный Python-модуль (имя файла валидное, без дефисов):

    from mcp_config import (
        MCP_URL,
        META_TIME_KEYS,
        ENV_FILE,
        require_token,
        load_token_from_env_file,
        headers_for_call,
        parse_sse_response,
    )

⚠️ Не путать с `metadata.hermes` в SKILL.md — это **конфигурация Hermes**, а
`mcp_config` — это **настройки Python-скриптов**, которые могут вызываться
вне Hermes (через /tmp/script.py, cron, отладка).

Pitfalls реализованы здесь как единая точка истины:
- #2 UTF-8: `parse_sse_response()` форсирует encoding="utf-8"
- #3 SSE: `parse_sse_response()` читает полное тело, не stream+iter_lines
- #7 Lazy token: `require_token()` падает только при реальном вызове,
  а не при импорте модуля
"""

from __future__ import annotations

__version__ = "1.0.19"
import json
import os
import re
from pathlib import Path
from typing import Optional

import requests


# ═══════════════════════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════════════════════════

# URL MCP-сервера Форсайт. Если переходите на другой инстанс (prod, dev, ...) —
# править ТОЛЬКО здесь, остальные скрипты подхватят через импорт.
MCP_URL: str = "https://ppreplica.hera.pmpractice.ru/mcp"

# Имя сущности MetaModel — ВНИМАНИЕ: сервер принимает lowercase "metamodel",
# НЕ "MetaModel" с CamelCase. Исторически скилл использовал "MetaModel",
# но на проде (2026-08-07) это даёт 400 Bad Request или "Запись не найдена".
# См. references/metamodel-endpoint.md.
METAMODEL_ENTITY: str = "metamodel"

# Известные ключи MetaModel, через которые Форсайт отдаёт метаданные.
# Полный список на 2026-08-07: ["Title", "Version", "CoreVersion"].
# Серверного времени в MetaModel **нет** — нужно брать datetime.now() локально.
METAMODEL_KEYS: dict[str, str] = {
    "title": "Title",           # → "Копия прода для MCP" (титул ИС)
    "version": "Version",       # → "Core latest 2022.11.18.1534"
    "core_version": "CoreVersion",  # → "2026.8.7.1548"
}

# ProjectResourcePlan — главное открытое view для трудозатрат.
# AccessForAll=true (открыт для всех), в отличие от ResourcePlanning и
# ResourcePlanningKp (403 для обычного пользователя). Содержит username,
# specialization, activity_name+id, planning_date, plan/forecast/fact_hours.
# Решает проблему 1.2 из "Вопросы по MCP 2026_08_07.md". Live-probe 2026-08-07.
PROJECT_RESOURCE_PLAN_VIEW: str = "ProjectResourcePlan"

# ⚠️ ИСПРАВЛЕНО (2026-09-01): переход с ?ProjectId=<id> в URL на стандартный
# параметр filters={...} в get_view. Работает для всех view, не ломается
# при изменениях сервера. Используйте через get_view_with_filters().
# Live-probe 2026-09-01: filters={ProjectId: 4595} → 1 строка за 1.4 сек.
#
# Параметр filters передаётся как JSON-объект с условиями фильтрации.
# Каждый атрибут отправляется на бэкенд отдельным полем верхнего уровня.
# Документация: tools/get_view из tools/list

def get_view_with_filters(sid, entity_name: str, view_name: str,
                          filters: dict | None = None,
                          limit: int | None = 100,
                          offset: int | None = None) -> dict:
    """Универсальный вызов get_view с правильным форматом filters.

    Args:
        sid: MCP session ID
        entity_name: имя сущности (например 'Project', 'Point', 'InContract')
        view_name: имя view (например 'ProjectHealthCostMy')
        filters: dict с фильтрами (например {'ProjectId': 4595})
        limit: максимум строк
        offset: смещение

    Returns:
        dict ответа от MCP
    """
    args = {
        "entityName": entity_name,
        "viewName": view_name,
        "filters": filters or {},
        "limit": limit,
    }
    if offset is not None:
        args["offset"] = offset
    return mcp_call(sid, "get_view", args)

# Базовые имена view (без URL-параметров)
PROJECT_HEALTH_COST_MY_VIEW: str = "ProjectHealthCostMy"
PROJECT_RESOURCE_PLAN_VIEW: str = "ProjectResourcePlan"
ALL_MY_POINT_VIEW: str = "AllMyPoint"
PROJECT_BUDGET_VIEW: str = "ProjectBudgetCompleteBusiness"
IN_CONTRACT_MY_PROJECT_VIEW: str = "InContractMyProject"

# Helpers для фильтров (новый стиль, рекомендуемый)
PROJECT_HEALTH_COST_MY_FILTERS = lambda project_id: {"ProjectId": project_id}
PROJECT_RESOURCE_PLAN_FILTERS = lambda project_id: {"ProjectId": project_id}
ALL_MY_POINT_FILTERS = lambda project_id: {"ProjectId": project_id}
PROJECT_BUDGET_FILTERS = lambda project_id: {"ProjectId": project_id}
IN_CONTRACT_MY_PROJECT_FILTERS = lambda project_id: {"ProjectId": project_id}

# DEPRECATED (удалено 2026-09-01): старые лямбды для формата `?<Field>=<id>` в URL.
# Если найдёте код, который их использует — замените на *_FILTERS(pid) и фильтр в get_view.
# Старые форматы больше не используются — поддержка прекращена.

# ⚠️ DEPRECATED: META_TIME_KEYS — оставлено для обратной совместимости.
# НИ ОДНОГО из этих ключей в MetaModel не существует (проверено 2026-08-07).
# Серверного времени в MetaModel нет. Время берётся через datetime.now().
# См. references/metamodel-endpoint.md.
META_TIME_KEYS: tuple[str, ...] = (
    "CurrentDateTime",
    "SystemDate",
    "ServerTime",
    "Now",
)

# Пути к .env-файлам (приоритет поиска от первого к последнему).
# Скилл portable: работает и в Hermes-профиле fst-control, и автономно
# в произвольном каталоге (если рядом со скиллом есть .env).
ENV_FILE_CANDIDATES: list[Path] = [
    # 1. Каталог скилла (для переноса на другой сервер)
    Path(__file__).resolve().parent.parent / ".env",
    # 2. Стандартный профиль Hermes fst-control
    Path.home() / ".hermes/profiles/fst-control/.env",
]
# Обратная совместимость: ENV_FILE = первый кандидат (для тестов/старого кода)
ENV_FILE: Path = ENV_FILE_CANDIDATES[0]

# Дефолтные таймауты HTTP-запросов к MCP (секунды).
TIMEOUT_INITIALIZE: int = 30
TIMEOUT_TOOLS_CALL: int = 60


# ═══════════════════════════════════════════════════════════════════════════════
# ЗАГРУЗКА ТОКЕНА
# ═══════════════════════════════════════════════════════════════════════════════

# Регулярка для парсинга .env-файла: PMP_TOKEN=<значение>, возможно в кавычках.
_ENV_TOKEN_RE = re.compile(r"^\s*PMP_TOKEN\s*=\s*(['\"]?)(.+?)\1\s*$", re.MULTILINE)


def require_token() -> str:
    """Ленивая проверка PMP_TOKEN — только когда реально нужна сессия.

    Pitfall #7: проверка на импорте ломает IDE/REPL — нельзя открыть модуль
    без секрета в окружении. Поэтому читаем env при первом вызове, а не на
    уровне модуля.

    Returns:
        str — токен из os.environ["PMP_TOKEN"].

    Raises:
        RuntimeError — если переменная не задана.
    """
    token = os.environ.get("PMP_TOKEN")
    if not token:
        raise RuntimeError(
            "PMP_TOKEN не задан в переменных окружения. "
            "Проверьте ~/.hermes/profiles/fst-control/.env"
        )
    return token


def get_current_user_from_token(token: Optional[str] = None) -> str:
    """Достаёт displayname пользователя из JWT-токена (PMP_TOKEN).

    Токен — JWT в формате header.payload.signature. Извлекаем payload,
    декодируем base64url → dict, ищем displayname или givenname.

    Args:
        token: (опц.) токен; если None — берётся из env.

    Returns:
        str — displayname (ФИО) пользователя, от имени которого строится отчёт.
        Если токен не JWT или не содержит нужных полей — "—".
    """
    import base64
    import json as _json

    if token is None:
        try:
            token = require_token()
        except RuntimeError:
            return "—"

    try:
        parts = token.split(".")
        if len(parts) < 2:
            return "—"
        payload_b64 = parts[1]
        # base64url без padding
        padding = "=" * (-len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode(payload_b64 + padding)
        payload = _json.loads(payload_json)
        # Приоритет: displayname > givenname (claim name)
        name = payload.get("displayname") or payload.get(
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname"
        ) or "—"
        return name
    except Exception:
        return "—"


def load_token_from_env_file(env_path: Path = None) -> Optional[str]:
    """Читает PMP_TOKEN из .env файла (для случаев когда env-переменная не задана).

    Используется `mcp_probe.py` (CLI-утилита), который может запускаться
    вне shell-сессии с экспортированными переменными. Для обычных
    Python-скриптов предпочтительнее `require_token()` — переменная
    окружения всегда доступна внутри Hermes / cron / systemd.

    Поиск токена (приоритет):
      1. Конкретный env_path (если передан)
      2. ENV_FILE_CANDIDATES[0] — .env в каталоге скилла
      3. ENV_FILE_CANDIDATES[1] — .env в профиле Hermes

    Args:
        env_path: явный путь к .env файлу. Если None — перебираются все кандидаты.

    Returns:
        Optional[str] — токен или None, если не найден / placeholder.
    """
    candidates = [env_path] if env_path else ENV_FILE_CANDIDATES
    for path in candidates:
        if not path or not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        m = _ENV_TOKEN_RE.search(text)
        if not m:
            continue
        token = m.group(2).strip()
        if token and not token.startswith("PASTE"):
            return token
    return None


def resolve_token(cli_token: Optional[str] = None) -> str:
    """Стратегия получения токена по приоритету:

    1. Явно переданный CLI-аргумент (`--token`)
    2. Переменная окружения PMP_TOKEN
    3. .env файл (fallback для CLI-утилит)

    Args:
        cli_token: значение из CLI-аргумента (если есть).

    Returns:
        str — токен.

    Raises:
        RuntimeError — если токен не найден ни в одном источнике.
    """
    if cli_token:
        return cli_token
    env_token = os.environ.get("PMP_TOKEN")
    if env_token:
        return env_token
    file_token = load_token_from_env_file()
    if file_token:
        return file_token
    raise RuntimeError(
        "PMP_TOKEN не найден: задайте переменную окружения, "
        "укажите --token, или создайте ~/.hermes/profiles/fst-control/.env"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ЗАГОЛОВКИ HTTP
# ═══════════════════════════════════════════════════════════════════════════════

def headers_for_call(token: str, *, session_id: Optional[str] = None) -> dict[str, str]:
    """Стандартные заголовки для HTTP-запросов к MCP.

    ⚠️ ВАЖНО: Content-Type "application/json, text/event-stream" обязателен
    по MCP-протоколу — иначе сервер вернёт 406 Not Acceptable.

    Args:
        token: Bearer-токен.
        session_id: (опц.) mcp-session-id для последующих вызовов после initialize.

    Returns:
        dict[str, str] — заголовки для requests.post.
    """
    h = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    if session_id:
        h["mcp-session-id"] = session_id
    return h


# ═══════════════════════════════════════════════════════════════════════════════
# ПАРСИНГ SSE-ОТВЕТА
# ═══════════════════════════════════════════════════════════════════════════════

class McpConnectionError(Exception):
    """Сетевая ошибка или некорректный ответ MCP-сервера."""
    pass


def parse_sse_response(resp: requests.Response, *, context: str = "MCP") -> dict:
    """Парсит SSE-ответ от MCP, возвращает JSON-RPC envelope.

    Реализует сразу три pitfalls:
    - #2 UTF-8: `resp.encoding = "utf-8"` (Форсайт-MCP не отдаёт charset,
      requests по умолчанию ставит ISO-8859-1, кириллица ломает JSON).
    - #3 SSE: читаем **полностью** тело ответа, не stream+iter_lines
      (на больших view iter_lines может обрезать данные на границе chunked).
    - Двойное кодирование: result.content[0].text — JSON-строка внутри JSON,
      парсим одним json.loads().

    Args:
        resp: requests.Response от MCP-сервера.
        context: имя метода/инструмента для диагностики.

    Returns:
        dict — JSON-RPC envelope `{"jsonrpc": "2.0", "id": ..., "result": {...}}`.

    Raises:
        McpConnectionError: при сетевых проблемах, невалидном JSON,
        отсутствии data-строки в SSE-ответе.
    """
    # Pitfall #2: форсируем UTF-8
    resp.encoding = "utf-8"

    for line in resp.text.splitlines():
        if line.startswith("data: "):
            try:
                return json.loads(line[6:])
            except json.JSONDecodeError as e:
                raise McpConnectionError(
                    f"{context}: невалидный JSON в SSE-ответе: {e}"
                ) from e

    raise McpConnectionError(
        f"{context}: нет data-строки в SSE-ответе: {resp.text[:200]}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ВЫСОКОУРОВНЕВЫЕ ВЫЗОВЫ
# ═══════════════════════════════════════════════════════════════════════════════

def mcp_init(*, token: Optional[str] = None, client_name: str = "fst-pmpractice-skill") -> tuple[str, dict]:
    """MCP handshake: initialize → notifications/initialized.

    Args:
        token: (опц.) токен; если None — берётся из env.
        client_name: имя клиента в serverInfo.

    Returns:
        tuple[str, dict]: (mcp-session-id, serverInfo из result).
    """
    if token is None:
        token = require_token()

    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": client_name, "version": "1.0"},
        },
    }
    resp = requests.post(
        MCP_URL,
        json=init_payload,
        headers=headers_for_call(token),
        timeout=TIMEOUT_INITIALIZE,
    )
    resp.raise_for_status()
    sid = resp.headers.get("mcp-session-id")
    if not sid:
        raise McpConnectionError(
            f"сервер не вернул mcp-session-id. headers={dict(resp.headers)}"
        )

    envelope = parse_sse_response(resp, context="initialize")
    server_info = envelope.get("result", {}).get("serverInfo", {})

    # notifications/initialized (best-effort, без ответа)
    try:
        requests.post(
            MCP_URL,
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            headers=headers_for_call(token, session_id=sid),
            timeout=10,
        )
    except requests.RequestException:
        pass  # best-effort

    return sid, server_info


def mcp_call(
    sid: str,
    tool_name: str,
    arguments: dict,
    *,
    token: Optional[str] = None,
    timeout: int = TIMEOUT_TOOLS_CALL,
) -> dict:
    """Вызов MCP-инструмента (tools/call).

    Args:
        sid: mcp-session-id от mcp_init().
        tool_name: имя инструмента (get_view, get_entity_data, ...).
        arguments: аргументы инструмента.
        token: (опц.) токен; если None — берётся из env.
        timeout: таймаут HTTP-запроса в секундах.

    Returns:
        dict — распарсенный JSON из result.content[0].text,
        или `{"_error": "<text>"}` если сервер вернул isError.

    Raises:
        McpConnectionError: при сетевых проблемах.
    """
    if token is None:
        token = require_token()

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    resp = requests.post(
        MCP_URL,
        json=payload,
        headers=headers_for_call(token, session_id=sid),
        timeout=timeout,
    )
    resp.raise_for_status()
    envelope = parse_sse_response(resp, context=tool_name)
    result = envelope.get("result", {})
    if result.get("isError"):
        return {"_error": result["content"][0]["text"]}
    # Двойное кодирование: text — это JSON-строка
    return json.loads(result["content"][0]["text"])


def get_project_property(sid, project_id: int, property_name: str):
    """Получает значение конкретного свойства проекта через get_entity_data.

    Используется для свойств которые не выводятся в views (например PresaleLimit,
    PresaleBudgetPercentage, DirectProjectCostsGrade).

    Args:
        sid: session ID
        project_id: ID проекта (int)
        property_name: имя свойства (например 'PresaleLimit')

    Returns:
        Значение свойства или None если не найдено.
    """
    r = mcp_call(sid, "get_entity_data", {
        "entityName": "Project",
        "data_id": str(project_id),
    })
    if isinstance(r, dict) and "properties" in r:
        prop = r["properties"].get(property_name, {})
        if isinstance(prop, dict):
            return prop.get("value")
    return None


def get_project_card(sid, project_id: int, project_code: str = None) -> dict:
    """Получает полную карточку проекта через get_entity_data.

    Возвращает словарь со всеми свойствами проекта. Кеширует результат.
    Используется для оптимизации — один вызов вместо множества запросов
    к ProjectParameter view.

    Args:
        sid: session ID
        project_id: ID проекта (int)
        project_code: код проекта (для имени кеша)

    Returns:
        Словарь свойств проекта (ключи - имена полей).
        Возвращает dict с базовыми ключами даже при ошибке.
    """
    # Кеш на 5 минут
    import os
    cache_dir = "/tmp"
    code_part = project_code or str(project_id)
    cache_file = os.path.join(cache_dir, f".cache_project_card_{code_part}.json")

    import time
    if os.path.exists(cache_file):
        age = time.time() - os.path.getmtime(cache_file)
        if age < 300:  # 5 мин
            import json
            try:
                with open(cache_file) as f:
                    return json.load(f)
            except Exception:
                pass

    r = mcp_call(sid, "get_entity_data", {
        "entityName": "Project",
        "data_id": str(project_id),
    })

    result = {}
    if isinstance(r, dict) and "properties" in r:
        for key, prop in r["properties"].items():
            if isinstance(prop, dict):
                result[key] = prop.get("value")

    # Кешируем
    try:
        import json
        with open(cache_file, "w") as f:
            json.dump(result, f)
    except Exception:
        pass

    return result
