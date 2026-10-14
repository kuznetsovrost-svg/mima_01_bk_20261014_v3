"""
mcp_config.py — переиспользуемый модуль для Python-скриптов, которые ходят
в MCP-сервер напрямую через requests (минуя Hermes-обёртку).

Когда использовать:
- Пишешь Python-скрипт, который должен вызвать mcp__<server>__<tool> без
  прохождения через Hermes-MCP-клиент.
- Нужна централизованная обработка pitfalls #2 (UTF-8), #3 (SSE),
  #7 (lazy token check) — все реализованы здесь в одном месте.
- Несколько скриптов ходят в один и тот же MCP-сервер — выносишь
  конфиг сюда, не дублируешь.

Использование:
    from mcp_config import mcp_init, mcp_call, parse_sse_response

    sid, server_info = mcp_init(client_name="my-script")
    data = mcp_call(sid, "get_view", {"entityName": "Project", "viewName": "MyProject"})

⚠️ Параметры ниже (URL, ENV_FILE, META_TIME_KEYS, таймауты) — заменить
под свой MCP-сервер. Токен-переменная (PMP_TOKEN) тоже зависит от сервера.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ — ЗАМЕНИ ПОД СВОЙ MCP-СЕРВЕР
# ═══════════════════════════════════════════════════════════════════════════════

# URL MCP-сервера. Если переходите на другой инстанс (prod, dev, ...) —
# править ТОЛЬКО здесь, остальные скрипты подхватят через импорт.
MCP_URL: str = "https://ppreplica.hera.pmpractice.ru/mcp"

# Имя переменной окружения с токеном (например, MYAPP_TOKEN).
# При первом вызове require_token() проверит os.environ[TOKEN_ENV_VAR].
TOKEN_ENV_VAR: str = "PMP_TOKEN"

# Ключи MetaModel-аналога для серверного времени.
# Пробуем по очереди. Если ни один не сработает — fallback на локальное.
META_TIME_KEYS: tuple[str, ...] = (
    "CurrentDateTime",
    "SystemDate",
    "ServerTime",
    "Now",
)

# Путь к .env профиля. Используется как fallback для CLI-утилит, которые
# могут запускаться вне shell-сессии с экспортированными переменными.
ENV_FILE: Path = Path.home() / ".hermes/profiles/fst-control/.env"

# Дефолтные таймауты HTTP-запросов к MCP (секунды).
TIMEOUT_INITIALIZE: int = 30
TIMEOUT_TOOLS_CALL: int = 60


# ═══════════════════════════════════════════════════════════════════════════════
# ЗАГРУЗКА ТОКЕНА (pitfall #7: lazy check)
# ═══════════════════════════════════════════════════════════════════════════════

# Регулярка для парсинга .env-файла: <NAME>=<value>, возможно в кавычках.
_ENV_TOKEN_RE = re.compile(r"^\s*[A-Z_][A-Z0-9_]*\s*=\s*(['\"]?)(.+?)\1\s*$", re.MULTILINE)


def require_token(env_var: str = TOKEN_ENV_VAR) -> str:
    """Ленивая проверка токена — только когда реально нужна сессия.

    Pitfall #7: проверка на импорте ломает IDE/REPL — нельзя открыть модуль
    без секрета в окружении. Поэтому читаем env при первом вызове, а не
    на уровне модуля.

    Args:
        env_var: имя переменной окружения. По умолчанию TOKEN_ENV_VAR.

    Returns:
        str — токен.

    Raises:
        RuntimeError: если переменная не задана.
    """
    token = os.environ.get(env_var)
    if not token:
        raise RuntimeError(
            f"{env_var} не задан в переменных окружения. "
            f"Проверьте {ENV_FILE} или `export {env_var}=...`"
        )
    return token


def load_token_from_env_file(
    var_name: str = TOKEN_ENV_VAR,
    env_path: Path = ENV_FILE,
) -> Optional[str]:
    """Читает <var_name>=<value> из .env файла.

    Используется CLI-утилитами (например, mcp_probe.py), которые могут
    запускаться вне shell-сессии с экспортированными переменными. Для
    обычных скриптов предпочтительнее require_token() — переменная
    окружения всегда доступна внутри Hermes / cron / systemd.

    Args:
        var_name: имя переменной.
        env_path: путь к .env файлу.

    Returns:
        Optional[str] — токен или None, если не найден / placeholder.
    """
    if not env_path.exists():
        return None
    text = env_path.read_text(encoding="utf-8")
    # Ищем конкретно var_name (а не любую первую строку)
    pattern = re.compile(rf"^\s*{re.escape(var_name)}\s*=\s*(['\"]?)(.+?)\1\s*$", re.MULTILINE)
    m = pattern.search(text)
    if not m:
        return None
    token = m.group(2).strip()
    if not token or token.startswith("PASTE"):
        return None
    return token


def resolve_token(cli_token: Optional[str] = None, env_var: str = TOKEN_ENV_VAR) -> str:
    """Стратегия получения токена по приоритету:

    1. Явно переданный CLI-аргумент (--token)
    2. Переменная окружения TOKEN_ENV_VAR
    3. .env файл (fallback для CLI-утилит)

    Args:
        cli_token: значение из CLI-аргумента (если есть).
        env_var: имя переменной окружения.

    Returns:
        str — токен.

    Raises:
        RuntimeError: если токен не найден ни в одном источнике.
    """
    if cli_token:
        return cli_token
    env_token = os.environ.get(env_var)
    if env_token:
        return env_token
    file_token = load_token_from_env_file(var_name=env_var)
    if file_token:
        return file_token
    raise RuntimeError(
        f"{env_var} не найден: задайте переменную окружения, "
        f"укажите --token, или создайте {ENV_FILE}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ЗАГОЛОВКИ HTTP
# ═══════════════════════════════════════════════════════════════════════════════

def headers_for_call(token: str, *, session_id: Optional[str] = None) -> dict[str, str]:
    """Стандартные заголовки для HTTP-запросов к MCP.

    ⚠️ Content-Type "application/json, text/event-stream" обязателен
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
# ПАРСИНГ SSE-ОТВЕТА (pitfalls #2, #3)
# ═══════════════════════════════════════════════════════════════════════════════

class McpConnectionError(Exception):
    """Сетевая ошибка или некорректный ответ MCP-сервера."""
    pass


def parse_sse_response(resp: requests.Response, *, context: str = "MCP") -> dict:
    """Парсит SSE-ответ от MCP, возвращает JSON-RPC envelope.

    Реализует сразу два pitfalls:
    - #2 UTF-8: resp.encoding = "utf-8" (Форсайт-MCP не отдаёт charset,
      requests по умолчанию ставит ISO-8859-1, кириллица ломает JSON).
    - #3 SSE: читаем полностью тело ответа, не stream+iter_lines
      (на больших view iter_lines может обрезать данные на границе chunked).

    Args:
        resp: requests.Response от MCP-сервера.
        context: имя метода/инструмента для диагностики.

    Returns:
        dict — JSON-RPC envelope {"jsonrpc": "2.0", "id": ..., "result": {...}}.

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

def mcp_init(*, token: Optional[str] = None, client_name: str = "mcp-client") -> tuple[str, dict]:
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
        или {"_error": "<text>"} если сервер вернул isError.

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
